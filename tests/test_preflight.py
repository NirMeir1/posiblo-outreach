from pathlib import Path

import pytest

from outreach.backup import create_backup
from outreach.config import load_config
from outreach.ledger import Ledger
from outreach.preflight import preflight_checks, run_preflight
from outreach.sendlog import SendLog


def _cfg(root: Path, **env: str):
    return load_config(root=root, environ=env)


def test_fresh_project_passes(project: Path) -> None:
    assert run_preflight(_cfg(project)) == []
    assert not _cfg(project).ledger_path.exists()  # preflight never creates the ledger


def test_existing_healthy_ledger_passes(project: Path) -> None:
    cfg = _cfg(project)
    Ledger(cfg.ledger_path).close()
    assert run_preflight(cfg) == []


def test_stop_file_fails(project: Path) -> None:
    (project / "STOP").write_text("")
    failures = run_preflight(_cfg(project))
    assert len(failures) == 1 and "STOP" in failures[0]
    assert run_preflight(_cfg(project), require_no_stop=False) == []


def test_refuses_when_ledger_missing_but_backup_exists(project: Path) -> None:
    cfg = _cfg(project)
    with Ledger(cfg.ledger_path) as led:
        led.claim("example.co.il", domain="example.co.il", input_url="x")
    backup = create_backup(cfg).local
    for suffix in ("", "-wal", "-shm"):
        Path(str(cfg.ledger_path) + suffix).unlink(missing_ok=True)
    failures = run_preflight(cfg)
    assert len(failures) == 1
    assert "MISSING" in failures[0] and "Refusing" in failures[0]
    assert str(backup) in failures[0] and "To restore" in failures[0]
    assert not cfg.ledger_path.exists()


def test_refuses_when_ledger_missing_but_offsite_backup_exists(project: Path, tmp_path: Path) -> None:
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    cfg = _cfg(project, OFFSITE_BACKUP_DIR=str(cloud))
    Ledger(cfg.ledger_path).close()
    create_backup(cfg)
    for p in cfg.backup_dir.iterdir():
        p.unlink()  # only the offsite copy is left
    cfg.ledger_path.unlink()
    failures = run_preflight(cfg)
    assert len(failures) == 1 and "MISSING" in failures[0]


def test_refuses_when_ledger_missing_but_send_log_exists(project: Path) -> None:
    cfg = _cfg(project)
    SendLog(cfg.send_log_path).append("claimed", site_key="example.co.il")
    failures = run_preflight(cfg)
    assert len(failures) == 1
    assert "MISSING" in failures[0] and "send log" in failures[0] and "rebuilt" in failures[0]


def test_corrupt_ledger_fails_integrity(project: Path) -> None:
    cfg = _cfg(project)
    cfg.ledger_path.parent.mkdir(parents=True)
    cfg.ledger_path.write_bytes(b"this is not a sqlite database at all" * 200)
    failures = run_preflight(cfg)
    assert len(failures) == 1 and "cannot be read as SQLite" in failures[0]


def test_damaged_ledger_pages_fail_integrity(project: Path) -> None:
    cfg = _cfg(project)
    with Ledger(cfg.ledger_path) as led:
        for i in range(300):
            led.claim(f"site{i}.co.il", domain=f"site{i}.co.il", input_url="x" * 200)
    data = bytearray(cfg.ledger_path.read_bytes())
    page = 4096
    data[page * 2: page * 2 + 64] = b"\xff" * 64  # scribble over the start of a b-tree page
    cfg.ledger_path.write_bytes(bytes(data))
    failures = run_preflight(cfg)
    assert len(failures) == 1
    assert "integrity_check" in failures[0] or "cannot be read" in failures[0]


def test_missing_template_fails(project: Path) -> None:
    (project / "templates" / "consent_request_v1.txt").unlink()
    failures = run_preflight(_cfg(project))
    assert len(failures) == 1 and "template" in failures[0]


def test_todo_sender_rejected_in_live_mode_only(project: Path) -> None:
    cfg = _cfg(project)  # SENDER_ADDRESS defaults to TODO
    assert run_preflight(cfg, live=False) == []
    live = run_preflight(cfg, live=True)
    assert len(live) == 1 and "address" in live[0]
    done = _cfg(project, SENDER_ADDRESS="רחוב הרצל 1, תל אביב")
    assert run_preflight(done, live=True) == []
    lower = _cfg(project, SENDER_ADDRESS="רחוב הרצל 1", SENDER_PHONE="todo")
    assert "phone" in run_preflight(lower, live=True)[0]


def test_checks_run_in_required_order(project: Path) -> None:
    cfg = _cfg(project)
    names = [c.name for c in preflight_checks(cfg, live=True)]
    assert names == ["stop_file", "ledger_integrity", "ledger_missing", "template", "sender_details"]
    assert [c.name for c in preflight_checks(cfg, live=False)][-1] == "template"


def test_all_failures_reported_in_order(project: Path) -> None:
    cfg = _cfg(project)
    (project / "STOP").write_text("")
    SendLog(cfg.send_log_path).append("claimed", site_key="x.co.il")
    (project / "templates" / "consent_request_v1.txt").unlink()
    failures = run_preflight(cfg, live=True)
    assert len(failures) == 4
    assert "STOP" in failures[0]
    assert "MISSING" in failures[1]
    assert "template" in failures[2]
    assert "sender details" in failures[3]
