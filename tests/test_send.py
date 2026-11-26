"""Live sending against a LOCAL test server that counts POSTs.

ALLOW_LIVE is never set as an environment variable here: run_send() takes an
`environ` mapping and the tests pass {"ALLOW_LIVE": "1"} as a plain dict.
"""

import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Request, Response

from conftest import REPO
from outreach import send as send_mod
from outreach.approve import approve_batch
from outreach.cli import main
from outreach.config import load_config
from outreach.dryrun import run_dry_run
from outreach.fetch import Fetcher
from outreach.ledger import Ledger
from outreach.message import render_message
from outreach.send import (SENT, SENT_UNCONFIRMED, SUBJECT, PostOutcome, SendRefused, build_payload, live_allowed,
                           run_send, verify)
from outreach.sendlog import SendLog

LIVE = {"ALLOW_LIVE": "1"}
ADDRESS = "רחוב הדוגמה 1, תל אביב"
SUCCESS_PAGE = "<html><body><div class='ok'>תודה! ההודעה נשלחה</div></body></html>"


class LocalSites:
    """Contact pages /<name>/ with fresh hidden tokens; POST targets count every request."""

    def __init__(self, server: HTTPServer, names: list[str]):
        self.server, self.names = server, names
        self.action = {n: f"/{n}/submit" for n in names}
        self.extra_field = {n: "" for n in names}
        self.footer = ""
        self.post_response = {n: lambda req: Response(SUCCESS_PAGE, content_type="text/html; charset=utf-8")
                              for n in names}
        self.tokens = itertools.count(1)
        self.last_token: dict[str, str] = {}
        self.robots = "User-agent: *\nAllow: /\n"
        server.expect_request("/robots.txt").respond_with_handler(lambda r: Response(self.robots,
                                                                                      content_type="text/plain"))
        for n in names:
            server.expect_request(f"/{n}/", method="GET").respond_with_handler(self._page(n))
            server.expect_request(f"/{n}/submit", method="POST").respond_with_handler(
                lambda req, n=n: self.post_response[n](req))
            server.expect_request(f"/{n}/other", method="POST").respond_with_handler(
                lambda req: Response(SUCCESS_PAGE, content_type="text/html; charset=utf-8"))

    def _page(self, n: str):
        def handler(_req: Request) -> Response:
            token = f"tok-{n}-{next(self.tokens)}"
            self.last_token[n] = token
            html = f"""<html><body><h1>צור קשר</h1>
<form action="{self.action[n]}" method="post">
<input type="hidden" name="token" value="{token}">
<label for="n">שם מלא</label><input id="n" name="name" required>
<label for="e">אימייל</label><input id="e" type="email" name="email" required>
<label for="m">הודעה</label><textarea id="m" name="message" required></textarea>
<label><input type="checkbox" name="privacy" value="yes" required> אני מאשר את מדיניות הפרטיות</label>
<input type="text" name="hp_field" style="display:none">
{self.extra_field[n]}
<button type="submit">שלח</button></form>{self.footer}</body></html>"""
            return Response(html, content_type="text/html; charset=utf-8")
        return handler

    def url(self, n: str) -> str:
        return self.server.url_for(f"/{n}/")

    def posts(self, n: str | None = None) -> list[Request]:
        return [r for r, _ in self.server.log if r.method == "POST" and (n is None or r.path.startswith(f"/{n}/"))]


def key(n: str) -> str:
    return f"{n}-site.co.il"


def prepare(project: Path, server: HTTPServer, names: list[str], approve: bool = True, **env: str):
    sites = LocalSites(server, names)
    cfg = load_config(root=project, environ={"SENDER_ADDRESS": ADDRESS, "OUTREACH_HOST_DELAY_SECONDS": "0", **env})
    led = Ledger(cfg.ledger_path)
    led.create_batches([[{"site_key": key(n), "domain": "127.0.0.1", "input_url": sites.url(n)} for n in names]])
    with Fetcher(delay_seconds=0) as f:
        report = run_dry_run(cfg, led, "B0001", fetcher=f, out=lambda s: None)
    assert report.completed and all(o.outcome == "ready" for o in report.outcomes), report.outcomes
    if approve:
        approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    server.clear_log()
    return cfg, led, sites


