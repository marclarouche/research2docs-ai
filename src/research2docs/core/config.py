"""Bounded operator-owned TOML, explicit storage override and loopback-only transport."""

import ipaddress
import os
import tomllib
from pathlib import Path

from pydantic import Field, ValidationError, field_validator

from research2docs.core.errors import ConfigurationError
from research2docs.core.models import Record
from research2docs.generation.models import GenerationLimits
from research2docs.ingestion.models import ImportLimits
from research2docs.verification.models import VerificationLimits


class OllamaSettings(Record):
    host: str = "127.0.0.1"
    port: int = Field(default=11434, ge=1, le=65535)
    timeout_seconds: float = Field(default=3.0, ge=0.1, le=30)
    max_response_bytes: int = Field(default=1048576, ge=1024, le=4194304)

    @field_validator("host")
    @classmethod
    def loopback(cls, value: str) -> str:
        if value == "localhost":
            return "127.0.0.1"
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            raise ValueError("Only literal loopback addresses are allowed") from None
        if not address.is_loopback:
            raise ValueError("Only literal loopback addresses are allowed")
        return str(address)


class Settings(Record):
    data_dir: str = Field(default="data", min_length=1, max_length=4096)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    ingestion: ImportLimits = Field(default_factory=ImportLimits)
    generation: GenerationLimits = Field(default_factory=GenerationLimits)
    verification: VerificationLimits = Field(default_factory=VerificationLimits)


def load_settings(root: Path) -> Settings:
    """Load fixed config beneath the app root; no source-controlled config discovery."""
    try:
        with (root / "config/research2docs.toml").open("rb") as stream:
            raw = stream.read(32769)
        if len(raw) > 32768:
            raise ValueError("Config too large")
        settings = Settings.model_validate(tomllib.loads(raw.decode("utf-8")))
        override = os.environ.get("RESEARCH2DOCS_DATA_DIR")
        data_dir = Path(override if override is not None else settings.data_dir).expanduser()
        if override == "":
            raise ValueError("Empty storage override")
        if not data_dir.is_absolute():
            data_dir = root / data_dir
        return Settings(
            data_dir=str(data_dir.resolve()),
            ollama=settings.ollama,
            ingestion=settings.ingestion,
            generation=settings.generation,
            verification=settings.verification,
        )
    except (OSError, ValueError, ValidationError):
        raise ConfigurationError(
            "Unable to load settings. Review the local configuration."
        ) from None
