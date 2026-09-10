# Update the Copilot

Use this guide when the user asks to update an existing Merch Jar Copilot. This changes local Copilot files only. It does not connect to or change an ad account.

## Request to copy

> Update my Copilot from the Merch Jar Library. Keep my settings and custom skills, and tell me if anything needs my attention.

## Instructions for the Copilot

Locate the current Copilot folder containing `AGENTS.md` or `CLAUDE.md`. Do not read or print files under `user/`.

Resolve the filenames in this guide against the guide's HTTPS origin. This keeps an explicitly supplied preview on that preview origin.

Use `tools/update_copilot.py` when it exists. For an older Copilot without that file, download `copilot-update-bootstrap.py` from this guide's origin to a temporary file and verify its SHA256 is `742ec25e066340bcf631797901b59d7871569c04059933cac9012402b3838d91` before running it. The bootstrap is the same updater included in version 1.2.6.

Run a read-only check and then a dry run against `copilot-update-v1.2.6.json` from this guide's origin. For this copied update request, continue with `--apply` when there are no conflicts. The request already authorizes the local update, backup and verification. Do not ask again merely because a required official dependency must be updated too.

For the normal whole-Copilot update, omit `--skill`. This updates the default Copilot and any already-installed official optional skills. It does not add absent optional skills. For one requested skill, use `--skill ID`; compatible dependencies are included.

After applying, refresh `installed-skills.json`, run `check` again using the installed `tools/update_copilot.py`, and report the installed and available versions, preserved customizations, conflicts, backup location and update receipt. Never describe checksum verification as a digital signature.
