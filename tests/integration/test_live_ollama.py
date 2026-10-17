import pytest

from research2docs.core.config import OllamaSettings
from research2docs.generation.ollama_client import OllamaClient


@pytest.mark.ollama
def test_local_discovery_only():
    status = OllamaClient(OllamaSettings()).status()
    assert status.available, status.message
    assert all(not model.name.endswith(":cloud") for model in status.models)
