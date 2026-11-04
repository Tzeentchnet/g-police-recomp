#!/usr/bin/env python3
"""PSXRecomp CLI adapter for G-Police's SCPH5552 retail BIOS profile."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_CLI = ROOT / "psxrecomp" / "psxrecomp_cli.py"
DEFAULT_RETAIL_BIOS_STEM = "SCPH1001"


def load_upstream() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gpolice_upstream_psxrecomp_cli", UPSTREAM_CLI
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load PSXRecomp CLI: {UPSTREAM_CLI}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_parser(upstream: ModuleType):
    parser = upstream.build_parser()
    subcommands = next(
        action
        for action in parser._actions
        if getattr(action, "choices", None)
        and "generate" in action.choices
    )
    generate = subcommands.choices["generate"]
    for action in generate._actions:
        if action.dest == "bios":
            action.help = (
                "retail BIOS dump staged and regenerated through the profile "
                "selected by [recompiler] bios_config"
            )
        elif action.dest == "force_bios":
            action.help = "regenerate the selected retail BIOS backend"
    return parser


def retail_bios_stem(recompiler: dict[str, Any]) -> str:
    config = str(recompiler.get("bios_config") or "").strip()
    if not config:
        return DEFAULT_RETAIL_BIOS_STEM
    return Path(config.replace("\\", "/")).stem or DEFAULT_RETAIL_BIOS_STEM


def retail_bios_rom_relpath(upstream: ModuleType, framework: Path, stem: str) -> str:
    profile = framework / "bios" / f"{stem}.toml"
    sections = upstream.parse_toml_simple(profile.read_text(encoding="utf-8"))
    program = sections.get("program") or {}
    return str(program.get("rom") or f"bios/{stem}.BIN").strip()


def project_root_for(args: Any, config: Path) -> Path:
    if getattr(args, "project_root", ""):
        return Path(args.project_root).expanduser().resolve()
    return config.parent


def stage_retail_bios(
    upstream: ModuleType,
    args: Any,
    progress: Any,
    project_root: Path,
    framework: Path,
    stem: str,
) -> None:
    bios_path = Path(args.bios).expanduser()
    if not bios_path.is_absolute():
        bios_path = (project_root / bios_path).resolve()
    else:
        bios_path = bios_path.resolve()
    if not bios_path.is_file():
        raise FileNotFoundError(f"BIOS not found: {bios_path}")

    profile_rel = f"bios/{stem}.toml"
    profile = framework / profile_rel
    if not profile.is_file():
        raise FileNotFoundError(f"BIOS profile not found for {stem}: {profile}")

    upstream.ensure_emitters(
        project_root,
        progress,
        download_toolchain=not bool(args.no_toolchain_download),
        force=bool(args.force_emitters),
    )
    args.force_emitters = False

    destination = framework / retail_bios_rom_relpath(upstream, framework, stem)
    destination.parent.mkdir(parents=True, exist_ok=True)
    progress.phase("bios", pct=0.15, message=f"Staging retail BIOS dump ({stem})...")
    progress.log(f"generate --bios {bios_path} --bios-stem {stem}")
    if destination.resolve() != bios_path:
        upstream.shutil.copy2(bios_path, destination)

    if args.force_bios or not upstream.bios_backend_present(framework, stem):
        progress.phase("bios", pct=0.2, message=f"Generating {stem} BIOS C...")
        upstream.regen_bios_profile(project_root, profile_rel, progress=progress)
    else:
        progress.log(
            f"{stem} backend already present - skipping BIOS regeneration "
            "(pass --force-bios to regenerate)"
        )


def run_generate(upstream: ModuleType, args: Any, progress: Any) -> int:
    config = Path(args.config).expanduser().resolve()
    if not config.is_file():
        progress.error(f"config not found: {config}", code=upstream.EXIT_USAGE)
        return upstream.EXIT_USAGE

    sections = upstream.load_sections(config)
    recompiler = sections.get("recompiler") or {}
    runtime = sections.get("runtime") or {}
    stem = retail_bios_stem(recompiler)
    if stem == DEFAULT_RETAIL_BIOS_STEM:
        return int(upstream.cmd_generate(args, progress))

    project_root = project_root_for(args, config)
    framework = upstream.ensure_framework(project_root, progress=progress)
    try:
        if args.bios:
            stage_retail_bios(
                upstream, args, progress, project_root, framework, stem
            )
            args.bios = ""
        elif not bool(runtime.get("openbios", True)) and not upstream.bios_backend_present(
            framework, stem
        ):
            progress.error(
                f"This title requires a retail BIOS dump for {stem}. "
                "Pass --bios <dump> (or pick one in the setup wizard).",
                code=upstream.EXIT_USAGE,
            )
            return upstream.EXIT_USAGE
    except Exception as exc:
        progress.error(str(exc), code=upstream.EXIT_ERROR)
        return upstream.EXIT_ERROR

    original_backend_present = upstream.bios_backend_present

    def configured_backend_present(candidate_framework: Path, candidate_stem: str) -> bool:
        if candidate_stem == DEFAULT_RETAIL_BIOS_STEM:
            candidate_stem = stem
        return bool(original_backend_present(candidate_framework, candidate_stem))

    upstream.bios_backend_present = configured_backend_present
    try:
        return int(upstream.cmd_generate(args, progress))
    finally:
        upstream.bios_backend_present = original_backend_present


def main() -> int:
    upstream = load_upstream()
    upstream._configure_stdio()
    args = build_parser(upstream).parse_args()
    progress = upstream.ProgressReporter(
        json_progress=bool(getattr(args, "json_progress", False))
    )
    try:
        if args.command == "generate":
            return run_generate(upstream, args, progress)
        return int(args.handler(args, progress))
    except BrokenPipeError:
        return upstream.EXIT_ERROR
    except KeyboardInterrupt:
        progress.error("interrupted", code=upstream.EXIT_ERROR)
        return upstream.EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
