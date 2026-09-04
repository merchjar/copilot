#!/usr/bin/env python3
"""
library_test.py -- live validate + preview every template against real profiles.
Read-only: it never creates, patches, enables, or deletes anything.

    python tools/library_test.py --profiles 1137618295323225,2751686654039572
    python tools/library_test.py --profiles <id> --only core-search-term-waste-elimination
    python tools/library_test.py --profiles <id> --ads-profile <small-profile-id>

Key: MERCHJAR_API_KEY env var, or --config <path to a pack user/MJ_COPILOT_CONFIG.md>.
Never pass the key on the command line.

For each template: POST /segments/validate, then POST /segments/preview with the
action derived from the header (Risk + Recommended). Records status, row total,
totals, timing, and any blank-name rows. The preview endpoint has a tight burst
bucket, so calls are spaced (--pause seconds, default 20).

Known failures (engine/scale issues we do not want to fail the gate on) live in
tools/known-failures.json as {"<template-id>@<profile-id>": "reason"}.

Results: printed table + JSON written to tmp/library-test-<date>.json (gitignored).
Exit 1 on any unexpected failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_manifest import REPO_ROOT, build  # noqa: E402

BASE = "https://app.merchjar.com"
KNOWN = REPO_ROOT / "tools" / "known-failures.json"


def load_key(config: str | None) -> str:
    k = os.environ.get("MERCHJAR_API_KEY")
    if k:
        return k.strip()
    if config:
        text = Path(config).read_text(encoding="utf-8")
        sec = re.search(r"^## API Key\s*(.*?)(?:\n## |\Z)", text, flags=re.M | re.S)
        if sec:
            block = re.sub(r"<!--.*?-->", "", sec.group(1), flags=re.S)
            m = re.search(r"mj_live_[A-Za-z0-9_]+", block)
            if m:
                return m.group(0)
    raise SystemExit("no API key: set MERCHJAR_API_KEY or pass --config <MJ_COPILOT_CONFIG.md>")


def call(key: str, method: str, path: str, body=None, profile=None, retries=4):
    hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"}
    if profile:
        hdr["profileid"] = str(profile)
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        try:
            with urlopen(Request(BASE + path, data=data, method=method, headers=hdr), timeout=180) as r:
                txt = r.read().decode()
                return r.status, (json.loads(txt) if txt else None)
        except HTTPError as e:
            txt = e.read().decode(errors="replace")
            if e.code == 429 and attempt < retries - 1:
                time.sleep(20 * (attempt + 1)); continue
            try:
                return e.code, json.loads(txt)
            except Exception:  # noqa: BLE001
                return e.code, txt[:300]
    return 0, None


def action_for(t: dict) -> tuple[str, dict]:
    """Derive (action, action_params) from the header. Previews never mutate, so any
    valid action works; we pick the one the template is meant to run with."""
    rec = (t.get("recommended") or "").lower()
    risk = t.get("risk") or ""
    var = re.search(r"using\s+\$(\w+)", rec)
    if risk == "negatives":
        return "create_negatives", {}
    if risk == "state":
        return "set_state", {"value": 1 if "enable" in rec and "pause" not in rec else 2}
    if risk == "bids":
        if var:
            return "set_bid", {"direction": "set-to-$", "value": var.group(1), "source": "variable"}
        return "set_bid", {"direction": "decrease-%", "value": 1, "source": "value"}
    if risk == "budgets":
        if var:
            return "set_budget", {"direction": "set-to-$", "value": var.group(1), "source": "variable"}
        return "set_budget", {"direction": "decrease-%", "value": 1, "source": "value"}
    return "set_state", {"value": 2}  # read-only: preview only, harmless action


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profiles", required=True, help="comma-separated profile ids")
    ap.add_argument("--ads-profile", help="profile to use for the `ads` dataset (large accounts time out)")
    ap.add_argument("--config", help="path to a pack user/MJ_COPILOT_CONFIG.md holding the key")
    ap.add_argument("--only", help="comma-separated template ids")
    ap.add_argument("--pause", type=float, default=20.0, help="seconds between previews")
    ap.add_argument("--per-page", type=int, default=25)
    args = ap.parse_args()

    key = load_key(args.config)
    manifest, errs = build("0.0.0")
    if errs:
        print("manifest errors; run library_lint.py first", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    known = json.loads(KNOWN.read_text(encoding="utf-8")) if KNOWN.exists() else {}
    only = set(args.only.split(",")) if args.only else None
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]

    results, failures = [], 0
    for t in manifest["templates"]:
        if only and t["id"] not in only:
            continue
        ad_type = t.get("ad_type")
        if not ad_type:
            # "Any level" templates: test on campaigns
            ad_type = "campaigns"
        text = (REPO_ROOT / t["path"]).read_text(encoding="utf-8")
        action, params = action_for(t)
        targets = [args.ads_profile] if (ad_type == "ads" and args.ads_profile) else profiles
        for prof in targets:
            row = {"template": t["id"], "profile": prof, "ad_type": ad_type, "action": action}
            t0 = time.time()
            st, resp = call(key, "POST", "/api/v5/segments/validate",
                            {"trigger": text, "ad_type": ad_type, "profile_id": prof})
            row["validate"] = st
            row["validate_ok"] = st == 200 and isinstance(resp, dict) and resp.get("valid") is True
            if not row["validate_ok"]:
                row["validate_error"] = (resp.get("error") if isinstance(resp, dict) else resp)
            st, resp = call(key, "POST", "/api/v5/segments/preview",
                            {"profile_id": prof, "trigger": text, "ad_type": ad_type, "action": action,
                             "action_params": params, "per_page": args.per_page, "page": 1})
            row["preview"] = st
            row["seconds"] = round(time.time() - t0, 1)
            if st == 200 and isinstance(resp, dict):
                rows = resp.get("data") or []
                row["total"] = (resp.get("pagination") or {}).get("total")
                row["rows"] = len(rows)
                row["blank_rows"] = sum(1 for r in rows if not (r.get("campaign_name") or r.get("name")))
                nan = sum(1 for r in rows for v in r.values() if isinstance(v, float) and v != v)
                row["nan_values"] = nan
                row["spend_total"] = (resp.get("totals") or {}).get("cost_lifetime")
                row["preview_ok"] = row["blank_rows"] == 0 and nan == 0
            else:
                row["preview_ok"] = False
                row["preview_error"] = (resp.get("error") if isinstance(resp, dict) else resp)
            ok = row["validate_ok"] and row["preview_ok"]
            k = f"{t['id']}@{prof}"
            if not ok and k in known:
                row["known_failure"] = known[k]
            elif not ok:
                failures += 1
            row["ok"] = ok
            results.append(row)
            flag = "OK " if ok else ("KNOWN" if k in known else "FAIL")
            print(f"{flag:5} {t['id']:45} {prof:17} {ad_type:22} v={row['validate']} p={row['preview']} "
                  f"total={row.get('total')} {row['seconds']}s", flush=True)
            time.sleep(args.pause)

    out_dir = REPO_ROOT / "tmp"; out_dir.mkdir(exist_ok=True)
    out = out_dir / f"library-test-{date.today().isoformat()}.json"
    out.write_text(json.dumps({"run": datetime.now().isoformat(timespec="seconds"), "results": results}, indent=1), encoding="utf-8")
    print(f"\n{len(results)} checks, {failures} unexpected failures -> {out.relative_to(REPO_ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
