from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gpolice_psxrecomp_cli.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("gpolice_codegen_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CodegenCliBiosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = load_adapter()
        cls.upstream = cls.adapter.load_upstream()

    def test_game_config_selects_scph5552(self):
        sections = self.upstream.load_sections(ROOT / "game.toml")
        self.assertEqual(
            self.adapter.retail_bios_stem(sections["recompiler"]),
            "SCPH5552",
        )

    def test_scph5552_profile_uses_european_rom_name(self):
        self.assertEqual(
            self.adapter.retail_bios_rom_relpath(
                self.upstream, ROOT / "psxrecomp", "SCPH5552"
            ),
            "bios/EUR-PSX-SCPH5552.bin",
        )

    def test_generate_help_describes_profile_driven_bios(self):
        parser = self.adapter.build_parser(self.upstream)
        subcommands = next(
            action
            for action in parser._actions
            if getattr(action, "choices", None)
            and "generate" in action.choices
        )
        bios_action = next(
            action
            for action in subcommands.choices["generate"]._actions
            if action.dest == "bios"
        )
        self.assertIn("[recompiler] bios_config", bios_action.help)

    def test_setup_host_and_packager_use_adapter(self):
        codegen = (ROOT / "codegen_setup.c").read_text(encoding="utf-8")
        package = (ROOT / "scripts" / "package_setup_release.sh").read_text(
            encoding="utf-8"
        )
        relpath = "scripts/gpolice_psxrecomp_cli.py"
        self.assertIn(f'.psxrecomp_cli_relpath = "{relpath}"', codegen)
        self.assertIn(f"--project-file {relpath}", package)
        self.assertIn("--omit-openbios", package)

    def test_setup_host_contract_matches_project(self):
        codegen = (ROOT / "codegen_setup.c").read_text(encoding="utf-8")
        expected = {
            "display_name": "G-Police",
            "project_root_env": "G_POLICE_PROJECT_ROOT",
            "build_dir_env": "G_POLICE_BUILD_DIR",
            "force_setup_env": "G_POLICE_FORCE_SETUP",
            "psxrecomp_cli_relpath": "scripts/gpolice_psxrecomp_cli.py",
            "seed_cfg_relpath": "game.toml",
            "game_toml_relpath": "game.toml",
            "gen_marker_relpath": "generated/SLUS_005.44_dispatch.c",
            "build_dir_name": "build-release",
            "cmake_target": "psx-runtime",
            "exe_basename": "G_Police_Recompiled",
        }

        for field, value in expected.items():
            match = re.search(
                rf'\.{re.escape(field)}\s*=\s*"([^"]+)"',
                codegen,
            )
            self.assertIsNotNone(match, f"missing setup field: {field}")
            self.assertEqual(match.group(1), value, field)

        self.assertTrue((ROOT / expected["psxrecomp_cli_relpath"]).is_file())


if __name__ == "__main__":
    unittest.main()
