from pathlib import Path

import pytest

from outreach.cli import main
from outreach.config import load_config
from outreach.ingest import ingest
from outreach.ledger import FINAL_STATUSES, REOPENABLE_STATUSES, Ledger
from outreach.reopen import ReopenRefused, reopen_site

KEY = "example.co.il"


@pytest.fixture
def led(project: Path):
    cfg = load_config(root=project, environ={})
    with Ledger(cfg.ledger_path) as ledger:
        yield ledger


def seed(led: Ledger, status: str) -> None:
    led.claim(KEY, domain=KEY, input_url=f"https://{KEY}/")
    if status != "pending":
        led.finish(KEY, status, "seeded")


@pytest.mark.parametrize("status", ["sent", "sent_unconfirmed", "pending", "opted_out", "no_solicitation",
                                    "invalid_url"])
def test_reopen_refused_for_statuses_where_a_post_may_have_happened(led: Ledger, status: str) -> None:
    seed(led, status)
    with pytest.raises(ReopenRefused, match="only allowed"):
        reopen_site(led, KEY, ask=lambda p: KEY, out=lambda s: None)
    assert led.get(KEY)["status"] == status


@pytest.mark.parametrize("status", REOPENABLE_STATUSES)
def test_reopen_allowed_statuses(led: Ledger, status: str) -> None:
    seed(led, status)
    assert reopen_site(led, KEY, ask=lambda p: KEY, out=lambda s: None) == status
    assert led.get(KEY) is None
    assert led.claim(KEY, domain=KEY, input_url="again") is True
    events = led._conn.execute("SELECT message FROM events WHERE site_key = ?", (KEY,)).fetchall()
    assert any(f"reopened by operator (was {status})" in e[0] for e in events)


def test_reopenable_statuses_are_exactly_the_prompt_list() -> None:
    assert set(REOPENABLE_STATUSES) == {"no_form", "captcha", "login_required", "robots_blocked", "unclear_fields"}
    assert set(REOPENABLE_STATUSES) < set(FINAL_STATUSES)


@pytest.mark.parametrize("typed", ["", "yes", "EXAMPLE.CO.IL", "example.co.i", "www.example.co.il"])
def test_reopen_requires_typing_the_site_key(led: Ledger, typed: str) -> None:
    seed(led, "captcha")
    with pytest.raises(ReopenRefused, match="did not match"):
        reopen_site(led, KEY, ask=lambda p: typed, out=lambda s: None)
    assert led.get(KEY)["status"] == "captcha"


def test_reopen_unknown_site(led: Ledger) -> None:
    with pytest.raises(ReopenRefused, match="no site"):
        reopen_site(led, "nope.co.il", ask=lambda p: "nope.co.il", out=lambda s: None)


def test_ledger_reopen_refuses_directly_too(led: Ledger) -> None:
    from outreach.ledger import LedgerError
    seed(led, "sent")
    with pytest.raises(LedgerError):
        led.reopen(KEY)
    assert led.get(KEY)["status"] == "sent"


def test_cli_reopen(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    cfg = load_config(root=project, environ={})
    with Ledger(cfg.ledger_path) as led:
        seed(led, "no_form")
    monkeypatch.setattr("builtins.input", lambda prompt="": "wrong")
    assert main(["reopen", KEY]) == 1
    monkeypatch.setattr("builtins.input", lambda prompt="": KEY)
    assert main(["reopen", KEY]) == 0
    assert "reopened example.co.il (was no_form)" in capsys.readouterr().out
    with Ledger(cfg.ledger_path) as led:
        seed(led, "sent")
    assert main(["reopen", KEY]) == 1


def test_unclaimed_site_of_a_finished_batch_can_be_planned_again(led: Ledger, tmp_path: Path) -> None:
    csv = tmp_path / "s.csv"
    csv.write_text("url\nhttps://again-example.co.il\n", encoding="utf-8")
    assert ingest(csv, led, batch_size=25).planned == 1
    assert ingest(csv, led, batch_size=25).already_planned == 1      # open batch: not planned twice
    led._conn.execute("UPDATE batches SET state = 'send_done' WHERE batch_id = 'B0001'")
    assert ingest(csv, led, batch_size=25).planned == 1               # never claimed, batch finished: eligible
