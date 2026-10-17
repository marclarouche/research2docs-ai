"""Private fixed-command parser worker. No database, UI or source-driven commands."""

import contextlib
import json
import os
import sys
from pathlib import Path

from research2docs.core.errors import IngestionError
from research2docs.ingestion.models import ImportLimits, SourceType


def deny_network(event: str, args: tuple[object, ...]) -> None:
    if event in {
        "socket.connect",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "os.system",
        "os.posix_spawn",
    }:
        raise PermissionError("Parser workers cannot connect or execute commands")


def run(input_path: Path, output_path: Path, kind: SourceType, limits: ImportLimits) -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (12582912, 12582912))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
    # macOS rejects RLIMIT_AS; the parent monitors resident memory and kills excess.
    sys.addaudithook(deny_network)
    # Parser diagnostics can contain untrusted text: discard Python stdout as well as CLI streams.
    with (
        open(os.devnull, "w") as sink,
        contextlib.redirect_stdout(sink),
        contextlib.redirect_stderr(sink),
    ):
        from research2docs.ingestion.parsers import parse

        with input_path.open("rb") as stream:
            data = stream.read(limits.max_file_bytes + 1)
        parsed = parse(data, kind, limits)
    payload = {"ok": True, "parsed": parsed.model_dump(mode="json")}
    encoded = json.dumps(payload, ensure_ascii=False).encode()
    if len(encoded) > 12582912:
        raise IngestionError("worker_response_limit")
    output_path.write_bytes(encoded)


def main() -> None:
    # All arguments are constructed by runner.py, never by a document or model.
    input_path, output_path, kind, config_path = sys.argv[1:]
    try:
        limits = ImportLimits.model_validate_json(Path(config_path).read_bytes())
        if kind not in {"pdf", "docx", "markdown", "txt", "html"}:
            raise IngestionError("unsupported_type")
        from typing import cast

        run(Path(input_path), Path(output_path), cast(SourceType, kind), limits)
    except IngestionError as error:
        Path(output_path).write_text(json.dumps({"ok": False, "reason": error.reason}))
    except Exception:  # noqa: BLE001 -- Final process boundary must not expose parser/source diagnostics.
        # Raw native/parser messages must never reach application logs/UI.
        Path(output_path).write_text('{"ok":false,"reason":"parser_failed"}')


if __name__ == "__main__":
    main()
