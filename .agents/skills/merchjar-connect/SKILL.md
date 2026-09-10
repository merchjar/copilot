---
name: merchjar-connect
description: Connect an AI agent to a Merch Jar account (Amazon Sponsored Products PPC) through the Merch Jar API. Use when starting any Merch Jar session, and whenever another Merch Jar skill needs the API client, the API key, the safety protocol, or the DSL and API references. Handles key setup (config file or MERCHJAR_API_KEY), profile discovery, the shell client, and the non-negotiable deploy safety rules.
license: Proprietary. Use requires an active Merch Jar account; see LICENSE in the repo root.
compatibility: Shell + network access (Claude Code, Codex, Cursor, Gemini CLI, any Agent Skills client that can run Python 3.9+). Claude Desktop/Cowork uses the Chrome extension instead of the shell client; the safety rules and references still apply.
metadata:
  version: "1.4"
  tags: "connect, api, setup, safety, references"
  goal: "set-up"
  risk: "read-only"
  requires-skills: ""
  requires-scopes: "profiles:read"
  produces: "a connected account (profiles listed) and a working API client the other skills call"
  last-updated: "2026-09-10"
---

# Merch Jar Connect

The base skill every other Merch Jar skill depends on. It owns three things:

1. **The API client** at `scripts/merchjar_client.py` (stdlib only).
2. **The key and profile handling** (below).
3. **The references** in `references/`: `MJ_API_REFERENCE.md` (endpoints, gotchas), `V2_SYNTAX_REFERENCE.md` (the Segment DSL), `SEGMENT_CREATION_GUIDELINES.md` (quality standards). Load only the one a task needs.

## Shared naming preferences

Campaign-authoring skills resolve `campaign-naming.json` beside the active private configuration through [references/campaign-naming.md](references/campaign-naming.md) and `scripts/campaign_naming.py`. This helper is offline and needs no credentials. Campaign Naming guides convention selection; Creation and relevant reviews read the same preference without needing the optional naming skill installed. Preserve this file, `campaign-naming-records/`, and saved launch structures during updates. Resolve the profile explicitly and never treat a malformed store as absent.

## Two layouts, same skill

- **Copilot Pack** (the zip from merchjar.com): the client is at `tools/merchjar_client.py` and the references at `reference/`, relative to the pack root. The pack's `CLAUDE.md` / `AGENTS.md` cold-start protocol already routes you there.
- **Standalone install** (`npx skills add merchjar/copilot`, a plugin, or a copied folder): everything is inside this skill folder: `scripts/merchjar_client.py` and `references/`. Other Merch Jar skills reference them as `../merchjar-connect/scripts/` and `../merchjar-connect/references/`.

Both files are byte-identical copies; the repo's build syncs them.

## Key handling

The client looks for the key in this order:

1. `MERCHJAR_API_KEY` environment variable.
2. `MJ_COPILOT_CONFIG` environment variable pointing at a config file.
3. `user/MJ_COPILOT_CONFIG.md` found by walking up from the script's folder (the pack layout).
4. `~/.merchjar/MJ_COPILOT_CONFIG.md`.

A key looks like `mj_live_...`. Create one at https://app.merchjar.com/api-keys (enable every scope the skills you plan to use need; it is shown once).

**Never silently consume a pasted key.** If the user pastes one, confirm first: "I see what looks like a Merch Jar API key. Want me to save it and connect your account?" Only after a yes, save it as a bare line under the `## API Key` heading of the config file (no backticks, quotes, labels, or list markers). Never echo the key back, never write it into any other file, never put it in a command line argument.

If there is no key and none was pasted: "To get started, paste your Merch Jar API key. Create one at https://app.merchjar.com/api-keys. Setup guide: https://www.merchjar.com/help/docs/api-ai-copilot-quickstart".

## Connect

```bash
python scripts/merchjar_client.py profiles
```

Lists the ad-account profiles the key can see: name, nickname, country, type, managed flag, 30-day spend. **Spend fields (`ad_spend_30d`, `ad_spend_30d_usd`) are in cents: divide by 100.** Use `nickname` as the display name when present. Record the profile ids the user works with (pack: the `## Profile IDs` section of the config). If exactly one profile has meaningful spend and the user did not name one, default to it and say so.

Preflight before promising live data: run `profiles` once. If the network is off (Codex sandbox: Settings → Network access), say so with the fix instead of advertising a scan you cannot run.

## Call the API

```bash
python scripts/merchjar_client.py request GET  /api/v5/segments --profileid 123456
python scripts/merchjar_client.py request POST /api/v5/segments/preview --body-file tmp/preview.json
python scripts/merchjar_client.py request PATCH /api/v5/segments/123 --profileid 123456 --body-file tmp/patch.json
```

Rules that keep calls working:

- **Write JSON payloads to a file and pass `--body-file`.** Never inline `--body` for DSL payloads; PowerShell splits them at spaces and quotes before the call is made.
- `per_page` for previews goes in the JSON body (max 100), not the URL.
- Profile-scoped entity calls, including campaign/ad-group/ad/target creates, need `--profileid`. Segment preview/create carry `profile_id` in the body. Entity-create schemas reject body `profile_id`; follow the live contract for each endpoint.
- Entity updates, archives and bulk actions use `--idempotency-key <unique-request-key>` where required by the live contract. Persist the key with the exact method, path, profile and body; reuse it only for an identical request. This option does not make entity creation idempotent, and the client does not automatically retry.
- `set_state` params are `{"value": 1}` (enabled) or `{"value": 2}` (paused).
- Report raw API errors exactly before recovering. `HTTP 401` on an unknown path means the endpoint does not exist (there is no `GET /campaigns`; discover entities via preview).
- The preview endpoint has a tight burst bucket: space repeated previews out, and back off on 429.

## Safety rules (non-negotiable, every skill inherits them)

For automatic campaign creation, load the Entity creation section of the API reference. `autoCreateTargets: true` selects automatic targeting; Amazon generates the four groups. Create the campaign, ad group and Product Ad PAUSED, then inspect the generated targets. Do not POST four duplicate THEME targets. Generated targets can have enabled own state while paused parents prevent delivery. Empty Merch Jar previews do not establish their absence in Amazon. Reconcile in Amazon before retrying any unknown creation outcome.

- **Deploy disabled.** Every `POST /api/v5/segments` uses `"enabled": false`. Enabling is a separate, explicit step the user asks for.
- **Preview first.** Run `POST /api/v5/segments/preview` and show the headline result (rows, spend, sample) before any create or trigger change.
- **Duplicate check.** `GET /api/v5/segments` before every create; look for name or purpose conflicts on that profile.
- **PATCH for updates.** "Modify / update / tune" means `PATCH` the existing segment, never a second `POST`. Include `ad_type` in PATCH bodies.
- **One `keywords_and_targets` segment for bid management**, never a keywords segment plus a targets segment.
- **Custom-property writes are gated like deploys**: defining fields or bulk-writing values needs the `custom_fields:write` scope, an explicit user yes on the plan, and a `source_reference` audit tag on every bulk write.
- **Confirm a pasted key before saving it.**

## Which reference to load

| Task | Load |
|---|---|
| Any API call shape, scopes, error codes | `references/MJ_API_REFERENCE.md` |
| Writing or reading Segment DSL | `references/V2_SYNTAX_REFERENCE.md` |
| Judging or building a segment to standard | `references/SEGMENT_CREATION_GUIDELINES.md` |

Keep them on demand; do not preload all three.
