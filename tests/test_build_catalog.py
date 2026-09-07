from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.build_catalog import ValidationError, build_catalog, main, read_archive


def manifest(*, author: str = "Alice", version: str = "1.0.0") -> dict:
    return {
        "format_version": 1,
        "name": "Zero Hotori",
        "description": "Example team",
        "author": author,
        "version": version,
        "slots": [
            {
                "index": 0,
                "kind": "builtin",
                "impl_id": "builtin:zero",
                "display": {"zh_CN": "零", "en_US": "Zero"},
            },
            {
                "index": 1,
                "kind": "external",
                "file": "hotori.py",
                "class_name": "Hotori",
                "display": {"zh_CN": "热里", "en_US": "Hotori"},
            },
        ],
    }


def write_archive(path: Path, data: dict | None = None, extra: dict[str, str] | None = None) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("team.json", json.dumps(data or manifest(), ensure_ascii=False))
        archive.writestr("hotori.py", "class Hotori:\n    pass\n")
        for name, content in (extra or {}).items():
            archive.writestr(name, content)


class BuildCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "codes").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_keeps_every_author_and_version(self) -> None:
        write_archive(self.root / "codes" / "zero_alice_1.0.0.zip")
        write_archive(
            self.root / "codes" / "zero_bob_2.0.0.zip",
            manifest(author="Bob", version="2.0.0"),
        )

        catalog = build_catalog(self.root, lambda path: "2026-01-01T00:00:00+00:00")

        self.assertEqual(len(catalog["packages"]), 2)
        self.assertEqual({item["author"] for item in catalog["packages"]}, {"Alice", "Bob"})
        self.assertEqual(catalog["packages"][0]["archive"], "codes/zero_bob_2.0.0.zip")

    def test_rejects_nested_or_unlisted_files(self) -> None:
        archive_path = self.root / "codes" / "invalid.zip"
        write_archive(archive_path, extra={"nested/helper.py": "pass"})

        with self.assertRaisesRegex(ValidationError, "root directory"):
            read_archive(archive_path)

    def test_rejects_path_traversal(self) -> None:
        archive_path = self.root / "codes" / "unsafe.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("team.json", json.dumps(manifest()))
            archive.writestr("hotori.py", "class Hotori:\n    pass\n")
            archive.writestr("../outside.py", "pass")

        with self.assertRaisesRegex(ValidationError, "root directory"):
            read_archive(archive_path)

    def test_rejects_python_syntax_without_importing_module(self) -> None:
        archive_path = self.root / "codes" / "broken.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("team.json", json.dumps(manifest()))
            archive.writestr("hotori.py", "raise RuntimeError('must not execute')\nif")

        with self.assertRaisesRegex(ValidationError, "syntax"):
            read_archive(archive_path)

    def test_valid_source_is_not_executed_during_validation(self) -> None:
        archive_path = self.root / "codes" / "safe.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("team.json", json.dumps(manifest()))
            archive.writestr("hotori.py", "raise RuntimeError('must not execute')\n")

        self.assertEqual(read_archive(archive_path)["name"], "Zero Hotori")

    def test_rejects_directory_entries_symbolic_links_and_invalid_class_names(self) -> None:
        directory_archive = self.root / "codes" / "directory.zip"
        with zipfile.ZipFile(directory_archive, "w") as archive:
            archive.writestr("folder/", "")
            archive.writestr("team.json", json.dumps(manifest()))
            archive.writestr("hotori.py", "class Hotori:\n    pass\n")
        with self.assertRaisesRegex(ValidationError, "directory"):
            read_archive(directory_archive)

        link_archive = self.root / "codes" / "link.zip"
        link = zipfile.ZipInfo("hotori.py")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(link_archive, "w") as archive:
            archive.writestr("team.json", json.dumps(manifest()))
            archive.writestr(link, "hotori.py")
        with self.assertRaisesRegex(ValidationError, "symbolic"):
            read_archive(link_archive)

        invalid_class_archive = self.root / "codes" / "class.zip"
        invalid_manifest = manifest()
        invalid_manifest["slots"][1]["class_name"] = "not a class"
        write_archive(invalid_class_archive, invalid_manifest)
        with self.assertRaisesRegex(ValidationError, "identifier"):
            read_archive(invalid_class_archive)

    def test_rejects_duplicate_team_author_and_version(self) -> None:
        write_archive(self.root / "codes" / "first.zip")
        write_archive(self.root / "codes" / "second.zip")

        with self.assertRaisesRegex(ValidationError, "duplicate"):
            build_catalog(self.root)

    def test_catalog_size_limit_fails_check(self) -> None:
        write_archive(self.root / "codes" / "zero.zip")
        with patch("scripts.build_catalog.MAX_CATALOG_BYTES", 1):
            with redirect_stderr(StringIO()):
                self.assertEqual(main(["--check", "--root", str(self.root)]), 1)

    def test_versions_require_three_canonical_numeric_parts(self) -> None:
        path = self.root / "codes" / "version.zip"
        for version in (
            "1", "1.0", "v1.0.0", "1.0.0-beta", "01.0.0", "1.00.0", "-1.0.0",
            "\uff11.0.0", "1.0.0.0", "1" * 33 + ".0.0",
        ):
            with self.subTest(version=version):
                write_archive(path, manifest(version=version))
                with self.assertRaises(ValidationError):
                    read_archive(path)
        for version in ("0.0.0", "1.9.0", "1.10.0"):
            write_archive(path, manifest(version=version))
            self.assertEqual(read_archive(path)["version"], version)

    def test_different_names_allow_same_author_members_and_version(self) -> None:
        write_archive(self.root / "codes" / "first.zip")
        second = {**manifest(), "name": "Another strategy"}
        write_archive(self.root / "codes" / "second.zip", second)
        self.assertEqual(len(build_catalog(self.root)["packages"]), 2)

    def test_same_named_version_rejects_changed_members(self) -> None:
        write_archive(self.root / "codes" / "first.zip")
        second = manifest()
        second["slots"][0]["impl_id"] = "builtin:another"
        write_archive(self.root / "codes" / "second.zip", second)
        with self.assertRaises(ValidationError):
            build_catalog(self.root)

    def test_retains_history_with_same_author_and_name(self) -> None:
        for version in ("1.0.0", "1.9.0", "1.10.0"):
            write_archive(self.root / "codes" / f"team_{version}.zip", manifest(version=version))
        catalog = build_catalog(self.root, lambda path: "2026-09-01T00:00:00+00:00")
        self.assertEqual(
            {entry["version"] for entry in catalog["packages"]}, {"1.0.0", "1.9.0", "1.10.0"}
        )


if __name__ == "__main__":
    unittest.main()
