"""Check that header downloads cannot pollute Xcode's synchronized folders."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "fetch_headers", Path(__file__).with_name("fetch-headers.py")
)
fetch_headers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_headers)


class HeaderDestinationTests(unittest.TestCase):
    def test_downloads_are_outside_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            destination = fetch_headers.prepare_destination(root)
            self.assertTrue(destination.is_relative_to(root / "build"))
            self.assertFalse(destination.is_relative_to(root / "Dependencies"))
            self.assertTrue(destination.is_dir())

    def test_migrates_legacy_header_tree_without_losing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            legacy = root / "Dependencies/CIHeaders"
            header = legacy / "glslang/glslang/HLSL/pch.h"
            header.parent.mkdir(parents=True)
            header.write_text("legacy downloaded header", encoding="utf-8")
            destination = fetch_headers.prepare_destination(root)
            self.assertFalse(legacy.exists())
            self.assertEqual(
                (destination / "glslang/glslang/HLSL/pch.h").read_text(encoding="utf-8"),
                "legacy downloaded header",
            )

    def test_refuses_to_overwrite_two_existing_header_trees(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for directory in ("Dependencies/CIHeaders", "build/headers"):
                path = root / directory
                path.mkdir(parents=True)
                (path / "marker").write_text(directory, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Both .+ exist"):
                fetch_headers.prepare_destination(root)
            for directory in ("Dependencies/CIHeaders", "build/headers"):
                self.assertEqual(
                    (root / directory / "marker").read_text(encoding="utf-8"), directory
                )


if __name__ == "__main__":
    unittest.main()
