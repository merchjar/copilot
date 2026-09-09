# Private campaign structures

Find the active configuration through Connect's existing resolution order. Place `campaign-structures.json` beside that configuration, normally `user/campaign-structures.json`. Do not read or copy credentials to this store. Its schema version is independent of Config Version 3. Preserve the entire private `user/` directory on upgrades. The release contains no saved structures. Local files persist only for clients sharing those files; there is no automatic synchronization.

Use the bundled `scripts/campaign_structures.py`, relative to this skill:

```text
python scripts/campaign_structures.py inspect --store PATH
python scripts/campaign_structures.py select --store PATH --profile PROFILE_ID --purpose launch
python scripts/campaign_structures.py select --store PATH --profile PROFILE_ID --purpose launch --id STRUCTURE_ID
python scripts/campaign_structures.py save --store PATH --revision REVISION --definition PRIVATE_JSON_PATH
python scripts/campaign_structures.py remove --store PATH --revision REVISION --id STRUCTURE_ID
```

`inspect` returns data and a revision hash, including for a nonexistent store. After explicit save/update/remove instructions, use that revision for the mutation. Show the proposed change when replacing a definition; a direct unambiguous update needs no second approval. A stale revision, unknown schema, malformed JSON or existing lock stops the write. Read again and reconcile; never delete or reset storage to bypass an error. The helper serializes cooperating writers, checks for newer external edits and atomically replaces the file. Other editors should use the helper; arbitrary editors can still race an atomic replace. A leftover lock needs local investigation, not automatic deletion.

The executable `validate()` function defines schema version 1. A store has exactly `schema_version: 1` and a `structures` list. Each definition requires:

| Field | Meaning |
|---|---|
| `id`, `name` | Stable unique ID and readable name |
| `scope` | `global` or `profile:DECIMAL_ID` |
| `purposes` | Nonempty list such as `launch`, `discovery`, `known-targets` |
| `default` | Boolean; at most one default per scope and purpose |
| `grouping` | `per-product` or `shared-purpose`; storage is not execution acceptance |
| `roles` | Objects with unique `id`, explanatory `job` and `mode`: `auto-combined`, `keyword-broad`, `keyword-exact` |
| `naming` | Pattern such as `{asin} - {role}`; resolve tokens and check resulting names before approval |
| `budget_policy` | `basis: fresh-batch-total`, `weights` keyed by role ID with positive numeric ratios |
| `bid_defaults` | Currency code keyed maps of role ID to positive bid, or `{}`; never convert currencies silently |
| `keyword_policy` | `ask`, `defer-manual` or `paused-placeholders`. The last proposes complete manual campaigns with generated dummy keywords held paused when real seeds are absent; parent states are approved separately. It never authorizes creation or enabling. Store the policy, not dummy keyword strings. |
| `provenance` | `confirmed_at` timestamp and a non-secret summary in `instruction` |

No batch amount, product list, live campaign IDs, seeds or credentials are fields in this schema. Use private per-batch manifests and receipts for those. The initial schema deliberately requires a fresh batch budget and supports only the initial role modes. If an explicit durable policy cannot be represented, explain that limit and retain a portable non-secret description; do not silently approximate it or claim it was saved.

Resolve current explicit instructions first, then a selected named structure, profile default, global default, and finally a recommendation. `select` implements the stored portion and returns choices when there is no default. Apply conversation overrides to a working copy only. Account facts and capability limits still constrain execution. Currency conflict means the bid is unresolved, not that a numeric bid can be carried into the new currency.

When persistent files or Python are unavailable, offer a portable definition and say it applies to this conversation until successfully stored. Never claim memory from a proposed write or from chat history alone.
