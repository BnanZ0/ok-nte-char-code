"""Validate community team archives and build the public teams catalog.

The builder intentionally never imports submitted Python modules.  It only
validates archive structure, metadata, and Python syntax before publishing the
metadata required by OK-NTE's workshop.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable


CATALOG_FORMAT_VERSION = 1
PACKAGE_FORMAT_VERSION = 1


class ValidationError(ValueError):
    """Raised when a submitted community archive does not follow the format."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _root_file_name(value: object, field: str) -> str:
    name = _text(value, field).replace("\\", "/")
    if "/" in name or name in {".", ".."} or ".." in name.split("/"):
        raise ValidationError(f"{field} must name a file in the archive root")
    return name


def _display(value: object, field: str, class_name: str) -> dict[str, str]:
    if value is None:
        return {"zh_CN": class_name, "en_US": class_name}
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be an object")
    zh_name = value.get("zh_CN") or value.get("en_US") or class_name
    en_name = value.get("en_US") or value.get("zh_CN") or class_name
    return {
        "zh_CN": _text(zh_name, f"{field}.zh_CN"),
        "en_US": _text(en_name, f"{field}.en_US"),
    }


def _validate_slots(value: object) -> tuple[list[dict], set[str]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 4:
        raise ValidationError("slots must contain between one and four entries")

    slots: list[dict] = []
    external_files: set[str] = set()
    used_indices: set[int] = set()
    for raw_slot in value:
        if not isinstance(raw_slot, dict):
            raise ValidationError("each slot must be an object")
        index = raw_slot.get("index")
        if not isinstance(index, int) or not 0 <= index < 4 or index in used_indices:
            raise ValidationError("slot indices must be unique integers from 0 to 3")
        used_indices.add(index)
        kind = raw_slot.get("kind")
        if kind == "builtin":
            impl_id = _text(raw_slot.get("impl_id"), "builtin impl_id")
            if not impl_id.startswith("builtin:"):
                raise ValidationError("builtin impl_id must start with 'builtin:'")
            display = _display(raw_slot.get("display"), "builtin display", impl_id[8:])
            slots.append(
                {"index": index, "kind": "builtin", "impl_id": impl_id, "display": display}
            )
            continue
        if kind == "external":
            filename = _root_file_name(raw_slot.get("file"), "external file")
            if not filename.lower().endswith(".py"):
                raise ValidationError("external file must end with .py")
            if filename in external_files:
                raise ValidationError("each external file may be referenced by only one slot")
            external_files.add(filename)
            class_name = _text(raw_slot.get("class_name"), "external class_name")
            display = _display(raw_slot.get("display"), "external display", class_name)
            slots.append(
                {
                    "index": index,
                    "kind": "external",
                    "file": filename,
                    "class_name": class_name,
                    "display": display,
                }
            )
            continue
        raise ValidationError("slot kind must be 'builtin' or 'external'")
    return sorted(slots, key=lambda slot: slot["index"]), external_files


def read_archive(path: Path) -> dict:
    """Read and validate one archive without executing its contained source files."""
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ValidationError(f"cannot open zip: {error}") from error

    with archive:
        files: dict[str, zipfile.ZipInfo] = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/").lstrip("/")
            if not name or "/" in name or name in files:
                raise ValidationError("archive files must be unique files in the root directory")
            files[name] = info

        if "team.json" not in files:
            raise ValidationError("archive must contain team.json")
        try:
            manifest = json.loads(archive.read(files["team.json"]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValidationError(f"team.json is invalid: {error}") from error
        if not isinstance(manifest, dict):
            raise ValidationError("team.json must contain an object")
        if manifest.get("format_version") != PACKAGE_FORMAT_VERSION:
            raise ValidationError(f"format_version must be {PACKAGE_FORMAT_VERSION}")

        slots, external_files = _validate_slots(manifest.get("slots"))
        expected_files = {"team.json", *external_files}
        if set(files) != expected_files:
            raise ValidationError("archive must contain only team.json and declared external files")

        for filename in external_files:
            try:
                source = archive.read(files[filename]).decode("utf-8")
                compile(source, filename, "exec")
            except UnicodeDecodeError as error:
                raise ValidationError(f"{filename} must be UTF-8") from error
            except SyntaxError as error:
                raise ValidationError(f"{filename} has invalid Python syntax: {error.msg}") from error

    return {
        "format_version": PACKAGE_FORMAT_VERSION,
        "name": _text(manifest.get("name"), "name"),
        "description": str(manifest.get("description", "")).strip(),
        "author": _text(manifest.get("author"), "author"),
        "version": _text(manifest.get("version"), "version"),
        "slots": slots,
    }


def _commit_time(repository_root: Path, relative_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", relative_path.as_posix()],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
        timestamp = result.stdout.strip()
        if timestamp:
            return timestamp
    except (OSError, subprocess.CalledProcessError):
        pass
    modified = (repository_root / relative_path).stat().st_mtime
    return datetime.fromtimestamp(modified, UTC).isoformat()


def build_catalog(
    repository_root: Path,
    timestamp_resolver: Callable[[Path], str] | None = None,
) -> dict:
    """Build the deterministic public catalog for every zip under codes/."""
    codes_dir = repository_root / "codes"
    packages = []
    for archive_path in sorted(codes_dir.glob("*.zip"), key=lambda path: path.name.lower()):
        manifest = read_archive(archive_path)
        relative_path = archive_path.relative_to(repository_root)
        updated_at = (
            timestamp_resolver(relative_path)
            if timestamp_resolver is not None
            else _commit_time(repository_root, relative_path)
        )
        packages.append(
            {
                "archive": relative_path.as_posix(),
                "filename": archive_path.name,
                "size": archive_path.stat().st_size,
                "updated_at": updated_at,
                **manifest,
            }
        )
    packages.sort(key=lambda package: (package["updated_at"], package["filename"].lower()), reverse=True)
    return {"format_version": CATALOG_FORMAT_VERSION, "packages": packages}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate archives without writing teams.json")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        catalog = build_catalog(root)
    except ValidationError as error:
        print(f"Archive validation failed: {error}", file=sys.stderr)
        return 1
    if not args.check:
        (root / "teams.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
