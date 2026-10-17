import io
import json

import pytest

from research2docs.core.config import OllamaSettings
from research2docs.core.errors import OllamaError
from research2docs.generation.ollama_client import OllamaClient


class Reply:
    def __init__(self, value, status=200):
        self.data = io.BytesIO(value)
        self.status = status
        self.closed = False

    def read1(self, size):
        return self.data.read(size)

    def close(self):
        self.closed = True


class Transport:
    def __init__(self):
        self.timeouts = []

    def settimeout(self, value):
        self.timeouts.append(value)


class Connection:
    def __init__(self, reply):
        self.reply = reply
        self.sock = Transport()
        self.calls = []
        self.closed = False

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    def getresponse(self):
        return self.reply

    def close(self):
        self.closed = True


@pytest.fixture
def transport(monkeypatch):
    client = OllamaClient(OllamaSettings())
    monkeypatch.setattr(client, "validate_selection", lambda *a, **k: None)
    return client


def invoke(client):
    return client.generate(
        "fixture:latest",
        [{"role": "system", "content": "Fixture"}],
        {},
        timeout=2.0,
        max_bytes=4096,
        context=8192,
        output=512,
    )


def response(**changes):
    value = {
        "model": "fixture:latest",
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": '{"sections":[]}'},
    }
    value.update(changes)
    return json.dumps(value).encode()


@pytest.mark.parametrize(
    "data,status",
    [
        (b"PRIVATE diagnostic", 500),
        (b"PRIVATE redirect", 302),
        (b"[]", 200),
        (b"bad json", 200),
        (b"x" * 4097, 200),
        (response(done=False), 200),
        (response(done_reason="length"), 200),
        (response(model="wrong"), 200),
        (response(message={"role": "assistant", "content": "", "tool_calls": [{}]}), 200),
    ],
)
def test_transport_failures_bounded_safe_and_closed(transport, monkeypatch, data, status):
    reply = Reply(data, status)
    conn = Connection(reply)
    monkeypatch.setattr("http.client.HTTPConnection", lambda *a, **k: conn)
    with pytest.raises(OllamaError) as failure:
        invoke(transport)
    assert "PRIVATE" not in str(failure.value)
    assert conn.closed and reply.closed and len(conn.calls) == 1


def test_structured_request_uses_fixed_endpoint_and_options(transport, monkeypatch):
    conn = Connection(Reply(response()))
    monkeypatch.setattr("http.client.HTTPConnection", lambda *a, **k: conn)
    assert invoke(transport) == '{"sections":[]}'
    args, kwargs = conn.calls[0]
    assert args == ("POST", "/api/chat")
    payload = json.loads(kwargs["body"])
    assert payload["stream"] is False and payload["think"] is False
    assert payload["options"]["num_predict"] == 512
    assert "tools" not in payload and "images" not in payload
    assert conn.sock.timeouts and conn.closed


def test_deadline_rejects_slow_drip(transport, monkeypatch):
    conn = Connection(Reply(response()))
    monkeypatch.setattr("http.client.HTTPConnection", lambda *a, **k: conn)
    ticks = iter([0.0, 0.5, 1.0, 3.0])
    monkeypatch.setattr(
        "research2docs.generation.ollama_client.time.monotonic", lambda: next(ticks)
    )
    with pytest.raises(OllamaError, match="timed out"):
        invoke(transport)
    assert conn.closed and conn.reply.closed


def test_inference_rechecks_model_before_request(monkeypatch):
    client = OllamaClient(OllamaSettings())
    monkeypatch.setattr(
        client,
        "validate_selection",
        lambda *a, **k: (_ for _ in ()).throw(OllamaError("Not local")),
    )
    monkeypatch.setattr(
        "http.client.HTTPConnection", lambda *a, **k: pytest.fail("No request allowed")
    )
    with pytest.raises(OllamaError, match="Not local"):
        invoke(client)


@pytest.mark.parametrize(
    "info", [{}, {"fixture.context_length": 4096}, {"fixture.context_length": True}]
)
def test_unknown_or_small_context_rejected(monkeypatch, info):
    from research2docs.generation.ollama_client import LocalModel

    client = OllamaClient(OllamaSettings())
    monkeypatch.setattr(
        client, "models", lambda: [LocalModel(name="fixture:latest", digest="sha", size_bytes=1)]
    )
    monkeypatch.setattr(
        client, "_request", lambda *a: {"details": {"family": "fixture"}, "model_info": info}
    )
    with pytest.raises(OllamaError, match="context"):
        client.validate_selection("fixture:latest", context=8192)


def test_watchdog_interrupts_slow_response_headers(transport, monkeypatch):
    """A socket pair exercises HTTP parsing without any listening/network endpoint."""
    import http.client
    import socket
    import threading
    import time

    left, right = socket.socketpair()
    stop = threading.Event()

    class PairConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = left

    original = PairConnection
    monkeypatch.setattr(
        "http.client.HTTPConnection", lambda *a, **k: original("127.0.0.1", timeout=2)
    )

    def peer():
        try:
            right.recv(8192)
            right.sendall(b"HTTP/1.1 200 OK\r\nX-Slow: ")
            while not stop.wait(0.02):
                right.sendall(b"a")
        except OSError:
            pass
        finally:
            right.close()

    thread = threading.Thread(target=peer, daemon=True)
    thread.start()
    started = time.monotonic()
    try:
        with pytest.raises(OllamaError):
            transport.generate(
                "fixture:latest", [], {}, timeout=0.15, max_bytes=4096, context=8192, output=512
            )
        assert time.monotonic() - started < 1.0
    finally:
        stop.set()
        left.close()
        thread.join(timeout=1)
    assert not thread.is_alive()
