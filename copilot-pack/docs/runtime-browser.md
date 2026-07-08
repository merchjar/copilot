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

> "I need the Claude for Chrome extension to make API calls. If it's not installed, the setup guide is at https://www.merchjar.com/help/docs/api-ai-copilot-quickstart"

### Chrome extension content filter blocks

Certain return-value patterns trigger the Chrome extension's content filter — notably `=` signs in strings, base64 (`btoa()`) output, and some Unicode characters (em-dashes especially).

**Symptoms:** the JS ran successfully but `javascript_tool` returned an empty string, a partial result, or a "blocked" message.

**Workarounds in order:**

1. **Pre-process on the page.** Parse the API response inside the `(async () => ...)` block and return a clean primitive (number, short string) or a JSON string with problematic characters stripped/replaced.
2. **Pipe-delimit multi-field returns** instead of returning raw JSON. Example: `return row.name + "|" + row.id + "|" + row.cost;` and split in the next JS call.
3. **Stash in `window` and fetch in pieces.** Store the large response in `window._mjResponse` on one call, then return one field at a time in subsequent calls.
4. **Last resort:** Render results into DOM and read with `get_page_text`.

Narrate the workaround briefly — "The response got filtered by the browser extension, so I'm going to re-run it pipe-delimited" — instead of silently retrying.

### Empty response after a 201 (segment create)

If `POST /api/v5/segments` returns 201 but the response body comes back empty (likely a content filter hit on the response payload), do not retry. Instead, immediately call `GET /api/v5/segments` and check whether the segment was actually created. Report what you find before deciding next steps.

---

## Files and Paths

In Cowork, the pack lives in a workspace folder the user has selected. File operations use the Read, Write, and Edit tools at absolute paths under that workspace folder. Do not assume any specific location — use the paths the user's environment exposes.

For shell operations (rare in this runtime), the workspace folder is mounted under `/sessions/.../mnt/<folder-name>/` from inside the bash sandbox. The bash sandbox cannot reach external network endpoints.

---

## Universal Errors

For non-runtime-specific errors (401, 429, malformed key, empty response on a non-create endpoint, preview errors), see the Error Handling section in `docs/copilot.md`.
