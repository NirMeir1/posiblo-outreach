"""The one fixed message: templates/consent_request_v1.txt with {address} filled in.

No personalization: the only substitution is the sender address from config.
"""

from __future__ import annotations

import re

from .config import MESSAGE_VERSION, Config

PLACEHOLDER = "{address}"


class MessageError(ValueError):
    pass


def load_template(config: Config) -> str:
    path = config.template_path
    try:
        text = path.read_bytes().decode("utf-8")
    except FileNotFoundError:
        raise MessageError(f"template {path} is missing") from None
    except UnicodeDecodeError as e:
        raise MessageError(f"template {path} is not valid UTF-8: {e}") from None
    text = text.replace("\r\n", "\n")
    if text.count(PLACEHOLDER) != 1:
        raise MessageError(f"template {path} must contain {PLACEHOLDER} exactly once")
    return text


def render_message(config: Config) -> str:
    text = load_template(config).replace(PLACEHOLDER, config.sender_address)
    leftover = re.findall(r"\{[^{}\s]*\}", text)
    if leftover:
        raise MessageError(f"unfilled placeholder(s) in the message: {leftover}")
    return text


def message_version() -> str:
    return MESSAGE_VERSION