@pytest.fixture
def two(project: Path, httpserver: HTTPServer):
    cfg, led, sites = prepare(project, httpserver, ["a", "b"])
    yield cfg, led, sites
    led.close()


def quiet(**kw):
    return dict(out=lambda s: None, **kw)


# --- the happy path ---------------------------------------------------------

def test_one_post_per_site_with_fresh_token_and_exact_message(two) -> None:
    cfg, led, sites = two
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert [s.result for s in report.sites] == [SENT, SENT]
    assert len(sites.posts("a")) == 1 and len(sites.posts("b")) == 1
    form = sites.posts("a")[0].form
    assert form["token"] == sites.last_token["a"]        # fresh token from the re-fetch, not the dry-run one
    assert form["name"] == cfg.sender_name and form["email"] == cfg.sender_email
    assert form["message"] == render_message(cfg)
    assert ADDRESS in form["message"]
    assert form["privacy"] == "yes"                       # required consent box is ticked
    assert form["hp_field"] == ""                         # honeypot sent empty
    assert led.get(key("a"))["status"] == SENT and led.get(key("a"))["message_version"] == "consent_request_v1"
    events = [(r["event"], r["site_key"]) for r in SendLog(cfg.send_log_path).read()]
    assert events == [("claimed", key("a")), ("result", key("a")), ("claimed", key("b")), ("result", key("b"))]
    assert led.get_batch("B0001")["state"] == "send_done"


def test_send_twice_gives_exactly_one_post_per_site(two) -> None:
    cfg, led, sites = two
    run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    second = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert len(sites.posts("a")) == 1 and len(sites.posts("b")) == 1
    assert [s.result for s in second.sites] == ["skipped", "skipped"]
    assert not any(s.posted for s in second.sites)


def test_claim_refused_means_no_post(two, monkeypatch: pytest.MonkeyPatch) -> None:
    """Another process claimed the site after our is_handled() check: claim() returns False, nothing is sent."""
    cfg, led, sites = two
    monkeypatch.setattr(Ledger, "is_handled", lambda self, k: False)
    other = Ledger(cfg.ledger_path)
    assert other.claim(key("a"), domain="127.0.0.1", input_url="elsewhere")
    other.close()
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == "skipped" and "claim refused" in report.sites[0].detail
    assert sites.posts("a") == []
    assert len(sites.posts("b")) == 1


# --- crashes ------------------------------------------------------------------

class SimulatedCrash(BaseException):
    pass


def test_crash_between_claim_and_post_then_rerun_sends_nothing_more(two, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led, sites = two

    def crash(*a, **k):
        raise SimulatedCrash()

    monkeypatch.setattr(send_mod, "_post_once", crash)
    with pytest.raises(SimulatedCrash):
        run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert led.get(key("a"))["status"] == "pending"          # claim was committed before the (missing) POST
    assert [r["event"] for r in SendLog(cfg.send_log_path).read()] == ["claimed"]
    assert sites.posts() == []
    monkeypatch.undo()

    run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert sites.posts("a") == []                              # pending is never retried
    assert led.get(key("a"))["status"] == "pending"
    assert len(sites.posts("b")) == 1                          # the untouched site goes out normally


def test_hard_process_crash_between_claim_and_post(project: Path, httpserver: HTTPServer) -> None:
    cfg, led, sites = prepare(project, httpserver, ["a"])
    led.close()
    code = f"""
import os, sys
sys.path.insert(0, {str(REPO / 'src')!r})
os.chdir({str(project)!r})
from outreach import send
from outreach.config import load_config
from outreach.ledger import Ledger
send._post_once = lambda *a, **k: os._exit(9)   # the process dies right before the POST
cfg = load_config(environ={{"SENDER_ADDRESS": {ADDRESS!r}, "OUTREACH_HOST_DELAY_SECONDS": "0"}})
send.run_send(cfg, Ledger(cfg.ledger_path), "B0001", environ={{"ALLOW_LIVE": "1"}}, out=lambda s: None)
"""
    env = {k: v for k, v in os.environ.items() if k != "ALLOW_LIVE"}
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120, env=env)
    assert proc.returncode == 9, proc.stderr
    with Ledger(cfg.ledger_path) as led2:
        assert led2.get(key("a"))["status"] == "pending"
        run_send(cfg, led2, "B0001", environ=LIVE, **quiet())
        assert led2.get(key("a"))["status"] == "pending"
    assert sites.posts() == []


