"""Scan an exact publishable-source snapshot with Gitleaks; never copy ignored data."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    binary = shutil.which("gitleaks")
    if binary is None:
        raise SystemExit("Install Gitleaks from its official distribution, then retry.")
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    output = ROOT / "outputs"
    output.mkdir(exist_ok=True, mode=0o700)
    hashes = {}
    with tempfile.TemporaryDirectory(prefix="research2docs-source-scan-") as folder:
        snapshot = Path(folder)
        for name in sorted(set(filter(None, names))):
            source = ROOT / name
            if source.is_symlink() or not source.resolve().is_relative_to(ROOT):
                raise SystemExit("Refusing a symbolic link or outside-root source file.")
            if not source.is_file():
                continue
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        environment = {
            k: v
            for k, v in os.environ.items()
            if k not in {"GITLEAKS_CONFIG", "GITLEAKS_CONFIG_TOML"}
        }
        result = subprocess.run(
            [
                binary,
                "dir",
                str(snapshot),
                "--redact",
                "--ignore-gitleaks-allow",
                "--no-banner",
                "--report-format",
                "json",
                "--report-path",
                str(output / "gitleaks.json"),
                "--timeout",
                "60",
            ],
            cwd=snapshot,
            env=environment,
            check=False,
        )
    (output / "gitleaks-manifest.json").write_text(
        json.dumps(
            {
                "scope": "Publishable current source snapshot; ignored runtime data and Git history excluded",
                "files_sha256": hashes,
                "exit_code": result.returncode,
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
