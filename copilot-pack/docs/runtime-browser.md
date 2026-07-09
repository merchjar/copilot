# Runtime: Browser-Mediated (Cowork)

This runtime applies when the Copilot is running inside Cowork mode. The shell is sandboxed and **cannot reach `app.merchjar.com`** directly. All API calls are routed through the user's browser via the Claude in Chrome extension.

If `mcp__Claude_in_Chrome__*` tools are exposed in this session, you are in this runtime.

---

## Making API Calls

The sandbox shell cannot reach `app.merchjar.com`. Always use the Claude in Chrome extension for API calls.

1. Get a tab with `tabs_context_mcp` (create one if needed)
2. Navigate the tab to `https://app.merchjar.com`
3. Execute fetch calls via `javascript_tool`:

```javascript
(async () => {
  const response = await fetch("https://app.merchjar.com/api/v5/ENDPOINT", {
    method: "GET",  // or POST, PATCH, DELETE
    headers: {
      "Authorization": "Bearer YOUR_API_KEY",
      "Content-Type": "application/json"  // include for POST/PATCH
      // "profileid": "PROFILE_ID"  // include for profile-scoped endpoints
    }
    // body: JSON.stringify({...})  // include for POST/PATCH
  });
  return JSON.stringify(await response.json());
})();
```

**Rules:**
- Always wrap in `(async () => { ... })();` — top-level await is not supported.
- If the tab is already on `app.merchjar.com`, skip the navigate step.
- Never use `curl`, `wget`, or shell-based HTTP — they will always fail in this runtime.
- Read the API key from `user/MJ_COPILOT_CONFIG.md` (`## API Key` section).

---

## Reaching the Template Library

The pack ships no template files. The template library lives in the public `merchjar/copilot` GitHub repo and is fetched on demand. This runtime has **no shell**, so `tools/library.py` is not available — fetch plain URLs via the Chrome extension (`javascript_tool`), exactly as you do for API calls. Both endpoints are public, CDN-served, and need no auth. Do **not** use the GitHub REST API (it rate-limits unauthenticated callers at 60 requests/hour).

**1. Catalog / discovery — fetch the release manifest:**

```javascript
(async () => {
  const r = await fetch("https://github.com/merchjar/copilot/releases/latest/download/manifest.json");
  return JSON.stringify(await r.json());
})();
```

This URL redirects to the latest release asset. If the extension's fetch does not follow the redirect (or CORS blocks it), fall back to the raw manifest on the pinned ref: `https://raw.githubusercontent.com/merchjar/copilot/<tag>/manifest.json` (pre-release, use `main`). Read the `templates` array to list or filter; read `pack_version` and each template's `last_updated` for the update check.

**2. Template bytes — fetch one template's DSL:**

Read the chosen template's `path` and the manifest's top-level `tag`, then:

```javascript
(async () => {
  const r = await fetch("https://raw.githubusercontent.com/merchjar/copilot/<tag>/<path>");
  return await r.text();
})();
```

Pinning to the manifest's `tag` guarantees the catalog and the files agree.

**3. Update check (manifest diff — no `check-updates` command here):**

1. Fetch the release manifest (step 1).
2. Read the cached copy at `user/.library-cache.json`. **Absent on a fresh install** — treat that as first run: write the cache, report nothing.
3. Compare each template's `last_updated` and the top-level `pack_version`. Collect new / updated / removed ids.
4. Report the differences to the user **inline, at the moment you run the check** — the next step overwrites the cache, so the diff is one-shot.
5. Overwrite `user/.library-cache.json` with the freshly fetched manifest.

Deploy safety is unchanged: fetching a template never touches the account. Preview, deploy-disabled, and explicit-enable still apply on every build.

---

## API Key Paste Handling

Cowork has built-in safety behavior around pasted credentials: when the user pastes a raw token (anything matching `mj_live_...` or other credential-like patterns), Cowork flags it as a potentially accidental paste and prompts the user before letting the Copilot act on it. This conflicts with the initialization protocol in `docs/copilot.md`, which assumes a key paste is intentional setup.

**Pattern to use in this runtime:** when a user message contains a raw `mj_live_` key, do not silently save it. Instead, confirm intent explicitly:

> "I see what looks like a Merch Jar API key. Should I save this to your config and connect your account?"

Wait for an explicit "yes" / "save it" / "connect" before writing to `user/MJ_COPILOT_CONFIG.md`. This matches Cowork's security posture and makes the setup flow explicit rather than implicit.

If the user types `init` expecting the Copilot's initialization to run, redirect: `init` is a Claude Code built-in skill that modifies CLAUDE.md — not what the user wants. Tell them to paste their API key or say "setup" / "connect my account" instead.

---

## Runtime-Specific Errors

### Chrome extension not available

If `tabs_context_mcp` fails or `javascript_tool` is unavailable, tell the user:

> "I need the Claude for Chrome extension to make API calls. If it's not installed, the setup guide is at https://