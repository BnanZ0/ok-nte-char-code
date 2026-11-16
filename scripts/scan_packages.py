"""Run Semgrep over Python sources stored inside validated community archives."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from build_catalog import ValidationError, read_archive


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIRECTORY = REPOSITORY_ROOT / "codes"
SEMGREP_CONFIG = REPOSITORY_ROOT / ".semgrep.yml"


def _stage_sources(destination: Path) -> int:
    archives = sorted(ARCHIVE_DIRECTORY.glob("*.zip"), key=lambda path: path.name.lower())
    source_count = 0

    for index, archive_path in enumerate(archives, start=1):
        # Reuse the package validator before reading any submitted paths or contents.
        read_archive(archive_path)
        package_directory = destination / f"package-{index:03d}"
        with zipfile.ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                if not entry.filename.lower().endswith(".py"):
                    continue
                target = package_directory / entry.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
                source_count += 1
        print(f"package-{index:03d} <- {archive_path.name}")

    return source_count


def _run_scan(source_directory: Path, severity: str, *, fail_on_findings: bool) -> int:
    command = [
        "semgrep",
        "scan",
        "--metrics=off",
        "--no-git-ignore",
        "--config",
        str(SEMGREP_CONFIG),
        "--severity",
        severity,
    ]
    if fail_on_findings:
        command.append("--error")
    command.append(str(source_directory))
    return subprocess.run(command, cwd=REPOSITORY_ROOT, check=False).returncode


def main() -> int:
    if not SEMGREP_CONFIG.is_file():
        print(f"Semgrep configuration not found: {SEMGREP_CONFIG}", file=sys.stderr)
        return 2

    try:
        with tempfile.TemporaryDirectory(prefix="ok-nte-semgrep-") as temporary_directory:
            source_directory = Path(temporary_directory)
            source_count = _stage_sources(source_directory)
            if source_count == 0:
                print("No external Python files to scan.")
                return 0

            # Warnings are visible in the job log but do not block a PR.
            warning_status = _run_scan(source_directory, "WARNING", fail_on_findings=False)
            if warning_status:
                return warning_status

            # High-confidence policy violations fail the validation job.
            return _run_scan(source_directory, "ERROR", fail_on_findings=True)
    except (OSError, zipfile.BadZipFile, ValidationError) as error:
        print(f"Unable to scan community package source: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
