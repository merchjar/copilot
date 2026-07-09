#!/usr/bin/env python3
"""
library.py - fetch client for the Merch Jar template library (GitHub source of truth).

Stdlib only. The Copilot Pack ships no templates; the master library lives in the
public merchjar/copilot repo and is fetched on demand. This client lists, searches,
fetches, and update-checks templates against the RELEASED manifest and raw files.

Two public data sources (no auth, CDN-served):
  - Catalog / update check: the manifest attached to the latest Release
        https://github.com/merchjar/copilot/releases/latest/download/manifest.json
  - Template bytes: raw files pinned to the manifest's tag
        https://raw.githubusercontent.com/merchjar/copilot/<tag>/<path>

We deliberately avoid the GitHub REST API for fetches (60 req/hr unauthenticated
per IP). Both sources above are unauthenticated CDN endpoints with no such limit.

Usage:
    python tools/library.py list [--category core] [--tag waste] [--json]
    python tools/library.py search "search term waste"
    python tools/library.py info <id>
    python tools/library.py fetch <id> [--out PATH_OR_DIR]      # default: stdout
    python tools/library.py check-updates

Overrides (testing / pre-launch, all optional):
    MJ_COPILOT_REPO   default "merchjar/copilot"
    MJ_MANIFEST_URL   full manifest URL (overrides the release-asset default)
    MJ_COPILOT_REF    pin the manifest + raw fetches to a branch/tag (e.g. "main")
                      instead of the latest release. Useful before the first
                      release exists, or to preview main.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PACK_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = PACK_ROOT / "user" / ".library-cache.json"
DEFAULT_REPO = "merchjar/copilot"
UA = "merchjar-copilot-library/1.0"
TIMEOUT = 20


# ---- config / URLs --------------------------------------------------------

def repo() -> str:
    return os.environ.get("MJ_COPILOT_REPO", DEFAULT_REPO)


def ref_override() -> str | None:
    r = os.environ.get("MJ_COPILOT_REF")
    return r.strip() if r else None


def manifest_url() -> str:
    if os.environ.get("MJ_MANIFEST_URL"):
        return os.environ["MJ_MANIFEST_URL"]
    ref = ref_override()
    if ref:
        return f"https://raw.githubusercontent.com/{repo()}/{ref}/manifest.json"
    return f"https://github.com/{repo()}/releases/latest/download/manifest.json"


def raw_url(ref: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo()}/{ref}/{path}"


def resolve_ref(manifest: dict) -> str:
    """Which ref template bytes are pinned to. Override wins; else the manifest's
    recorded tag; else derive from pack_version (v-prefixed by convention)."""
    ov = ref_override()
    if ov:
        return ov
    tag = manifest.get("tag")
    if tag:
        return tag
    pv = manifest.get("pack_version", "")
    return f"v{pv}" if pv else "main"


# ---- HTTP -----------------------------------------------------------------

def http_get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except HTTPError as e:
        if e.code == 404 and "releases/latest/download" in url:
            raise SystemExit(
                "No published release yet: " + url + " returned 404.\n"
                "If you are testing before launch, set MJ_COPILOT_REF=main to read "
                "the template library from the main branch instead."
            )
        raise SystemExit(f"HTTP {e.code} fetching {url}: {e.reason}")
    except URLError as e:
        raise SystemExit(f"Network error fetching {url}: {e.reason}")


def load_manifest() -> dict:
    return json.loads(http_get(manifest_url()).decode("utf-8"))


# ---- helpers --------------------------------------------------------------

def find_template(manifest: dict, tid: str) -> dict:
    for t in manifest.get("templates", []):
        if t.get("id") == tid or t.get("slug") == tid:
            return t
    ids = ", ".join(sorted(t.get("id", "") for t in manifest.get("templates", [])))
    raise SystemExit(f"Template '{tid}' not found. Available ids: {ids}")


def print_table(templates: list[dict]) -> None:
    if not templates:
        print("No templates match.")
        return
    width = max(len(t.get("id", "")) for t in templates)
    for t in templates:
        tags = ",".join(t.get("tags", []))
        print(f"{t.get('id','').ljust(width)}  [{t.get('category','')}]  "
              f"{t.get('dataset','')}  ({tags})")
        print(f"{' ' * width}  {t.get('description','')}")


# ---- commands -------------------------------------------------------------

def cmd_list(args) -> int:
    m = load_manifest()
    ts = m.get("templates", [])
    if args.category:
        ts = [t for t in ts if t.get("category") == args.category]
    if args.tag:
        ts = [t for t in ts if args.tag in t.get("tags", [])]
    if args.json:
        print(json.dumps(ts, indent=2))
    else:
        print(f"Merch Jar template library ({m.get('pack_version','?')}, "
              f"{len(ts)} of {len(m.get('templates', []))} templates)\n")
        print_table(ts)
    return 0


def cmd_search(args) -> int:
    m = load_manifest()
    q = args.query.lower()
    hits = []
    for t in m.get("templates", []):
        hay = " ".join([
            t.get("id", ""), t.get("name", ""), t.get("description", ""),
            t.get("dataset", ""), t.get("category", ""), " ".join(t.get("tags", [])),
        ]).lower()
        if q in hay:
            hits.append(t)
    print(f"{len(hits)} match(es) for '{args.query}':\n")
    print_table(hits)
    return 0 if hits else 1


def cmd_info(args) -> int:
    m = load_manifest()
    t = find_template(m, args.id)
    ref = resolve_ref(m)
    print(json.dumps(t, indent=2))
    print("\nraw URL:", raw_url(ref, t["path"]))
    return 0


def cmd_fetch(args) -> int:
    m = load_manifest()
    t = find_template(m, args.id)
    ref = resolve_ref(m)
    data = http_get(raw_url(ref, t["path"]))
    if not args.out or args.out == "-":
        sys.stdout.buffer.write(data)
        return 0
    out = Path(args.out)
    if out.is_dir():
        out = out / Path(t["path"]).name
    out.write_bytes(data)
    print(f"wrote {out}  ({len(data)} bytes, {t['id']} @ {ref})")
    return 0


def _index(manifest: dict) -> dict:
    """id -> (version, last_updated) for diffing."""
    return {t.get("id"): (t.get("version", ""), t.get("last_updated", ""))
            for t in manifest.get("templates", [])}


def cmd_check_updates(args) -> int:
    remote = load_manifest()
    if not CACHE_PATH.exists():
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(remote, indent=2), encoding="utf-8")
        print(f"No local baseline yet. Recorded {len(remote.get('templates', []))} "
              f"templates at pack_version {remote.get('pack_version','?')}.")
        print("Run check-updates again after a release to see what changed.")
        return 0

    cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    r_idx, c_idx = _index(remote), _index(cached)
    added = sorted(set(r_idx) - set(c_idx))
    removed = sorted(set(c_idx) - set(r_idx))
    updated = sorted(i for i in set(r_idx) & set(c_idx) if r_idx[i] != c_idx[i])

    rv, cv = remote.get("pack_version", "?"), cached.get("pack_version", "?")
    if rv != cv:
        print(f"Pack version: {cv} -> {rv}")
    else:
        print(f"Pack version: {rv} (unchanged)")

    if not (added or removed or updated):
        print("Templates: up to date.")
    else:
        for i in added:
            print(f"  + new      {i}")
        for i in updated:
            print(f"  ~ updated  {i}  (v{c_idx[i][0]} {c_idx[i][1]} -> "
                  f"v{r_idx[i][0]} {r_idx[i][1]})")
        for i in removed:
            print(f"  - removed  {i}")

    CACHE_PATH.write_text(json.dumps(remote, indent=2), encoding="utf-8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Merch Jar template library fetch client")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list templates in the library")
    p.add_argument("--category")
    p.add_argument("--tag")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("search", help="search templates by keyword")
    p.add_argument("query")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("info", help="show one template's metadata + raw URL")
    p.add_argument("id")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("fetch", help="fetch a template's DSL (stdout or --out)")
    p.add_argument("id")
    p.add_argument("--out", help="file or directory; default stdout")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("check-updates", help="diff the released library against local cache")
    p.set_defaults(func=cmd_check_updates)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
