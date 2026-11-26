import json
import sqlite3
from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

from conftest import FakeFetcher, fixture_html
from outreach.cli import main
from outreach.config import load_config
from outreach.dryrun import run_dry_run, start_url
from outreach.ledger import Ledger, LedgerError
from outreach.message import render_message

SITES = [
    ("a-example.co.il", "https://a-example.co.il/"),
    ("b-example.co.il", "b-example.co.il"),
    ("c-example.co.il", "https://www.c-example.co.il/about?utm_source=x#top"),
    ("d-example.co.il", "https://d-example.co.il/"),
]


def pages(**overrides: str) -> dict[str, str]:
    p = {
        "https://a-example.co.il/": fixture_html("cf7_hebrew.html"),          # ready
        "https://b-example.co.il/": fixture_html("no_form.html"),             # no_form
        "https://www.c-example.co.il/about?utm_source=x": fixture_html("recaptcha.html"),  # captcha
        # d-example.co.il: missing -> 404 -> fetch_error
    }
    p.update(overrides)
    return p


@pytest.fixture
def env(project: Path):
    cfg = load_config(root=project, environ={})
    led = Ledger(cfg.ledger_path)
    led.create_batches([[{"site_key": k, "domain": k, "input_url": u} for k, u in SITES]])
    yield cfg, led
    led.close()


def sites_rows(cfg) -> int:
    conn = sqlite3.connect(cfg.ledger_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
    finally:
        conn.close()


def test_dry_run_records_outcomes_and_sets_state(env) -> None:
    cfg, led = env
    report = run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages()), out=lambda s: None)
    assert report.completed
    got = {r["site_key"]: r["outcome"] for r in led.dry_run_results("B0001")}
    assert got == {"a-example.co.il": "ready", "b-example.co.il": "no_form", "c-example.co.il": "captcha",
                   "d-example.co.il": "fetch_error"}
    ready = next(r for r in led.dry_run_results("B0001") if r["outcome"] == "ready")
    plan = json.loads(ready["fields_json"])
    assert plan["hidden_fields"]["_wpcf7"] == "42"
    assert {f["role"] for f in plan["fields"]} >= {"name", "email", "message"}
    assert led.get_batch("B0001")["state"] == "dry_run_done"


def test_dry_run_leaves_sites_table_empty_and_never_claims(env, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, led = env

    def forbidden(*a, **k):
        raise AssertionError("dry-run must never claim or finish a site")

    monkeypatch.setattr(Ledger, "claim", forbidden)
    monkeypatch.setattr(Ledger, "finish", forbidden)
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages()), out=lambda s: None)
    assert sites_rows(cfg) == 0
    assert led.list_pending() == []


def test_rerun_replaces_previous_results(env) -> None:
    cfg, led = env
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages()), out=lambda s: None)
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages(**{"https://b-example.co.il/":
                                                                fixture_html("elementor.html")})),
                out=lambda s: None)
    rows = led.dry_run_results("B0001")
    assert len(rows) == 4  # replaced, not appended
    assert {r["site_key"]: r["outcome"] for r in rows}["b-example.co.il"] == "ready"
    assert led.get_batch("B0001")["state"] == "dry_run_done"


def test_report_shows_each_site_and_exact_message(env) -> None:
    cfg, led = env
    lines: list[str] = []
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages()), out=lines.append)
    text = "\n".join(lines)
    assert "[1/4] a-example.co.il  READY  https://a-example.co.il/" in text
    assert "message->your-message" in text and "email->your-email" in text
    assert "[2/4] b-example.co.il  NO_FORM" in text
    assert "[3/4] c-example.co.il  CAPTCHA" in text
    assert "[4/4] d-example.co.il  FETCH_ERROR" in text
    message = render_message(cfg)
    assert message in text
    assert message.startswith("פרסומת\n") and "Posiblo, TODO, 052-251-8189" in message
    assert "SENDER_ADDRESS is still TODO" in text


