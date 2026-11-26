"""Ledger backups through the sqlite3 online backup API (never a raw file copy).

create_backup() writes backups/ledger-<UTC timestamp>.db, checks it with
PRAGMA integrity_check, keeps the newest KEEP files, and (when
OFFSITE_BACKUP_DIR is set) writes a second backup there the same way.
Any failure raises BackupError.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import Config

KEEP = 30
PREFIX = "ledger-"
SUFFIX = ".db"


class BackupError(RuntimeError):
    pass


@dataclass
class BackupResult:
    local: Path
    offsite: Path | None = None
    pruned: list[Path] = field(default_factory=list)


def _uri(path: Path, mode: str) -> str:
    return f"{path.resolve().as_uri()}?mode={mode}"


def list_backups(directory: Path | None) -> list[Path]:
    """Backup files in a folder, oldest first (names sort by timestamp)."""
    if directory is None or not directory.is_dir():
        return []
    return sorted(p for p in directory.glob(f"{PREFIX}*{SUFFIX}") if p.is_file())


def _new_name(directory: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"{PREFIX}{stamp}{SUFFIX}"
    n = 1
    while path.exists():
        path = directory / f"{PREFIX}{stamp}-{n}{SUFFIX}"
        n += 1
    return path


def backup_database(source: Path, dest: Path) -> None:
    """Copy `source` to `dest` with sqlite3's backup API and verify the result."""
    partial = dest.with_name(dest.name + ".partial")
    try:
        src = sqlite3.connect(_uri(source, "rw"), uri=True)  # mode=rw: never creates a missing file
        try:
            dst = sqlite3.connect(partial)
            try:
                src.backup(dst)
                dst.execute("PRAGMA journal_mode = DELETE")  # self-contained single file
                result = dst.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                dst.close()
        finally:
            src.close()
        if result != "ok":
            raise BackupError(f"backup {dest} failed integrity_check: {result}")
        os.replace(partial, dest)
    except BackupError:
        partial.unlink(missing_ok=True)
        raise
    except (sqlite3.Error, OSError) as e:
        partial.unlink(missing_ok=True)
        raise BackupError(f"backup of {source} to {dest} failed: {e}") from e


def prune(directory: Path, keep: int = KEEP) -> list[Path]:
    backups = list_backups(directory)
    doomed = backups[:-keep] if len(backups) > keep else []
    for p in doomed:
        p.unlink()
    return doomed


def create_backup(config: Config, keep: int = KEEP) -> BackupResult:
    ledger = config.ledger_path
    if not ledger.is_file():
        raise BackupError(f"ledger {ledger} does not exist; nothing to back up")
    config.backup_dir.mkdir(parents=True, exist_ok=True)
    local = _new_name(config.backup_dir)
    backup_database(ledger, local)
    result = BackupResult(local=local, pruned=prune(config.backup_dir, keep))

    offsite_dir = config.offsite_backup_dir
    if offsite_dir is not None:
        # Do not create it: a missing folder usually means the cloud drive is not mounted.
        if not offsite_dir.is_dir():
            raise BackupError(f"OFFSITE_BACKUP_DIR {offsite_dir} does not exist or is not a folder "
                              f"(local backup {local} was written)")
        offsite = offsite_dir / local.name
        try:
            backup_database(local, offsite)
        except BackupError as e:
            raise BackupError(f"offsite backup failed (local backup {local} was written): {e}") from e
        result.offsite = offsite
        result.pruned += prune(offsite_dir, keep)
    return result
