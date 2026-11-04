#!/usr/bin/env python3
"""Reject setup ZIPs whose toolchain copy does not match the host platform."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path, PurePosixPath


PLATFORM_MARKERS = {
    "windows": ("windows-x64",),
    "linux": ("linux-x64",),
    "macos": ("macos-x64", "macos-arm64"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def infer_platform(path: Path) -> str:
    lower = path.name.lower()
    matches = [
        platform
        for platform, markers in PLATFORM_MARKERS.items()
        if any(marker in lower for marker in markers)
    ]
    if len(matches) != 1:
        raise ValueError(
            "archive name must contain exactly one supported platform marker: "
            "windows-x64, linux-x64, macos-x64, or macos-arm64"
        )
    return matches[0]


def root_member(names: list[str], basename: str) -> str:
    matches = [
        name
        for name in names
        if not name.endswith("/")
        and len(PurePosixPath(name).parts) == 1
        and PurePosixPath(name).name.lower() == basename.lower()
    ]
    if len(matches) != 1:
        raise ValueError(f"archive must contain exactly one root {basename}")
    return matches[0]


def pe_resources(
    image: bytes, resource_type: int
) -> list[tuple[int | None, int, bytes]]:
    def unpack(fmt: str, offset: int) -> tuple[int, ...]:
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > len(image):
            raise ValueError("truncated PE resource data")
        return struct.unpack_from(fmt, image, offset)

    if image[:2] != b"MZ":
        raise ValueError("Windows setup host has no DOS header")
    pe_offset = unpack("<I", 0x3C)[0]
    if image[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("Windows setup host has no PE header")

    coff = pe_offset + 4
    section_count = unpack("<H", coff + 2)[0]
    optional_size = unpack("<H", coff + 16)[0]
    optional = coff + 20
    magic = unpack("<H", optional)[0]
    if magic == 0x20B:
        directory_offset = optional + 112
    elif magic == 0x10B:
        directory_offset = optional + 96
    else:
        raise ValueError(f"unsupported PE optional-header magic: {magic:#x}")

    resource_rva, resource_size = unpack("<II", directory_offset + 2 * 8)
    if resource_rva == 0 or resource_size == 0:
        return []

    sections = optional + optional_size

    def rva_to_offset(rva: int) -> int:
        for index in range(section_count):
            section = sections + index * 40
            virtual_size, virtual_address, raw_size, raw_offset = unpack(
                "<IIII", section + 8
            )
            extent = max(virtual_size, raw_size)
            if virtual_address <= rva < virtual_address + extent:
                offset = raw_offset + (rva - virtual_address)
                if offset > len(image):
                    break
                return offset
        raise ValueError(f"PE resource RVA is outside file sections: {rva:#x}")

    resource_base = rva_to_offset(resource_rva)

    def directory_entries(relative: int) -> list[tuple[int | None, bool, int]]:
        directory = resource_base + relative
        named_count, id_count = unpack("<HH", directory + 12)
        entries = []
        for index in range(named_count + id_count):
            name, target = unpack("<II", directory + 16 + index * 8)
            identifier = None if name & 0x80000000 else name & 0xFFFF
            entries.append(
                (identifier, bool(target & 0x80000000), target & 0x7FFFFFFF)
            )
        return entries

    resources: list[tuple[int | None, int, bytes]] = []
    for type_id, type_is_directory, type_target in directory_entries(0):
        if type_id != resource_type:
            continue
        if not type_is_directory:
            raise ValueError("PE resource type does not point to a directory")
        for name_id, name_is_directory, name_target in directory_entries(type_target):
            if not name_is_directory:
                raise ValueError("PE resource name does not point to a directory")
            for language_id, language_is_directory, language_target in directory_entries(
                name_target
            ):
                if language_id is None or language_is_directory:
                    raise ValueError("PE resource language does not point to data")
                data_rva, data_size = unpack(
                    "<II", resource_base + language_target
                )
                data_offset = rva_to_offset(data_rva)
                if data_offset + data_size > len(image):
                    raise ValueError("truncated PE resource payload")
                resources.append(
                    (
                        name_id,
                        language_id,
                        image[data_offset : data_offset + data_size],
                    )
                )
    return resources


def require(text: str, tokens: tuple[str, ...], where: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise ValueError(f"{where} is missing: {', '.join(missing)}")


def reject(text: str, tokens: tuple[str, ...], where: str) -> None:
    found = [token for token in tokens if token in text]
    if found:
        raise ValueError(f"{where} contains forbidden copy: {', '.join(found)}")


def audit(path: Path) -> dict[str, object]:
    platform = infer_platform(path)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        readme_name = root_member(names, "README-SETUP.txt")
        readme = archive.read(readme_name).decode("utf-8")

        run_match = re.search(r"(?m)^\s*\d+\.\s+Run\s+([^\s.]+(?:\.exe)?)\.\s*$", readme)
        if not run_match:
            raise ValueError("README-SETUP.txt has no numbered Run instruction")
        host_name = run_match.group(1)
        if platform == "windows" and not host_name.lower().endswith(".exe"):
            host_name += ".exe"
        host_member = root_member(names, host_name)
        host_bytes = archive.read(host_member)
        host_copy = host_bytes.decode("latin-1")

    if platform == "windows":
        require(
            readme,
            ("downloads", "cmake-clang-v1", "toolchain pack"),
            "Windows README-SETUP.txt",
        )
        require(
            host_copy,
            (
                "Download latest portable toolchain",
                "Select cmake-clang-v1 toolchain zip",
                "cmake-clang-v1",
            ),
            "Windows setup host",
        )
        manifests = pe_resources(host_bytes, 24)
        if len(manifests) != 1 or manifests[0][:2] != (1, 0x409):
            identities = [(name, language, len(data)) for name, language, data in manifests]
            raise ValueError(
                "Windows setup host must contain exactly one ID-1/en-US manifest: "
                f"{identities}"
            )
        manifest = manifests[0][2].decode("utf-8-sig")
        require(
            manifest,
            ("activeCodePage", "UTF-8", "longPathAware", "true", "asInvoker"),
            "Windows setup host manifest",
        )
        if not pe_resources(host_bytes, 3) or not pe_resources(host_bytes, 14):
            raise ValueError("Windows setup host is missing application icon resources")
    else:
        require(
            readme,
            (
                "Install CMake, Ninja, Python 3",
                "C/C++ compiler",
                "available on PATH",
                "native build tools",
            ),
            "POSIX README-SETUP.txt",
        )
        reject(
            readme.lower(),
            ("cmake-clang-v1", "portable toolchain", "toolchain pack", "toolchain zip"),
            "POSIX README-SETUP.txt",
        )
        require(
            host_copy,
            (
                "1. Native build tools",
                "Install CMake, Ninja, Python 3, and either Clang or GCC",
                "Check tools",
            ),
            "POSIX setup host",
        )
        reject(
            host_copy,
            ("Download latest portable toolchain##tc", "1. Portable toolchain"),
            "POSIX setup host",
        )

    return {
        "archive": str(path.resolve()),
        "platform": platform,
        "sha256": sha256(path),
        "size": path.stat().st_size,
        "status": "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    failed = False
    for path in args.archives:
        try:
            result = audit(path)
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            result = {"archive": str(path.resolve()), "status": "fail", "error": str(error)}
            failed = True
        results.append(result)
        print(f"{result['status'].upper()}: {path}: {result.get('error', result.get('platform'))}")

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(
            json.dumps({"schema": 1, "results": results}, indent=2) + "\n",
            encoding="utf-8",
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
