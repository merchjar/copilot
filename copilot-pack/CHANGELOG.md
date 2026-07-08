# Merch Jar AI Copilot — Changelog

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
