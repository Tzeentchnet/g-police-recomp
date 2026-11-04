from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".release" / "sanitize_setup_package.py"


def load_sanitizer():
    spec = importlib.util.spec_from_file_location("sanitize_setup_package", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SanitizeSetupPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sanitizer = load_sanitizer()

    def test_removes_private_inputs_and_development_trees(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "setup.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("CMakeLists.txt", "project(Test)")
                output.writestr("psxrecomp/bios/EUR-PSX-SCPH5552.bin", b"retail")
                output.writestr("psxrecomp/bios/openbios.bin", b"openbios")
                output.writestr("psxrecomp/runtime/tests/card.mcd", b"state")
                output.writestr("psxrecomp/docs/BUILDING.md", "docs")
                output.writestr("psxrecomp/overlay_toolchain/compiler.txt", "C:\\Users\\dev")
                output.writestr("recomp-ui/tests/launcher_test.c", "test")

            result = self.sanitizer.sanitize(archive)

            with zipfile.ZipFile(archive) as sanitized:
                self.assertEqual(sanitized.namelist(), ["CMakeLists.txt"])
            self.assertEqual(result["kept_entries"], 1)
            self.assertEqual(result["removed_entries"], 6)
            self.assertEqual(result["removed_by_reason"]["BIOS image"], 2)

    def test_rejects_unsafe_member_without_replacing_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "setup.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape.txt", "no")
            original = archive.read_bytes()

            with self.assertRaisesRegex(ValueError, "unsafe archive member"):
                self.sanitizer.sanitize(archive)

            self.assertEqual(archive.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
