from __future__ import annotations

from pathlib import Path
import re
import unittest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PGXP_MANIFEST = (
    ROOT
    / "mods"
    / "preloaded"
    / "packages"
    / "psx.enhancement.pgxp"
    / "1.0.0"
    / "manifest.toml"
)
FAST_LOADING_MANIFEST = (
    ROOT
    / "mods"
    / "preloaded"
    / "packages"
    / "psx.enhancement.fast-loading"
    / "1.0.0"
    / "manifest.toml"
)
DRAW_DISTANCE_MANIFEST = (
    ROOT
    / "mods"
    / "preloaded"
    / "packages"
    / "psx.enhancement.draw-distance"
    / "1.0.0"
    / "manifest.toml"
)
DRAW_DISTANCE_SOURCE = ROOT / "src" / "gpolice_draw_distance_mod.c"


class QuickModConfigTests(unittest.TestCase):
    def test_launcher_and_pgxp_use_one_mod_owned_switch(self):
        game = tomllib.loads((ROOT / "game.toml").read_text(encoding="utf-8"))

        self.assertIs(game["launcher"]["quick_controls"], True)
        self.assertIs(game["video"]["pgxp_mod_only"], True)

    def test_runtime_uses_pgxp_hooks_and_title_catalog(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        runtime_call = re.search(
            r"psxrecomp_add_game_runtime\(psx-runtime(?P<body>.*?)^\)",
            cmake,
            re.DOTALL | re.MULTILINE,
        )

        self.assertIsNotNone(runtime_call)
        body = runtime_call.group("body")
        self.assertRegex(body, r"(?m)^\s+PGXP\s*$")
        self.assertIn(
            'PRELOADED_MODS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded"',
            body,
        )

    def test_pgxp_is_quick_and_enabled_by_default(self):
        manifest = tomllib.loads(PGXP_MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(manifest["id"], "psx.enhancement.pgxp")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["target"], [{"game_id": "SLUS-00544"}])

        self.assertEqual(len(manifest["feature"]), 1)
        feature = manifest["feature"][0]
        self.assertEqual(feature["id"], "pgxp")
        self.assertIs(feature["quick"], True)
        self.assertIs(feature["default_enabled"], True)

        defaults = {
            option["id"]: option["default"] for option in manifest["option"]
        }
        self.assertEqual(defaults, {"cpu_mode": "false", "culling": "false"})
        self.assertEqual(
            manifest["plugin"],
            [{"feature": "pgxp", "id": "psx.pgxp"}],
        )

    def test_fast_loading_is_fixed_to_validated_quick_mode(self):
        manifest = tomllib.loads(
            FAST_LOADING_MANIFEST.read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["id"], "psx.enhancement.fast-loading")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["target"], [{"game_id": "SLUS-00544"}])
        self.assertNotIn("option", manifest)

        self.assertEqual(len(manifest["feature"]), 1)
        feature = manifest["feature"][0]
        self.assertEqual(feature["id"], "fast-loading")
        self.assertEqual(feature["name"], "Fast Loading (4x)")
        self.assertIs(feature["quick"], True)
        self.assertIs(feature["default_enabled"], True)
        self.assertNotIn("hidden", feature)
        self.assertEqual(
            manifest["plugin"],
            [{"feature": "fast-loading", "id": "psx.fast-loading"}],
        )

    def test_draw_distance_uses_guarded_native_maximum(self):
        manifest = tomllib.loads(
            DRAW_DISTANCE_MANIFEST.read_text(encoding="utf-8")
        )
        game = tomllib.loads((ROOT / "game.toml").read_text(encoding="utf-8"))
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        source = DRAW_DISTANCE_SOURCE.read_text(encoding="utf-8")

        self.assertEqual(manifest["id"], "psx.enhancement.draw-distance")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["target"], [{"game_id": "SLUS-00544"}])
        self.assertEqual(manifest["save_compatibility"], "isolated")
        self.assertNotIn("option", manifest)

        self.assertEqual(len(manifest["feature"]), 1)
        feature = manifest["feature"][0]
        self.assertEqual(feature["id"], "draw-distance")
        self.assertEqual(feature["name"], "Extended Draw Distance")
        self.assertIs(feature["quick"], True)
        self.assertIs(feature["default_enabled"], False)
        self.assertEqual(
            manifest["plugin"],
            [
                {
                    "feature": "draw-distance",
                    "id": "gpolice.extended-draw-distance",
                }
            ],
        )

        self.assertEqual(
            game["recompiler"]["mod_instruction_sites"],
            ["0x80020FB8", "0x80020FCC"],
        )
        self.assertIn(
            '"${CMAKE_CURRENT_SOURCE_DIR}/src/gpolice_draw_distance_mod.c"',
            cmake,
        )
        self.assertIn("#define GPOLICE_DRAW_DISTANCE 145000u", source)
        self.assertIn("#define GPOLICE_DRAW_DISTANCE_STORE 0xAC22453Cu", source)
        self.assertIn("#define GPOLICE_DRAW_DISTANCE_NORMAL_PC 0x80020FB8u", source)
        self.assertIn("#define GPOLICE_DRAW_DISTANCE_SPECIAL_PC 0x80020FCCu", source)
        self.assertIn("cpu->gpr[2] = GPOLICE_DRAW_DISTANCE;", source)
        self.assertEqual(
            source.count("psx_mod_register_instruction_plugin("),
            2,
        )


if __name__ == "__main__":
    unittest.main()
