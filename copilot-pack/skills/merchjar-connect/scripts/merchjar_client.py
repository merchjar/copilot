#!/usr/bin/env python3
"""
Minimal Merch Jar API client (stdlib only). Shipped as the `merchjar-connect` skill's
script and, byte-identical, as the Copilot Pack's tools/merchjar_client.py.

Usage examples:
    python merchjar_client.py profiles
    python merchjar_client.py request GET /api/v5/segments --profileid 123456
    python merchjar_client.py request POST /api/v5/segments/preview --body-file payload.json

Key lookup order (first hit wins; the key value is never printed):
    1. MERCHJAR_API_KEY environment variable
    2. MJ_COPILOT_CONFIG environment variable = path to a MJ_COPILOT_CONFIG.md
    3. user/MJ_COPILOT_CONFIG.md found by walking up from this script's folder
       (the Copilot Pack layout: <pack>/tools/merchjar_client.py -> <pack>/user/...)
    4. ~/.merchjar/MJ_COPILOT_CONFIG.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("MERCHJAR_BASE_URL", "https://app.merchjar.com")
HERE = Path(__file__).resolve().parent
CONFIG_NAME = "MJ_COPILOT_CONFIG.md"


def find_config() -> Path | None:
    env = os.environ.get("MJ_COPILOT_CONFIG")
    if env:
        p = Path(env).expanduser()
        return p if p.exists() else None
    for base in [HERE, *HERE.parents]:
        cand = base / "user" / CONFIG_NAME
        if cand.exists():
            return cand
    home = Path.home() / ".merchjar" / CONFIG_NAME
    return home if home.exists() else None


def key_from_config(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    section = re.search(r"^## API Key\s*(.*?)(?:\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not section:
        return None
    # Strip HTML comments so instructional examples are never mistaken for the real key.
    block = re.sub(r"<!--.*?-->", "", section.group(1), flags=re.DOTALL)
    # Tolerant of backticks, quotes, list markers, labels, indentation: extract the token only.
    m = re.search(r"mj_live_[A-Za-z0-9_]+", block)
    return m.group(0) if m else None


def load_api_key() -> str:
    env = os.environ.get("MERCHJAR_API_KEY", "").strip()
    if env:
        return env
    cfg = find_config()
    if cfg:
        key = key_from_config(cfg)
        if key:
            return key
        raise RuntimeError(
            f"No Merch Jar API key found under the '## API Key' heading in {cfg}. "
            "Add your key as a bare line directly under that heading "
            "(just the key itself, e.g. mj_live_abc123 -- no backticks, quotes, or label)."
        )
    raise RuntimeError(
        "No Merch Jar API key found. Set MERCHJAR_API_KEY, or create user/MJ_COPILOT_CONFIG.md "
        "(pack layout) or ~/.merchjar/MJ_COPILOT_CONFIG.md with the key under a '## API Key' heading. "
        "Create a key at https://app.merchjar.com/api-keys"
    )


def load_body(body: str | None, body_file: str | None) -> Any:
    if body and body_file:
        raise RuntimeError("Use either --body or --body-file, not both.")
    if body_file:
        # utf-8-sig strips a BOM (PowerShell often writes JSON with one; json.loads rejects it).
        return json.loads(Path(body_file).read_text(encoding="utf-8-sig"))
    if body:
        return json.loads(body)
    return None


def request_json(method: str, path: str, api_key: str, profileid: str | None = None, body: Any = None, idempotency_key: str | None = None) -> Any:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if idempotency_key is not None:
        if not idempotency_key.strip() or any(c in idempotency_key for c in '\r\n'):
            raise RuntimeError("Idempotency key must be non-empty and contain no line breaks.")
        headers["Idempotency-Key"] = idempotency_key
    data = None
    if profileid:
        headers["profileid"] = profileid
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = Request(url, headers=headers, data=data, method=method.upper())
    try:
        with urlopen(req, timeout=180) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Merch Jar API client")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("profiles", help="Fetch ad account profiles")
    p.add_argument("--raw", action="store_true", help="Return the raw response")
    r = sub.add_parser("request", help="Make a direct API request")
    r.add_argument("method", help="HTTP method")
    r.add_argument("path", help="API path, e.g. /api/v5/segments")
    r.add_argument("--profileid", help="Optional profileid header")
    r.add_argument("--idempotency-key", help="Stable key for one immutable update/archive request; reuse only for the identical request")
    r.add_argument("--body", help="Inline JSON body (avoid for DSL payloads; use --body-file)")
    r.add_argument("--body-file", help="Path to a JSON file body")
    sub.add_parser("whereis", help="Show which config file (if any) the client would read")
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1
    try:
        if args.command == "whereis":
            cfg = find_config()
            src = "MERCHJAR_API_KEY env" if os.environ.get("MERCHJAR_API_KEY") else (str(cfg) if cfg else "none found")
            print(json.dumps({"key_source": src}))
            return 0
        api_key = load_api_key()
        if args.command == "profiles":
            result = request_json("GET", "/api/v5/profiles", api_key)
            profiles = result.get("profiles", result.get("data", result))
            print(json.dumps(result if args.raw else profiles, indent=2))
            return 0
        if args.command == "request":
            body = load_body(args.body, args.body_file)
            result = request_json(args.method, args.path, api_key, profileid=args.profileid, body=body, idempotency_key=args.idempotency_key)
            print(json.dumps(result, indent=2))
            return 0
    except RuntimeError as exc:
        # Compact error on stderr; agents read stdout.
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
