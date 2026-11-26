import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FIXTURES, REPO
from outreach.cli import main
from outreach.ledger import Ledger, open_readonly

SAMPLE = FIXTURES / "sample_sites.csv"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_help_lists_commands() -> None:
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    proc = subprocess.run([sys.executable, "-m", "outreach", "--help"], capture_output=True, text=True,
                          encoding="utf-8", env=env, cwd=REPO, timeout=60)
    assert proc.returncode == 0, proc.stderr
    for cmd in ("ingest", "status", "backup", "suppress"):
        assert cmd in proc.stdout


def test_ingest_then_status(project: Path, capsys: pytest.CaptureFixture) -> None:
    before = _sha(SAMPLE)
    assert main(["ingest", str(SAMPLE)]) == 0
    out = capsys.readouterr().out
    # fresh ledger: the "handled" and "suppressed" rows of the sample are ordinary sites here
    assert "planned now:        11 site(s) in 1 batch(es): B0001" in out
    assert "(not modified)" in out
    assert _sha(SAMPLE) == before
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "B0001  planned" in out and "size=11" in out


def test_status_without_ledger_creates_nothing(project: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["status"]) == 0
    assert "no ledger yet" in capsys.readouterr().out
    assert not (project / "data" / "ledger.db").exists()


def test_status_does_not_modify_ledger(project: Path) -> None:
    main(["ingest", str(SAMPLE)])
    db = project / "data" / "ledger.db"
    with Ledger(db):  # checkpoint & close cleanly
        pass
    before = _sha(db)
    assert main(["status"]) == 0
    assert _sha(db) == before


def test_ingest_refused_when_ledger_missing_but_backup_exists(project: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["ingest", str(SAMPLE)]) == 0
    assert main(["backup"]) == 0
    capsys.readouterr()
    for suffix in ("", "-wal", "-shm"):
        Path(str(project / "data" / "ledger.db") + suffix).unlink(missing_ok=True)
    assert main(["ingest", str(SAMPLE)]) == 1
    assert "MISSING" in capsys.readouterr().err
    assert not (project / "data" / "ledger.db").exists()


def test_ingest_refused_by_stop_file(project: Path, capsys: pytest.CaptureFixture) -> None:
    (project / "STOP").write_text("")
    assert main(["ingest", str(SAMPLE)]) == 1
    assert "STOP" in capsys.readouterr().err


def test_backup_command(project: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["backup"]) == 1  # no ledger yet
    assert "BACKUP FAILED" in capsys.readouterr().err
    main(["ingest", str(SAMPLE)])
    assert main(["backup"]) == 0
    assert "backup written:" in capsys.readouterr().out
    assert len(list((project / "backups").glob("ledger-*.db"))) == 1


def test_suppress_add_then_ingest_skips_it(project: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["suppress", "add", "domain", "https://www.lawyer-example.co.il", "--reason", "asked"]) == 0
    assert main(["suppress", "add", "domain", "lawyer-example.co.il"]) == 0
    assert "already suppressed" in capsys.readouterr().out
    assert main(["suppress", "add", "email", "a@b.co.il"]) == 0
    assert main(["suppress", "add", "phone", "052-000-0000"]) == 0
    main(["ingest", str(SAMPLE)])
    assert "suppressed:         1" in capsys.readouterr().out
    conn = open_readonly(project / "data" / "ledger.db")
    assert conn.execute("SELECT COUNT(*) FROM suppression").fetchone()[0] == 3
    conn.close()


def test_suppress_allowed_during_stop(project: Path) -> None:
    (project / "STOP").write_text("")
    assert main(["suppress", "add", "domain", "x-example.co.il"]) == 0


def test_suppress_bad_value(project: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["suppress", "add", "email", "not-an-email"]) == 2
    assert "not an email" in capsys.readouterr().err


def test_ingest_missing_csv(project: Path) -> None:
    assert main(["ingest", "nope.csv"]) == 2
