"""Explicit local discovery and bounded structured inference; no pulls or cloud fallback."""

import http.client
import json
import socket
import threading
import time
from typing import Any

from pydantic import Field, ValidationError

from research2docs.core.config import OllamaSettings
from research2docs.core.errors import OllamaError
from research2docs.core.models import Record


class LocalModel(Record):
    name: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1f]+$")
    digest: str = Field(min_length=1, max_length=200)
    size_bytes: int = Field(ge=0)


class OllamaStatus(Record):
    available: bool
    message: str
    models: list[LocalModel] = Field(default_factory=list)


class OllamaClient:
    def __init__(self, settings: OllamaSettings):
        self.settings = OllamaSettings.model_validate_json(settings.model_dump_json())

    def _request(self, path: str, model: str | None = None) -> dict[str, Any]:
        # The validated host is a literal loopback IP; HTTPConnection does not use proxies.
        if path not in {"/api/tags", "/api/show"}:
            raise OllamaError("Unsupported local discovery request.")
        connection: http.client.HTTPConnection | None = None
        try:
            connection = http.client.HTTPConnection(
                self.settings.host, self.settings.port, timeout=self.settings.timeout_seconds
            )
            body = None if model is None else json.dumps({"model": model}).encode()
            connection.request(
                "GET" if body is None else "POST",
                path,
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            if response.status != 200:
                raise OllamaError("Ollama returned an unavailable or invalid response.")
            content = response.read(self.settings.max_response_bytes + 1)
            if len(content) > self.settings.max_response_bytes:
                raise OllamaError("Ollama response exceeded the local response limit.")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise OllamaError("Ollama returned an invalid response.")
            return result
        except (TimeoutError, OSError, http.client.HTTPException, ValueError, RecursionError):
            raise OllamaError(
                "Ollama is unavailable or returned invalid data. Check the local service."
            ) from None
        finally:
            if connection is not None:
                connection.close()

    def models(self) -> list[LocalModel]:
        response = self._request("/api/tags")
        raw = response.get("models")
        if not isinstance(raw, list) or len(raw) > 1000:
            raise OllamaError("Ollama returned an invalid model catalog.")
        models: list[LocalModel] = []
        names: set[str] = set()
        try:
            for item in raw:
                if not isinstance(item, dict):
                    raise TypeError("Invalid model entry")
                if item.get("remote_host") or item.get("remote_model"):
                    continue
                name = item.get("name")
                if isinstance(name, str) and name.endswith(":cloud"):
                    continue
                entry = LocalModel.model_validate(
                    {"name": name, "digest": item.get("digest"), "size_bytes": item.get("size")}
                )
                if entry.name in names:
                    raise ValueError("Duplicate model")
                names.add(entry.name)
                models.append(entry)
        except (TypeError, ValueError, ValidationError):
            raise OllamaError("Ollama returned an invalid model catalog.") from None
        return sorted(models, key=lambda item: item.name)

    def status(self) -> OllamaStatus:
        try:
            models = self.models()
            return OllamaStatus(available=True, message="Local Ollama is reachable.", models=models)
        except OllamaError:
            return OllamaStatus(
                available=False,
                message="Ollama is unavailable or its response is invalid. Check the local service.",
            )

    def validate_selection(self, name: str, *, context: int | None = None) -> LocalModel:
        match = next((model for model in self.models() if model.name == name), None)
        if match is None:
            raise OllamaError("Choose an installed local model from the discovered catalog.")
        details = self._request("/api/show", name)
        if (
            details.get("remote_host")
            or details.get("remote_model")
            or not isinstance(details.get("details"), dict)
            or not details["details"]
        ):
            raise OllamaError(
                "Choose a local model; cloud-backed or invalid model entries are rejected."
            )
        if context is not None:
            info = details.get("model_info", {})
            lengths = (
                [
                    value
                    for key, value in info.items()
                    if key.endswith(".context_length")
                    and isinstance(value, int)
                    and not isinstance(value, bool)
                ]
                if isinstance(info, dict)
                else []
            )
            if not lengths or min(lengths) < context:
                raise OllamaError(
                    "Model context is unknown or too small. Choose a compatible local model or lower the configured context budget."
                )
        return match

    def generate(
        self,
        name: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        *,
        timeout: float,
        max_bytes: int,
        context: int,
        output: int,
    ) -> str:
        """Recheck local selection; bound response bytes and slow-drip reads.

        A local server is trusted not to proxy a model after discovery.
        """
        self.validate_selection(name, context=context)
        response: http.client.HTTPResponse | None = None
        connection: http.client.HTTPConnection | None = None
        transport: socket.socket | None = None
        watchdog: threading.Timer | None = None
        deadline = time.monotonic() + timeout

        def expire() -> None:
            active = transport or (connection.sock if connection is not None else None)
            if active is not None:
                try:
                    active.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        try:
            connection = http.client.HTTPConnection(
                self.settings.host, self.settings.port, timeout=timeout
            )
            watchdog = threading.Timer(timeout, expire)
            watchdog.daemon = True
            watchdog.start()
            body = json.dumps(
                {
                    "model": name,
                    "messages": messages,
                    "format": schema,
                    "stream": False,
                    "think": False,
                    "keep_alive": "5m",
                    "options": {
                        "temperature": 0,
                        "seed": 0,
                        "num_ctx": context,
                        "num_predict": output,
                    },
                }
            ).encode()
            connection.request(
                "POST", "/api/chat", body=body, headers={"Content-Type": "application/json"}
            )
            # getresponse may detach a Connection:close socket, so retain the transport handle.
            transport = connection.sock
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if transport is not None:
                transport.settimeout(remaining)
            response = connection.getresponse()
            if response.status != 200:
                raise OllamaError("Local inference failed. Check the model and Ollama service.")
            content = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                if transport is not None:
                    transport.settimeout(remaining)
                block = response.read1(min(16384, max_bytes + 1 - len(content)))
                if not block:
                    break
                content.extend(block)
                if len(content) > max_bytes:
                    raise OllamaError("Model response exceeded the configured response limit.")
            result = json.loads(content)
            if (
                not isinstance(result, dict)
                or result.get("done") is not True
                or result.get("done_reason") != "stop"
                or result.get("model") != name
            ):
                raise OllamaError("Model response was incomplete or invalid. Try a shorter draft.")
            message = result.get("message")
            if (
                not isinstance(message, dict)
                or message.get("role") != "assistant"
                or message.get("tool_calls")
                or not isinstance(message.get("content"), str)
                or not message["content"].strip()
            ):
                raise OllamaError("Model did not return a valid structured draft.")
            return str(message["content"])
        except (OSError, TimeoutError, http.client.HTTPException, ValueError, RecursionError):
            raise OllamaError(
                "Local inference timed out or returned invalid data. Check Ollama and retry."
            ) from None
        finally:
            if watchdog is not None:
                watchdog.cancel()
            if response is not None:
                response.close()
            if connection is not None:
                connection.close()
