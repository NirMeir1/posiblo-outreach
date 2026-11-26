"""Test-wide safety net: no test may touch the real network.

An autouse fixture replaces socket connect/connect_ex and getaddrinfo so that
anything other than loopback (127.0.0.0/8, ::1, localhost) raises
RealNetworkBlocked before a packet is sent or a DNS query is made.
"""

from __future__ import annotations

import ipaddress
import socket

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
