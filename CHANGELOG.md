# Changelog

Pack versions ship as GitHub Releases. Release notes are the canonical, detailed
record of what changed in each version. This file is a thin pointer.

See the full history at: https://github.com/merchjar/copilot/releases

## Unreleased

Repository restructured to the master-library plus thin-client model: templates
live in the top-level `templates/` library organized by category, the Copilot
Pack ships as a thin client with no bundled templates, and `manifest.json`
catalogs the full library. The first public release, Copilot Pack v1.0.0, is cut
from this layout.
