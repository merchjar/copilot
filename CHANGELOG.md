# Changelog

Pack versions ship as GitHub Releases. Release notes are the canonical, detailed
record of what changed in each version. This file is a thin pointer.

See the full history at: https://github.com/merchjar/copilot/releases

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
