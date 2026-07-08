#!/usr/bin/env python3
"""
Minimal Merch Jar API client for the OpenAI/Codex Copilot Pack.

Usage examples:
    python tools/merchjar_client.py profiles
    python tools/merchjar_client.py request GET /api/v5/segments --profileid 123456
    python tools/merchjar_client.py request POST /api/v5/segments/preview --body-file payload.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://app.merchjar.com"
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "user" / "MJ_COPILOT_CONFIG.md"


def load_api_key() -> str:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Config file not found: {CONFIG_PATH}")

    text = CONFIG_PATH.read_text(encoding="utf-8")
    section = re.search(r"^## API Key\s*(.*?)(?:\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not section:
        raise RuntimeError("Could not find the '## API Key' section in MJ_COPILOT_CONFIG.md")

    block = section.group(1)

    # Strip HTML comments first so instructional examples (e.g. "mj_live_xxxx" inside a
    # <!-- comment -->) are never mistaken for the real key. Handles multi-line comments.
    block = re.sub(r"<!--.*?-->", "", block, flags=re.DOTALL)

    # Find the key anywhere in the section, tolerant of the wrapping characters an agent
    # might add when writing markdown: backticks, quotes, a "- " list marker, a "Key:" label,
    # or indentation. We extract just the mj_live_ token, so all of those still parse.
    key_match = re.search(r"mj_live_[A-Za-z0-9_]+", block)
    if key_match:
        return key_match.group(0)

    raise RuntimeError(
        "No Merch Jar API key found under the '## API Key' heading in MJ_COPILOT_CONFIG.md. "
        "Add your key as a bare line directly under that heading "
        "(just the key itself, e.g. mj_live_abc123 -- no backticks, quotes, or label)."
    )


def load_body(body: str | None, body_file: str | None) -> Any:
    if body and body_file:
        raise RuntimeError("Use either --body or --body-file, not both.")
    if body_file:
        # utf-8-sig strips a BOM if present. PowerShell on Windows often writes JSON
        # files as UTF-8 with BOM, which json.loads rejects with "Unexpected UTF-8 BOM".
        return json.loads(Path(body_file).read_text(encoding="utf-8-sig"))
    if body:
        return json.loads(body)
    return None


def request_json(method: str, path: str, api_key: str, profileid: str | None = None, body: Any = None) -> Any:
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    data = None

    if profileid:
        headers["profileid"] = profileid
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = Request(url, headers=headers, data=data, method=method.upper())
    try:
        with urlopen(req) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Merch Jar API client")
    subparsers = parser.add_subparsers(dest="command")

    profiles_parser = subparsers.add_parser("profiles", help="Fetch ad account profiles")
    profiles_parser.add_argument("--raw", action="store_true", help="Return the raw response")

    request_parser = subparsers.add_parser("request", help="Make a direct API request")
    request_parser.add_argument("method", help="HTTP method")
    request_parser.add_argument("path", help="API path, e.g. /api/v5/segments")
    request_parser.add_argument("--profileid", help="Optional profileid header")
    request_parser.add_argument("--body", help="Inline JSON body")
    request_parser.add_argument("--body-file", help="Path to a JSON file body")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        api_key = load_api_key()

        if args.command == "profiles":
            result = request_json("GET", "/api/v5/profiles", api_key)
            profiles = result.get("profiles", result.get("data", result))
            if args.raw:
                print(json.dumps(result, indent=2))
            else:
                print(json.dumps(profiles, indent=2))
            return 0

        if args.command == "request":
            body = load_body(args.body, args.body_file)
            result = request_json(args.method, args.path, api_key, profileid=args.profileid, body=body)
            print(json.dumps(result, indent=2))
            return 0
    except RuntimeError as exc:
        # Print a compact error to stderr instead of a Python traceback.
        # Agents read stdout; stderr keeps the error visible without polluting parseable output.
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
