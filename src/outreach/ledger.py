"""SQLite ledger: the single source of truth for "was this site already contacted?".

Send-once guarantees implemented here:
- `sites.site_key` is the PRIMARY KEY and `sites.form_url` is UNIQUE.
- claim() is one INSERT ... ON CONFLICT DO NOTHING inside BEGIN IMMEDIATE /
  COMMIT. It returns True only if this call created the row, and only after
  the COMMIT returned (WAL + synchronous=FULL: the commit is fsynced).
- finish() is the only code that changes a site row, and only moves a
  `pending` row to a final status.
- Triggers refuse, at the database level, to delete rows whose status means a
  POST may have happened (pending, sent, sent_unconfirmed) or opted_out rows;
  to move any row back to pending; to change a sent/sent_unconfirmed row to
  anything except opted_out; to change an opted_out row; and to re-key a row.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .normalize import normalize_url

DEFAULT_PATH = Path("data") / "ledger.db"
DEFAULT_BUSY_TIMEOUT_MS = 10_000

STATUSES = (
    "pending", "sent", "sent_unconfirmed", "no_form", "captcha", "login_required",
    "robots_blocked", "no_solicitation", "unclear_fields", "opted_out", "invalid_url",
)
FINAL_STATUSES = tuple(s for s in STATUSES if s != "pending")
SUPPRESSION_KINDS = ("domain", "email", "phone")

_STATUS_SQL = ", ".join(f"'{s}'" for s in STATUSES)
_KIND_SQL = ", ".join(f"'{k}'" for k in SUPPRESSION_KINDS)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS batches (
    batch_id    TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    size        INTEGER NOT NULL,
    state       TEXT NOT NULL,
    approved_at TEXT
);

CREATE TABLE IF NOT EXISTS sites (
    site_key        TEXT PRIMARY KEY,
    domain          TEXT NOT NULL,
    input_url       TEXT NOT NULL,
    form_url        TEXT UNIQUE,
    status          TEXT NOT NULL CHECK (status IN ({_STATUS_SQL})),
    batch_id        TEXT REFERENCES batches(batch_id),
    message_version TEXT,
    source_url      TEXT,
    collected_at    TEXT,
    claimed_at      TEXT NOT NULL,
    finished_at     TEXT,
    detail          TEXT
);

CREATE TABLE IF NOT EXISTS suppression (
    kind     TEXT NOT NULL CHECK (kind IN ({_KIND_SQL})),
    value    TEXT NOT NULL,
    reason   TEXT,
    added_at TEXT NOT NULL,
    PRIMARY KEY (kind, value)
);

CREATE TABLE IF NOT EXISTS dry_run_results (
    batch_id    TEXT NOT NULL REFERENCES batches(batch_id),
    site_key    TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    form_url    TEXT,
    fields_json TEXT,
    detail      TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    site_key TEXT,
    level    TEXT NOT NULL,
    message  TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS sites_protect_delete
BEFORE DELETE ON sites
WHEN OLD.status IN ('pending', 'sent', 'sent_unconfirmed', 'opted_out')
BEGIN
    SELECT RAISE(ABORT, 'ledger: refusing to delete a pending/sent/sent_unconfirmed/opted_out site row');
END;

CREATE TRIGGER IF NOT EXISTS sites_protect_update
BEFORE UPDATE ON sites
WHEN NEW.site_key IS NOT OLD.site_key
  OR (NEW.status = 'pending' AND OLD.status <> 'pending')
  OR (OLD.status IN ('sent', 'sent_unconfirmed') AND NEW.status IS NOT OLD.status AND NEW.status <> 'opted_out')
  OR (OLD.status = 'opted_out' AND NEW.status IS NOT OLD.status)
BEGIN
    SELECT RAISE(ABORT, 'ledger: refusing to re-key a site row, move it back to pending, or downgrade a sent/sent_unconfirmed/opted_out row');
END;
"""


