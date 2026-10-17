"""One fixed interpreter command, bounded files and a killed/reaped parser worker."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil
from pydantic import ValidationError

from research2docs.core.errors import IngestionError
from research2docs.ingestion.models import ImportLimits, ParsedSource, SourceType

SAFE_REASONS = {
    "extraction_limit",
    "invalid_utf8",
    "binary_text",
    "content_type_mismatch",
    "invalid_docx_package",
    "unsafe_docx_package",
    "archive_expansion_limit",
    "archive_ratio_limit",
    "unsafe_xml",
    "encrypted_pdf",
    "pdf_page_limit",
    "file_size_limit",
    "no_extractable_text",
    "worker_response_limit",
    "unsupported_type",
    "parser_failed",
}


def extract(data: bytes, kind: SourceType, limits: ImportLimits) -> ParsedSource:
    if not data or len(data) > limits.max_file_bytes:
        raise IngestionError("file_size_limit")
    if os.name != "posix":
        raise IngestionError(
            "worker_platform", "Bounded parser workers require a supported POSIX platform."
        )
    with tempfile.TemporaryDirectory(prefix="research2docs-parser-") as folder:
        root = Path(folder)
        source = root / "source.bin"
        result = root / "result.json"
        config = root / "limits.json"
        source.write_bytes(data)
        config.write_text(limits.model_dump_json())
        try:
            with subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "research2docs.ingestion.worker",
                    str(source),
                    str(result),
                    kind,
                    str(config),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) as process:
                try:
                    deadline = time.monotonic() + limits.parser_seconds
                    monitored = psutil.Process(process.pid)
                    while process.poll() is None:
                        failure = None
                        if time.monotonic() >= deadline:
                            failure = "parser_timeout"
                        else:
                            try:
                                if monitored.memory_info().rss > limits.memory_bytes:
                                    failure = "parser_memory_limit"
                            except psutil.NoSuchProcess:
                                break
                        if failure is not None:
                            process.kill()
                            process.wait()
                            raise IngestionError(
                                failure,
                                "Document processing exceeded its time or memory limit. Try a smaller file.",
                            )
                        time.sleep(0.02)
                    code = process.wait()
                except psutil.Error:
                    raise IngestionError(
                        "parser_monitor_unavailable", "Unable to monitor the parser worker safely."
                    ) from None
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            if code != 0 or not result.is_file() or result.is_symlink():
                raise IngestionError("parser_resource_or_process_failure")
            with result.open("rb") as stream:
                raw = stream.read(12582913)
            if len(raw) > 12582912:
                raise IngestionError("worker_response_limit")
            response = json.loads(raw)
            if not isinstance(response, dict):
                raise IngestionError("parser_failed")
            if response.get("ok") is not True:
                reason = response.get("reason")
                raise IngestionError(
                    reason
                    if isinstance(reason, str) and reason in SAFE_REASONS
                    else "parser_failed"
                )
            parsed = ParsedSource.model_validate(response.get("parsed"))
            if (
                parsed.source_type != kind
                or len(parsed.sections) > limits.max_sections
                or sum(len(s.text) for s in parsed.sections) > limits.max_text_chars
                or [s.ordinal for s in parsed.sections] != list(range(len(parsed.sections)))
            ):
                raise IngestionError("invalid_extraction")
            return parsed
        except (OSError, ValueError, ValidationError, RecursionError):
            raise IngestionError("parser_failed") from None
