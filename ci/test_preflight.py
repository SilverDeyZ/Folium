"""Regression tests for framework discovery in extracted SwiftPM downloads."""
from pathlib import Path
import plistlib
import tempfile
import unittest

import preflight


class FrameworkDiscoveryTests(unittest.TestCase):
    def test_ignores_appledouble_file_from_sdl3_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            framework = root / "shareddependencies/lib_sdl3/SDL3.xcframework"
            framework.mkdir(parents=True)
            metadata = root / "shareddependencies/lib_sdl3/__MACOSX/._SDL3.xcframework"
            metadata.parent.mkdir(parents=True)
            metadata.write_bytes(b"AppleDouble metadata, not an XCFramework directory")

            self.assertIn(metadata, list(root.rglob("*.xcframework")))
            self.assertEqual(preflight.discover_xcframeworks(root), [framework])

    def test_ignores_metadata_directories_and_other_suffix_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "__MACOSX/SDL3.xcframework").mkdir(parents=True)
            (root / "._SDL3.xcframework").mkdir()
            (root / "download.xcframework").write_bytes(b"not a directory")
            self.assertEqual(preflight.discover_xcframeworks(root), [])

    def test_malformed_real_framework_still_fails_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            framework = root / "Broken.xcframework"
            framework.mkdir()
            self.assertEqual(preflight.discover_xcframeworks(root), [framework])
            with self.assertRaises(FileNotFoundError):
                preflight.inspect_framework(framework)

    def test_simulator_arm64_does_not_pass_as_device_arm64(self):
        with tempfile.TemporaryDirectory() as temporary:
            framework = Path(temporary) / "Simulator.xcframework"
            framework.mkdir()
            with (framework / "Info.plist").open("wb") as content:
                plistlib.dump({"AvailableLibraries": [{
                    "SupportedPlatform": "ios",
                    "SupportedPlatformVariant": "simulator",
                    "SupportedArchitectures": ["arm64"],
                }]}, content)
            with self.assertRaisesRegex(ValueError, "No arm64 iOS device slice"):
                preflight.inspect_framework(framework)


if __name__ == "__main__":
    unittest.main()
