import sqlite3
from pathlib import Path

import pytest

from conftest import FakeFetcher, fixture_html
from outreach.approve import ApprovalRefused, approve_batch
from outreach.cli import main
from outreach.config import load_config
from outreach.dryrun import run_dry_run
from outreach.ledger import Ledger

PAGES = {
    "https://a-example.co.il/": fixture_html("cf7_hebrew.html"),
    "https://b-example.co.il/": fixture_html("no_form.html"),
    "https://c-example.co.il/": fixture_html("elementor.html"),
    "https://d-example.co.il/": fixture_html("recaptcha.html"),
}


@pytest.fixture
def env(project: Path):
    cfg = load_config(root=project, environ={})
    led = Ledger(cfg.ledger_path)
    keys = ["a-example.co.il", "b-example.co.il", "c-example.co.il", "d-example.co.il"]
    led.create_batches([[{"site_key": k, "domain": k, "input_url": f"https://{k}/"} for k in keys]])
    yield cfg, led
    led.close()


def dry(cfg, led) -> None:
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(PAGES), out=lambda s: None)


def test_approve_refuses_before_dry_run(env) -> None:
    cfg, led = env
    with pytest.raises(ApprovalRefused, match="dry-run"):
        approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    assert led.get_batch("B0001")["state"] == "planned"
    assert led.approved_sites("B0001") == []


def test_approve_refuses_after_halted_dry_run(env) -> None:
    cfg, led = env
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher(PAGES, on_get=lambda u: cfg.stop_file.write_text("")),
                out=lambda s: None)
    with pytest.raises(ApprovalRefused):
        approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)


@pytest.mark.parametrize("typed", ["", "yes", "b0001", "B0002", "B000", "y"])
def test_approve_requires_typing_the_batch_id(env, typed: str) -> None:
    cfg, led = env
    dry(cfg, led)
    with pytest.raises(ApprovalRefused, match="did not match"):
        approve_batch(led, "B0001", ask=lambda p: typed, out=lambda s: None)
    assert led.get_batch("B0001")["state"] == "dry_run_done"
    assert led.approved_sites("B0001") == []


def test_approved_list_contains_only_ready_sites(env) -> None:
    cfg, led = env
    dry(cfg, led)
    lines: list[str] = []
    count = approve_batch(led, "B0001", ask=lambda p: " B0001 ", out=lines.append)
    assert count == 2
    approved = led.approved_sites("B0001")
    assert [a["site_key"] for a in approved] == ["a-example.co.il", "c-example.co.il"]
    assert all(a["fields_json"] and a["form_url"] for a in approved)
    batch = led.get_batch("B0001")
    assert batch["state"] == "approved" and batch["approved_at"]
    text = "\n".join(lines)
    assert "ready (will be approved): 2" in text
    assert "skipped, captcha: 1" in text and "skipped, no_form: 1" in text


def test_approved_list_is_frozen(env) -> None:
    cfg, led = env
    dry(cfg, led)
    approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    conn = sqlite3.connect(cfg.ledger_path, isolation_level=None)
    with pytest.raises(sqlite3.IntegrityError, match="frozen"):
        conn.execute("DELETE FROM approved_sites")
    with pytest.raises(sqlite3.IntegrityError, match="frozen"):
        conn.execute("UPDATE approved_sites SET form_url = 'https://evil.example/'")
    with pytest.raises(sqlite3.IntegrityError, match="frozen"):
        conn.execute("UPDATE approved_sites SET site_key = 'b-example.co.il'")
    conn.close()
    assert len(led.approved_sites("B0001")) == 2


def test_approve_twice_is_refused(env) -> None:
    cfg, led = env
    dry(cfg, led)
    approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    with pytest.raises(ApprovalRefused, match="approved"):
        approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    assert len(led.approved_sites("B0001")) == 2


def test_approve_with_no_ready_sites_is_refused(env) -> None:
    cfg, led = env
    run_dry_run(cfg, led, "B0001", fetcher=FakeFetcher({}), out=lambda s: None)  # all 404
    # 4 fetch errors < default threshold 5, so the run completes with zero ready sites
    with pytest.raises(ApprovalRefused, match="no ready sites"):
        approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)


def test_approve_does_not_touch_sites_table(env) -> None:
    cfg, led = env
    dry(cfg, led)
    approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
    assert led.list_pending() == [] and led.get("a-example.co.il") is None


def test_cli_approve_reads_typed_confirmation(env, monkeypatch: pytest.MonkeyPatch,
                                              capsys: pytest.CaptureFixture) -> None:
    cfg, led = env
    dry(cfg, led)
    monkeypatch.setattr("builtins.input", lambda prompt="": "nope")
    assert main(["approve", "B0001"]) == 1
    assert "did not match" in capsys.readouterr().err
    monkeypatch.setattr("builtins.input", lambda prompt="": "B0001")
    assert main(["approve", "B0001"]) == 0
    assert "Approved B0001: 2 site(s) frozen" in capsys.readouterr().out
