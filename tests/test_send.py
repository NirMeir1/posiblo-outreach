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


def test_two_terminals_sending_the_same_batch_at_once(two) -> None:
    """Two concurrent `send` runs (separate ledger connections, started together): one POST per site."""
    import threading
    cfg, led, sites = two
    barrier = threading.Barrier(2)
    reports, errors = [], []

    def run() -> None:
        try:
            with Ledger(cfg.ledger_path) as mine, Fetcher(delay_seconds=0) as f:
                barrier.wait(timeout=30)
                reports.append(run_send(cfg, mine, "B0001", environ=LIVE, fetcher=f, out=lambda s: None))
        except BaseException as e:  # surface thread failures
            errors.append(e)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not errors, errors
    assert len(sites.posts("a")) == 1 and len(sites.posts("b")) == 1
    posted = [s.site_key for r in reports for s in r.sites if s.posted]
    assert sorted(posted) == [key("a"), key("b")]
    assert led.get(key("a"))["status"] == SENT and led.get(key("b"))["status"] == SENT


def test_send_refused_when_ledger_missing_but_send_log_exists(two) -> None:
    cfg, led, sites = two
    run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    led.close()
    for suffix in ("", "-wal", "-shm"):
        Path(str(cfg.ledger_path) + suffix).unlink(missing_ok=True)
    for p in cfg.backup_dir.glob("*.db"):
        p.unlink()                                   # even with no backups left, the send log blocks it
    sites.server.clear_log()
    fresh = Ledger(cfg.ledger_path.with_name("elsewhere.db"))   # any ledger object; preflight checks the real path
    with pytest.raises(SendRefused, match="MISSING"):
        run_send(cfg, fresh, "B0001", environ=LIVE, **quiet())
    fresh.close()
    assert httpserver_requests(sites) == 0
    assert not cfg.ledger_path.exists()


# --- unexpected errors after the claim (per-site guard) ----------------------

