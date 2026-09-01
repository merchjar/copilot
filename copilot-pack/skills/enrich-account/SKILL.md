---
name: enrich-account
description: Set up and populate custom fields on a Merch Jar account — profit margins, product lifecycle phase, inventory or seasonality flags, labels — so segments can automate against business data Amazon doesn't have. Use when the user says "add my margins," "set up custom fields," "tag my campaigns by phase," "label my products," "track profitability per product," or when build-segment or account-review surfaces a goal that needs business data the account doesn't carry yet.
---

# Enrich Account (Custom Fields)

## What This Does

Custom fields attach user-defined typed data to ad entities (campaigns, ad groups, keywords/targets, product ads). Once populated, segments read them in DSL as `custom.<key>` — which unlocks automation the ad data alone can't express: profit-true bidding against per-product margins, phase-based automation (launch vs. harvest), inventory or seasonality gating, and human-readable labels maintained by automation.

This skill covers the write side: defining fields, populating values, and verifying the result. The read side (using `custom.<key>` in segment logic) lives in `build-segment`.

## Context to Load Before Starting

1. https://merchjar.com/api/ and its downloadable OpenAPI specification — Custom Fields endpoints, types, and quotas
2. User preferences from `user/MJ_COPILOT_CONFIG.md` (already loaded)

**Scope check:** everything here needs `custom_fields:read`, and every write needs `custom_fields:write`. A `403` means the user's key predates these scopes — direct them to create a new key at https://app.merchjar.com/api-keys with all scopes enabled.

---

## Safety Rules (non-negotiable, same spirit as the Deployment Safety Protocol)

1. **Confirm before every write.** Show the plan (field names, types, entity type, how many values, where the values come from) and wait for an explicit yes before creating definitions or writing values. The Require Approval flag does not relax this — value writes touch the user's account data.
2. **Every bulk write carries a `source_reference`.** Format: `mj-copilot: <short purpose> <YYYY-MM-DD>` (max 100 chars), e.g. `mj-copilot: margin enrichment 2026-08-26`. This is the audit trail — an unattributed write is a protocol violation.
3. **Check quotas first.** The catalog returns `definition_count/limit` (50 per profile + entity type) and `value_count/limit` (100,000 per profile + entity type). Surface headroom before large writes; never burn quota on a speculative field.
4. **Deletes are dangerous.** Deleting a definition can disable live segments (`disabled_dependants[]` in the response). Before any delete: name the dependant segments to the user and get explicit confirmation. Prefer leaving an unused field in place over a delete that risks automation.
5. **Verify after writing.** Read back a sample (values endpoint or per-entity history) and confirm counts match what was sent. Report exactly what was written: "[N] values set on [entity type], source_reference '[tag]'."
6. **AI-derived values are labeled as such.** If the Copilot computes or infers values (e.g., auto-labeling campaigns by apparent purpose), say so before writing, show a sample of the derived values for approval, and use a source_reference that makes the derivation obvious (e.g., `mj-copilot: AI campaign labels 2026-08-26`).

---

## Workflow

### Step 1 — Understand the Goal → Field Plan

Translate the business goal into a concrete field plan:

| User goal | Typical plan |
|---|---|
| "Bid to my margins" / profit-true bidding | `Profit Margin` — number, on `target` (or `campaign` if margins are per-line) |
| "Treat launches differently" / phase-based automation | `Launch Phase` — string (`launch` / `grow` / `harvest`), on `campaign` |
| "Skip out-of-stock products" / inventory gating | `In Stock` — boolean, on `ad` or `campaign` |
| "Seasonal products" | `Seasonal` — boolean, or `Season` — string, on `campaign` |
| "Label / organize my campaigns" | `Label` — string, on `campaign` |

Pick the entity type by where the segment logic will run: fields are only readable by segments on the matching dataset. Bid logic reads `target` fields; budget/state logic reads `campaign` fields.

### Step 2 — Catalog Check

`GET /api/v5/custom-fields/catalog/:entityType`. Check: does a field with this purpose already exist (reuse it — never create a near-duplicate)? Is there definition and value quota headroom? Note the exact `key` of any existing field.

### Step 3 — Confirm the Plan

Read the plan back in plain English: field name(s), type, entity type, how many entities get values, and the value source. Value sources, in order of preference:

1. **User-provided data** — a pasted list, an uploaded CSV (product/ASIN → margin, etc.)
2. **Derived from account data** — e.g., labeling campaigns by naming convention or performance pattern (show samples first)
3. **A single default the user states** — e.g., "everything is 35% margin except these five"

Wait for explicit confirmation.

### Step 4 — Create Definitions

`POST /api/v5/custom-fields/definitions` per field. Capture the returned `definition_id` and generated `key` — report the key to the user ("your field's DSL name is `custom.cf_profit_margin`").

### Step 5 — Write Values

- **Up to a few hundred values:** `POST /api/v5/custom-fields/values/:entityType/bulk` with a `mutations` array (`set` operations; numbers as strings) and the `source_reference`. Batch sensibly; the standard limit is 1,200 requests per minute per key, so a few hundred values in batches of 100 is fine.
- **Large sets:** CSV import (`POST /custom-fields/csv/imports/:entityType`). **Run `dry_run=true` first**, show the user the dry-run result (rows accepted / errored), then run the real import and poll the job.
- **Entity id discovery:** there is no `GET /campaigns` endpoint. Get entity ids from segment preview results, or from the values-by-definition endpoint for already-enriched fields.

### Step 6 — Verify + Log

Read back a sample of the written values (`GET /values/:entityType?entity_id=...` or the history endpoint) and confirm the count matches. Then append to `user/MJ_COPILOT_LOG.md` — use the Deployed Segments section's schema conventions in a dedicated `## Custom Fields` section (create it if missing): date, profile, field key, entity type, values written, source_reference.

### Step 7 — Offer the Payoff

Enrichment exists to power automation. Close the loop: "Your margins are on the account now. Want me to build the segment that uses them — bids capped by each product's actual profitability instead of one account-wide target?" Hand off to `build-segment` (the `custom.<key>` rules live there).

---

## Maintenance Patterns

- **Updating values** (margins change, phases advance): same bulk endpoint, same rules — confirm, source_reference, verify. `expected_version` per mutation protects against clobbering a value someone changed in the UI mid-flight.
- **Renaming a field:** `PATCH /definitions/:id` with `expected_version` from the catalog. The `key` does NOT change on rename — DSL references stay valid.
- **Rollback:** each history entry can be reverted via `POST /custom-fields/history/:historyId/rollback`. If the user says a write was wrong, find the entries via the history endpoint and roll back — don't hand-reconstruct old values.
- **"What did the Copilot change?"** — the per-entity history endpoint filtered to `source_type = 2` (API) with the Copilot's source_reference tags answers this precisely.
