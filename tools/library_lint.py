#!/usr/bin/env python3
"""
library_lint.py -- static checks for every Library item (templates, skills,
property sets, collections). No network, no API key. Run from the repo root:

    python tools/library_lint.py            # lint everything
    python tools/library_lint.py --online   # also compare against the latest released manifest
                                            # (flags body changes without a version bump)

Template rules (from reference/SEGMENT_CREATION_GUIDELINES.md and rulings):
  T1  header v2 fields present: Name, Version, Purpose, Dataset, Recommended, Tags,
      Risk, Schedule, Goal, Last-Updated, Min-Pack-Version
  T2  exclusion filters use `does not contain all` (never `any`, which silently disables them)
  T3  the diagnostic action variable is `$planned_action` (`$result` is retired)
  T4  a `$reason` diagnostic exists
  T5  the final filter must not START with an `is_null(...)` clause (engine bug: a leading
      is_null in an AND chain disables the whole where-clause)
  T6  bid templates run on the combined `Keywords & Targets` dataset, never `Keywords` or
      `Targets` alone
  T7  Risk matches the Recommended action line
  T8  body unchanged since the last release, or Version bumped (--online only)

Skill rules (Agent Skills spec + our metadata contract):
  S1  frontmatter name matches folder, 1-64 chars, lowercase alphanumerics/hyphens
  S2  description 1-1024 chars, says what AND when
  S3  metadata keys are strings only (spec) and include version, tags, goal, risk
  S4  SKILL.md body under 500 lines (spec recommendation) -> warning
  S5  account skills declare requires-skills: merchjar-connect; local installation is exempt

Exit 1 on any error; warnings never fail the run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_manifest import (REPO_ROOT, SKILLS_DIR, TEMPLATE_DIR, build, normalize_dsl,  # noqa: E402
                            parse_frontmatter, parse_template_header)

LATEST_MANIFEST = "https://github.com/merchjar/copilot/releases/latest/download/manifest.json"
REQUIRED_HEADER = ("version", "purpose", "dataset", "recommended", "tags", "risk", "schedule",
                   "goal", "last-updated", "min-pack-version")
RISK_HINTS = {
    "negatives": ("negative",),
    "state": ("set state", "pause", "enable"),
    "bids": ("change bid", "set bid", "bid:"),
    "budgets": ("budget",),
    "read-only": ("ad-hoc", "investigation", "review-only", "insight", "read"),
}


def final_filter(text: str) -> str:
    m = re.search(r"===\s*Final Filter\s*===\s*(.*)$", text, flags=re.S)
    body = m.group(1) if m else text
    body = re.sub(r"//[^\n]*", "", body)
    return body.strip()


def lint_template(path: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    f, errs = parse_template_header(text)
    errors += errs
    for req in REQUIRED_HEADER:
        if not f.get(req):
            errors.append(f"T1 header missing '{req.title()}:'")
    risk = f.get("risk", "")
    # T2
    for m in re.finditer(r"does not contain any\s+\$(\w+)", text):
        if "exclude" in m.group(1).lower():
            errors.append(f"T2 exclusion filter uses 'does not contain any ${m.group(1)}' (must be 'all')")
    # T3 / T4
    if risk != "read-only":
        if re.search(r"let\s+\$result\s*=", text):
            errors.append("T3 defines `$result`; use `$planned_action`")
        if not re.search(r"let\s+\$planned_action\s*=", text):
            errors.append("T3 no `$planned_action` diagnostic")
    else:
        if re.search(r"let\s+\$result\s*=", text):
            errors.append("T3 defines `$result`; use `$planned_action` (read-only templates too)")
    if not re.search(r"let\s+\$reason\s*=", text):
        errors.append("T4 no `$reason` diagnostic")
    # T5
    ff = final_filter(text)
    if re.match(r"^\(?\s*is_null\(", ff):
        errors.append("T5 final filter starts with is_null(...) (move it to the end of the AND chain)")
    # T6
    ds = f.get("dataset", "").strip().lower()
    if risk == "bids" and ds in ("keywords", "targets"):
        errors.append(f"T6 bid template on '{f.get('dataset')}' alone; use 'Keywords & Targets'")
    # T7
    rec = f.get("recommended", "").lower()
    if risk and rec:
        hints = RISK_HINTS.get(risk, ())
        if hints and not any(h in rec for h in hints):
            warnings.append(f"T7 Risk '{risk}' does not match Recommended line '{f.get('recommended')}'")
    return [f"{rel}: {e}" for e in errors], [f"{rel}: {w}" for w in warnings]


def lint_skill(path: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    rel = path.relative_to(REPO_ROOT).as_posix()
    raw = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)
    name = fm.get("name", "")
    if name != path.parent.name:
        errors.append(f"S1 name '{name}' != folder '{path.parent.name}'")
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name or "") or len(name) > 64:
        errors.append("S1 name must be 1-64 lowercase alphanumerics/hyphens, no leading/trailing/double hyphens")
    desc = fm.get("description", "")
    if not (1 <= len(desc) <= 1024):
        errors.append("S2 description must be 1-1024 chars")
    elif not re.search(r"\buse when\b|\buse this\b|\bwhen the user\b", desc, flags=re.I):
        warnings.append("S2 description should say WHEN to use it ('Use when ...')")
    allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    for k in fm:
        if k not in allowed:
            errors.append(f"S3 unknown frontmatter field '{k}' (spec allows {sorted(allowed)})")
    meta = fm.get("metadata")
    if not isinstance(meta, dict):
        errors.append("S3 metadata block missing")
    else:
        for k, v in meta.items():
            if not isinstance(v, str):
                errors.append(f"S3 metadata.{k} must be a string (spec: string->string map)")
        for req in ("version", "tags", "goal", "risk"):
            if not meta.get(req):
                errors.append(f"S3 metadata.{req} missing")
        if name not in {"merchjar-connect", "manage-library"} and "merchjar-connect" not in str(meta.get("requires-skills", "")):
            errors.append("S5 metadata.requires-skills must include merchjar-connect")
    if body.count("\n") > 500:
        warnings.append(f"S4 SKILL.md body is {body.count(chr(10))} lines (>500); move detail to references/")
    return [f"{rel}: {e}" for e in errors], [f"{rel}: {w}" for w in warnings]


def online_version_check(local_templates: list[dict]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    try:
        with urllib.request.urlopen(LATEST_MANIFEST, timeout=30) as r:
            released = json.load(r)
    except Exception as e:  # noqa: BLE001
        return [], [f"T8 could not fetch latest released manifest ({e}); skipped"]
    rel_by_id = {t["id"]: t for t in released.get("templates", [])}
    for t in local_templates:
        r = rel_by_id.get(t["id"])
        if not r:
            continue
        released_sha = r.get("body_sha")
        if released_sha is None:
            # v1 manifests carry no body hash; fetch the released bytes and hash them
            try:
                with urllib.request.urlopen(r.get("raw_url") or f"https://raw.githubusercontent.com/merchjar/copilot/{released['tag']}/{r['path']}", timeout=30) as rr:
                    from build_manifest import _sha
                    released_sha = _sha(normalize_dsl(rr.read().decode("utf-8")))
            except Exception:  # noqa: BLE001
                continue
        if released_sha != t["body_sha"] and r.get("version") == t["version"]:
            errors.append(f"{t['path']}: T8 body changed since {released['tag']} but Version is still {t['version']}")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true", help="compare bodies against the latest released manifest")
    ap.add_argument("--pack-version", default="0.0.0", help="only used to build the in-memory manifest")
    args = ap.parse_args()

    errors, warnings = [], []
    for p in sorted(TEMPLATE_DIR.glob("*/*.txt")):
        e, w = lint_template(p); errors += e; warnings += w
    for p in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        e, w = lint_skill(p); errors += e; warnings += w
    manifest, merr = build(args.pack_version)
    errors += [f"manifest: {m}" for m in merr]
    if args.online:
        e, w = online_version_check(manifest["templates"]); errors += e; warnings += w

    for w in warnings:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    c = manifest["counts"]
    print(f"lint: {c['templates']} templates, {c['skills']} skills, {c['properties']} property sets, "
          f"{c['collections']} collections -> {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
