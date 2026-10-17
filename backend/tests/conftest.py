import socket

import pytest

_real_connect = socket.socket.connect
_real_create = socket.create_connection
LOCAL = ("127.0.0.1", "localhost", "::1")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never touch the network: any connection to a non-loopback address fails loudly
    (loopback is allowed: asyncio uses a local socket pair on Windows)."""
    def guarded(self, addr, *a, **k):
        host = addr[0] if isinstance(addr, tuple) else addr
        if host not in LOCAL:
            raise RuntimeError(f"network access in tests is not allowed ({host})")
        return _real_connect(self, addr, *a, **k)

    def refuse(addr, *a, **k):
        if addr[0] not in LOCAL:
            raise RuntimeError(f"network access in tests is not allowed ({addr[0]})")
        return _real_create(addr, *a, **k)
    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket, "create_connection", refuse)
