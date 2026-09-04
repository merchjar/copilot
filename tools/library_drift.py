#!/usr/bin/env python3
"""
library_drift.py -- compare the segments live on a profile with the Library templates.

    python tools/library_drift.py --profile 2751686654039572
    python tools/library_drift.py --profile <id> --json

Key: MERCHJAR_API_KEY env var, or --config <pack user/MJ_COPILOT_CONFIG.md>. Read-only.

Matching: a live segment matches a template when its name equals the template
name, or contains the template name (so "Core: X (v1.1) - demo" still matches
"Core: X"). Bodies are compared comment- and whitespace-insensitive.

Verdict per template:
  clean         live body identical to the library
  differs       bodies differ (shows which side carries the newer header Version /
                Last-Updated, so you can tell "account ahead" from "account behind")
  not-deployed  no live segment matches
Plus: live-only segments (candidates for new templates).

Run before every release and monthly. The lab account is where segments get
improved; this is the only thing that notices.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_manifest import REPO_ROOT, build, normalize_dsl, parse_template_header  # noqa: E402
from library_test import call, load_key  # noqa: E402


def header_of(text: str) -> dict:
    f, _ = parse_template_header(text)
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--config")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    key = load_key(args.config)
    manifest, errs = build("0.0.0")
    if errs:
        print("manifest errors; run library_lint.py first", file=sys.stderr); return 1
    st, resp = call(key, "GET", "/api/v5/segments", profile=args.profile)
    if st != 200:
        print(f"GET /segments failed: {st} {resp}", file=sys.stderr); return 1
    live = resp.get("data", [])
    report, matched_live = [], set()
    for t in manifest["templates"]:
        text = (REPO_ROOT / t["path"]).read_text(encoding="utf-8")
        lib_norm = normalize_dsl(text)
        cands = [s for s in live if s["name"] == t["name"]] or [s for s in live if t["name"].lower() in s["name"].lower()]
        if not cands:
            report.append({"template": t["id"], "verdict": "not-deployed"}); continue
        for s in cands:
            matched_live.add(s["id"])
            live_norm = normalize_dsl(s["trigger"])
            if live_norm == lib_norm:
                report.append({"template": t["id"], "verdict": "clean", "segment": s["id"], "segment_name": s["name"], "enabled": s["enabled"]})
            else:
                lh = header_of(s["trigger"])
                report.append({"template": t["id"], "verdict": "differs", "segment": s["id"], "segment_name": s["name"], "enabled": s["enabled"],
                               "library_version": t["version"], "live_version": lh.get("version"),
                               "library_updated": t["last_updated"], "live_updated": lh.get("last-updated"),
                               "live_uses_result": bool(re.search(r"let\s+\$result\s*=", s["trigger"])),
                               "live_uses_any_exclusion": "does not contain any $exclude" in s["trigger"]})
    live_only = [{"segment": s["id"], "name": s["name"], "ad_type": s["ad_type"], "action": s["action"], "enabled": s["enabled"]}
                 for s in live if s["id"] not in matched_live]
    out = {"profile": args.profile, "templates": report, "live_only": live_only}
    if args.json:
        print(json.dumps(out, indent=1)); return 0
    for r in report:
        extra = ""
        if r["verdict"] == "differs":
            extra = f"  lib v{r['library_version']} ({r['library_updated']}) vs live v{r['live_version']} ({r['live_updated']})"
        print(f"{r['verdict']:13} {r['template']:45} {r.get('segment_name', '')}{extra}")
    print("\nlive-only segments (template candidates):")
    for s in live_only:
        print(f"  {s['segment']:8} {s['name']:50} {s['ad_type']:22} {s['action']:17} {'enabled' if s['enabled'] else 'disabled'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
