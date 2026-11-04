from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets" / "windows" / "gpolice.manifest"


class WindowsManifestTests(unittest.TestCase):
    def test_manifest_preserves_utf8_and_long_path_support(self):
        root = ET.parse(MANIFEST).getroot()
        active_code_page = root.find(
            ".//{http://schemas.microsoft.com/SMI/2019/WindowsSettings}"
            "activeCodePage"
        )
        long_path_aware = root.find(
            ".//{http://schemas.microsoft.com/SMI/2016/WindowsSettings}"
            "longPathAware"
        )

        self.assertIsNotNone(active_code_page)
        self.assertEqual(active_code_page.text, "UTF-8")
        self.assertIsNotNone(long_path_aware)
        self.assertEqual(long_path_aware.text, "true")

    def test_cmake_selects_the_title_manifest(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn(
            'set(PSXRECOMP_WINDOWS_MANIFEST\n'
            '    "${CMAKE_CURRENT_SOURCE_DIR}/assets/windows/gpolice.manifest")',
            cmake,
        )


if __name__ == "__main__":
    unittest.main()
