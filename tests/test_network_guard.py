"""The conftest network guard must block non-loopback traffic and allow loopback."""

import socket

import pytest

from conftest import RealNetworkBlocked


def test_guard_blocks_non_loopback_connect() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RealNetworkBlocked):
            s.connect(("192.0.2.1", 80))  # TEST-NET-1, never routed
        with pytest.raises(RealNetworkBlocked):
            s.connect_ex(("192.0.2.1", 80))
    finally:
        s.close()


def test_guard_blocks_dns_for_real_hosts() -> None:
    with pytest.raises(RealNetworkBlocked):
        socket.getaddrinfo("guard-test.invalid", 80)
    with pytest.raises(RealNetworkBlocked):
        socket.create_connection(("guard-test.invalid", 80), timeout=1)


def test_guard_allows_loopback() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.create_connection(server.getsockname(), timeout=5)
    conn, _ = server.accept()
    for s in (client, conn, server):
        s.close()
