import hashlib
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO
from outreach import dashboard
from outreach.cli import main
from outreach.config import load_config
from outreach.dashboard import BIND_HOST, create_app, open_db, serve, snapshot
from outreach.ledger import Ledger
from outreach.runstatus import read_status, write_status

PORT = 8765
GOOD = {"Host": f"127.0.0.1:{PORT}", "Origin": f"http://127.0.0.1:{PORT}"}


def seed(cfg) -> None:
    with Ledger(cfg.ledger_path) as led:
        sites = [{"site_key": k, "domain": k, "input_url": f"https://{k}/"}
                 for k in ("a.co.il", "b.co.il", "c.co.il", "d.co.il")]
        led.create_batches([sites])
        for s in sites:
            led.add_dry_run_result("B0001", s["site_key"], "ready" if s["site_key"] != "d.co.il" else "captcha",
                                   f"https://{s['site_key']}/contact", "{}", None)
        led.finish_dry_run("B0001")
        led.approve("B0001")
        led.begin_send("B0001")
        for k, status in (("a.co.il", "sent"), ("b.co.il", "sent_unconfirmed")):
            led.claim(k, domain=k, input_url="x", batch_id="B0001", form_url=f"https://{k}/contact")
            led.finish(k, status, "seeded")
        led.claim("c.co.il", domain="c.co.il", input_url="x", batch_id="B0001", form_url="https://c.co.il/contact")
        led.add_event("info", "send B0001: sent: HTTP 200, success text 'תודה'", site_key="a.co.il")
        led.add_event("warning", "send B0001: sent_unconfirmed: HTTP 500 after POST", site_key="b.co.il")
        led.add_event("error", "send B0001 halted: circuit breaker tripped")
    write_status(cfg.log_dir, mode="send", batch_id="B0001", state="running", index=3, total=3, site_key="c.co.il",
                 breaker={"threshold": 5, "consecutive_failures": 1, "tripped": False}, halted_reason=None)


@pytest.fixture
def cfg(project: Path):
    c = load_config(root=project, environ={})
    seed(c)
    return c


@pytest.fixture
def client(cfg):
    return create_app(cfg, PORT).test_client()


def test_status_endpoint_counters_for_seeded_ledger(client) -> None:
    r = client.get("/api/status", headers={"Host": GOOD["Host"]})
    assert r.status_code == 200
    d = r.get_json()
    assert d["counters"]["sent"] == 1 and d["counters"]["sent_unconfirmed"] == 1 and d["counters"]["pending"] == 1
    assert sum(d["counters"].values()) == 3
    assert d["batch"]["batch_id"] == "B0001" and d["batch"]["state"] == "sending"
    assert (d["batch"]["done"], d["batch"]["total"], d["batch"]["percent"]) == (2, 3, 67)
    assert d["run"]["site_key"] == "c.co.il" and d["run"]["breaker"]["consecutive_failures"] == 1
    assert [p["site_key"] for p in d["pending"]] == ["c.co.il"]
    levels = [e["level"] for e in d["events"]]
    assert levels[:3] == ["error", "warning", "info"]  # newest first
    assert d["events"][1]["site_status"] == "sent_unconfirmed"
    assert d["events"][2]["message"].endswith("'תודה'")
    assert d["stop_file"] is False


def test_dashboard_connection_is_read_only(cfg) -> None:
    conn = open_db(cfg)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO events (ts, level, message) VALUES ('t', 'info', 'x')")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("UPDATE sites SET status = 'sent' WHERE site_key = 'c.co.il'")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM events")
    finally:
        conn.close()
    with Ledger(cfg.ledger_path) as led:
        assert led.get("c.co.il")["status"] == "pending"


def test_dashboard_requests_do_not_change_the_ledger(cfg, client) -> None:
    with Ledger(cfg.ledger_path):
        pass  # checkpoint, so the main file holds everything
    before = hashlib.sha256(cfg.ledger_path.read_bytes()).hexdigest()
    for _ in range(3):
        client.get("/api/status", headers={"Host": GOOD["Host"]})
        client.get("/", headers={"Host": GOOD["Host"]})
    assert hashlib.sha256(cfg.ledger_path.read_bytes()).hexdigest() == before


def test_dashboard_uses_mode_ro(monkeypatch: pytest.MonkeyPatch, cfg, client) -> None:
    uris: list[str] = []
    real = sqlite3.connect

    def spy(database, *a, **k):
        uris.append(str(database))
        return real(database, *a, **k)

    monkeypatch.setattr(sqlite3, "connect", spy)
    client.get("/api/status", headers={"Host": GOOD["Host"]})
    assert uris and all(u.endswith("?mode=ro") for u in uris)


