# Runtime: Direct Shell

This runtime applies when the Copilot is running in an environment with a local shell and direct network access to `app.merchjar.com`. Examples:

- **Codex CLI** (after enabling Settings → Network access)
- **Claude Code CLI** (the developer terminal tool)
- **Cursor**, **Aider**, or any other agent with shell tools

If `mcp__Claude_in_Chrome__*` tools are NOT exposed and you have a shell tool that can reach external URLs, you are in this runtime.

---

## Network Access Prerequisite (Codex)

Codex runs in a sandboxed environment with network access **off by default**. The Copilot needs to reach `app.merchjar.com` to make API calls. If the user is on Codex and the first API call fails with a connection error, point them to:

> Open **Settings → Network access** in Codex and turn it on. The first API call needs internet access to reach `app.merchjar.com`.

Other shell environments (Claude Code CLI, Cursor, etc.) generally have network access enabled by default. If a request fails with a network error, surface it to the user before assuming a configuration problem.

---

## Making API Calls

Use the local Python client at `tools/merchjar_client.py` for all Merch Jar API calls. It reads the API key from `user/MJ_COPILOT_CONFIG.md` automatically.

### Common patterns

```bash
# Fetch ad account profiles
python tools/merchjar_client.py profiles

# GET a profile-scoped endpoint
python tools/merchjar_client.py request GET /api/v5/segments --profileid 123456

# POST with an inline JSON body
python tools/merchjar_client.py request POST /api/v5/segments/preview --body '{"profile_id":"123456","ad_type":"search_terms","trigger":"clicks(lifetime) >= 20","action":"create_negatives","action_params":{}}'

# POST with a JSON payload file (preferred for complex payloads)
python tools/merchjar_client.py request POST /api/v5/segments/preview --body-file payload.json
python tools/merchjar_client.py request POST /api/v5/segments --body-file payload.json

# PATCH a segment (include --profileid; PATCH is profile-scoped)
python tools/merchjar_client.py request PATCH /api/v5/segments/123456 --profileid 123456 --body-file patch.json

# DELETE a segment
python tools/merchjar_client.py request DELETE /api/v5/segments/123456 --profileid 123456
```

### Rules

- Prefer the bundled client over ad-hoc HTTP (`curl`, raw `requests`, etc.). The client handles auth, JSON parsing, and error reporting consistently.
- Use `--body-file` for any payload longer than ~100 characters — easier to inspect, version, and reuse.
- **PowerShell (Windows): NEVER use inline `--body` for a DSL/segment payload — always write a file and use `--body-file`.** PowerShell splits a quoted JSON string into multiple arguments at spaces and special characters, so an inline `--body '{...}'` arrives at the client mangled and validate/preview fails before it ever hits the API (observed in live testing). DSL triggers are full of spaces and quotes, so this hits every real payload. Write the JSON to `tmp/payload.json` (see the PowerShell example below) and pass `--body-file tmp/payload.json`. Inline `--body` is only ever safe for trivial, space-free payloads.
- Use `--profileid` for profile-scoped GET endpoints when required by the API.
- `per_page` for preview queries belongs in the JSON body, **not** the URL query string. Max 100, default 25.
- `set_state` action_params: use `{"value": 1}` for enabled, `{"value": 2}` for paused — not `{"state": "enabled"}`.
- Report raw API errors exactly before recovering.

### Working with payload files

Write JSON payload files to a `tmp/` directory in the pack root (gitignored). Read responses back via the client's stdout. The client uses `utf-8-sig` for body files so UTF-8-with-BOM (common on Windows PowerShell) works without manual cleanup.

**Bash / zsh (macOS, Linux):**

```bash
cat > tmp/preview.json <<'EOF'
{
  "profile_id": "123456",
  "ad_type": "search_terms",
  "trigger": "let $spend90 = spend(90d); clicks(lifetime) >= 20 AND orders(lifetime) = 0 AND negated = false",
  "action": "create_negatives",
  "action_params": {}
}
EOF

python tools/merchjar_client.py request POST /api/v5/segments/preview --body-file tmp/preview.json
```

**PowerShell (Windows):**

```powershell
@'
{
  "profile_id": "123456",
  "ad_type": "search_terms",
  "trigger": "let $spend90 = spend(90d); clicks(lifetime) >= 20 AND orders(lifetime) = 0 AND negated = false",
  "action": "create_negatives",
  "action_params": {}
}
'@ | Out-File -FilePath tmp/preview.json -Encoding utf8

python tools/merchjar_client.py request POST /api/v5/segments/preview --body-file tmp/preview.json
```

The response prints to stdout as formatted JSON. Pipe through `jq` (if available) on Unix or use `ConvertFrom-Json` in PowerShell to parse.

**Error format:** the client prints API errors to stderr in a compact `Error: <message>` format and exits with code 2. Successful responses always go to stdout. This lets you split parseable output from error narration when running the client from scripts.

---

## Runtime-Specific Errors

### Network unreachable / connection refused

For Codex: most likely the network access toggle is off. Surface the fix message above. In Codex desktop, you may also need to approve the command for outside-sandbox network access at runtime (separate from the Settings toggle). If the first call hits `WinError 10061` or equivalent connection refused, this is usually the cause.

For other shells: surface the actual error to the user. Don't retry blindly — there may be a firewall, DNS issue, or a real outage.

### `python` command not found

If `python` is missing from `PATH`, try `python3 tools/merchjar_client.py ...`. If neither exists, surface the issue and let the user resolve before continuing.

### Permission denied on tmp/

If the pack root isn't writable for `tmp/`, fall back to inline `--body` for short payloads or write to the user's temp directory (`/tmp/` on Linux/macOS, `%TEMP%` on Windows).

---

## Files and Paths

In shell runtimes, the pack lives at the path the user opened. All bundled files (skills, reference, config, log) are accessible directly via filesystem reads. Templates are not bundled — they're fetched from the GitHub library on demand (`tools/library.py`; see `docs/library.md`).

The bundled client expects `user/MJ_COPILOT_CONFIG.md` to live in the pack root's `user/` folder. The client resolves this relative to its own location, so `python tools/merchjar_client.py ...` works from the pack root regardless of cwd.

---

## Universal Errors

For non-runtime-specifi