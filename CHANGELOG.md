# Changelog

Pack versions ship as GitHub Releases. Release notes are the canonical, detailed
record of what changed in each version. This file is a thin pointer.

See the full history at: https://github.com/merchjar/copilot/releases

## v1.2.0 (2026-09-04)

Library foundation release.

- **Skills on the Agent Skills standard.** Every skill carries spec frontmatter
  (`license`, `compatibility`, `metadata` with version / tags / goal / risk /
  required scopes). New base skill **`merchjar-connect`** owns the API client
  (`scripts/merchjar_client.py`, now also reads `MERCHJAR_API_KEY`), key handling,
  the safety protocol, and the API / DSL / guidelines references. Skills install
  standalone with `npx skills add merchjar/copilot`; a Claude Code plugin
  marketplace (`.claude-plugin/`) is included. Mirrors added for GitHub Copilot /
  VS Code (`.github/skills/`) and Gemini CLI (`.gemini/skills/`).
- **Template header v2**: `Risk`, `Schedule`, `Goal`, `Requires-Properties`,
  `Pairs-With`, `Changelog` on every template. **Manifest schema v2** catalogs
  templates, skills, property sets, and collections. New `collections/` (The Core
  Six) and `properties/` shelves.
- **Standards fixes**: Anomaly Detection: Spend v1.1 (exclusion filter `does not
  contain all`; `$planned_action`), Core: Pause Underperforming Keywords & Targets
  v1.1 (`$planned_action`). Logic unchanged.
- **Tooling**: `tools/library_lint.py`, `tools/library_test.py` (live, read-only),
  `tools/library_drift.py`, `tools/release.py` (the one-command release gate).

## v1.1.0 (2026-09-04)

Library update: **Core: Search Term Waste Elimination v1.1** ships CTR-relevance
scaling (low CTR negates sooner, high CTR earns more runway) with new
`$ctr_reference` / `$ctr_low_floor` / `$ctr_high_ceiling` settings and CTR-aware
diagnostics. Validated and previewed on a live account before release. Stray
empty template folders removed from the dev tree; the three-folder taxonomy
(optimize / insight / utility) plus tags stands. No skill behavior changes.

## v1.0.1 (2026-09-01)

Documentation sync with the canonical public API reference at
https://merchjar.com/api/: corrected rate limits, documented the new schedule,
history, audit-item, and entity-creation endpoints, fixed a dead README link.
No template or skill behavior changes. Full notes on the Release.

## v1.0.0 (2026-08-26)

First public release. Repository structured on the master-library plus
thin-client model: templates live in the top-level `templates/` library
organized by category, the Copilot Pack ships as a thin client with no bundled
templates, and `manifest.json` catalogs the full library (7 templates at
release, including all six account-default cores). This release adds custom
fields support throughout the pack. Full notes on the Release.
