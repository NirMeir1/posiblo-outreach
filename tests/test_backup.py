import sqlite3
from pathlib import Path

import pytest

from outreach import backup as backup_mod
from outreach.backup import KEEP, BackupError, create_backup, list_backups
from outreach.config import load_config
from outreach.ledger import Ledger


def _config(root: Path, **env: str):
    return load_config(root=root, environ=env)


def _seed(cfg) -> None:
    with Ledger(cfg.ledger_path) as led:
        led.claim("example.co.il", domain="example.co.il", input_url="https://example.co.il")
        led.finish("example.co.il", "sent")
        led.claim("pending.co.il", domain="pending.co.il", input_url="https://pending.co.il")
        led.add_suppression("domain", "suppressed.co.il", reason="test")


def test_backup_is_valid_openable_database(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _seed(cfg)
    result = create_backup(cfg)
    assert result.local.parent == cfg.backup_dir
    assert result.local.name.startswith("ledger-") and result.local.suffix == ".db"
    conn = sqlite3.connect(f"{result.local.as_uri()}?mode=ro", uri=True)
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"  # single self-contained file
        rows = dict(conn.execute("SELECT site_key, status FROM sites").fetchall())
        assert rows == {"example.co.il": "sent", "pending.co.il": "pending"}
        assert conn.execute("SELECT value FROM suppression").fetchall() == [("suppressed.co.il",)]
    finally:
        conn.close()


def test_backup_includes_uncheckpointed_wal_content(tmp_path: Path) -> None:
    """Rows still only in the -wal file (ledger open, not checkpointed) are in the backup."""
    cfg = _config(tmp_path)
    led = Ledger(cfg.ledger_path)
    try:
        led.claim("wal-only.co.il", domain="wal-only.co.il", input_url="x")
        result = create_backup(cfg)
    finally:
        led.close()
    conn = sqlite3.connect(result.local)
    assert conn.execute("SELECT status FROM sites WHERE site_key='wal-only.co.il'").fetchone() == ("pending",)
    conn.close()


def test_backup_keeps_only_newest_30(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _seed(cfg)
    made = [create_backup(cfg).local for _ in range(KEEP + 5)]
    kept = list_backups(cfg.backup_dir)
    assert len(kept) == KEEP == 30
    assert kept == sorted(made)[-KEEP:]
    for old in sorted(made)[:5]:
        assert not old.exists()


def test_offsite_copy_is_written_and_valid(tmp_path: Path) -> None:
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    cfg = _config(tmp_path, OFFSITE_BACKUP_DIR=str(cloud))
    _seed(cfg)
    result = create_backup(cfg)
    assert result.offsite == cloud / result.local.name
    conn = sqlite3.connect(result.offsite)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0] == 2
    conn.close()


def test_offsite_missing_folder_fails_loudly(tmp_path: Path) -> None:
    cfg = _config(tmp_path, OFFSITE_BACKUP_DIR=str(tmp_path / "not-mounted"))
    _seed(cfg)
    with pytest.raises(BackupError, match="OFFSITE_BACKUP_DIR"):
        create_backup(cfg)
    assert not (tmp_path / "not-mounted").exists()  # never created silently
    assert len(list_backups(cfg.backup_dir)) == 1   # the local backup was still written


def test_offsite_copy_error_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    cfg = _config(tmp_path, OFFSITE_BACKUP_DIR=str(cloud))
    _seed(cfg)
    real = backup_mod.backup_database

    def failing(source: Path, dest: Path) -> None:
        if dest.parent == cloud:
            raise BackupError("disk full (simulated)")
        real(source, dest)

    monkeypatch.setattr(backup_mod, "backup_database", failing)
    with pytest.raises(BackupError, match="offsite backup failed"):
        create_backup(cfg)


def test_backup_of_missing_ledger_raises_and_creates_nothing(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    with pytest.raises(BackupError, match="does not exist"):
        create_backup(cfg)
    assert not cfg.ledger_path.exists()


def test_backup_uses_sqlite_backup_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every backup goes through sqlite3.Connection.backup; shutil is never used."""
    import shutil

    calls = []
    real_connect = sqlite3.connect

    class Spy:
        def __init__(self, conn): self._c = conn
        def backup(self, target, *a, **k):
            calls.append(1)
            return self._c.backup(target._c if isinstance(target, Spy) else target, *a, **k)
        def __getattr__(self, name): return getattr(self._c, name)

    monkeypatch.setattr(backup_mod.sqlite3, "connect", lambda *a, **k: Spy(real_connect(*a, **k)))
    for name in ("copy", "copy2", "copyfile"):
        monkeypatch.setattr(shutil, name, lambda *a, **k: pytest.fail("raw file copy used"))
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    cfg = _config(tmp_path, OFFSITE_BACKUP_DIR=str(cloud))
    monkeypatch.setattr(backup_mod.sqlite3, "connect", real_connect)
    _seed(cfg)
    monkeypatch.setattr(backup_mod.sqlite3, "connect", lambda *a, **k: Spy(real_connect(*a, **k)))
    create_backup(cfg)
    assert len(calls) == 2  # local + offsite
