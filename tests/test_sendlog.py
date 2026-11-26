import json
import os
from pathlib import Path

import pytest

from outreach import sendlog as sendlog_mod
from outreach.sendlog import SendLog


def test_append_writes_one_json_line_per_event(tmp_path: Path) -> None:
    log = SendLog(tmp_path / "logs" / "send-log.jsonl")
    log.append("claimed", site_key="example.co.il", batch_id="B0001")
    log.append("result", site_key="example.co.il", status="sent", detail="תודה, ההודעה נשלחה")
    lines = (tmp_path / "logs" / "send-log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first, second = (json.loads(l) for l in lines)
    assert first["event"] == "claimed" and first["site_key"] == "example.co.il" and first["ts"]
    assert second["detail"] == "תודה, ההודעה נשלחה"  # Hebrew kept as text
    assert log.read() == [first, second]


def test_each_append_is_flushed_and_fsynced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    synced: list[int] = []
    real_fsync = os.fsync

    def spy(fd: int) -> None:
        synced.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(sendlog_mod.os, "fsync", spy)
    log = SendLog(tmp_path / "send-log.jsonl")
    for i in range(3):
        log.append("claimed", site_key=f"s{i}.co.il")
        assert len(synced) == i + 1
        # flushed before fsync: an independent reader sees the line immediately
        assert len((tmp_path / "send-log.jsonl").read_text(encoding="utf-8").splitlines()) == i + 1


def test_append_only_never_truncates(tmp_path: Path) -> None:
    path = tmp_path / "send-log.jsonl"
    path.write_text('{"ts": "old", "event": "claimed", "site_key": "old.co.il"}\n', encoding="utf-8")
    SendLog(path).append("result", site_key="old.co.il", status="sent")
    records = SendLog(path).read()
    assert [r["ts"] for r in records][0] == "old"
    assert len(records) == 2


def test_unknown_event_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SendLog(tmp_path / "x.jsonl").append("deleted", site_key="x")
    assert not (tmp_path / "x.jsonl").exists()


def test_torn_last_line_is_skipped_on_read(tmp_path: Path) -> None:
    path = tmp_path / "send-log.jsonl"
    SendLog(path).append("claimed", site_key="a.co.il")
    with open(path, "a", encoding="utf-8") as f:
        f.write('{"ts": "2026-01-01", "event": "res')  # crash mid-write
    assert [r["site_key"] for r in SendLog(path).read()] == ["a.co.il"]
