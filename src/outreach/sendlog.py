"""Append-only JSONL send log (logs/send-log.jsonl).

Every append opens the file in append mode, writes one JSON line, flushes and
fsyncs before returning. Together with the ledger it lets the send history be
reconstructed if the ledger is ever lost.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_CLAIMED = "claimed"
EVENT_RESULT = "result"
EVENTS = (EVENT_CLAIMED, EVENT_RESULT)


class SendLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, event: str, **fields: Any) -> dict[str, Any]:
        if event not in EVENTS:
            raise ValueError(f"unknown send-log event {event!r}; expected one of {EVENTS}")
        record = {"ts": datetime.now(timezone.utc).isoformat(timespec="microseconds"), "event": event, **fields}
        line = json.dumps(record, ensure_ascii=False) + "\n"
        if "\n" in line[:-1]:
            raise ValueError("send-log record must serialize to a single line")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        return record

    def read(self) -> list[dict[str, Any]]:
        """All complete records. A torn final line (crash mid-write) is skipped."""
        if not self.path.exists():
            return []
        records = []
        lines = self.path.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                if i == len(lines) - 1:  # last line without newline: torn write
                    continue
                raise
        return records

    def exists(self) -> bool:
        return self.path.is_file() and self.path.stat().st_size > 0
