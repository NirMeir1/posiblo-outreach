from pathlib import Path

import pytest

from conftest import REPO
from outreach.config import SETTINGS, ConfigError, load_config


def test_defaults(tmp_path: Path) -> None:
    c = load_config(root=tmp_path, environ={})
    assert c.ledger_path == tmp_path / "data" / "ledger.db"
    assert c.backup_dir == tmp_path / "backups"
    assert c.offsite_backup_dir is None
    assert c.log_dir == tmp_path / "logs"
    assert c.send_log_path == tmp_path / "logs" / "send-log.jsonl"
    assert c.batch_size == 25
    assert c.host_delay_seconds == 5
    assert c.breaker_threshold == 5
    assert c.sender_address == "TODO"
    assert c.sender_placeholders() == ["address"]
    assert c.stop_file == tmp_path / "STOP"
    assert c.template_path == tmp_path / "templates" / "consent_request_v1.txt"


def test_environment_overrides(tmp_path: Path) -> None:
    env = {"OUTREACH_BATCH_SIZE": "10", "OUTREACH_HOST_DELAY_SECONDS": "2.5", "OUTREACH_BREAKER_THRESHOLD": "3",
           "OUTREACH_LEDGER_PATH": "x/l.db", "OFFSITE_BACKUP_DIR": str(tmp_path / "cloud"),
           "SENDER_ADDRESS": "רחוב הרצל 1, תל אביב"}
    c = load_config(root=tmp_path, environ=env)
    assert (c.batch_size, c.host_delay_seconds, c.breaker_threshold) == (10, 2.5, 3)
    assert c.ledger_path == tmp_path / "x" / "l.db"
    assert c.offsite_backup_dir == tmp_path / "cloud"
    assert c.sender_address == "רחוב הרצל 1, תל אביב"
    assert c.sender_placeholders() == []


def test_dotenv_is_read_and_environment_wins(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "# comment\nOUTREACH_BATCH_SIZE=7\nexport SENDER_NAME=\"שם מ-env\"\nOUTREACH_BREAKER_THRESHOLD='9'\n",
        encoding="utf-8")
    c = load_config(root=tmp_path, environ={"OUTREACH_BREAKER_THRESHOLD": "4"})
    assert c.batch_size == 7
    assert c.sender_name == "שם מ-env"
    assert c.breaker_threshold == 4


def test_allow_live_in_dotenv_is_ignored(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("ALLOW_LIVE=1\n", encoding="utf-8")
    c = load_config(root=tmp_path, environ={})
    assert any("ALLOW_LIVE" in w for w in c.warnings)
    assert not hasattr(c, "allow_live")


@pytest.mark.parametrize(("name", "value"), [
    ("OUTREACH_BATCH_SIZE", "0"), ("OUTREACH_BATCH_SIZE", "abc"), ("OUTREACH_BREAKER_THRESHOLD", "-1"),
    ("OUTREACH_HOST_DELAY_SECONDS", "soon"), ("OUTREACH_LEDGER_PATH", " "),
])
def test_invalid_values_raise(tmp_path: Path, name: str, value: str) -> None:
    with pytest.raises(ConfigError):
        load_config(root=tmp_path, environ={name: value})


def test_bad_dotenv_line_raises(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("this is not a setting\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(root=tmp_path, environ={})


def test_every_setting_is_documented_in_readme() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    missing = [s.env for s in SETTINGS if f"`{s.env}`" not in readme]
    assert not missing, missing
