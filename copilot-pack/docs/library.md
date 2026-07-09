# Template library

The Merch Jar template library is the master set of automation Segments. It lives
in the public `merchjar/copilot` GitHub repo and is fetched on demand. The Copilot
Pack ships no template files: the core automations are already deployed on the
account by the app, and everything else is pulled from the library when needed.

There are two ways to reach it. Use the fetch client in shell runtimes; use plain
URLs in web-fetch-only runtimes (for example Cowork via the Chrome extension).

## Shell runtimes: `tools/library.py`

Stdlib only, no dependencies. Run from the pack root.

| Command | What it does |
|---|---|
| `python tools/library.py list` | List the whole library (id, category, dataset, tags, description). |
| `python tools/library.py list --category core` | Filter by category. |
| `python tools/library.py list --tag waste` | Filter by metadata tag. |
| `python tools/library.py search "search term waste"` | Keyword search across id, name, tags, dataset, description. |
| `python tools/library.py info <id>` | Show one template's metadata and its raw URL. |
| `python tools/library.py fetch <id>` | Print the template DSL to stdout. |
| `python tools/library.py fetch <id> --out .` | Save the DSL to a file (directory or explicit path). |
| `python tools/library.py check-updates` | Report new, updated, or removed templates since the last check. |

## Web-fetch-only runtimes: plain URLs

Both endpoints are public, CDN-served, and need no auth. Do not use the GitHub REST
API for this (it rate-limits unauthenticated callers at 60 requests per hour).

1. **Catalog and update check.** Fetch the manifest attached to the latest release:

       https://github.com/merchjar/copilot/releases/latest/download/manifest.json

   It always resolves to the latest released catalog. Read its `templates` array to
   list or filter; read `pack_version` and each template's `last_updated` to detect
   changes.

2. **Template bytes.** For a chosen template, read its `path` and the manifest's
   top-level `tag`, then fetch:

       https://raw.githubusercontent.com/merchjar/copilot/<tag>/<path>

   Pinning to the manifest's `tag` guarantees the catalog and the files agree.

## Deploy safety is unchanged

Fetching a template never changes an account. The Deployment Safety Protocol still
applies in full: preview against the live account, deploy disabled by default, and
prompt for an explicit enable afterward.

## Overrides (advanced / testing)

- `MJ_COPILOT_REPO` points the client at a different repo (default `merchjar/copilot`).
- `MJ_MANIFEST_URL` overrides the manifest URL.
- `MJ_COPILOT_REF` pins the manifest and raw fetches to a branch or tag (for example
  `main`) instead of the latest release. Useful before the first release exists.
