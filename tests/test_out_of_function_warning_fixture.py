from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "fixtures" / "out_of_function_warning_fixture.py"


def load_fixture():
    spec = importlib.util.spec_from_file_location(
        "out_of_function_warning_fixture", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OutOfFunctionWarningFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = load_fixture()

    def test_writes_deterministic_synthetic_psx_exe(self):
        with tempfile.TemporaryDirectory() as directory:
            executable, seeds = self.fixture.write_fixture(Path(directory))
            image = executable.read_bytes()

            self.assertEqual(image[:8], b"PS-X EXE")
            self.assertEqual(
                struct.unpack_from("<I", image, 0x10)[0],
                self.fixture.LOAD_ADDRESS,
            )
            self.assertEqual(
                struct.unpack_from("<I", image, 0x18)[0],
                self.fixture.LOAD_ADDRESS,
            )
            self.assertEqual(
                struct.unpack_from("<I", image, 0x1C)[0],
                len(self.fixture.fixture_words()) * 4,
            )
            self.assertEqual(
                struct.unpack_from(
                    f"<{len(self.fixture.fixture_words())}I", image, 0x800
                ),
                self.fixture.fixture_words(),
            )
            self.assertEqual(
                seeds.read_text(encoding="ascii").splitlines(),
                [
                    f"0x{self.fixture.LOAD_ADDRESS + offset:08X}"
                    for offset in self.fixture.SEED_OFFSETS
                ],
            )


if __name__ == "__main__":
    unittest.main()