def test_message_uses_configured_address(project: Path) -> None:
    cfg = load_config(root=project, environ={"SENDER_ADDRESS": "רחוב הרצל 1, תל אביב"})
    assert "Posiblo, רחוב הרצל 1, תל אביב, 052-251-8189, posiblo.contact@gmail.com" in render_message(cfg)


def test_stop_file_halts_and_batch_cannot_be_approved(env) -> None:
    cfg, led = env

    def create_stop(url: str) -> None:
        cfg.stop_file.write_text("")

    report = run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages(), on_get=create_stop), out=lambda s: None)
    assert not report.completed and "STOP" in report.halted_reason
    assert len(led.dry_run_results("B0001")) == 1
    assert led.get_batch("B0001")["state"] == "planned"


def test_circuit_breaker_halts_after_consecutive_fetch_errors(project: Path) -> None:
    cfg = load_config(root=project, environ={"OUTREACH_BREAKER_THRESHOLD": "2"})
    with Ledger(cfg.ledger_path) as led:
        led.create_batches([[{"site_key": f"s{i}.co.il", "domain": f"s{i}.co.il", "input_url": f"s{i}.co.il"}
                             for i in range(5)]])
        fetcher = FakeFetcher({})  # every homepage is a 404 -> fetch_error
        report = run_dry_run(cfg, led, "B0001", fetcher=fetcher, out=lambda s: None)
        assert not report.completed and "circuit breaker" in report.halted_reason
        assert len(led.dry_run_results("B0001")) == 2
        assert len(fetcher.requested) == 2
        assert led.get_batch("B0001")["state"] == "planned"


def test_suppressed_and_handled_sites_are_not_fetched(env) -> None:
    cfg, led = env
    led.add_suppression("domain", "b-example.co.il", reason="asked")
    led.claim("c-example.co.il", domain="c-example.co.il", input_url="x")
    led.finish("c-example.co.il", "sent")
    fetcher = FakeFetcher(pages())
    run_dry_run(cfg, led, "B0001", fetcher=fetcher, out=lambda s: None)
    got = {r["site_key"]: r["outcome"] for r in led.dry_run_results("B0001")}
    assert got["b-example.co.il"] == "opted_out" and got["c-example.co.il"] == "already_handled"
    assert not any("b-example" in u or "c-example" in u for u in fetcher.requested)


def test_dry_run_refused_after_approval(env) -> None:
    cfg, led = env
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages()), out=lambda s: None)
    led.approve("B0001")
    with pytest.raises(LedgerError, match="only allowed before approval"):
        run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(pages()), out=lambda s: None)
    assert len(led.approved_sites("B0001")) == 1


@pytest.mark.parametrize(("raw", "url"), [
    ("example.co.il", "https://example.co.il/"),
    ("www.example.co.il/contact", "https://www.example.co.il/contact"),
    ("http://example.co.il/x?y=1#frag", "http://example.co.il/x?y=1"),
    ("HTTPS://Example.co.il", "https://Example.co.il/"),
])
def test_start_url(raw: str, url: str) -> None:
    assert start_url(raw) == url


def test_cli_dry_run_against_local_server(project: Path, httpserver: HTTPServer, monkeypatch: pytest.MonkeyPatch,
                                          capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("OUTREACH_HOST_DELAY_SECONDS", "0")
    httpserver.expect_request("/robots.txt").respond_with_data("User-agent: *\nAllow: /\n")
    httpserver.expect_request("/").respond_with_data(fixture_html("elementor.html"),
                                                     content_type="text/html; charset=utf-8")
    cfg = load_config()
    with Ledger(cfg.ledger_path) as led:
        # Real keys come from the normalizer (which rejects IP addresses), so a valid key is
        # paired here with the local server's URL by hand.
        led.create_batches([[{"site_key": "local-test.co.il", "domain": "127.0.0.1",
                              "input_url": httpserver.url_for("/")}]])
    assert main(["dry-run", "B0001"]) == 0
    out = capsys.readouterr().out
    assert "READY" in out and "פרסומת" in out
    assert {req.method for req, _ in httpserver.log} == {"GET"}
    assert sites_rows(cfg) == 0
