# Merch Jar AI Copilot Pack

**Pack Version:** 12

The Merch Jar AI Copilot is a stateful, agent-agnostic pack for Amazon Sponsored Products PPC automation. It runs in any AI coding agent that has file access and either browser or shell capabilities — Claude Code, Cowork, Codex CLI, Cursor, Aider, and more.

This pack lets the AI:

- Connect to live Merch Jar data via the Merch Jar API
- Run preview queries against real ad accounts
- Build, review, and deploy automation Segments with safety guardrails
- Save preferences, profile context, and deployment history locally over time

---

## Pick your runtime

The pack works in any AI coding agent with file access. There are two underlying API mechanisms (browser-mediated for sandboxed environments, direct shell for everything else), and the agent picks the right one automatically based on what tools it has available.

| Agent | Entry point read | API mechanism |
|---|---|---|
| **Cowork** (Claude Desktop) | `CLAUDE.md` | Chrome extension fetch (browser-mediated) |
| **Claude Code CLI** | `CLAUDE.md` | `tools/merchjar_client.py` (direct shell) |
| **Codex CLI** | `AGENTS.md` | `tools/merchjar_client.py` (direct shell) |
| **Cursor / Aider / other** | `CLAUDE.md` or `AGENTS.md` | `tools/merchjar_client.py` (direct shell) |

The agent decides behaviorally: in Cowork / Claude Desktop it uses the browser-mediated path (Claude in Chrome extension); in a shell environment it uses the Python client. It does NOT decide by sniffing its tool list — in Cowork, tools are often deferred and not immediately visible, so a missing-tool check would misfire. If unsure, it tries one path and falls back to the other. Behavior is identical across runtimes: same brain, same skills.

---

## Setup

### Step 1 — Get your API key

In the Merch Jar app: **Settings → API Keys → Create new key**. Copy the key (it's only shown once).

### Step 2 — Open the pack in your agent

**Cowork (Claude Desktop):**
1. Make sure the Claude in Chrome extension is installed.
2. Open the pack folder as a workspace folder in Cowork.
3. Start a chat — the agent picks up `CLAUDE.md` automatically.

**Codex CLI:**
1. Open **Settings → Network access** in Codex and turn it on. The pack needs network access to reach `app.merchjar.com`.
2. Open the pack folder in Codex.
3. Start a session — Codex picks up `AGENTS.md` automatically.

**Claude Code CLI / Cursor / Aider / other:**
1. Open the pack folder in the agent.
2. The agent reads `CLAUDE.md` (or `AGENTS.md` if it prefers that). Both point at the same brain.

### Step 3 — Paste your API key

The agent will prompt you for an API key on first run. Paste it in chat. The pack saves it to `user/MJ_COPILOT_CONFIG.md` and loads your ad profiles automatically.

> **If the agent doesn't seem to know about the pack** (it didn't read the entry file — some agents, including Codex desktop, don't auto-read `CLAUDE.md` / `AGENTS.md`), send this as your first message and it will pick everything up:
>
> ```
> Read CLAUDE.md (or AGENTS.md) in this folder and follow its setup instructions. Here's my Merch Jar API key: mj_live_...
> ```
>
> This works on any agent — including ones not listed above.

### Step 4 — Run a quick scan or full review

Once profiles are loaded, you can:

- `Run a quick scan on my search terms.`
- `Review my whole account and tell me what to automate first.`
- `Build the search term waste elimination segment.`
- `What segments do I already have running on this account?`
- `Why is my ACOS up over the last two weeks?`

---

## Pack contents

```
copilot-pack/
├── CLAUDE.md             # Claude entry point (auto-detects runtime)
├── AGENTS.md             # Codex entry point
├── README.md             # This file
├── CHANGELOG.md          # Version history
├── build.sh              # Sync script for skills/ → .claude/skills/ + .agents/skills/
├── docs/
│   ├── copilot.md        # The operating brain (runtime-agnostic)
│   ├── library.md        # How to reach the GitHub template library
│   ├── runtime-browser.md # Cowork-specific API mechanics
│   └── runtime-shell.md   # Shell-runtime API mechanics
├── skills/               # Canonical skill source (8 skills)
├── .claude/skills/       # Generated from skills/ — auto-discovered by Claude
├── .agents/skills/       # Generated from skills/ — auto-discovered by Codex
├── reference/            # API reference, DSL syntax, segment guidelines
├── tools/
│   ├── merchjar_client.py # Local API client used by shell runtimes
│   └── library.py         # Fetch client for the GitHub template library
└── user/                 # API key, profile state, deployment log (per-install)
```

The pack ships no templates. The core automations are deployed to your Merch
Jar account by the app, and the full template library lives in this repo under
`templates/`, fetched on demand.

---

## What this pack does for you

- **Connects to your live Merch Jar account** and runs preview queries before deploying anything
- **Surfaces dollar-impact findings first** — search term waste, bid inefficiency, budget waste, missed opportunities
- **Builds automation Segments** from the Merch Jar template library or custom logic, always previewed and always deployed disabled by default
- **Tracks what's running** in `user/MJ_COPILOT_LOG.md` so future sessions know your account history
- **Explains every decision** — Show Your Work mode surfaces the full DSL before deploy

---

## Editing the pack

If you customize skills, edit files in `skills/` (the canonical source) and then run the build to sync to `.claude/skills/` and `.agents/skills/`:

```bash
# Cross-platform (recommended):
python tools/build_skills.py

# Unix shim (macOS, Linux, WSL):
./build.sh
```

The Python script is the canonical build implementation — stdlib only, runs on Windows/macOS/Linux. The shell shim calls it. Don't edit the generated copies directly; they regenerate on the next build.

Note that auto-discovery from `.claude/skills/` and `.agents/skills/` only works in some runtimes (Claude Code CLI, Codex CLI). Cowork and Codex desktop don't auto-load any folder — they route to skills via the brain's intent table and read `skills/NAME/SKILL.md` directly. Either way, editing `skills/` is the right move.

---

## Help & docs

- **Quickstart guide:** https://www.merchjar.com/help/docs/api-ai-copilot-quickstart
- **Template registry:** https://www.merchjar.com/help/api-template-index
- **API key creation:** https://app.merchjar.com/api-keys
- **In-pack:** Type "help" in chat for an overview of available commands.

---

## Customer-facing language

The product works with both ChatGPT (via Codex) and Claude (Cowork, Claude Code CLI, Claude Desktop). Approved phrasing:

- `Works with ChatGPT and Claude`
- `ChatGPT support runs through Codex`
- `Connect Merch Jar to ChatGPT or Claude so AI can run previews and build automation that shows its work`
- `One pack, multiple agents — Cowork, Claude Code, Codex, Cursor, and more`
