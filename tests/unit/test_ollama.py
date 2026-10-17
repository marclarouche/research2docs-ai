import io
import json
from typing import ClassVar

import pytest

from research2docs.core.config import OllamaSettings, Settings
from research2docs.core.errors import OllamaError
from research2docs.generation.ollama_client import OllamaClient
from research2docs.services.workspace_service import WorkspaceService


class Reply:
    status = 200

    def __init__(self, data):
        self.data = io.BytesIO(data)

    def read(self, n):
        return self.data.read(n)


class Connection:
    responses: ClassVar[list[Reply]] = []
    calls: ClassVar[list[tuple]] = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.closed = False

    def request(self, method, path, body=None, headers=None):
        self.calls.append((self.host, method, path, body))

    def getresponse(self):
        return self.responses.pop(0)

    def close(self):
        self.closed = True


def catalog():
    return {
        "models": [
            {"name": "local:latest", "digest": "sha", "size": 12},
            {"name": "remote:cloud", "digest": "remote", "size": 0},
        ]
    }


def test_read_only_discovery_and_persistent_model_selection(tmp_path, monkeypatch):
    monkeypatch.setattr("http.client.HTTPConnection", Connection)
    Connection.calls: ClassVar[list[tuple]] = []
    Connection.responses = [
        Reply(json.dumps(catalog()).encode()),
        Reply(json.dumps(catalog()).encode()),
        Reply(b'{"details":{"family":"fixture"}}'),
    ]
    workspace = WorkspaceService(Settings(data_dir=str(tmp_path)))
    status = workspace.check_ollama()
    assert status.available and [m.name for m in status.models] == ["local:latest"]
    workspace.select_model("local:latest")
    assert WorkspaceService(Settings(data_dir=str(tmp_path))).selected_model() == "local:latest"
    assert [call[2] for call in Connection.calls] == ["/api/tags", "/api/tags", "/api/show"]
    assert all(call[0] == "127.0.0.1" for call in Connection.calls)


@pytest.mark.parametrize(
    "data",
    [
        b"not json",
        b"[]",
        b'{"models":null}',
        b'{"models":[{}]}',
        b'{"models":[{"name":"a","digest":"b","size":true}]}',
        b"x" * 2049,
    ],
)
def test_invalid_and_bounded_responses_fail_safely(monkeypatch, data):
    monkeypatch.setattr("http.client.HTTPConnection", Connection)
    Connection.responses = [Reply(data)]
    status = OllamaClient(OllamaSettings(max_response_bytes=1024)).status()
    assert not status.available and not status.models
    assert data.decode(errors="replace") not in status.message


def test_redirect_is_not_followed(monkeypatch):
    monkeypatch.setattr("http.client.HTTPConnection", Connection)
    reply = Reply(b"private remote response")
    reply.status = 302
    Connection.responses = [reply]
    Connection.calls: ClassVar[list[tuple]] = []
    assert not OllamaClient(OllamaSettings()).status().available
    assert len(Connection.calls) == 1


def test_unavailable_service_has_no_remote_fallback(monkeypatch):
    def denied(*args, **kwargs):
        raise TimeoutError("PRIVATE endpoint detail")

    monkeypatch.setattr("http.client.HTTPConnection", denied)
    # Construction failures must also be translated to a safe typed status.
    assert not OllamaClient(OllamaSettings()).status().available


def test_cloud_backed_selected_model_is_rejected(monkeypatch):
    monkeypatch.setattr("http.client.HTTPConnection", Connection)
    Connection.responses = [
        Reply(json.dumps(catalog()).encode()),
        Reply(b'{"details":{},"remote_host":"https://example.invalid"}'),
    ]
    with pytest.raises(OllamaError):
        OllamaClient(OllamaSettings()).validate_selection("local:latest")
