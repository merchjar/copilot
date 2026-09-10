#!/usr/bin/env python3
"""
build_skills.py -- sync the canonical skills/ folder to every place an agent looks.

Run from the repo root after editing anything under skills/:

    python tools/build_skills.py

Canonical source: skills/<name>/ (Agent Skills spec: SKILL.md + optional scripts/,
references/, assets/). Targets, all generated, never edit them directly:

  copilot-pack/skills/            the pack's own skills folder (the brain routes here)
  copilot-pack/.claude/skills/    Claude Code auto-discovery inside the pack
  copilot-pack/.agents/skills/    Codex auto-discovery inside the pack
  copilot-pack/.github/skills/    GitHub Copilot / VS Code discovery
  copilot-pack/.gemini/skills/    Gemini CLI discovery
  .claude/skills/                 Claude Code, when the repo itself is the project
  .agents/skills/                 Codex, when the repo itself is the project
  .github/skills/                 GitHub Copilot / VS Code
  .gemini/skills/                 Gemini CLI

Plus two flattened copies the pack's docs reference by their old paths:

  skills/merchjar-connect/scripts/merchjar_client.py -> copilot-pack/tools/merchjar_client.py
  skills/merchjar-connect/references/*.md            -> copilot-pack/reference/*.md

`npx skills add merchjar/copilot` reads skills/ directly and dedupes by name, so the
mirrors do not produce duplicates there. Stdlib only; works on Windows, macOS, Linux.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "skills"
PACK = REPO_ROOT / "copilot-pack"
PACK_TARGETS = [
    PACK / "skills",
    PACK / ".claude" / "skills",
    PACK / ".agents" / "skills",
    PACK / ".github" / "skills",
    PACK / ".gemini" / "skills",
]
REPO_TARGETS = [
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".agents" / "skills",
    REPO_ROOT / ".github" / "skills",
    REPO_ROOT / ".gemini" / "skills",
]
DEFAULT_SKILLS = {
    "account-review", "audit-log", "build-segment", "check-segments",
    "create-campaigns", "enrich-account", "explain-segment", "manage-library",
    "merchjar-connect", "performance-check", "review-segment", "troubleshoot",
}
CONNECT = SOURCE / "merchjar-connect"
FLAT = [
    (CONNECT / "scripts" / "merchjar_client.py", PACK / "tools" / "merchjar_client.py"),
    (CONNECT / "references" / "MJ_API_REFERENCE.md", PACK / "reference" / "MJ_API_REFERENCE.md"),
    (CONNECT / "references" / "V2_SYNTAX_REFERENCE.md", PACK / "reference" / "V2_SYNTAX_REFERENCE.md"),
    (CONNECT / "references" / "SEGMENT_CREATION_GUIDELINES.md", PACK / "reference" / "SEGMENT_CREATION_GUIDELINES.md"),
    (SOURCE / "manage-library" / "scripts" / "update_copilot.py", PACK / "tools" / "update_copilot.py"),
]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def sync(source: Path, target: Path, include: set[str] | None = None) -> tuple[int, list[str]]:
    warnings: list[str] = []
    target.parent.mkdir(parents=True, exist_ok=True)
    selected = [child for child in source.iterdir()
                if child.is_dir() and (include is None or child.name in include)]
    try:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for child in selected:
            shutil.copytree(child, target / child.name, ignore=IGNORE)
    except PermissionError:
        warnings.append(f"could not clear {target} (sandbox); merged instead, removed skills may linger")
        target.mkdir(parents=True, exist_ok=True)
        for child in selected:
            for f in child.rglob("*"):
                if f.is_file() and "__pycache__" not in f.parts:
                    d = target / f.relative_to(source)
                    d.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, d)
    return sum(1 for c in target.iterdir() if c.is_dir()), warnings


def main() -> int:
    if not SOURCE.is_dir() or not any(SOURCE.iterdir()):
        print(f"error: canonical skills/ missing or empty at {SOURCE}", file=sys.stderr)
        return 1
    n = sum(1 for c in SOURCE.iterdir() if c.is_dir())
    print(f"source: skills/ ({n} skills)")
    warnings: list[str] = []
    for t in PACK_TARGETS:
        count, w = sync(SOURCE, t, DEFAULT_SKILLS)
        warnings += w
        print(f"  -> {t.relative_to(REPO_ROOT).as_posix()} ({count})")
    for t in REPO_TARGETS:
        count, w = sync(SOURCE, t)
        warnings += w
        print(f"  -> {t.relative_to(REPO_ROOT).as_posix()} ({count})")
    for src, dst in FLAT:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  -> {dst.relative_to(REPO_ROOT).as_posix()} (flattened copy)")
        else:
            warnings.append(f"missing {src.relative_to(REPO_ROOT)}")
    for w in warnings:
        print("warning: " + w, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