# --- gates ----------------------------------------------------------------

@pytest.mark.parametrize("environ", [{}, {"ALLOW_LIVE": ""}, {"ALLOW_LIVE": "0"}, {"ALLOW_LIVE": "true"},
                                     {"ALLOW_LIVE": "yes"}, {"ALLOW_LIVE": " 1"}, {"ALLOW_LIVE": "1 "},
                                     {"ALLOW_LIVE": "01"}, {"allow_live": "1"}])
def test_without_allow_live_nothing_happens(two, environ: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led, sites = two
    monkeypatch.setattr(httpx.Client, "__init__", lambda *a, **k: pytest.fail("HTTP client created"))
    backups_before = len(list(cfg.backup_dir.glob("*.db"))) if cfg.backup_dir.exists() else 0
    with pytest.raises(SendRefused, match="ALLOW_LIVE"):
        run_send(cfg, led, "B0001", environ=environ, **quiet())
    assert httpserver_requests(sites) == 0
    assert led.get(key("a")) is None
    assert (len(list(cfg.backup_dir.glob("*.db"))) if cfg.backup_dir.exists() else 0) == backups_before


def httpserver_requests(sites: LocalSites) -> int:
    return len(sites.server.log)


def test_live_allowed_only_for_exactly_1() -> None:
    assert live_allowed({"ALLOW_LIVE": "1"}) is True
    for v in ("", "0", "true", "TRUE", "yes", " 1", "1\n", "2"):
        assert live_allowed({"ALLOW_LIVE": v}) is False
    assert live_allowed({}) is False


def test_cli_send_without_allow_live_makes_zero_network_calls(two, monkeypatch: pytest.MonkeyPatch,
                                                              capsys: pytest.CaptureFixture) -> None:
    cfg, led, sites = two
    assert "ALLOW_LIVE" not in os.environ
    monkeypatch.setattr(httpx.Client, "__init__", lambda *a, **k: pytest.fail("HTTP client created"))
    monkeypatch.setattr(Ledger, "__init__", lambda *a, **k: pytest.fail("ledger opened"))
    assert main(["send", "B0001"]) == 1
    assert "Live sending is disabled" in capsys.readouterr().err
    assert httpserver_requests(sites) == 0


def test_unapproved_batch_is_refused(project: Path, httpserver: HTTPServer) -> None:
    cfg, led, sites = prepare(project, httpserver, ["a"], approve=False)
    with pytest.raises(SendRefused, match="only an approved batch"):
        run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert httpserver_requests(sites) == 0
    assert led.get(key("a")) is None
    led.close()


def test_todo_sender_address_is_refused(project: Path, httpserver: HTTPServer) -> None:
    cfg, led, sites = prepare(project, httpserver, ["a"])
    todo_cfg = load_config(root=project, environ={"OUTREACH_HOST_DELAY_SECONDS": "0"})  # address stays TODO
    with pytest.raises(SendRefused, match="address"):
        run_send(todo_cfg, led, "B0001", environ=LIVE, **quiet())
    assert httpserver_requests(sites) == 0
    led.close()


def test_stop_file_refuses_before_any_network(two) -> None:
    cfg, led, sites = two
    cfg.stop_file.write_text("")
    with pytest.raises(SendRefused, match="STOP"):
        run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert httpserver_requests(sites) == 0


def test_stop_file_created_mid_run_halts(two) -> None:
    cfg, led, sites = two
    orig = sites.post_response["a"]

    def post_then_stop(req):
        cfg.stop_file.write_text("")
        return orig(req)

    sites.post_response["a"] = post_then_stop
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert "STOP" in report.halted_reason
    assert len(sites.posts("a")) == 1 and sites.posts("b") == [] and led.get(key("b")) is None
    assert led.get_batch("B0001")["state"] == "sending"


def test_failed_backup_refuses_before_any_network(project: Path, httpserver: HTTPServer) -> None:
    cfg, led, sites = prepare(project, httpserver, ["a"], OFFSITE_BACKUP_DIR=str(project / "not-mounted"))
    with pytest.raises(SendRefused, match="backup"):
        run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert httpserver_requests(sites) == 0
    led.close()


def test_backup_before_and_after(two) -> None:
    cfg, led, sites = two
    lines: list[str] = []
    report = run_send(cfg, led, "B0001", environ=LIVE, out=lines.append)
    assert sum("backup written" in l for l in lines) == 2
    assert report.backup and Path(report.backup).exists()


# --- changes since approval -------------------------------------------------

def test_changed_form_action_is_skipped_and_not_claimed(two) -> None:
    cfg, led, sites = two
    sites.action["a"] = "/a/other"
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == "skipped" and "action_url" in report.sites[0].detail
    assert sites.posts("a") == []
    assert led.get(key("a")) is None                    # unclaimed: eligible for a future batch
    assert len(sites.posts("b")) == 1
    conn_events = [e for e in SendLog(cfg.send_log_path).read() if e["site_key"] == key("a")]
    assert conn_events == []


def test_new_required_field_since_approval_is_skipped(two) -> None:
    cfg, led, sites = two
    sites.extra_field["a"] = '<label for="c">שם החברה</label><input id="c" name="company" required>'
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == "skipped" and sites.posts("a") == []


def test_robots_disallowing_the_form_target_is_skipped(two) -> None:
    cfg, led, sites = two
    sites.robots = "User-agent: *\nDisallow: /a/submit\n"
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == "skipped" and "robots" in report.sites[0].detail
    assert sites.posts("a") == [] and led.get(key("a")) is None


def test_suppressed_after_approval_is_not_sent(two) -> None:
    cfg, led, sites = two
    led.add_suppression("domain", key("a"), reason="asked")
    run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert sites.posts("a") == [] and led.get(key("a")) is None


# --- errors and verification ------------------------------------------------

def test_network_error_before_claim_leaves_site_unclaimed_with_event(two) -> None:
    cfg, led, sites = two
    sites.server.clear_all_handlers()
    sites.server.expect_request("/robots.txt").respond_with_data("User-agent: *\nAllow: /\n")
    sites.server.expect_request("/a/").respond_with_data("unavailable", status=503)
    sites.server.expect_request("/b/").respond_with_data("unavailable", status=503)
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert [s.result for s in report.sites] == ["fetch_error", "fetch_error"]
    assert sites.posts() == []
    assert led.get(key("a")) is None and led.get(key("b")) is None   # eligible for a future batch
    msgs = [r[0] for r in led._conn.execute("SELECT message FROM events WHERE site_key = ?", (key("a"),))]
    assert any("re-fetch failed" in m for m in msgs)
    assert SendLog(cfg.send_log_path).read() == []                   # nothing claimed, nothing logged as sent

def test_http_error_after_post_is_sent_unconfirmed_without_retry(two) -> None:
    cfg, led, sites = two
    sites.post_response["a"] = lambda req: Response("boom", status=500)
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == SENT_UNCONFIRMED
    assert len(sites.posts("a")) == 1
    assert led.get(key("a"))["status"] == SENT_UNCONFIRMED


def test_timeout_during_post_is_sent_unconfirmed_without_retry(two) -> None:
    cfg, led, sites = two

    def slow(req):
        time.sleep(1.5)
        return Response(SUCCESS_PAGE, content_type="text/html")

    sites.post_response["a"] = slow
    with Fetcher(delay_seconds=0, timeout=0.5) as f:
        report = run_send(cfg, led, "B0001", environ=LIVE, fetcher=f, **quiet())
    assert report.sites[0].result == SENT_UNCONFIRMED and "error during POST" in report.sites[0].detail
    time.sleep(1.2)
    assert len(sites.posts("a")) == 1
    second = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert len(sites.posts("a")) == 1 and second.sites[0].result == "skipped"


def test_breaker_trips_after_n_consecutive_failures(project: Path, httpserver: HTTPServer) -> None:
    cfg, led, sites = prepare(project, httpserver, ["a", "b", "c"], OUTREACH_BREAKER_THRESHOLD="2")
    for n in "abc":
        sites.post_response[n] = lambda req: Response("<p>שגיאה בשליחה</p>", content_type="text/html")
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert "circuit breaker" in report.halted_reason
    assert [s.result for s in report.sites] == [SENT_UNCONFIRMED, SENT_UNCONFIRMED]
    assert len(sites.posts()) == 2 and sites.posts("c") == []
    assert led.get(key("c")) is None
    led.close()


def test_success_by_redirect(two) -> None:
    cfg, led, sites = two
    sites.post_response["a"] = lambda req: Response("", status=303, headers={"Location": "/a/thank-you"})
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == SENT and "redirect" in report.sites[0].detail


def test_success_word_already_on_the_page_does_not_count(two) -> None:
    cfg, led, sites = two
    sites.footer = "<footer>תודה שבחרתם בנו</footer>"
    sites.post_response["a"] = lambda req: Response(f"<form></form><footer>תודה שבחרתם בנו</footer>",
                                                    content_type="text/html")
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == SENT_UNCONFIRMED


@pytest.mark.parametrize(("outcome", "status"), [
    (PostOutcome(200, None, "<p>Thank you, we will get back to you</p>"), SENT),
    (PostOutcome(200, None, "<p>נשלח בהצלחה</p>"), SENT),
    (PostOutcome(302, "/he/%D7%AA%D7%95%D7%93%D7%94", ""), SENT),
    (PostOutcome(302, "/success?x=1", ""), SENT),
    (PostOutcome(302, "/contact?error=1", ""), SENT_UNCONFIRMED),
    (PostOutcome(200, None, "<p>שגיאה</p>"), SENT_UNCONFIRMED),
    (PostOutcome(500, None, "thank you"), SENT_UNCONFIRMED),
    (PostOutcome(error="ReadTimeout"), SENT_UNCONFIRMED),
])
def test_verify_rules(outcome: PostOutcome, status: str) -> None:
    assert verify(outcome, "<form>contact</form>")[0] == status


def test_payload_subject_and_optional_consent(project: Path) -> None:
    from bs4 import BeautifulSoup
    from outreach.classify import build_plan
    html = ('<form method="post"><input name="first" placeholder="שם פרטי"><input name="last" placeholder="שם משפחה">'
            '<input name="subject" placeholder="נושא"><input type="email" name="email"><textarea name="msg"></textarea>'
            '<input type="checkbox" name="terms" value="1"> מסכים לתקנון</form>')
    plan = build_plan(BeautifulSoup(html, "lxml").find("form"), "https://x.co.il/").plan
    cfg = load_config(root=project, environ={"SENDER_ADDRESS": ADDRESS})
    pairs = dict(build_payload(plan, cfg, "MSG"))
    assert pairs["first"] == "ניר" and pairs["last"] == "מאיר"
    assert pairs["subject"] == SUBJECT == "פרסומת - בקשת הסכמה"
    assert pairs["msg"] == "MSG"
    assert "terms" not in pairs  # optional consent is NOT ticked


def test_only_one_post_function_and_no_retry_wrapper() -> None:
    src = (REPO / "src" / "outreach" / "send.py").read_text(encoding="utf-8")
    assert src.count('client.stream("POST"') == 1
    assert "retry" not in src.lower().replace("no retry", "").replace("never retried", "").replace(
        "not retried", "").replace("no automatic retry", "")
