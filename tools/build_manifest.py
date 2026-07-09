#!/usr/bin/env python3
"""
build_manifest.py -- generate manifest.json for the merchjar/copilot repo.

The manifest is the machine-readable catalog the Copilot fetches to list
templates, filter by tag, fetch bytes, and check for updates. It is GENERATED
from per-template front-matter, never hand-edited. Run from the repo root:

    python tools/build_manifest.py --pack-version 1.0.0            # write manifest.json
    python tools/build_manifest.py --pack-version 1.0.0 --check    # validate only, no write

Front-matter source: the leading C-style /* ... */ header in each
templates/<category>/*.txt DSL file (the top-level master library). Header
fields parsed:
    === <Name> ===   -> name
    Version:         -> version   (template-level; not pack semver)
    Docs:            -> docs
    Purpose:         -> description
    Dataset:         -> dataset
    Tags:            -> tags (comma-separated -> list)
    Last-Updated:    -> last_updated (YYYY-MM-DD)
    Min-Pack-Version:-> min_pack_version

stdlib only. Exit non-zero on any validation failure so CI can gate on it.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SCHEMA_VERSION = 1
REPO_ROOT = Path(__file__).resolve().parent.parent
# Top-level master library, organized by category subdirectory. The pack ships
# no templates (core automations are auto-deployed to accounts by the app); the
# manifest catalogs the full library that the Copilot fetches on demand.
TEMPLATE_DIR = REPO_ROOT / "templates"
TEMPLATE_GLOB = "*/*.txt"  # templates/<category>/<slug>.txt
MANIFEST_PATH = REPO_ROOT / "manifest.json"

REQUIRED = ["id", "slug", "name", "path", "category", "version", "dataset",
            "tags", "description", "last_updated", "min_pack_version"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_header(text):
    """Extract the leading /* ... */ block and parse its labelled fields."""
    m = re.search(r"/\*(.*?)\*/", text, re.DOTALL)
    if not m:
        raise ValueError("no /* ... */ header block")
    body = m.group(1)
    fields = {}
    name = None
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        title = re.match(r"^===\s*(.+?)\s*===$", line)
        if title:
            name = title.group(1)
            continue
        kv = re.match(r"^([A-Za-z][A-Za-z\- ]*?):\s*(.*)$", line)
        if kv:
            fields[kv.group(1).strip().lower()] = kv.group(2).strip()
    fields["_name"] = name
    return fields


def build_entry(path, pack_version):
    text = path.read_text(encoding="utf-8")
    f = parse_header(text)
    slug = path.stem  # filename without .txt == stable id/slug
    category = path.parent.name  # templates/<category>/<slug>.txt
    tags = [t.strip() for t in f.get("tags", "").split(",") if t.strip()]
    entry = {
        "id": slug,
        "slug": slug,
        "name": f.get("_name") or slug,
        "path": "templates/" + category + "/" + path.name,
        "category": category,
        "version": f.get("version", ""),
        "dataset": f.get("dataset", ""),
        "tags": tags,
        "description": f.get("purpose", ""),
        "last_updated": f.get("last-updated", ""),
        "min_pack_version": f.get("min-pack-version", ""),
        "docs": f.get("docs", ""),
    }
    return entry


def validate(entries):
    errors = []
    seen = set()
    for e in entries:
        label = e.get("id") or "<no-id>"
        for k in REQUIRED:
            v = e.get(k)
            if v in (None, "", []):
                errors.append(label + ": missing required field '" + k + "'")
        if e["id"] in seen:
            errors.append(label + ": duplicate id")
        seen.add(e["id"])
        p = REPO_ROOT / e["path"]
        if not p.exists():
            errors.append(label + ": path does not exist: " + e["path"])
        if e.get("last_updated") and not DATE_RE.match(e["last_updated"]):
            errors.append(label + ": last_updated not YYYY-MM-DD: " + e["last_updated"])
    on_disk = {str(p.relative_to(REPO_ROOT)).replace("\\", "/")
               for p in sorted(TEMPLATE_DIR.glob(TEMPLATE_GLOB))}
    in_manifest = {e["path"] for e in entries}
    for orphan in on_disk - in_manifest:
        errors.append("orphan template not in manifest: " + orphan)
    for missing in in_manifest - on_disk:
        errors.append("manifest references missing template: " + missing)
    return errors


def main():
    ap = argparse.ArgumentParser(description="Generate/validate manifest.json")
    ap.add_argument("--pack-version", required=True, help="e.g. 1.0.0")
    ap.add_argument("--check", action="store_true", help="validate only; do not write")
    args = ap.parse_args()

    paths = sorted(TEMPLATE_DIR.glob(TEMPLATE_GLOB))
    if not paths:
        print("ERROR: no templates found in " + str(TEMPLATE_DIR), file=sys.stderr)
        return 2

    entries = [build_entry(p, args.pack_version) for p in paths]
    errors = validate(entries)
    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        return 1

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pack_version": args.pack_version,
        "generated": date.today().isoformat(),
        "template_count": len(entries),
        "templates": entries,
    }

    if args.check:
        print("OK  " + str(len(entries)) + " templates valid (schema_version="
              + str(SCHEMA_VERSION) + ", pack_version=" + args.pack_version
              + "). --check: not written.")
        return 0

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote " + str(MANIFEST_PATH.relative_to(REPO_ROOT)) + "  ("
          + str(len(entries)) + " templates, pack_version=" + args.pack_version + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
