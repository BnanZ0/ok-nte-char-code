"""Run Semgrep over Python sources stored inside community package archives."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from build_catalog import ValidationError, read_archive


ROOT = Path(__file__).resolve().parents[1]
CODES = ROOT / "codes"
CONFIG = ROOT / ".semgrep.yml"


def _archives(raw: str | None) -> list[Path]:
    if raw is None:
        return sorted(CODES.glob("*.zip"), key=lambda path: path.name.lower())

    names = json.loads(raw)
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
        raise ValidationError("Package paths must be a JSON string array")

    result = []
    for name in names:
        path = PurePosixPath(name)
        if (
            "\\" in name
            or len(path.parts) != 2
            or path.parts[0] != "codes"
            or path.suffix.lower() != ".zip"
        ):
            raise ValidationError(f"Invalid package path: {name}")
        archive = CODES / path.name
        if not archive.is_file():
            raise ValidationError(f"Package archive is missing: {name}")
        if archive not in result:
            result.append(archive)
    return result


def _stage(destination: Path, archives: list[Path]) -> tuple[int, dict[str, str]]:
    count = 0
    packages = {}
    for index, archive_path in enumerate(archives, 1):
        read_archive(archive_path)
        package = destination / f"package-{index:03d}"
        packages[package.name] = PurePosixPath("codes", archive_path.name).as_posix()
        with zipfile.ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                if entry.filename.lower().endswith(".py"):
                    target = package / entry.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(entry))
                    count += 1
    return count, packages


def _scan(source: Path, severity: str, fail: bool) -> tuple[int, list[dict]]:
    command = [
        "semgrep", "scan", "--metrics=off", "--no-git-ignore",
        "--config", str(CONFIG), "--severity", severity, "--json",
    ]
    if fail:
        command.append("--error")
    completed = subprocess.run(
        command + [str(source)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    try:
        findings = json.loads(completed.stdout).get("results", [])
    except (json.JSONDecodeError, AttributeError) as error:
        raise RuntimeError(f"Semgrep did not return JSON results: {error}") from error
    print(f"Semgrep {severity}: {len(findings)} finding(s)")
    return completed.returncode, findings


def _findings(results: list[dict], source: Path, packages: dict[str, str]) -> list[dict]:
    output = []
    root = source.resolve()
    for result in results:
        path = Path(result["path"])
        if not path.is_absolute():
            path = source / path
        try:
            relative = path.resolve().relative_to(root)
        except ValueError:
            continue
        extra = result.get("extra", {})
        if len(relative.parts) < 2 or relative.parts[0] not in packages:
            continue
        output.append({
            "archive": packages[relative.parts[0]],
            "path": PurePosixPath(*relative.parts[1:]).as_posix(),
            "line": result.get("start", {}).get("line", 1),
            "rule_id": result.get("check_id", "unknown"),
            "severity": extra.get("severity", "WARNING"),
            "message": extra.get("message", ""),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives-json", help="Only scan these codes/*.zip paths")
    parser.add_argument("--report-file", type=Path, help="Write findings as JSON")
    args = parser.parse_args()
    if not CONFIG.is_file():
        print(f"Semgrep configuration not found: {CONFIG}", file=sys.stderr)
        return 2

    try:
        archives = _archives(args.archives_json)
        findings = []
        warning_status = error_status = 0
        with tempfile.TemporaryDirectory(prefix="ok-nte-semgrep-") as temporary:
            source = Path(temporary)
            count, packages = _stage(source, archives)
            if count:
                warning_status, warning_results = _scan(source, "WARNING", False)
                findings += _findings(warning_results, source, packages)
                if warning_status == 0:
                    error_status, error_results = _scan(source, "ERROR", True)
                    findings += _findings(error_results, source, packages)

        if args.report_file:
            args.report_file.parent.mkdir(parents=True, exist_ok=True)
            args.report_file.write_text(json.dumps({
                "schema_version": 1,
                "packages": [PurePosixPath("codes", path.name).as_posix() for path in archives],
                "findings": findings,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for item in findings:
            print(f"{item['archive']}:{item['path']}:{item['line']} {item['rule_id']}")
        return warning_status or error_status
    except (OSError, zipfile.BadZipFile, ValidationError, json.JSONDecodeError, RuntimeError) as error:
        print(f"Unable to scan package source: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
