import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never touch the network: any outbound connection fails loudly."""
    def refuse(*a, **k):
        raise RuntimeError("network access in tests is not allowed")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