def test_exception_after_the_post_leaves_row_pending_and_run_continues(two, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led, sites = two
    real_finish = Ledger.finish

    def finish_fails_for_a(self, site_key, status, detail=None):
        if site_key == key("a"):
            raise RuntimeError("disk hiccup while finishing")
        return real_finish(self, site_key, status, detail)

    monkeypatch.setattr(Ledger, "finish", finish_fails_for_a)
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert [s.result for s in report.sites] == ["error", SENT]          # the run went on to site b
    assert report.sites[0].posted is True and "POST was attempted" in report.sites[0].detail
    assert len(sites.posts("a")) == 1 and len(sites.posts("b")) == 1    # exactly one POST each
    assert led.get(key("a"))["status"] == "pending"                     # left for manual review
    msgs = [r[0] for r in led._conn.execute("SELECT message FROM events WHERE site_key = ? AND level = 'error'",
                                             (key("a"),))]
    assert any("unexpected error after the claim" in m and "RuntimeError" in m for m in msgs)
    monkeypatch.undo()
    run_send(cfg, led, "B0001", environ=LIVE, **quiet())                 # rerun: no second POST for a
    assert len(sites.posts("a")) == 1 and led.get(key("a"))["status"] == "pending"


def test_exception_inside_verify_leaves_row_pending_and_run_continues(two, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led, sites = two
    real_verify = send_mod.verify
    calls = []

    def verify_fails_first(outcome, before_html, handler="html"):
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("parser blew up on the response")
        return real_verify(outcome, before_html, handler)

    monkeypatch.setattr(send_mod, "verify", verify_fails_first)
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert [s.result for s in report.sites] == ["error", SENT]
    assert "ValueError" in report.sites[0].detail and report.sites[0].posted is True
    assert len(sites.posts("a")) == 1 and len(sites.posts("b")) == 1
    assert led.get(key("a"))["status"] == "pending"
    events = [e["event"] for e in SendLog(cfg.send_log_path).read() if e["site_key"] == key("a")]
    assert events == ["claimed"]                                         # no result line: outcome unknown


def test_exception_after_claim_before_post_makes_no_post(two, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led, sites = two
    real_append = SendLog.append

    def append_fails_for_a(self, event, **fields):
        if event == "claimed" and fields.get("site_key") == key("a"):
            raise OSError("log disk full")
        return real_append(self, event, **fields)

    monkeypatch.setattr(SendLog, "append", append_fails_for_a)
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == "error" and report.sites[0].posted is False
    assert "no POST made" in report.sites[0].detail
    assert sites.posts("a") == [] and len(sites.posts("b")) == 1
    assert led.get(key("a"))["status"] == "pending"


def test_unexpected_errors_count_for_the_breaker(project: Path, httpserver: HTTPServer,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led, sites = prepare(project, httpserver, ["a", "b", "c"], OUTREACH_BREAKER_THRESHOLD="2")

    def always_fails(outcome, before_html):
        raise RuntimeError("boom")

    monkeypatch.setattr(send_mod, "verify", always_fails)
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert "circuit breaker" in report.halted_reason
    assert [s.result for s in report.sites] == ["error", "error"]
    assert len(sites.posts()) == 2 and sites.posts("c") == [] and led.get(key("c")) is None
    led.close()


# --- recording no-POST outcomes when a batch finishes -------------------------

def prepare_mixed(project: Path, server: HTTPServer, **env: str):
    """Batch with one ready site (a), plus sites whose dry-run gives no_form, captcha and fetch_error."""
    from conftest import fixture_html
    sites = LocalSites(server, ["a"])
    server.expect_request("/n/").respond_with_data(fixture_html("no_form.html"), content_type="text/html; charset=utf-8")
    server.expect_request("/c/").respond_with_data(fixture_html("recaptcha.html"),
                                                   content_type="text/html; charset=utf-8")
    server.expect_request("/f/").respond_with_data("gone", status=404)
    cfg = load_config(root=project, environ={"SENDER_ADDRESS": ADDRESS, "OUTREACH_HOST_DELAY_SECONDS": "0", **env})
    led = Ledger(cfg.ledger_path)
    led.create_batches([[{"site_key": key(n), "domain": "127.0.0.1", "input_url": server.url_for(f"/{n}/")}
                         for n in ("a", "n", "c", "f")]])
    with Fetcher(delay_seconds=0) as f:
        assert run_dry_run(cfg, led, "B0001", fetcher=f, out=lambda s: None).completed
    outcomes = {r["site_key"]: r["outcome"] for r in led.dry_run_results("B0001")}
    assert outcomes == {key("a"): "ready", key("n"): "no_form", key("c"): "captcha", key("f"): "fetch_error"}
    approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    server.clear_log()
    return cfg, led, sites


def test_finished_batch_records_no_post_outcomes_without_any_request(project: Path, httpserver: HTTPServer) -> None:
    cfg, led, sites = prepare_mixed(project, httpserver)
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert sorted(report.recorded) == sorted([(key("n"), "no_form"), (key("c"), "captcha")])
    assert led.get(key("a"))["status"] == SENT                     # the ready site went through send, not this path
    assert led.get(key("n"))["status"] == "no_form" and led.get(key("c"))["status"] == "captcha"
    assert led.get(key("n"))["finished_at"] and "no message sent" in led.get(key("n"))["detail"]
    assert led.get(key("f")) is None                               # fetch_error is not recorded: may work later
    paths_requested = [r.path for r, _ in httpserver.log]
    assert not any(p.startswith(("/n/", "/c/", "/f/")) for p in paths_requested)   # no request at all for them
    assert len(sites.posts()) == 1
    assert {e["site_key"] for e in SendLog(cfg.send_log_path).read()} == {key("a")}  # no send-log claims for them
    from outreach.preflight import run_preflight
    assert run_preflight(cfg, live=True) == []                     # send-log/ledger consistency still holds
    led.close()


def test_recorded_outcome_can_be_reopened_and_planned_again(project: Path, httpserver: HTTPServer,
                                                            tmp_path: Path) -> None:
    from outreach.ingest import ingest
    from outreach.reopen import reopen_site
    cfg, led, sites = prepare_mixed(project, httpserver)
    run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    csv = tmp_path / "again.csv"
    csv.write_text(f"url\nhttps://{key('n')}/\n", encoding="utf-8")
    assert ingest(csv, led, batch_size=25).handled == 1             # recorded: not planned again by itself
    assert reopen_site(led, key("n"), ask=lambda p: key("n"), out=lambda s: None) == "no_form"
    assert ingest(csv, led, batch_size=25).planned == 1             # after reopen it can be planned again
    led.close()


def test_halted_by_breaker_records_nothing(project: Path, httpserver: HTTPServer,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led, sites = prepare_mixed(project, httpserver)                  # dry-run with the default breaker
    send_cfg = load_config(root=project, environ={"SENDER_ADDRESS": ADDRESS, "OUTREACH_HOST_DELAY_SECONDS": "0",
                                                  "OUTREACH_BREAKER_THRESHOLD": "1"})
    sites.post_response["a"] = lambda req: Response("boom", status=500)   # sent_unconfirmed -> breaker trips
    report = run_send(send_cfg, led, "B0001", environ=LIVE, **quiet())
    assert "circuit breaker" in report.halted_reason
    assert report.recorded == []
    assert led.get(key("n")) is None and led.get(key("c")) is None
    led.close()


def test_ready_site_skipped_at_send_time_is_not_recorded(project: Path, httpserver: HTTPServer) -> None:
    cfg, led, sites = prepare_mixed(project, httpserver)
    sites.action["a"] = "/a/other"                                  # form changed since approval: skipped
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == "skipped"
    assert led.get(key("a")) is None                                # a ready site is never recorded
    assert dict(report.recorded) == {key("n"): "no_form", key("c"): "captcha"}
    led.close()


# --- suppression with platform-aware keys ------------------------------------

def test_suppressed_platform_account_is_not_sent(project: Path, httpserver: HTTPServer) -> None:
    sites = LocalSites(httpserver, ["a", "b"])
    cfg = load_config(root=project, environ={"SENDER_ADDRESS": ADDRESS, "OUTREACH_HOST_DELAY_SECONDS": "0"})
    led = Ledger(cfg.ledger_path)
    keys = {"a": "user.wixsite.com/shop", "b": "facebook.com/bakery"}
    led.create_batches([[{"site_key": keys[n], "domain": "127.0.0.1", "input_url": sites.url(n)} for n in "ab"]])
    with Fetcher(delay_seconds=0) as f:
        run_dry_run(cfg, led, "B0001", fetcher=f, out=lambda s: None)
    approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    led.add_suppression("domain", "https://user.wixsite.com/")      # the whole account
    led.add_suppression("domain", "https://www.facebook.com/OtherPage")  # a different facebook page
    httpserver.clear_log()
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert report.sites[0].result == "skipped" and "suppression" in report.sites[0].detail
    assert sites.posts("a") == [] and led.get(keys["a"]) is None
    assert report.sites[1].result == SENT and len(sites.posts("b")) == 1   # other page on the platform: not blocked
    led.close()


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


# --- Elementor forms (sent to the AJAX address the page states, JSON reply) --

ELEMENTOR_KEY = "elementor-site.co.il"
ELEMENTOR_AJAX = "/wp-admin/admin-ajax.php"


def prepare_elementor(project: Path, server: HTTPServer, reply):
    from conftest import fixture_html
    server.expect_request("/robots.txt").respond_with_data("User-agent: *\nAllow: /\n", content_type="text/plain")
    server.expect_request("/", method="GET").respond_with_data(fixture_html("elementor.html"),
                                                                content_type="text/html; charset=utf-8")
    server.expect_request(ELEMENTOR_AJAX, method="POST").respond_with_handler(reply)
    cfg = load_config(root=project, environ={"SENDER_ADDRESS": ADDRESS, "OUTREACH_HOST_DELAY_SECONDS": "0"})
    led = Ledger(cfg.ledger_path)
    led.create_batches([[{"site_key": ELEMENTOR_KEY, "domain": "127.0.0.1", "input_url": server.url_for("/")}]])
    with Fetcher(delay_seconds=0) as f:
        report = run_dry_run(cfg, led, "B0001", fetcher=f, out=lambda s: None)
    assert [o.outcome for o in report.outcomes] == ["ready"], report.outcomes
    approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    server.clear_log()
    return cfg, led


def posts(server: HTTPServer) -> list[Request]:
    return [r for r, _ in server.log if r.method == "POST"]


def json_reply(body: str):
    return lambda req: Response(body, content_type="application/json; charset=UTF-8")


def test_elementor_form_is_posted_once_to_its_ajax_address(project: Path, httpserver: HTTPServer) -> None:
    cfg, led = prepare_elementor(project, httpserver, json_reply('{"success":true,"data":{"message":"ok"}}'))
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert [s.result for s in report.sites] == [SENT]
    sent = posts(httpserver)
    assert len(sent) == 1 and sent[0].path == ELEMENTOR_AJAX     # never a POST to the page itself
    req = sent[0]
    assert req.mimetype == "multipart/form-data"
    assert req.headers["X-Requested-With"] == "XMLHttpRequest"
    form = req.form
    assert form["action"] == "elementor_pro_forms_send_form"
    assert form["referrer"] == httpserver.url_for("/")
    assert form["post_id"] == "123" and form["form_id"] == "4f1a2b3"
    assert form["form_fields[name]"] == cfg.sender_name and form["form_fields[email]"] == cfg.sender_email
    assert form["form_fields[message]"] == render_message(cfg)
    assert led.get(ELEMENTOR_KEY)["status"] == SENT
    led.close()


@pytest.mark.parametrize("body", [
    '{"success":false,"data":{"message":"Your submission failed because of an error."}}',
    "0",                                   # WordPress: no handler registered for this action
    "<html><body>תודה</body></html>",      # an HTML page, even with a success word, is not Elementor's reply
])
def test_elementor_without_success_true_is_unconfirmed_and_never_resent(project: Path, httpserver: HTTPServer,
                                                                        body: str) -> None:
    cfg, led = prepare_elementor(project, httpserver, json_reply(body))
    report = run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert [s.result for s in report.sites] == [SENT_UNCONFIRMED]
    run_send(cfg, led, "B0001", environ=LIVE, **quiet())
    assert len(posts(httpserver)) == 1
    assert led.get(ELEMENTOR_KEY)["status"] == SENT_UNCONFIRMED
    led.close()


@pytest.mark.parametrize(("outcome", "status"), [
    (PostOutcome(200, None, '{"success":true,"data":{}}'), SENT),
    (PostOutcome(200, None, '{"success":"true"}'), SENT_UNCONFIRMED),
    (PostOutcome(200, None, '{"success":false,"data":{"message":"x"}}'), SENT_UNCONFIRMED),
    (PostOutcome(200, None, "[]"), SENT_UNCONFIRMED),
    (PostOutcome(400, None, "0"), SENT_UNCONFIRMED),
    (PostOutcome(302, "/thank-you", ""), SENT_UNCONFIRMED),
    (PostOutcome(500, None, '{"success":true}'), SENT_UNCONFIRMED),
    (PostOutcome(error="ReadTimeout"), SENT_UNCONFIRMED),
])
def test_verify_elementor_rules(outcome: PostOutcome, status: str) -> None:
    assert verify(outcome, "<form>contact</form>", "elementor")[0] == status


def test_plan_approved_before_the_elementor_change_is_not_sent() -> None:
    from bs4 import BeautifulSoup
    from conftest import fixture_html
    from outreach.classify import build_plan
    from outreach.finder import choose_form
    page = "https://www.example.co.il/contact/"
    fresh = build_plan(choose_form(BeautifulSoup(fixture_html("elementor.html"), "lxml"))[0], page).plan
    old = fresh.to_dict()
    del old["handler"]
    old.update(action_url=page, encoding="application/x-www-form-urlencoded")
    assert {"handler", "action_url", "encoding"} <= set(send_mod.plan_differences(fresh, old))
