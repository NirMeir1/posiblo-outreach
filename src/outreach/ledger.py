"""SQLite ledger: the single source of truth for "was this site already contacted?".

Send-once guarantees implemented here:
- `sites.site_key` is the PRIMARY KEY and `sites.form_url` is UNIQUE.
- claim() is one INSERT ... ON CONFLICT DO NOTHING inside BEGIN IMMEDIATE /
  COMMIT. It returns True only if this call created the row, and only after
  the COMMIT returned (WAL + synchronous=FULL: the commit is fsynced).
- finish() is the only code that changes a site row, and only moves a
  `pending` row to a final status. reopen() is the only code that removes
  one, and only for statuses where no POST ever happened
  (REOPENABLE_STATUSES).
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
# Statuses where no POST was ever made: the only ones `reopen` may remove.
REOPENABLE_STATUSES = ("no_form", "captcha", "login_required", "robots_blocked", "unclear_fields")
BATCH_STATES = ("planned", "dry_run_done", "approved", "sending", "send_done")
OPEN_BATCH_STATES = ("planned", "dry_run_done", "approved", "sending")
SENDABLE_BATCH_STATES = ("approved", "sending", "send_done")

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

CREATE TABLE IF NOT EXISTS batch_sites (
    batch_id    TEXT NOT NULL REFERENCES batches(batch_id),
    position    INTEGER NOT NULL,
    site_key    TEXT NOT NULL,
    domain      TEXT NOT NULL,
    input_url   TEXT NOT NULL,
    source_file TEXT,
    source_row  INTEGER,
    PRIMARY KEY (batch_id, site_key)
);
CREATE INDEX IF NOT EXISTS batch_sites_site_key ON batch_sites(site_key);

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

CREATE TABLE IF NOT EXISTS approved_sites (
    batch_id    TEXT NOT NULL REFERENCES batches(batch_id),
    site_key    TEXT NOT NULL,
    input_url   TEXT NOT NULL,
    domain      TEXT NOT NULL,
    form_url    TEXT,
    fields_json TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    PRIMARY KEY (batch_id, site_key)
);

CREATE TRIGGER IF NOT EXISTS approved_sites_frozen_update
BEFORE UPDATE ON approved_sites
BEGIN
    SELECT RAISE(ABORT, 'ledger: the approved list of a batch is frozen');
END;

CREATE TRIGGER IF NOT EXISTS approved_sites_frozen_delete
BEFORE DELETE ON approved_sites
BEGIN
    SELECT RAISE(ABORT, 'ledger: the approved list of a batch is frozen');
END;

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

    # -- batches ----------------------------------------------------------
    def is_planned(self, site_key: str) -> bool:
        """True if the site is part of a batch that is still open (not yet sent).

        A site of a finished batch that was never claimed (e.g. a network error
        before the claim) is eligible for a future batch.
        """
        row = self._conn.execute(
            "SELECT 1 FROM batch_sites s JOIN batches b ON b.batch_id = s.batch_id "
            f"WHERE s.site_key = ? AND b.state IN ({', '.join(repr(s) for s in OPEN_BATCH_STATES)}) LIMIT 1",
            (site_key,)).fetchone()
        return row is not None

    def create_batches(self, groups: list[list[dict[str, Any]]], source_file: str | None = None) -> list[str]:
        """Store each group as a new batch in state `planned`. Returns the new batch ids (B0001, B0002, ...).

        Each item needs site_key, domain, input_url and optionally source_row.
        One transaction: either every batch is stored or none is.
        """
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT MAX(CAST(SUBSTR(batch_id, 2) AS INTEGER)) FROM batches WHERE batch_id GLOB 'B[0-9]*'"
            ).fetchone()
            next_n = (row[0] or 0) + 1
            ids: list[str] = []
            now = _now()
            for group in groups:
                if not group:
                    continue
                batch_id = f"B{next_n:04d}"
                next_n += 1
                conn.execute("INSERT INTO batches (batch_id, created_at, size, state) VALUES (?, ?, ?, 'planned')",
                             (batch_id, now, len(group)))
                conn.executemany(
                    "INSERT INTO batch_sites (batch_id, position, site_key, domain, input_url, source_file, source_row) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [(batch_id, i, it["site_key"], it["domain"], it["input_url"], source_file, it.get("source_row"))
                     for i, it in enumerate(group, 1)],
                )
                ids.append(batch_id)
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return ids

    def list_batches(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM batches ORDER BY batch_id").fetchall()]

    def batch_sites(self, batch_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM batch_sites WHERE batch_id = ? ORDER BY position", (batch_id,)).fetchall()]

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()
        return dict(row) if row else None

    # -- dry run ------------------------------------------------------------
    def start_dry_run(self, batch_id: str) -> None:
        """Reset a batch for a (re-)run: state back to planned, old dry-run results removed.

        Refused for an approved batch (its approved list is frozen).
        """
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT state FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()
            if row is None:
                raise LedgerError(f"no batch {batch_id!r}")
            if row[0] not in ("planned", "dry_run_done"):
                raise LedgerError(f"batch {batch_id} is {row[0]}; dry-run is only allowed before approval")
            conn.execute("UPDATE batches SET state = 'planned' WHERE batch_id = ?", (batch_id,))
            conn.execute("DELETE FROM dry_run_results WHERE batch_id = ?", (batch_id,))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise

    def add_dry_run_result(self, batch_id: str, site_key: str, outcome: str, form_url: str | None,
                           fields_json: str | None, detail: str | None) -> None:
        self._conn.execute(
            "INSERT INTO dry_run_results (batch_id, site_key, outcome, form_url, fields_json, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (batch_id, site_key, outcome, form_url, fields_json, detail, _now()))

    def finish_dry_run(self, batch_id: str) -> None:
        cur = self._conn.execute(
            "UPDATE batches SET state = 'dry_run_done' WHERE batch_id = ? AND state = 'planned'", (batch_id,))
        if cur.rowcount != 1:
            raise LedgerError(f"batch {batch_id} is not in state planned")

    def dry_run_results(self, batch_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT d.* FROM dry_run_results d LEFT JOIN batch_sites s "
            "ON s.batch_id = d.batch_id AND s.site_key = d.site_key "
            "WHERE d.batch_id = ? ORDER BY s.position, d.rowid", (batch_id,)).fetchall()]

    # -- approval -------------------------------------------------------------
    def approve(self, batch_id: str) -> int:
        """Freeze the `ready` sites of a dry-run-done batch and mark it approved. Returns how many."""
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT state FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()
            if row is None:
                raise LedgerError(f"no batch {batch_id!r}")
            if row[0] != "dry_run_done":
                raise LedgerError(f"batch {batch_id} is {row[0]}; approve needs a completed dry-run (dry_run_done)")
            now = _now()
            cur = conn.execute(
                "INSERT INTO approved_sites (batch_id, site_key, input_url, domain, form_url, fields_json, approved_at) "
                "SELECT d.batch_id, d.site_key, s.input_url, s.domain, d.form_url, d.fields_json, ? "
                "FROM dry_run_results d JOIN batch_sites s ON s.batch_id = d.batch_id AND s.site_key = d.site_key "
                "WHERE d.batch_id = ? AND d.outcome = 'ready' ORDER BY s.position",
                (now, batch_id))
            count = cur.rowcount
            conn.execute("UPDATE batches SET state = 'approved', approved_at = ? WHERE batch_id = ? "
                         "AND state = 'dry_run_done'", (now, batch_id))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return count

    # -- live run -----------------------------------------------------------
    def begin_send(self, batch_id: str) -> None:
        cur = self._conn.execute(
            f"UPDATE batches SET state = 'sending' WHERE batch_id = ? AND state IN "
            f"({', '.join(repr(s) for s in SENDABLE_BATCH_STATES)})", (batch_id,))
        if cur.rowcount != 1:
            raise LedgerError(f"batch {batch_id} is not approved")

    def finish_send(self, batch_id: str) -> None:
        self._conn.execute("UPDATE batches SET state = 'send_done' WHERE batch_id = ? AND state = 'sending'",
                           (batch_id,))

    # -- reopen -----------------------------------------------------------
    def reopen(self, site_key: str) -> str:
        """Remove a site row whose status means no POST ever happened, so the site can be planned again.

        Refused for every other status (pending, sent, sent_unconfirmed, opted_out, ...). Returns the
        removed status. The sites_protect_delete trigger independently refuses pending/sent rows.
        """
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT status FROM sites WHERE site_key = ?", (site_key,)).fetchone()
            if row is None:
                raise LedgerError(f"no site {site_key!r} in the ledger")
            if row[0] not in REOPENABLE_STATUSES:
                raise LedgerError(f"site {site_key} is {row[0]}; reopen is only allowed for "
                                  f"{', '.join(REOPENABLE_STATUSES)}")
            cur = conn.execute(
                "DELETE FROM sites WHERE site_key = ? AND status IN "
                "('no_form', 'captcha', 'login_required', 'robots_blocked', 'unclear_fields')", (site_key,))
            if cur.rowcount != 1:
                raise LedgerError(f"reopen({site_key!r}) removed {cur.rowcount} rows")
            conn.execute("INSERT INTO events (ts, site_key, level, message) VALUES (?, ?, 'warning', ?)",
                         (_now(), site_key, f"reopened by operator (was {row[0]})"))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return row[0]

    def approved_sites(self, batch_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT a.* FROM approved_sites a LEFT JOIN batch_sites s "
            "ON s.batch_id = a.batch_id AND s.site_key = a.site_key "
            "WHERE a.batch_id = ? ORDER BY s.position", (batch_id,)).fetchall()]

    # -- events -----------------------------------------------------------
    def add_event(self, level: str, message: str, site_key: str | None = None) -> None:
        self._conn.execute(
            "INSERT INTO events (ts, site_key, level, message) VALUES (?, ?, ?, ?)",
            (_now(), site_key, level, message),
        )


def open_readonly(path: str | Path) -> sqlite3.Connection:
    """Read-only connection (SQLite URI mode=ro). Never creates or modifies the file."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"ledger {p} does not exist")
    conn = sqlite3.connect(f"{p.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def status_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Counts for `python -m outreach status`, from any (read-only) connection."""
    by_status = {s: 0 for s in STATUSES}
    for r in conn.execute("SELECT status, COUNT(*) FROM sites GROUP BY status"):
        by_status[r[0]] = r[1]
    batches = [dict(r) for r in conn.execute(
        "SELECT b.batch_id, b.state, b.size, b.created_at, b.approved_at FROM batches b ORDER BY b.batch_id")]
    suppression = {k: 0 for k in SUPPRESSION_KINDS}
    for r in conn.execute("SELECT kind, COUNT(*) FROM suppression GROUP BY kind"):
        suppression[r[0]] = r[1]
    return {"sites": by_status, "batches": batches, "suppression": suppression,
            "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]}