def test_stop_creates_file(cfg, client) -> None:
    r = client.post("/stop", headers=GOOD)
    assert r.status_code == 200 and cfg.stop_file.exists()
    assert client.get("/api/status", headers={"Host": GOOD["Host"]}).get_json()["stop_file"] is True


@pytest.mark.parametrize("headers", [
    {"Host": GOOD["Host"], "Origin": "http://evil.example"},
    {"Host": GOOD["Host"], "Origin": "http://127.0.0.1:9999"},
    {"Host": GOOD["Host"], "Origin": "null"},
    {"Host": GOOD["Host"]},                                      # no Origin at all
    {"Host": "evil.example", "Origin": GOOD["Origin"]},          # DNS rebinding: wrong Host
    {"Host": f"127.0.0.1:{PORT}.evil.example", "Origin": GOOD["Origin"]},
])
def test_stop_rejects_bad_origin_or_host(cfg, client, headers: dict) -> None:
    r = client.post("/stop", headers=headers)
    assert r.status_code == 403
    assert not cfg.stop_file.exists()


def test_status_and_page_reject_foreign_host(client) -> None:
    assert client.get("/api/status", headers={"Host": "evil.example"}).status_code == 403
    assert client.get("/", headers={"Host": "attacker.test:8765"}).status_code == 403


def test_stop_only_via_post_and_nothing_clears_it(cfg, client) -> None:
    cfg.stop_file.write_text("")
    assert client.get("/stop", headers=GOOD).status_code == 405
    assert client.delete("/stop", headers=GOOD).status_code == 405
    rules = {r.rule: sorted(r.methods - {"HEAD", "OPTIONS"}) for r in create_app(cfg, PORT).url_map.iter_rules()
             if r.endpoint != "static"}
    assert rules == {"/": ["GET"], "/api/status": ["GET"], "/stop": ["POST"]}
    assert cfg.stop_file.exists()
    src = (REPO / "src" / "outreach" / "dashboard.py").read_text(encoding="utf-8")
    assert "unlink" not in src and "os.remove" not in src


def test_clear_stop_is_a_cli_command(cfg, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg.stop_file.write_text("")
    monkeypatch.setattr("builtins.input", lambda p="": "no")
    assert main(["clear-stop"]) == 1 and cfg.stop_file.exists()
    monkeypatch.setattr("builtins.input", lambda p="": "CLEAR")
    assert main(["clear-stop"]) == 0 and not cfg.stop_file.exists()


def test_page_is_offline_and_hebrew_ready(client) -> None:
    r = client.get("/", headers={"Host": GOOD["Host"]})
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "text/html" in r.content_type
    assert not re.search(r"(src|href)\s*=\s*[\"']?(https?:)?//", html)  # no external assets
    assert "http://" not in html and "https://" not in html
    assert 'dir="auto"' in html and ".dir = \"auto\"" in html
    assert "Noto Sans Hebrew" in html and "Arial Hebrew" in html
    assert "setInterval(poll, 2000)" in html
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]


def test_serve_binds_to_loopback_only(cfg, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}
    monkeypatch.setattr("flask.Flask.run", lambda self, **kw: seen.update(kw))
    serve(cfg, port=PORT)
    assert BIND_HOST == "127.0.0.1"
    assert seen["host"] == "127.0.0.1" and seen["port"] == PORT and seen["debug"] is False


def test_snapshot_without_ledger_creates_nothing(project: Path) -> None:
    c = load_config(root=project, environ={})
    d = snapshot(c)
    assert d["ledger_exists"] is False and d["batch"] is None
    assert not c.ledger_path.exists()


def test_run_status_write_never_raises(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("")
    assert write_status(blocker / "sub", state="running") is False  # parent is a file: cannot write
    assert write_status(tmp_path / "logs", state="running", index=1) is True
    assert read_status(tmp_path / "logs")["index"] == 1
    assert read_status(tmp_path / "missing") is None


def test_send_and_dry_run_never_import_the_dashboard() -> None:
    code = ("import sys; sys.path.insert(0, %r)\n"
            "import outreach.cli, outreach.send, outreach.dryrun\n"
            "print('flask' in sys.modules, 'outreach.dashboard' in sys.modules)") % str(REPO / "src")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "False"]


def test_dashboard_module_has_no_write_to_ledger() -> None:
    src = (REPO / "src" / "outreach" / "dashboard.py").read_text(encoding="utf-8")
    assert "Ledger(" not in src
    assert not re.search(r"\b(INSERT|UPDATE|DELETE)\b", src)
    assert dashboard.open_db.__doc__ and "mode=ro" in dashboard.open_db.__doc__
