"""export <batch_id>: write reports/<batch_id>-<timestamp>.csv as a NEW file.

The file is opened with mode "x" (fails if it exists), so an existing report
is never overwritten; on a name clash a numeric suffix is added. The input
CSV is never read or touched by this command.
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path

COLUMNS = ["batch_id", "position", "site_key", "domain", "input_url", "dry_run_outcome", "form_url", "detail",
           "approved", "ledger_status"]


def export_rows(conn: sqlite3.Connection, batch_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT s.batch_id, s.position, s.site_key, s.domain, s.input_url,
               d.outcome AS dry_run_outcome, d.form_url, d.detail,
               CASE WHEN a.site_key IS NULL THEN 'no' ELSE 'yes' END AS approved,
               x.status AS ledger_status
        FROM batch_sites s
        LEFT JOIN dry_run_results d ON d.batch_id = s.batch_id AND d.site_key = s.site_key
        LEFT JOIN approved_sites a ON a.batch_id = s.batch_id AND a.site_key = s.site_key
        LEFT JOIN sites x ON x.site_key = s.site_key
        WHERE s.batch_id = ?
        ORDER BY s.position
        """, (batch_id,)).fetchall()
    return [dict(zip(COLUMNS, r)) for r in rows]


def export_batch(conn: sqlite3.Connection, batch_id: str, reports_dir: Path, now: datetime | None = None) -> Path:
    if conn.execute("SELECT 1 FROM batches WHERE batch_id = ?", (batch_id,)).fetchone() is None:
        raise ValueError(f"no batch {batch_id!r}")
    rows = export_rows(conn, batch_id)
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    n = 0
    while True:
        path = reports_dir / (f"{batch_id}-{stamp}.csv" if n == 0 else f"{batch_id}-{stamp}-{n}.csv")
        try:
            f = open(path, "x", newline="", encoding="utf-8-sig")  # "x": never overwrite
        except FileExistsError:
            n += 1
            continue
        with f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
        return path
