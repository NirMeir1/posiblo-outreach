import multiprocessing as mp
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from outreach.ledger import FINAL_STATUSES, Ledger, LedgerError
from outreach.normalize import normalize_url

SRC = Path(__file__).resolve().parent.parent / "src"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "ledger.db"


@pytest.fixture
def ledger(db_path: Path):
    with Ledger(db_path) as led:
        yield led


def claim_url(led: Ledger, raw: str, **kw) -> bool:
    key, domain = normalize_url(raw)
    return led.claim(key, domain=domain, input_url=raw, **kw)


# --- connection settings -------------------------------------------------

def test_pragmas_wal_full_fk_busy(ledger: Ledger) -> None:
    assert ledger.pragma("journal_mode") == "wal"
    assert ledger.pragma("synchronous") == 2  # FULL
    assert ledger.pragma("foreign_keys") == 1
    assert ledger.pragma("busy_timeout") >= 1000


def test_default_path_is_data_ledger_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with Ledger() as led:
        assert led.path == Path("data") / "ledger.db"
    assert (tmp_path / "data" / "ledger.db").is_file()


# --- claim ---------------------------------------------------------------

def test_first_claim_creates_pending_row(ledger: Ledger) -> None:
    assert ledger.claim("example.co.il", domain="example.co.il", input_url="https://example.co.il") is True
    row = ledger.get("example.co.il")
    assert row["status"] == "pending"
    assert row["claimed_at"] and row["finished_at"] is None


def test_second_claim_of_same_key_returns_false(ledger: Ledger) -> None:
    assert ledger.claim("example.co.il", domain="example.co.il", input_url="a") is True
    assert ledger.claim("example.co.il", domain="example.co.il", input_url="b") is False
    assert ledger.get("example.co.il")["input_url"] == "a"  # first claim untouched


def test_claim_via_different_url_spellings_returns_false(ledger: Ledger) -> None:
    assert claim_url(ledger, "https://www.example.co.il/") is True
    for spelling in ["example.co.il", "HTTP://SHOP.EXAMPLE.CO.IL/contact?utm_source=x",
                     "https://example.co.il.:443/#top", "‏www.example.co.il‏"]:
        assert claim_url(ledger, spelling) is False, spelling
    assert claim_url(ledger, "https://דוגמה.co.il") is True
    assert claim_url(ledger, "https://www.xn--6dbbec0c.co.il/צור-קשר") is False


def test_claim_with_already_used_form_url_returns_false(ledger: Ledger) -> None:
    assert ledger.claim("a.co.il", domain="a.co.il", input_url="a", form_url="https://a.co.il/contact") is True
    assert ledger.claim("b.co.il", domain="b.co.il", input_url="b", form_url="https://a.co.il/contact") is False
    assert ledger.get("b.co.il") is None


def test_claim_is_durable_when_it_returns(db_path: Path) -> None:
    """A second, independent connection sees the row immediately after claim() returns."""
    with Ledger(db_path) as a, Ledger(db_path) as b:
        assert a.claim("example.co.il", domain="example.co.il", input_url="x") is True
        assert b.get("example.co.il")["status"] == "pending"
        assert b.claim("example.co.il", domain="example.co.il", input_url="x") is False


def test_claim_with_unknown_batch_violates_foreign_key(ledger: Ledger) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        ledger.claim("example.co.il", domain="example.co.il", input_url="x", batch_id="no-such-batch")
    assert ledger.get("example.co.il") is None


# --- concurrency ---------------------------------------------------------

