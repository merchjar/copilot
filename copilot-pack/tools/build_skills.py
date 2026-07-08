#!/usr/bin/env python3
"""
build_skills.py - Sync canonical skills/ to runtime-specific discovery locations.

The Merch Jar Copilot Pack uses skills/ as the single source of truth. Claude
environments that support folder-based skill auto-discovery look at
.claude/skills/. Codex environments that support auto-discovery look at
.agents/skills/. This script syncs the canonical skills/ source to both
target locations.

Cross-platform: stdlib only, runs on Windows, macOS, Linux.

Usage:
    python tools/build_skills.py

Run from the pack root after editing skills/.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import List, Tuple


PACK_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PACK_ROOT / "skills"
TARGETS = [
    PACK_ROOT / ".claude" / "skills",
    PACK_ROOT / ".agents" / "skills",
]


def sync(source: Path, target: Path) -> Tuple[int, List[str]]:
    """Mirror source to target.

    Tries a clean replace first. If rmtree hits PermissionError (common in
    sandboxed environments like Cowork that block file deletion), falls back
    to a file-by-file merge. Returns (skill_count, list_of_warnings).
    """
    warnings: List[str] = []
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    except PermissionError:
        warnings.append(
            "Could not clear " + str(target) + " (sandbox restriction). "
            "Merging instead. Renamed or removed skills may leave stragglers."
        )
        target.mkdir(parents=True, exist_ok=True)
        for src_file in source.rglob("*"):
            if src_file.is_dir():
                continue
            rel = src_file.relative_to(source)
            dst_file = target / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    skill_count = sum(1 for child in target.iterdir() if child.is_dir())
    return skill_count, warnings


def main() -> int:
    if not SOURCE.exists() or not SOURCE.is_dir():
        print("Error: canonical skills/ not found at " + str(SOURCE), file=sys.stderr)
        return 1

    source_skills = sum(1 for child in SOURCE.iterdir() if child.is_dir())
    if source_skills == 0:
        print("Error: skills/ is empty at " + str(SOURCE), file=sys.stderr)
        return 1

    print("Source: " + str(SOURCE.relative_to(PACK_ROOT)) + " (" + str(source_skills) + " skills)")
    all_warnings: List[str] = []
    for target in TARGETS:
        count, warnings = sync(SOURCE, target)
        rel = target.relative_to(PACK_ROOT)
        print("  -> synced to " + str(rel) + " (" + str(count) + " skills)")
        all_warnings.extend(warnings)

    if all_warnings:
        print("", file=sys.stderr)
        for w in all_warnings:
            print("Warning: " + w, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
