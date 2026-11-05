#!/usr/bin/env python3
"""Verify the title exposes true GPU-rendered Vulkan internal scaling."""

from pathlib import Path
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    game = tomllib.loads((ROOT / "game.toml").read_text(encoding="utf-8"))
    video = game.get("video", {})
    if video.get("renderer") != "vulkan":
        raise AssertionError("game.toml must default to the Vulkan renderer")
    if video.get("offer_vulkan") is not True:
        raise AssertionError("game.toml must expose Vulkan in the launcher")

    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    if not re.search(
        r"set\s*\(\s*PSX_ENABLE_VULKAN\s+ON\s+CACHE\s+BOOL[^)]*FORCE\s*\)",
        cmake,
        re.DOTALL,
    ):
        raise AssertionError("CMake must force-enable the Vulkan backend")

    codegen = (ROOT / "codegen_setup.c").read_text(encoding="utf-8")
    for label in ("OpenGL (Fallback)", "Vulkan (Recommended)"):
        if f'"{label}"' not in codegen:
            raise AssertionError(f"missing title renderer label: {label}")

    package_path = (
        ROOT
        / "psxrecomp"
        / "mods"
        / "builtin"
        / "packages"
        / "psx.enhancement.internal-resolution"
        / "1.0.0"
        / "manifest.toml"
    )
    package = tomllib.loads(package_path.read_text(encoding="utf-8"))
    features = package.get("feature", [])
    options = package.get("option", [])
    if len(features) != 1 or features[0].get("default_enabled") is not True:
        raise AssertionError("Internal Resolution must be enabled by default")
    resolution = next(
        (option for option in options if option.get("id") == "resolution"),
        None,
    )
    if resolution is None or resolution.get("default") != "4x":
        raise AssertionError("Internal Resolution must default to 4x")

    renderer = (
        ROOT / "psxrecomp" / "runtime" / "src" / "gpu_vk_renderer.c"
    ).read_text(encoding="utf-8")
    required = (
        "ci.extent.width = VRAM_W * s_scale;",
        "ci.extent.height = VRAM_H * s_scale;",
        "if (scale >= 1 && scale <= 4) s_scale = scale;",
    )
    missing = [line for line in required if line not in renderer]
    if missing:
        raise AssertionError(
            "Vulkan backend no longer allocates a scaled GPU target: "
            + ", ".join(missing)
        )

    print("PASS: Vulkan is offered by default with true 4x GPU internal rendering")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, AssertionError, tomllib.TOMLDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
