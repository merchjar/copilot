# Merch Jar AI Copilot — Changelog

---

## v1.0.0 (2026-08-26)

First public release. This is the Copilot Pack going properly public, so it starts fresh at 1.0.0. The versions below (v10 through v12) were internal development releases, kept here so the history isn't lost.

### Custom fields: automate against your business data
- New: put data Amazon doesn't have onto your account as custom fields (profit margins, product phase, inventory flags, labels) and let segments automate against it. Say "add my margins" and the Copilot sets up the fields, loads your values, and can then build automation like bids capped by each product's actual profitability.
- Every value the Copilot writes carries an audit tag, and the full change history is readable per entity, so you can always see what was set, when, and why.
- Requires an API key with the custom fields scopes enabled. If you created your key before this release, you may need a new one with all scopes.

### Your strategy library now lives in the cloud
- Templates are no longer bundled in the download. The pack is a thin client: it ships the operating brain, the skills, and a small fetch tool, then pulls templates from the Merch Jar library on demand.
- The Copilot lists, searches, and fetches templates straight from the library, and checks for updates so you always know when a template you're running has a newer version or when new ones have been added.
- Works the same whether your AI client has a shell (it uses the bundled fetch tool) or is browser-only (it fetches the same library over plain web requests).

### The core automations come with your account
- The six core Segments (bid management, budget management, impression recovery, product-ad waste, search-term waste, underperformer pausing) are added to every account by default, so the Copilot reads what's already live first instead of rebuilding from scratch.
- When a core is installed but turned off, the Copilot recognizes it, previews what it would catch, and offers to enable it, rather than creating a duplicate.

### Safety unchanged
- Every deploy still previews first, deploys disabled by default, and asks before enabling. Nothing goes live without you saying so.

---

## v12 (2026-06-15)

Reliability, setup, and accuracy improvements. No breaking changes. If you're upgrading, replace the pack contents but keep your `user/` folder (it holds your API key and account settings).

### Setup is more robust
- Works out of the box on both Claude and ChatGPT (via Codex), including when you paste your API key as your very first message. The assistant confirms and connects cleanly instead of getting stuck.
- More forgiving about how your key is saved. It reads the key whether or not it ends up wrapped in backticks, quotes, or a label, and gives a clear, actionable message if no key is found.
- Added a one-line "bootstrap" prompt in the README for AI apps that don't automatically read the pack's instructions on their own.

### Clearer, more accurate guidance
- Bid management now deploys as a single segment that covers both your manual keywords and your auto-targets. No more confusing two-segment setup.
- Documented a match-type scoping gotcha that could silently include more targets than intended, with the correct pattern to use instead.
- Clarified how preview totals and ACOS values are reported, so the numbers are read correctly.
- When you tell the assistant to "remember" something about an account, it now saves it directly instead of asking you to confirm twice.

### Quality of life
- On the first segment you build in a session, the assistant shows you the actual logic once (even when "show work" is off), so you can see exactly what was deployed.
- Better help when a segment is enabled but stuck syncing. The assistant recognizes this as an account-sync issue and offers to draft a support message instead of re-debugging working logic.
- Template and formatting cleanups for smoother, more reliable runs across both Claude and ChatGPT.

---

## v11 (2026-05-08)

- One download now works in both Claude and ChatGPT (via Codex), sharing a single set of skills, references, and templates.

---

## v10 (2026-05-08)

- Improved segment-writing guidance and DSL reference accuracy (boolean variables, metric functions, and math edge cases) so generated segments run more reliably.

---

_Earlier versions were internal development releases._