def test_concurrent_claims_threads_exactly_one_winner(db_path: Path) -> None:
    workers, rounds = 16, 10
    Ledger(db_path).close()
    barrier = threading.Barrier(workers)
    wins: list[list[bool]] = [[] for _ in range(rounds)]
    lock = threading.Lock()
    errors: list[BaseException] = []

    def work() -> None:
        try:
            with Ledger(db_path) as led:
                for r in range(rounds):
                    barrier.wait()
                    won = led.claim(f"race-{r}.co.il", domain=f"race-{r}.co.il", input_url="x")
                    with lock:
                        wins[r].append(won)
        except BaseException as e:  # surface failures from threads
            errors.append(e)
            barrier.abort()

    threads = [threading.Thread(target=work) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not errors, errors
    for r in range(rounds):
        assert len(wins[r]) == workers
        assert wins[r].count(True) == 1, f"round {r}: {wins[r]}"


def _process_worker(db: str, rounds: int, barrier, results) -> None:
    sys.path.insert(0, str(SRC))
    from outreach.ledger import Ledger as L

    with L(db) as led:
        for r in range(rounds):
            barrier.wait(timeout=60)
            results.put((r, led.claim(f"proc-{r}.co.il", domain=f"proc-{r}.co.il", input_url="x")))


def test_concurrent_claims_processes_exactly_one_winner(db_path: Path) -> None:
    workers, rounds = 8, 10
    Ledger(db_path).close()
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(workers)
    results = ctx.Queue()
    procs = [ctx.Process(target=_process_worker, args=(str(db_path), rounds, barrier, results))
             for _ in range(workers)]
    for p in procs:
        p.start()
    got = [results.get(timeout=60) for _ in range(workers * rounds)]
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0
    for r in range(rounds):
        outcomes = [won for (rr, won) in got if rr == r]
        assert len(outcomes) == workers
        assert outcomes.count(True) == 1, f"round {r}: {outcomes}"
    with Ledger(db_path) as led:
        assert len(led.list_pending()) == rounds


# --- crash simulation ----------------------------------------------------

def test_crash_after_claim_leaves_row_pending_and_not_offered_again(db_path: Path) -> None:
    """A separate process claims and then dies without finish() or close()."""
    code = (
        f"import sys, os; sys.path.insert(0, {str(SRC)!r})\n"
        "from outreach.ledger import Ledger\n"
        f"led = Ledger({str(db_path)!r})\n"
        "assert led.claim('example.co.il', domain='example.co.il', input_url='https://example.co.il')\n"
        "os._exit(17)  # hard crash: no finish, no close, no cleanup\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 17, proc.stderr

    with Ledger(db_path) as led:
        row = led.get("example.co.il")
        assert row is not None and row["status"] == "pending"
        assert led.is_handled("example.co.il")
        assert [r["site_key"] for r in led.list_pending()] == ["example.co.il"]
        # not offered as work again, under any spelling
        assert claim_url(led, "https://www.example.co.il/contact") is False
        assert led.get("example.co.il")["status"] == "pending"


# --- finish --------------------------------------------------------------

@pytest.mark.parametrize("status", FINAL_STATUSES)
def test_finish_moves_pending_to_final(ledger: Ledger, status: str) -> None:
    ledger.claim("example.co.il", domain="example.co.il", input_url="x")
    ledger.finish("example.co.il", status, "detail")
    row = ledger.get("example.co.il")
    assert row["status"] == status and row["detail"] == "detail" and row["finished_at"]
    assert ledger.list_pending() == []


def test_finish_refuses_non_pending_and_missing_rows(ledger: Ledger) -> None:
    ledger.claim("example.co.il", domain="example.co.il", input_url="x")
    ledger.finish("example.co.il", "sent")
    with pytest.raises(LedgerError):
        ledger.finish("example.co.il", "no_form")
    assert ledger.get("example.co.il")["status"] == "sent"
    with pytest.raises(LedgerError):
        ledger.finish("missing.co.il", "sent")


def test_finish_refuses_pending_or_unknown_status(ledger: Ledger) -> None:
    ledger.claim("example.co.il", domain="example.co.il", input_url="x")
    for bad in ["pending", "done", ""]:
        with pytest.raises(ValueError):
            ledger.finish("example.co.il", bad)
    assert ledger.get("example.co.il")["status"] == "pending"


# --- database-level protection ------------------------------------------

def _raw(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path, isolation_level=None)


@pytest.mark.parametrize("status", ["pending", "sent", "sent_unconfirmed", "opted_out"])
def test_trigger_blocks_deleting_protected_rows(db_path: Path, status: str) -> None:
    with Ledger(db_path) as led:
        led.claim("example.co.il", domain="example.co.il", input_url="x")
        if status != "pending":
            led.finish("example.co.il", status)
    conn = _raw(db_path)
    with pytest.raises(sqlite3.IntegrityError, match="refusing to delete"):
        conn.execute("DELETE FROM sites WHERE site_key = 'example.co.il'")
    conn.close()


@pytest.mark.parametrize(("start", "new"), [
    ("sent", "pending"), ("sent", "no_form"), ("sent_unconfirmed", "pending"),
    ("sent_unconfirmed", "sent"), ("opted_out", "sent"), ("no_form", "pending"),
])
def test_trigger_blocks_downgrades(db_path: Path, start: str, new: str) -> None:
    with Ledger(db_path) as led:
        led.claim("example.co.il", domain="example.co.il", input_url="x")
        led.finish("example.co.il", start)
    conn = _raw(db_path)
    with pytest.raises(sqlite3.IntegrityError, match="refusing"):
        conn.execute("UPDATE sites SET status = ? WHERE site_key = 'example.co.il'", (new,))
    conn.close()
    with Ledger(db_path) as led:
        assert led.get("example.co.il")["status"] == start


def test_trigger_blocks_rekeying(db_path: Path) -> None:
    with Ledger(db_path) as led:
        led.claim("example.co.il", domain="example.co.il", input_url="x")
    conn = _raw(db_path)
    with pytest.raises(sqlite3.IntegrityError, match="refusing"):
        conn.execute("UPDATE sites SET site_key = 'other.co.il'")
    conn.close()


# --- suppression ---------------------------------------------------------

def test_suppressed_domain_is_blocked_for_any_spelling(ledger: Ledger) -> None:
    assert ledger.add_suppression("domain", "www.Example.co.il", reason="asked to be removed") is True
    assert ledger.add_suppression("domain", "https://example.co.il/") is False  # same entry
    for spelling in ["example.co.il", "https://shop.example.co.il/contact", "HTTP://WWW.EXAMPLE.CO.IL."]:
        assert ledger.is_suppressed("domain", spelling), spelling
    assert not ledger.is_suppressed("domain", "example.com")
    assert not ledger.is_suppressed("domain", "other.co.il")


def test_suppressed_email_and_phone(ledger: Ledger) -> None:
    ledger.add_suppression("email", "Info@Example.co.il")
    ledger.add_suppression("phone", "+972-52-251-8189")
    assert ledger.is_suppressed("email", "mailto:info@example.co.il")
    assert ledger.is_suppressed("phone", "052-251-8189")
    assert ledger.is_suppressed("phone", "0522518189")
    assert not ledger.is_suppressed("email", "other@example.co.il")
    assert not ledger.is_suppressed("phone", "052-251-8188")


def test_suppression_with_platform_aware_keys(ledger: Ledger) -> None:
    # facebook: one page suppressed, another page on the platform is not
    ledger.add_suppression("domain", "https://www.facebook.com/Bakery/")
    assert ledger.is_suppressed("domain", "facebook.com/bakery")
    assert ledger.is_suppressed("domain", "https://m.facebook.com/bakery?ref=x")
    assert not ledger.is_suppressed("domain", "facebook.com/other")
    ledger.add_suppression("domain", "https://www.facebook.com/profile.php?id=42")
    assert ledger.is_suppressed("domain", "facebook.com/profile.php?id=42")
    assert not ledger.is_suppressed("domain", "facebook.com/profile.php?id=43")
    # wixsite: suppressing the account host blocks every site under it; a site suppression blocks only that site
    ledger.add_suppression("domain", "https://user.wixsite.com/")
    assert ledger.is_suppressed("domain", "user.wixsite.com/shop")
    assert ledger.is_suppressed("domain", "https://user.wixsite.com/other-site/contact")
    assert not ledger.is_suppressed("domain", "someone.wixsite.com/shop")
    ledger.add_suppression("domain", "https://second.wixsite.com/shop")
    assert ledger.is_suppressed("domain", "second.wixsite.com/shop")
    assert not ledger.is_suppressed("domain", "second.wixsite.com/blog")
    # subdomain platform: the host is the key
    ledger.add_suppression("domain", "mybiz.blogspot.com")
    assert ledger.is_suppressed("domain", "https://mybiz.blogspot.com/p/contact.html")
    assert not ledger.is_suppressed("domain", "other.blogspot.com")


def test_a_bare_platform_can_never_be_suppressed(ledger: Ledger) -> None:
    """Otherwise one suppression could block every business on facebook or wix."""
    from outreach.normalize import InvalidUrl
    for bare in ("facebook.com", "https://www.facebook.com/", "wixsite.com", "linktr.ee"):
        with pytest.raises(InvalidUrl):
            ledger.add_suppression("domain", bare)


def test_record_no_post_outcomes_only_records_the_five_statuses(ledger: Ledger) -> None:
    outcomes = {"ready-x.co.il": "ready", "nf.co.il": "no_form", "cap.co.il": "captcha",
                "login.co.il": "login_required", "robots.co.il": "robots_blocked", "unc.co.il": "unclear_fields",
                "fe.co.il": "fetch_error", "ns.co.il": "no_solicitation", "opt.co.il": "opted_out",
                "ah.co.il": "already_handled", "sent-before.co.il": "captcha"}
    ledger.create_batches([[{"site_key": k, "domain": k, "input_url": f"https://{k}/"} for k in outcomes]])
    ledger.claim("sent-before.co.il", domain="sent-before.co.il", input_url="x")
    ledger.finish("sent-before.co.il", "sent")
    for k, o in outcomes.items():
        ledger.add_dry_run_result("B0001", k, o, f"https://{k}/contact", "{}", "detail")
    recorded = dict(ledger.record_no_post_outcomes("B0001"))
    assert recorded == {"nf.co.il": "no_form", "cap.co.il": "captcha", "login.co.il": "login_required",
                        "robots.co.il": "robots_blocked", "unc.co.il": "unclear_fields"}
    assert ledger.get("ready-x.co.il") is None                       # a ready site is never recorded
    for k in ("fe.co.il", "ns.co.il", "opt.co.il", "ah.co.il"):
        assert ledger.get(k) is None
    assert ledger.get("sent-before.co.il")["status"] == "sent"       # existing row untouched
    assert ledger.list_pending() == []                               # never pending
    assert ledger.record_no_post_outcomes("B0001") == []             # idempotent
    for k in recorded:
        assert ledger.get(k)["form_url"] is None and ledger.get(k)["finished_at"]


def test_suppression_rejects_bad_kind_or_value(ledger: Ledger) -> None:
    with pytest.raises(ValueError):
        ledger.add_suppression("fax", "123")
    with pytest.raises(ValueError):
        ledger.add_suppression("email", "not-an-email")
    with pytest.raises(ValueError):
        ledger.add_suppression("domain", "mailto:x@y.co.il")
