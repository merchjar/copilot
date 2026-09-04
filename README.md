# Merch Jar Copilot

The source of truth for the Merch Jar AI Copilot: the master Segment-template
library, the operating skills, and the downloadable Copilot Pack.

Merch Jar (merchjar.com) is automation for Amazon Sponsored Products PPC. The
Copilot Pack lets any AI coding agent (Claude, ChatGPT via Codex, Cursor, and
more) connect to your live Merch Jar account, run preview queries, and build
automation that shows its work.

## How this repo is organized

This repo is both the master library and the thin client that reads it.

- `templates/` is the master Segment-template library, organized into three
  category folders (`optimize/`, `insight/`, `utility/`) with finer classification
  as header tags (`default`, `bid`, `waste`, and more). It grows over time and is
  the canonical home for every template. The Copilot fetches from here on demand,
  pinned to a released tag.
- `skills/` holds the canonical skill sources, one folder per skill in the
  [Agent Skills](https://agentskills.io) format (`SKILL.md` + optional `scripts/`,
  `references/`, `assets/`). `merchjar-connect` is the base skill every other one
  depends on: it carries the API client, key handling, the safety protocol, and the
  API / DSL / guidelines references. `tools/build_skills.py` mirrors `skills/` into
  every folder agents auto-discover (`.claude/`, `.agents/`, `.github/`, `.gemini/`)
  and into the pack.
- `properties/` holds property sets: the custom-property schemas (Merch Jar custom
  fields, `cf_*`) that skills write and templates read.
- `collections/` holds curated bundles (templates + skills + property sets with a
  story) that the website renders as pages.
- `copilot-pack/` is the download: a thin client (the brain, the operating
  skills, and a fetch client). It ships no templates. The core automations are
  deployed to your account by the app, and everything else is pulled from the
  library on demand.
- `manifest.json` (schema v2) is the generated catalog of the whole Library:
  `templates`, `skills`, `properties`, `collections`, each with ids, paths, tags,
  goal, risk, versions, and raw URLs. The Copilot and the website read it; never
  hand-edit it.
- `tools/` is the repo build tooling: `library_lint.py` (static standards checks),
  `library_test.py` (live validate + preview of every template, read-only),
  `library_drift.py` (lab account vs library), `build_manifest.py`,
  `build_skills.py`, and `release.py` (the one-command gate). No secrets, ever.

## Installing the skills directly (any agent)

If your agent supports the Agent Skills standard (Claude Code, Codex, Cursor,
Gemini CLI, GitHub Copilot, and others), you can skip the zip:

    npx skills add merchjar/copilot              # pick skills interactively
    npx skills add merchjar/copilot --all        # everything, incl. merchjar-connect

Claude Code users can also add the plugin marketplace:

    /plugin marketplace add merchjar/copilot
    /plugin install merchjar-copilot@merchjar

Always install `merchjar-connect`; the other skills call its client and references.
Set `MERCHJAR_API_KEY` in your environment (or let the skill save the key to a
config file) and say "connect my Merch Jar account".

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