class LedgerError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_suppression(kind: str, value: str) -> str:
    """Canonical form of a suppression value, so lookups match any spelling."""
    if kind not in SUPPRESSION_KINDS:
        raise ValueError(f"unknown suppression kind: {kind!r}")
    value = value.strip()
    if kind == "domain":
        return normalize_url(value).site_key
    if kind == "email":
        value = value.lower().removeprefix("mailto:")
        if value.count("@") != 1 or not all(value.split("@")):
            raise ValueError(f"not an email address: {value!r}")
        return value
    digits = re.sub(r"\D", "", value)
    if digits.startswith("972"):
        digits = "0" + digits[3:]
    if len(digits) < 7:
        raise ValueError(f"not a phone number: {value!r}")
    return digits


class Ledger:
    def __init__(self, path: str | Path = DEFAULT_PATH, *, busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: no implicit transactions; every transaction below is explicit.
        self._conn = sqlite3.connect(self.path, isolation_level=None, timeout=busy_timeout_ms / 1000)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
        mode = self._conn.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        if mode.lower() != "wal":
            raise LedgerError(f"could not enable WAL mode (got {mode!r}) for {self.path}")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    # -- lifecycle --------------------------------------------------------
    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Ledger":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def pragma(self, name: str) -> Any:
        if not re.fullmatch(r"[a-z_]+", name):
            raise ValueError(name)
        return self._conn.execute(f"PRAGMA {name}").fetchone()[0]

    # -- send-once core ---------------------------------------------------
    def claim(
        self,
        site_key: str,
        *,
        domain: str,
        input_url: str,
        batch_id: str | None = None,
        form_url: str | None = None,
        message_version: str | None = None,
        source_url: str | None = None,
        collected_at: str | None = None,
        detail: str | None = None,
    ) -> bool:
        """Create the site row with status `pending`. True only if THIS call created it.

        The row is committed (and fsynced) before this returns. A conflict on
        site_key or form_url inserts nothing and returns False.
        """
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                """
                INSERT INTO sites (site_key, domain, input_url, form_url, status, batch_id,
                                   message_version, source_url, collected_at, claimed_at, detail)
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (site_key, domain, input_url, form_url, batch_id, message_version,
                 source_url, collected_at, _now(), detail),
            )
            created = cur.rowcount == 1
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return created

    def finish(self, site_key: str, status: str, detail: str | None = None) -> None:
        """Move a `pending` row to its final status. Raises if the row is not pending."""
        if status not in FINAL_STATUSES:
            raise ValueError(f"not a final status: {status!r}")
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                "UPDATE sites SET status = ?, detail = ?, finished_at = ? "
                "WHERE site_key = ? AND status = 'pending'",
                (status, detail, _now(), site_key),
            )
            if cur.rowcount != 1:
                raise LedgerError(f"finish({site_key!r}): no pending row with that key")
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise

    # -- queries ----------------------------------------------------------
    def is_handled(self, site_key: str) -> bool:
        """True if the site has a row in any status (including pending)."""
        row = self._conn.execute("SELECT 1 FROM sites WHERE site_key = ?", (site_key,)).fetchone()
        return row is not None

    def get(self, site_key: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM sites WHERE site_key = ?", (site_key,)).fetchone()
        return dict(row) if row else None

    def list_pending(self) -> list[dict[str, Any]]:
        """Rows stuck in `pending` (for the dashboard and preflight). Read-only."""
        rows = self._conn.execute(
            "SELECT * FROM sites WHERE status = 'pending' ORDER BY claimed_at, site_key"
        ).fetchall()
        return [dict(r) for r in rows]

    # -- suppression ------------------------------------------------------
    def add_suppression(self, kind: str, value: str, reason: str | None = None) -> bool:
        """Add a suppression entry. Returns False if it already existed."""
        norm = normalize_suppression(kind, value)
        cur = self._conn.execute(
            "INSERT INTO suppression (kind, value, reason, added_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT DO NOTHING",
            (kind, norm, reason, _now()),
        )
        return cur.rowcount == 1

    def is_suppressed(self, kind: str, value: str) -> bool:
        norm = normalize_suppression(kind, value)
        row = self._conn.execute(
            "SELECT 1 FROM suppression WHERE kind = ? AND value = ?", (kind, norm)
        ).fetchone()
        return row is not None

    # -- events -----------------------------------------------------------
    def add_event(self, level: str, message: str, site_key: str | None = None) -> None:
        self._conn.execute(
            "INSERT INTO events (ts, site_key, level, message) VALUES (?, ?, ?, ?)",
            (_now(), site_key, level, message),
        )
