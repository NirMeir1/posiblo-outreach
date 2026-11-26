"""Test-wide safety net: no test may touch the real network.

An autouse fixture replaces socket connect/connect_ex and getaddrinfo so that
anything other than loopback (127.0.0.0/8, ::1, localhost) raises
RealNetworkBlocked before a packet is sent or a DNS query is made.
"""

from __future__ import annotations

import ipaddress
import os
import shutil
import socket
from pathlib import Path

import pytest


class RealNetworkBlocked(RuntimeError):
    pass


def _is_loopback(host: object) -> bool:
    if host in (None, "", b"", "localhost", b"localhost"):
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo


def _guard(sock: socket.socket, address: object) -> None:
    if sock.family in (socket.AF_INET, socket.AF_INET6):
        host = address[0] if isinstance(address, tuple) else address
        if not _is_loopback(host):
            raise RealNetworkBlocked(f"test tried to connect to non-loopback address {address!r}")


def _connect(self: socket.socket, address: object) -> None:
    _guard(self, address)
    return _real_connect(self, address)


def _connect_ex(self: socket.socket, address: object) -> int:
    _guard(self, address)
    return _real_connect_ex(self, address)


def _getaddrinfo(host, *args, **kwargs):
    if not _is_loopback(host):
        raise RealNetworkBlocked(f"test tried to resolve non-loopback host {host!r}")
    return _real_getaddrinfo(host, *args, **kwargs)


@pytest.fixture(autouse=True)
def _block_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)


@pytest.fixture(scope="session")
def httpserver_listen_address() -> tuple[str, int]:
    """pytest-httpserver listens on 127.0.0.1 only (IPv4 loopback).

    With the default "localhost", clients try ::1 first and Windows spends
    about 2 s retrying the refused IPv6 connection on every request.
    """
    return ("127.0.0.1", 0)


REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_outreach_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may inherit settings or ALLOW_LIVE from the developer's shell."""
    for name in list(os.environ):
        if name.startswith(("OUTREACH_", "SENDER_")) or name in ("OFFSITE_BACKUP_DIR", "ALLOW_LIVE"):
            monkeypatch.delenv(name, raising=False)


class FakeFetcher:
    """Serves HTML by URL without any network. Unknown URLs are 404s. Records every URL requested."""

    def __init__(self, pages: dict[str, str], blocked=frozenset(), redirects=None, on_get=None):
        self.pages, self.blocked, self.redirects = pages, set(blocked), redirects or {}
        self.on_get = on_get
        self.requested: list[str] = []

    def get(self, url: str):
        from outreach.fetch import FETCH_ERROR, OK, ROBOTS_BLOCKED, FetchResult
        self.requested.append(url)
        if self.on_get:
            self.on_get(url)
        if url in self.blocked:
            return FetchResult(url, url, ROBOTS_BLOCKED, detail="robots.txt does not allow it")
        final = self.redirects.get(url, url)
        if final in self.pages:
            return FetchResult(url, final, OK, 200, "text/html; charset=utf-8", self.pages[final],
                               redirects=[final] if final != url else [])
        return FetchResult(url, final, FETCH_ERROR, 404, detail="HTTP 404")


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throw-away project root (cwd) containing the real message template."""
    root = tmp_path / "project"
    (root / "templates").mkdir(parents=True)
    shutil.copyfile(REPO / "templates" / "consent_request_v1.txt", root / "templates" / "consent_request_v1.txt")
    monkeypatch.chdir(root)
    return root
