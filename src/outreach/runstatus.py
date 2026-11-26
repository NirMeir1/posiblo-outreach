"""logs/run-status.json: what a running dry-run or send is doing right now.

Written by dry-run and send (atomic replace), read by the dashboard. Writing
is best-effort: any error is swallowed, so a dashboard-side problem (a locked
file, a full disk for this tiny file) can never stop or change a run.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FILENAME = "run-status.json"


def status_path(log_dir: Path) -> Path:
    return Path(log_dir) / FILENAME


def write_status(log_dir: Path, **fields: Any) -> bool:
    """Replace the status file. Returns False (never raises) if it could not be written."""
    try:
        path = status_path(log_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **fields}
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001 - by design: status reporting must never affect a run
        return False


def read_status(log_dir: Path) -> dict[str, Any] | None:
    try:
        return json.loads(status_path(log_dir).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - missing or half-written file: no status
        return None
