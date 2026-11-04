#!/usr/bin/env python3
"""Reproduce PSXRecomp out-of-function transfer warnings with synthetic code."""

from __future__ import annotations

import argparse
from pathlib import Path
import struct
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
LOAD_ADDRESS = 0x80010000
EXE_NAME = "transfer-warning-fixture.exe"
SEED_NAME = "transfer-warning-fixture-seeds.txt"
SEED_OFFSETS = (0x00, 0x20, 0x28, 0x38, 0x60, 0x78)
EXPECTED_WARNINGS = (
    "WARNING: func_80010020 has out-of-function branch at block_80010020, "
    "emitting fallthrough to func_80010028",
    "WARNING: func_80010060 has out-of-function jump at block_8001006C, "
    "emitting fallthrough to func_80010078",
)
EXPECTED_GENERATED_SNIPPETS = (
    "cpu->pc = 0x80010038u; return;  /* CPS taken: split */",
    "cpu->pc = 0x80010028u; return;  /* CPS not taken: split */",
    "func_80010028(cpu);  /* fallthrough to next function */",
    "cpu->pc = 0x8805CD40u; return;  /* CPS j: split */",
)
ABSENT_GENERATED_SNIPPETS = (
    "func_80010078(cpu);  /* fallthrough to next function */",
)


def fixture_words() -> tuple[int, ...]:
    words = [0] * (0x84 // 4)

    def put(offset: int, *values: int) -> None:
        start = offset // 4
        words[start : start + len(values)] = values

    # Reach both warning cases through ordinary JAL discovery.
    put(
        0x00,
        0x0C004008,  # jal 0x80010020
        0x00000000,
        0x0C004018,  # jal 0x80010060
        0x00000000,
        0x03E00008,
        0x00000000,
    )

    # Both outcomes leave this deliberately partitioned function piece.
    put(0x20, 0x14800005, 0x00000000)  # bne a0, zero, 0x80010038
    put(0x28, 0x27BDFFF8, 0xAFBF0004, 0x03E00008, 0x27BD0008)
    put(0x38, 0x03E00008, 0x00000000)

    # A JAL-discovered BIOS thunk keeps unreachable words up to the next thunk.
    put(
        0x60,
        0x240A00B0,
        0x01400008,
        0x24090038,
        0x00000000,
        0x0A017350,
        0x1036D11A,
    )
    put(0x78, 0x240A00B0, 0x01400008, 0x2409003F)
    return tuple(words)


def write_fixture(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    words = fixture_words()
    header = bytearray(0x800)
    header[:8] = b"PS-X EXE"
    struct.pack_into("<I", header, 0x10, LOAD_ADDRESS)
    struct.pack_into("<I", header, 0x18, LOAD_ADDRESS)
    struct.pack_into("<I", header, 0x1C, len(words) * 4)
    struct.pack_into("<I", header, 0x30, 0x801FFFF0)

    executable = directory / EXE_NAME
    executable.write_bytes(header + struct.pack(f"<{len(words)}I", *words))

    seeds = directory / SEED_NAME
    seeds.write_text(
        "".join(f"0x{LOAD_ADDRESS + offset:08X}\n" for offset in SEED_OFFSETS),
        encoding="ascii",
    )
    return executable, seeds


def run_fixture(emitter: Path, project_root: Path, workspace: Path) -> str:
    emitter = emitter.resolve()
    project_root = project_root.resolve()
    if not emitter.is_file():
        raise FileNotFoundError(emitter)
    if not project_root.is_dir():
        raise NotADirectoryError(project_root)

    executable, seeds = write_fixture(workspace)
    generated = workspace / "generated"
    completed = subprocess.run(
        [
            str(emitter),
            str(executable),
            "--seeds",
            str(seeds),
            "--out-dir",
            str(generated),
            "--strict",
            "--project-root",
            str(project_root),
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"emitter exited with {completed.returncode}\n{completed.stdout}"
        )

    for warning in EXPECTED_WARNINGS:
        if warning not in completed.stdout:
            raise AssertionError(f"missing expected warning: {warning}")

    shard = generated / f"{EXE_NAME}_full_00.c"
    emitted = shard.read_text(encoding="utf-8")
    for snippet in EXPECTED_GENERATED_SNIPPETS:
        if snippet not in emitted:
            raise AssertionError(f"missing generated transfer: {snippet}")
    for snippet in ABSENT_GENERATED_SNIPPETS:
        if snippet in emitted:
            raise AssertionError(f"unexpected generated fallthrough: {snippet}")
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emitter", required=True, type=Path)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="psxrecomp-transfer-warning-") as temp:
        output = run_fixture(args.emitter, args.project_root, Path(temp))

    for warning in EXPECTED_WARNINGS:
        print(warning)
    print(
        "Verified both explicit transfers, the continuation's unreachable "
        "fallthrough call, and the data warning's absent fallthrough call."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
