from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "aot" / "overlays.json"


class OverlayProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE.read_text(encoding="utf-8"))

    def test_profile_is_metadata_only_and_links_generated_static_output(self):
        self.assertEqual(self.profile["schema"], "psxrecomp AOT methods v1")
        self.assertEqual(self.profile["game_id"], "SLUS-00544")
        self.assertEqual(
            self.profile["static_output"], "generated/overlays_static.c"
        )
        self.assertEqual(
            self.profile["file_aliases"],
            {"BOOT.EXE": ["SLUS_005.44", "SLUS_005.56"]},
        )
        self.assertNotIn("bytes_b64", PROFILE.read_text(encoding="utf-8"))

        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        static_arg = (
            'GAME_OVERLAY_STATIC_C '
            '"${CMAKE_CURRENT_SOURCE_DIR}/${GPOLICE_OVERLAY_STATIC}"'
        )
        self.assertIn(
            'set(GPOLICE_OVERLAY_STATIC "generated/overlays_static.c")', cmake
        )
        self.assertIn(static_arg, cmake)
        self.assertLess(cmake.index(static_arg), cmake.index("GEN_FULL_GLOB"))

        package = (ROOT / "scripts" / "package_setup_release.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--project-dir aot", package)

    def test_both_same_address_modules_are_content_pinned(self):
        expected = {
            "FRONT.BIN": {
                "size": "0x3400C",
                "sha256": (
                    "e183ee4377b69e65b023b7cc573e108580dea423618164c0d021d1fa298eca7d"
                ),
                "entry": "0x8009DAE8",
            },
            "GAME.BIN": {
                "size": "0x5D364",
                "sha256": (
                    "07dad7905d0587f8b253b261c48f069da2c7bbf543ef36f4fce1fc3b32655f4b"
                ),
                "entry": "0x800B2A60",
            },
        }

        images = {}
        for image in self.profile["images"]:
            self.assertEqual(image["method"], "fixed_address_extents")
            self.assertTrue(image["allow_missing"])
            self.assertEqual(len(image["extents"]), 1)
            extent = image["extents"][0]
            self.assertEqual(extent["load_addr"], "0x80098B60")
            images[extent["file"]] = {
                "size": extent["size"],
                "sha256": extent["sha256"],
                "entry": image["entries"][0],
            }

        self.assertEqual(images, expected)
        self.assertTrue(self.profile["strict_bounds"])
        self.assertEqual(self.profile["expected_records"], 2)

    def test_front_dispatch_exports_are_preserved(self):
        front = next(
            image
            for image in self.profile["images"]
            if image["extents"][0]["file"] == "FRONT.BIN"
        )
        self.assertEqual(
            front["dispatch_entries"],
            [
                "0x8009A950",
                "0x8009A9D4",
                "0x8009A9E8",
                "0x8009AA74",
            ],
        )


if __name__ == "__main__":
    unittest.main()
