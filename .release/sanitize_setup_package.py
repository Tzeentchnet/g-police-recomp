#!/usr/bin/env python3
"""Remove non-runtime framework material from an owned-input setup ZIP."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile


STRIP_PREFIXES = (
    ("psxrecomp/docs/", "framework documentation"),
    ("psxrecomp/overlay_toolchain/", "generated overlay toolchain"),
    ("psxrecomp/recompiler/tests/", "framework tests"),
    ("psxrecomp/runtime/tests/", "framework tests"),
    ("psxrecomp/tests/", "framework tests"),
    ("psxrecomp/tools/aot_overlay_spike/", "framework research tools"),
    ("recomp-ui/docs/", "framework documentation"),
    ("recomp-ui/tests/", "framework tests"),
)
BIOS_IMAGE_SUFFIXES = {".bin", ".rom"}


def validate_member(name: str) -> str:
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized) or ".." in parts:
        raise ValueError(f"unsafe archive member: {name}")
    return normalized


def removal_reason(name: str) -> str | None:
    lower = name.casefold()
    for prefix, reason in STRIP_PREFIXES:
        if lower.startswith(prefix):
            return reason
    if lower.startswith("psxrecomp/bios/"):
        suffix = PurePosixPath(lower).suffix
        if suffix in BIOS_IMAGE_SUFFIXES:
            return "BIOS image"
    return None


def sanitize(path: Path) -> dict[str, object]:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    removed: Counter[str] = Counter()
    kept = 0
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)

    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
            temporary, "w"
        ) as target:
            target.comment = source.comment
            for info in source.infolist():
                name = validate_member(info.filename)
                reason = removal_reason(name)
                if reason is not None:
                    removed[reason] += 1
                    continue
                target.writestr(info, source.read(info))
                kept += 1
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return {
        "archive": str(path),
        "kept_entries": kept,
        "removed_entries": sum(removed.values()),
        "removed_by_reason": dict(sorted(removed.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(sanitize(args.archive), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
