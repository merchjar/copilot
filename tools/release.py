#!/usr/bin/env python3
"""
release.py -- the local release gate for the merchjar/copilot repo. One command:

    python tools/release.py --pack-version 1.2.0                 # lint -> skills sync -> manifest -> zip
    python tools/release.py --pack-version 1.2.0 --test --profiles <ids> [--ads-profile <id>]
    python tools/release.py --pack-version 1.2.0 --drift --profiles <lab-profile-id>

Steps (each stops the run on failure):
  1. library_lint.py  (--online: body changed without a Version bump is an error)
  2. build_skills.py  (root skills/ -> pack + every discovery mirror)
  3. optional library_test.py  (live validate + preview; needs MERCHJAR_API_KEY)
  4. optional library_drift.py (lab account vs library; informational)
  5. build_manifest.py --pack-version X  (writes manifest.json, schema v2)
  6. version stamps: copilot-pack/{CLAUDE,AGENTS,README}.md, docs/copilot.md, .claude-plugin/plugin.json
  7. zip copilot-pack/ -> merch-jar-copilot-pack-vX.zip (release asset)

It does NOT push or create the GitHub release: that needs a token and lives outside
this public repo (Merch Jar internal: tools/github/copilot_release.py). After this
script passes, push the tree and attach manifest.json + the zip to release vX.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(cmd: list[str], label: str) -> None:
    print(f"\n== {label}: {' '.join(cmd[1:])}")
    r = subprocess.run(cmd, cwd=REPO_ROOT)
    if r.returncode != 0:
        print(f"release gate FAILED at: {label}", file=sys.stderr)
        sys.exit(r.returncode)


def stamp_versions(version: str) -> list[str]:
    changed = []
    for rel in ("copilot-pack/CLAUDE.md", "copilot-pack/AGENTS.md", "copilot-pack/README.md", "copilot-pack/docs/copilot.md"):
        p = REPO_ROOT / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        n = re.sub(r"\*\*Pack Version:\*\* \d+\.\d+\.\d+", f"**Pack Version:** {version}", t)
        if n != t:
            p.write_text(n, encoding="utf-8"); changed.append(rel)
    pj = REPO_ROOT / ".claude-plugin" / "plugin.json"
    if pj.exists():
        d = json.loads(pj.read_text(encoding="utf-8"))
        if d.get("version") != version:
            d["version"] = version
            pj.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8"); changed.append(".claude-plugin/plugin.json")
    return changed


def build_zip(version: str) -> Path:
    name = REPO_ROOT / f"merch-jar-copilot-pack-v{version}.zip"
    with zipfile.ZipFile(name, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted((REPO_ROOT / "copilot-pack").rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc" and f.name != ".library-cache.json" and f.name not in ("campaign-structures.json", "campaign-structures.json.lock") and not f.name.startswith(".structures-"):
                z.write(f, "merch-jar-copilot-pack/" + f.relative_to(REPO_ROOT / "copilot-pack").as_posix())
    return name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack-version", required=True)
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--drift", action="store_true")
    ap.add_argument("--profiles")
    ap.add_argument("--ads-profile")
    ap.add_argument("--config")
    ap.add_argument("--offline", action="store_true", help="skip the online version-bump check in lint")
    args = ap.parse_args()

    lint = [PY, "tools/library_lint.py", "--pack-version", args.pack_version]
    if not args.offline:
        lint.append("--online")
    run(lint, "lint")
    run([PY, "tools/build_skills.py"], "skills sync")
    run([PY, "tools/test_library_install.py"], "bundled Library installer checks")
    if args.test:
        if not args.profiles:
            print("--test needs --profiles", file=sys.stderr); return 2
        cmd = [PY, "tools/library_test.py", "--profiles", args.profiles]
        if args.ads_profile: cmd += ["--ads-profile", args.ads_profile]
        if args.config: cmd += ["--config", args.config]
        run(cmd, "live test")
    if args.drift:
        if not args.profiles:
            print("--drift needs --profiles (first id is the lab profile)", file=sys.stderr); return 2
        cmd = [PY, "tools/library_drift.py", "--profile", args.profiles.split(",")[0]]
        if args.config: cmd += ["--config", args.config]
        run(cmd, "drift")
    run([PY, "tools/build_manifest.py", "--pack-version", args.pack_version], "manifest")
    changed = stamp_versions(args.pack_version)
    print(f"\n== version stamps: {changed or 'already current'}")
    z = build_zip(args.pack_version)
    print(f"== zip: {z.name} ({z.stat().st_size // 1024} KB)")
    print(f"\nrelease gate PASSED for v{args.pack_version}. Next: push the tree, then create release v{args.pack_version} with manifest.json + {z.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
