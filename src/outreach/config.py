"""Settings, from the environment and an optional .env file in the project root.

Precedence: real environment variable > .env file > default.
Relative paths are resolved against the project root (the directory the
command is run from). Every setting is listed in SETTINGS and documented in
README.md.

ALLOW_LIVE is deliberately NOT a setting here and is never read from .env:
live sending may only be enabled by a variable set in the real environment.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

TEMPLATE_RELPATH = Path("templates") / "consent_request_v1.txt"
MESSAGE_VERSION = "consent_request_v1"
STOP_FILENAME = "STOP"
SEND_LOG_FILENAME = "send-log.jsonl"
PLACEHOLDER = "TODO"

# Keys that .env may never set.
_ENV_ONLY = {"ALLOW_LIVE"}


@dataclass(frozen=True)
class Setting:
    env: str
    attr: str
    default: str
    kind: str  # path | optional_path | int | float | str
    help: str


SETTINGS: tuple[Setting, ...] = (
    Setting("OUTREACH_LEDGER_PATH", "ledger_path", "data/ledger.db", "path", "SQLite ledger file."),
    Setting("OUTREACH_BACKUP_DIR", "backup_dir", "backups", "path", "Local backup folder (newest 30 kept)."),
    Setting("OFFSITE_BACKUP_DIR", "offsite_backup_dir", "", "optional_path",
            "Optional second backup folder, e.g. a private cloud-synced folder. Must already exist."),
    Setting("OUTREACH_LOG_DIR", "log_dir", "logs", "path", "Folder for the append-only send log."),
    Setting("OUTREACH_BATCH_SIZE", "batch_size", "25", "int", "Sites per batch created by ingest."),
    Setting("OUTREACH_HOST_DELAY_SECONDS", "host_delay_seconds", "5", "float",
            "Minimum seconds between two requests to the same host."),
    Setting("OUTREACH_BREAKER_THRESHOLD", "breaker_threshold", "5", "int",
            "Consecutive failures that halt a run (circuit breaker)."),
    Setting("SENDER_NAME", "sender_name", "ניר מאיר", "str", "Sender name filled into contact forms."),
    Setting("SENDER_EMAIL", "sender_email", "posiblo.contact@gmail.com", "str", "Sender email filled into forms."),
    Setting("SENDER_PHONE", "sender_phone", "052-251-8189", "str", "Sender phone filled into forms."),
    Setting("SENDER_ADDRESS", "sender_address", PLACEHOLDER, "str",
            "Sender postal address, inserted into the message. Defaults to TODO; live sending refuses while it is TODO."),
)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    root: Path
    ledger_path: Path
    backup_dir: Path
    offsite_backup_dir: Path | None
    log_dir: Path
    batch_size: int
    host_delay_seconds: float
    breaker_threshold: int
    sender_name: str
    sender_email: str
    sender_phone: str
    sender_address: str
    warnings: tuple[str, ...] = field(default=())

    @property
    def stop_file(self) -> Path:
        return self.root / STOP_FILENAME

    @property
    def send_log_path(self) -> Path:
        return self.log_dir / SEND_LOG_FILENAME

    @property
    def template_path(self) -> Path:
        return self.root / TEMPLATE_RELPATH

    def sender_details(self) -> dict[str, str]:
        return {"name": self.sender_name, "email": self.sender_email,
                "phone": self.sender_phone, "address": self.sender_address}

    def sender_placeholders(self) -> list[str]:
        """Sender fields that are empty or still contain a TODO placeholder."""
        return [k for k, v in self.sender_details().items()
                if not v.strip() or PLACEHOLDER.lower() in v.lower()]


def parse_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser: KEY=VALUE lines, # comments, optional quotes and 'export '."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not m:
            raise ConfigError(f"{path}:{n}: not KEY=VALUE")
        key, value = m.group(1), m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_config(root: str | Path | None = None, environ: Mapping[str, str] | None = None,
                use_dotenv: bool = True) -> Config:
    root = Path(root) if root is not None else Path.cwd()
    environ = os.environ if environ is None else environ
    warnings: list[str] = []
    dotenv = parse_dotenv(root / ".env") if use_dotenv else {}
    for key in _ENV_ONLY & dotenv.keys():
        warnings.append(f".env sets {key}; ignored (it can only come from the real environment)")
        del dotenv[key]

    values: dict[str, object] = {}
    for s in SETTINGS:
        raw = environ.get(s.env, dotenv.get(s.env, s.default))
        values[s.attr] = _convert(s, raw, root)
    return Config(root=root, warnings=tuple(warnings), **values)  # type: ignore[arg-type]


def _convert(s: Setting, raw: str, root: Path) -> object:
    raw = raw.strip()
    if s.kind in ("path", "optional_path"):
        if not raw:
            if s.kind == "optional_path":
                return None
            raise ConfigError(f"{s.env} must not be empty")
        p = Path(raw).expanduser()
        return p if p.is_absolute() else root / p
    if s.kind == "int":
        try:
            v = int(raw)
        except ValueError:
            raise ConfigError(f"{s.env} must be an integer, got {raw!r}") from None
        if v < 1:
            raise ConfigError(f"{s.env} must be >= 1, got {v}")
        return v
    if s.kind == "float":
        try:
            f = float(raw)
        except ValueError:
            raise ConfigError(f"{s.env} must be a number, got {raw!r}") from None
        if f < 0:
            raise ConfigError(f"{s.env} must be >= 0, got {f}")
        return f
    return raw
