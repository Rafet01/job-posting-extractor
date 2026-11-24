"""Settings that apply to every test."""

import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any attempt to open a connection, e.g. to Ollama, fail the test."""
    def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Tests must not open network connections. Mock the LLM client.")

    monkeypatch.setattr(socket.socket, "connect", refuse)
