# Merch Jar Copilot

The source of truth for the Merch Jar AI Copilot: the master Segment-template
library, the operating skills, and the downloadable Copilot Pack.

Merch Jar (merchjar.com) is automation for Amazon Sponsored Products PPC. The
Copilot Pack lets any AI coding agent (Claude, ChatGPT via Codex, Cursor, and
more) connect to your live Merch Jar account, run preview queries, and build
automation that shows its work.

## How this repo is organized

This repo is both the master library and the thin client that reads it.

- `templates/` is the master Segment-template library, organized by category
  (`core/`, `defensive/`, `harvesting/`, `branded/`, and more). It grows over
  time and is the canonical home for every template. The Copilot fetches from
  here on demand, pinned to a released tag.
- `skills/` holds the canonical skill sources. A subset ships in the pack as the
  operating brain; others are library skills the Copilot can pull.
- `copilot-pack/` is the download: a thin client (the brain, the operating
  skills, and a fetch client). It ships no templates. The core automations are
  deployed to your account by the app, and everything else is pulled from the
  library on demand.
- `manifest.json` is the generated catalog of the template library (id, name,
  path, category, tags, description, last-updated). The Copilot fetches it to
  list, filter, and check for updates.
- `tools/` is the repo build tooling (manifest generator, sync scripts). No
  secrets, ever.

## Getting the pack

Pull released versions, not the `main` branch. The latest released catalog is
always available at a permanent URL:

    https://github.com/merchjar/copilot/releases/latest/download/manifest.json

Template bytes are fetched from the tag the manifest records:

    https://raw.githubusercontent.com/merchjar/copilot/<tag>/templates/<category>/<slug>.txt

Each release also attaches the full pack as a downloadable zip.

## License

Proprietary. Use requires an active Merch Jar account. See `LICENSE`. This is
not open source, and redistribution or derivative works outside the Merch Jar
service are not permitted.
