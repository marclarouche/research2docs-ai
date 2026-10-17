"""Optional local diagnostics contain only a fixed timestamped event vocabulary."""

import os
from pathlib import Path
from typing import Literal

from research2docs.core.errors import StorageError
from research2docs.core.models import utc_now

Event = Literal["storage_error", "project_saved", "ollama_checked", "model_selected"]


def record_event(root: Path, event: Event) -> None:
    """Append no titles, paths, model output, source content or exception strings.

    Logs are bounded to 64 KiB and one backup. No logging failure is hidden.
    """
    allowed = {"storage_error", "project_saved", "ollama_checked", "model_selected"}
    if event not in allowed:
        raise ValueError("Unsupported diagnostic event")
    path = root / "diagnostics.log"
    backup = root / "diagnostics.previous.log"
    try:
        if path.is_symlink() or backup.is_symlink():
            raise StorageError("Diagnostic files must not be symbolic links.")
        if path.exists() and path.stat().st_size > 65536:
            path.replace(backup)
        # O_NOFOLLOW protects the final component against symlink replacement.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(f"{utc_now().isoformat()} {event}\n")
    except OSError:
        raise StorageError(
            "Unable to write local diagnostics. Check storage permissions."
        ) from None
