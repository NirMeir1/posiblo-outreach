"""Checks that must pass before a command may touch the ledger or send.

Order (fixed): STOP file, ledger integrity, missing-ledger guard, template,
sender details (live mode only). All checks run; run_preflight() returns the
list of failure messages (empty list = OK).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .backup import list_backups
from .config import Config
from .sendlog import SendLog


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def preflight_checks(config: Config, *, live: bool = False, require_no_stop: bool = True) -> list[Check]:
    checks: list[Check] = []

    # 1. STOP file
    if require_no_stop:
        stop = config.stop_file
        checks.append(Check("stop_file", not stop.exists(),
                            f"STOP file present at {stop}: run halted. Clear it with the CLI when it is safe."
                            if stop.exists() else "no STOP file"))

    # 2. Ledger integrity (only if the file exists; mode=rw never creates it)
    ledger = config.ledger_path
    if ledger.exists():
        try:
            conn = sqlite3.connect(f"{ledger.resolve().as_uri()}?mode=rw", uri=True)
            try:
                rows = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
            finally:
                conn.close()
            ok = rows == ["ok"]
            detail = "integrity_check ok" if ok else f"ledger {ledger} failed integrity_check: {'; '.join(rows[:5])}"
        except sqlite3.Error as e:
            ok, detail = False, f"ledger {ledger} cannot be read as SQLite: {e}"
        checks.append(Check("ledger_integrity", ok, detail))
    else:
        checks.append(Check("ledger_integrity", True, f"ledger {ledger} does not exist yet (see next check)"))

    # 3. Missing ledger while history exists -> refuse
    if not ledger.exists():
        backups = list_backups(config.backup_dir) + list_backups(config.offsite_backup_dir)
        sendlog = SendLog(config.send_log_path)
        if backups or sendlog.exists():
            newest = max(backups, key=lambda p: p.name) if backups else None
            parts = [f"Ledger {ledger} is MISSING, but earlier history exists:"]
            if backups:
                parts.append(f"{len(backups)} backup(s), newest {newest}")
            if sendlog.exists():
                parts.append(f"send log {sendlog.path}")
            parts.append("Refusing to run: starting from an empty ledger could contact sites again.")
            if newest:
                parts.append(f"To restore: copy {newest} to {ledger}, then run `python -m outreach status` "
                             "and check the counts.")
            else:
                parts.append(f"No backup exists. The send log {sendlog.path} lists every claimed site; do not "
                             "continue until the ledger has been rebuilt from it.")
            checks.append(Check("ledger_missing", False, " ".join(parts)))
        else:
            checks.append(Check("ledger_missing", True, "no ledger and no history: fresh start"))
    else:
        checks.append(Check("ledger_missing", True, "ledger present"))

    # 4. Message template
    tpl = config.template_path
    checks.append(Check("template", tpl.is_file(),
                        f"template {tpl} found" if tpl.is_file() else f"template {tpl} is missing"))

    # 5. Sender details (live mode only)
    if live:
        bad = config.sender_placeholders()
        checks.append(Check("sender_details", not bad,
                            "sender details complete" if not bad else
                            f"sender details still contain a placeholder or are empty: {', '.join(bad)} "
                            "(set SENDER_* in the environment or .env)"))
    return checks


def run_preflight(config: Config, *, live: bool = False, require_no_stop: bool = True) -> list[str]:
    """Return the failure messages, in check order. Empty list means preflight passed."""
    return [c.detail for c in preflight_checks(config, live=live, require_no_stop=require_no_stop) if not c.ok]
