#!/usr/bin/env python3
"""
build_manifest.py -- generate manifest.json (schema v2) for the merchjar/copilot repo.

The manifest is the machine-readable catalog of the whole Library: templates,
skills, property sets, and collections. It is GENERATED, never hand-edited.
Run from the repo root:

    python tools/build_manifest.py --pack-version 1.2.0            # write manifest.json
    python tools/build_manifest.py --pack-version 1.2.0 --check    # validate only, no write

Sources
  templates/<category>/<slug>.txt   leading /* ... */ header block (see templates/README.md)
  skills/<name>/SKILL.md            YAML frontmatter (Agent Skills spec + metadata)
  properties/<id>/property-set.json property-set definitions
  collections/<id>.md               YAML frontmatter (curated bundles)

Schema v2 keeps the v1 `templates` array shape (with extra optional fields) so
existing consumers (tools/library.py, the site) keep working, and adds
`skills`, `properties`, `collections`, and `counts`.

stdlib only. Exit non-zero on any validation failure so CI can gate on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

SCHEMA_VERSION = 2
REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "templates"
SKILLS_DIR = REPO_ROOT / "skills"
PROPERTIES_DIR = REPO_ROOT / "properties"
COLLECTIONS_DIR = REPO_ROOT / "collections"
OUT = REPO_ROOT / "manifest.json"

RAW_BASE = "https://raw.githubusercontent.com/merchjar/copilot"

TEMPLATE_CATEGORIES = {"optimize", "insight", "utility"}
RISKS = {"read-only", "bids", "budgets", "state", "negatives"}
GOALS = {"cut-waste", "grow", "protect", "understand", "set-up"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

DATASET_TO_AD_TYPE = {
    "search terms": "search_terms",
    "keywords & targets": "keywords_and_targets",
    "keywords and targets": "keywords_and_targets",
    "campaigns": "campaigns",
    "ad groups": "ad_groups",
    "product ads": "ads",
    "keywords": "keywords",
    "targets": "targets",
}


# --------------------------------------------------------------------------- helpers
def _split_list(value: str) -> list[str]:
    value = (value or "").strip()
    if not value or value.lower() == "none":
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def normalize_dsl(dsl: str) -> str:
    """Comment- and whitespace-insensitive body, used for drift and change detection."""
    dsl = re.sub(r"/\*.*?\*/", "", dsl, flags=re.S)
    dsl = re.sub(r"//[^\n]*", "", dsl)
    return re.sub(r"\s+", " ", dsl).strip()


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Tiny YAML-subset parser: scalars, one level of nested maps, flow/dash lists."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, flags=re.S)
    if not m:
        return {}, text
    fm: dict = {}
    current_map = None
    current_list = None
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            current_map = current_list = None
            key, _, val = line.partition(":")
            key = key.strip(); val = val.strip()
            if val == "":
                fm[key] = {}
                current_map = fm[key]
            elif val.startswith("[") and val.endswith("]"):
                fm[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            else:
                fm[key] = val.strip("'\"")
        elif line.startswith("- "):
            item = line[2:].strip().strip("'\"")
            if current_list is not None:
                current_list.append(item)
            elif current_map is not None and isinstance(current_map, dict) and current_map:
                # list under the last key of the nested map
                last_key = list(current_map.keys())[-1]
                if not isinstance(current_map[last_key], list):
                    current_map[last_key] = []
                current_map[last_key].append(item)
            else:
                last_key = list(fm.keys())[-1]
                if not isinstance(fm[last_key], list):
                    fm[last_key] = []
                fm[last_key].append(item)
        else:
            key, _, val = line.partition(":")
            key = key.strip(); val = val.strip()
            if current_map is None:
                continue
            if val == "":
                current_map[key] = []
                current_list = current_map[key]
            elif val.startswith("[") and val.endswith("]"):
                current_map[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
                current_list = None
            else:
                current_map[key] = val.strip("'\"")
                current_list = None
    return fm, m.group(2)


# --------------------------------------------------------------------------- templates
HEADER_RE = re.compile(r"^\s*/\*(.*?)\*/", flags=re.S)


def parse_template_header(text: str) -> tuple[dict, list[str]]:
    errors: list[str] = []
    m = HEADER_RE.match(text)
    if not m:
        return {}, ["missing leading /* ... */ header block"]
    header = m.group(1)
    fields: dict = {}
    name_m = re.search(r"===\s*(.+?)\s*===", header)
    if name_m:
        fields["name"] = name_m.group(1).strip()
    else:
        errors.append("header has no '=== Name ===' line")
    changelog: list[str] = []
    for line in header.splitlines():
        line = line.strip()
        if not line or line.startswith("==="):
            continue
        key, sep, val = line.partition(":")
        if not sep:
            continue
        key = key.strip().lower(); val = val.strip()
        if key == "changelog":
            changelog.append(val)
        else:
            fields[key] = val
    fields["changelog"] = changelog
    return fields, errors


def build_templates(tag: str) -> tuple[list[dict], list[str]]:
    items, errors = [], []
    if not TEMPLATE_DIR.exists():
        return items, [f"missing {TEMPLATE_DIR.relative_to(REPO_ROOT)}"]
    for path in sorted(TEMPLATE_DIR.glob("*/*.txt")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        category = path.parent.name
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        f, errs = parse_template_header(text)
        errors += [f"{rel}: {e}" for e in errs]
        if category not in TEMPLATE_CATEGORIES:
            errors.append(f"{rel}: category folder '{category}' not in {sorted(TEMPLATE_CATEGORIES)}")
        for req in ("version", "dataset", "tags", "last-updated", "min-pack-version"):
            if req not in f:
                errors.append(f"{rel}: header missing '{req.title()}:'")
        if "purpose" not in f:
            errors.append(f"{rel}: header missing 'Purpose:'")
        for k in ("last-updated",):
            if k in f and not re.match(r"^\d{4}-\d{2}-\d{2}$", f[k]):
                errors.append(f"{rel}: {k} must be YYYY-MM-DD")
        if "min-pack-version" in f and not SEMVER.match(f["min-pack-version"]):
            errors.append(f"{rel}: Min-Pack-Version must be semver")
        risk = f.get("risk", "").strip()
        if risk and risk not in RISKS:
            errors.append(f"{rel}: Risk '{risk}' not in {sorted(RISKS)}")
        goal = f.get("goal", "").strip()
        if goal and goal not in GOALS:
            errors.append(f"{rel}: Goal '{goal}' not in {sorted(GOALS)}")
        dataset = f.get("dataset", "")
        ad_type = DATASET_TO_AD_TYPE.get(dataset.lower().strip())
        items.append({
            "id": slug,
            "slug": slug,
            "name": f.get("name", slug),
            "path": rel,
            "category": category,
            "version": f.get("version", ""),
            "dataset": dataset,
            "ad_type": ad_type,
            "tags": _split_list(f.get("tags", "")),
            "description": f.get("purpose", ""),
            "recommended": f.get("recommended", ""),
            "risk": risk or None,
            "schedule": f.get("schedule", "") or None,
            "goal": goal or None,
            "requires_properties": _split_list(f.get("requires-properties", "")),
            "pairs_with": _split_list(f.get("pairs-with", "")),
            "changelog": f.get("changelog", []),
            "last_updated": f.get("last-updated", ""),
            "min_pack_version": f.get("min-pack-version", ""),
            "body_sha": _sha(normalize_dsl(text)),
            "docs": f.get("docs", ""),
            "raw_url": f"{RAW_BASE}/{tag}/{rel}",
        })
    ids = [i["id"] for i in items]
    for dup in {i for i in ids if ids.count(i) > 1}:
        errors.append(f"duplicate template id '{dup}'")
    return items, errors


# --------------------------------------------------------------------------- skills
def build_skills(tag: str) -> tuple[list[dict], list[str]]:
    items, errors = [], []
    if not SKILLS_DIR.exists():
        return items, []
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        name = fm.get("name", "")
        if not name:
            errors.append(f"{rel}: frontmatter missing 'name'")
        elif name != path.parent.name:
            errors.append(f"{rel}: name '{name}' must match folder '{path.parent.name}'")
        elif not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) or len(name) > 64:
            errors.append(f"{rel}: name must be 1-64 lowercase alphanumerics/hyphens")
        desc = fm.get("description", "")
        if not desc or len(desc) > 1024:
            errors.append(f"{rel}: description must be 1-1024 chars")
        meta = fm.get("metadata", {}) if isinstance(fm.get("metadata"), dict) else {}
        items.append({
            "id": name,
            "name": name,
            "path": rel,
            "dir": path.parent.relative_to(REPO_ROOT).as_posix(),
            "description": desc,
            "version": meta.get("version", ""),
            "tags": _split_list(meta.get("tags", "")) if isinstance(meta.get("tags"), str) else meta.get("tags", []),
            "goal": meta.get("goal", "") or None,
            "requires_scopes": _split_list(meta.get("requires-scopes", "")),
            "requires_skills": _split_list(meta.get("requires-skills", "")),
            "requires_properties": _split_list(meta.get("requires-properties", "")),
            "produces": meta.get("produces", ""),
            "risk": meta.get("risk", "") or None,
            "compatibility": fm.get("compatibility", meta.get("compatibility", "")),
            "license": fm.get("license", ""),
            "last_updated": meta.get("last-updated", ""),
            "ships_in_pack": (REPO_ROOT / "copilot-pack" / "skills" / name / "SKILL.md").exists(),
            "has_scripts": (path.parent / "scripts").exists(),
            "has_references": (path.parent / "references").exists(),
            "body_sha": _sha(body),
            "raw_url": f"{RAW_BASE}/{tag}/{rel}",
            **({"connection_mode": meta["connection-mode"],
                "connected_skills": _split_list(meta.get("connected-skills", ""))}
               if meta.get("connection-mode") else {}),
        })
    return items, errors


# --------------------------------------------------------------------------- properties
def build_properties(tag: str) -> tuple[list[dict], list[str]]:
    items, errors = [], []
    if not PROPERTIES_DIR.exists():
        return items, []
    for path in sorted(PROPERTIES_DIR.glob("*/property-set.json")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{rel}: invalid JSON ({e})"); continue
        pid = data.get("id", path.parent.name)
        if pid != path.parent.name:
            errors.append(f"{rel}: id '{pid}' must match folder '{path.parent.name}'")
        for req in ("name", "description", "fields"):
            if req not in data:
                errors.append(f"{rel}: missing '{req}'")
        items.append({
            "id": pid, "name": data.get("name", pid), "path": rel,
            "description": data.get("description", ""),
            "version": data.get("version", ""),
            "entity_types": data.get("entity_types", []),
            "fields": [f.get("key") for f in data.get("fields", []) if isinstance(f, dict)],
            "pairs_with": data.get("pairs_with", []),
            "goal": data.get("goal") or None,
            "last_updated": data.get("last_updated", ""),
            "raw_url": f"{RAW_BASE}/{tag}/{rel}",
        })
    return items, errors


# --------------------------------------------------------------------------- collections
def build_collections(known_ids: set[str]) -> tuple[list[dict], list[str]]:
    items, errors = [], []
    if not COLLECTIONS_DIR.exists():
        return items, []
    for path in sorted(COLLECTIONS_DIR.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        cid = fm.get("id", path.stem)
        if cid != path.stem:
            errors.append(f"{rel}: id '{cid}' must match filename")
        for req in ("name", "items"):
            if req not in fm:
                errors.append(f"{rel}: frontmatter missing '{req}'")
        its = fm.get("items", []) if isinstance(fm.get("items"), list) else []
        for it in its:
            if it not in known_ids:
                errors.append(f"{rel}: item '{it}' is not a known template/skill/property id")
        items.append({
            "id": cid, "name": fm.get("name", cid), "path": rel,
            "description": fm.get("description", ""),
            "goal": fm.get("goal") or None,
            "items": its,
            "featured": str(fm.get("featured", "false")).lower() == "true",
            "story": body.strip(),
        })
    return items, errors


# --------------------------------------------------------------------------- main
def build(pack_version: str) -> tuple[dict, list[str]]:
    tag = f"v{pack_version}"
    templates, e1 = build_templates(tag)
    skills, e2 = build_skills(tag)
    properties, e3 = build_properties(tag)
    known = {t["id"] for t in templates} | {s["id"] for s in skills} | {p["id"] for p in properties}
    collections, e4 = build_collections(known)
    errors = e1 + e2 + e3 + e4
    # cross-reference checks
    for t in templates:
        for ref in t["pairs_with"]:
            if ref not in known:
                errors.append(f"{t['path']}: Pairs-With '{ref}' is not a known id")
        for ref in t["requires_properties"]:
            if ref not in {p["id"] for p in properties}:
                errors.append(f"{t['path']}: Requires-Properties '{ref}' is not a known property set")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pack_version": pack_version,
        "tag": tag,
        "generated": date.today().isoformat(),
        "template_count": len(templates),
        "counts": {"templates": len(templates), "skills": len(skills),
                   "properties": len(properties), "collections": len(collections)},
        "templates": templates,
        "skills": skills,
        "properties": properties,
        "collections": collections,
    }
    return manifest, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack-version", required=True, help="semver, e.g. 1.2.0 (tag becomes v1.2.0)")
    ap.add_argument("--check", action="store_true", help="validate only; do not write manifest.json")
    args = ap.parse_args()
    if not SEMVER.match(args.pack_version):
        print(f"error: --pack-version must be semver, got {args.pack_version}", file=sys.stderr)
        return 2
    manifest, errors = build(args.pack_version)
    if errors:
        print("manifest validation FAILED:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        return 1
    c = manifest["counts"]
    summary = f"{c['templates']} templates, {c['skills']} skills, {c['properties']} property sets, {c['collections']} collections (schema v{SCHEMA_VERSION}, pack {args.pack_version})"
    if args.check:
        print("OK  " + summary + ". --check: not written.")
        return 0
    OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote manifest.json  " + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
