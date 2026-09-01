# Merch Jar Public API Reference

**Base URL:** `https://app.merchjar.com/api/v5`

> **Canonical contract:** https://merchjar.com/api/ (machine-readable OpenAPI 3.1: https://merchjar.com/api/openapi.json). That page is the source of truth for endpoints, scopes, schemas, and rate limits. This file is the Copilot's working summary plus the operational gotchas that the contract doesn't cover. If the two disagree, the website wins; fetch the OpenAPI document when you need an exact request or response schema (for example, the entity-creation payloads) rather than guessing.

---

## Authentication

All requests require a valid API key passed as a Bearer token in the `Authorization` header.

**Key format:** Keys use the prefix `mj_live_` followed by a random string.

```
Authorization: Bearer mj_live_abc123def456...
```

API keys are created and managed at **https://app.merchjar.com/api-keys**. From there you can create new keys with specific scopes, view active keys (the full key is only shown once at creation), and revoke keys (revoked keys are rejected immediately).

---

## Scopes

Each API key is granted one or more scopes that control which endpoints it can access.

| Scope | Grants access to |
|---|---|
| `profiles:read` | GET /api/v5/profiles |
| `segments:read` | GET /api/v5/segments, GET /api/v5/segments/:id, GET schedule + schedule timezones |
| `segments:write` | POST /api/v5/segments, PATCH /api/v5/segments/:id, DELETE /api/v5/segments/:id, PUT/DELETE schedule, POST schedule/preview |
| `segments:preview` | POST /api/v5/segments/preview |
| `segments:validate` | POST /api/v5/segments/validate |
| `audit_logs:read` | GET /api/v5/audit-logs, GET /api/v5/audit-logs/:id/items |
| `history:read` | GET /api/v5/history/:entity_type/:entity_id |
| `campaigns:write` | POST /api/v5/campaigns |
| `ad_groups:write` | POST /api/v5/ad-groups |
| `ads:write` | POST /api/v5/product-ads |
| `targets:write` | POST /api/v5/targets |
| `negative-targets:write` | POST /api/v5/negative-targets |
| `custom_fields:read` | GET custom-fields catalog, values, history; snapshot + CSV export |
| `custom_fields:write` | Create/update/delete custom field definitions; bulk value writes; rollback; CSV import |

A request to an endpoint whose scope is not present on the key returns `403 Forbidden`.

---

## Rate Limiting

Limits are enforced before the operation runs. Use the response headers to decide when to retry.

| Request type | Limit |
|---|---|
| Standard operations | 1,200 requests per minute per API key by default (a key may carry a configured override) |
| `POST /segments/preview` | In addition to the standard limit: a 3-request burst per account (shared across its keys) that refills one request every 2 seconds |
| Entity creation (`/campaigns`, `/ad-groups`, `/product-ads`, `/targets`, `/negative-targets`) | No rate-limit middleware currently: no rate-limit headers, no 429s. Batch inside one request (1 to 1,000 items) instead of looping single creates |

Practical rule for the Copilot: previews are the tight one. Space preview calls at least 2 seconds apart when running more than three in a row.

Every rate-limited response includes these headers:

| Header | Description |
|---|---|
| `X-RateLimit-Limit` | Maximum requests allowed in the current window |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | Unix timestamp (seconds) when the window resets |

When the limit is exceeded, the response is `429 Too Many Requests` with a `Retry-After` header.

---

## Endpoints

### GET /api/v5/profiles

List all Amazon Advertising profiles accessible to the authenticated API key.

**Required scope:** `profiles:read`

**Response (200):**
```json
{
  "data": [
    {
      "profile_id": "381130241061574",
      "name": "Bent Piton",
      "nickname": "SC US",
      "country_code": "US",
      "currency_code": "USD",
      "marketplace_id": "ATVPDKIKX0DER",
      "timezone": "America/Los_Angeles",
      "type": "seller",
      "managed": true,
      "ad_spend_30d": 120050,
      "ad_spend_30d_usd": 120050
    }
  ]
}
```

**Profile object fields:**

| Field | Type | Description |
|---|---|---|
| `profile_id` | string | Amazon Advertising profile ID — used as the `profileid` header on all profile-scoped requests |
| `name` | string | Account name as it appears in Amazon Advertising |
| `nickname` | string \| null | Custom nickname set in Merch Jar |
| `country_code` | string | Two-letter country code (e.g. `US`, `DE`, `UK`) |
| `currency_code` | string | ISO currency code for this marketplace |
| `marketplace_id` | string | Amazon marketplace ID |
| `timezone` | string | IANA timezone string for the profile's marketplace |
| `type` | string | Account type: `seller`, `vendor`, or empty string for KDP |
| `managed` | boolean | Whether this profile is actively managed in Merch Jar. Non-agency users typically only want to work with `managed: true` profiles. |
| `ad_spend_30d` | number | Total ad spend over the last 30 days in the profile's local currency. **Returned in cents — divide by 100 for dollar display.** Example: `617700` = $6,177.00 |
| `ad_spend_30d_usd` | number | Total ad spend over the last 30 days in USD. **Returned in cents — divide by 100 for dollar display.** Example: `617700` = $6,177.00 |

---

### GET /api/v5/audit-logs

List the segment execution history for a profile. Each entry represents one segment run, including how many entities were affected and a snapshot of the segment at the time of execution.

**Required scope:** `audit_logs:read`

**Required header:** `profileid: <Amazon Advertising profile ID>`

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number (must be >= 1) |
| `per_page` | integer | 25 | Results per page (1–100) |

**Response (200):**
```json
{
  "data": [
    {
      "id": "456",
      "profile_id": "381130241061574",
      "target_type": "recipes",
      "source_type": "bulk_action",
      "source_id": "123",
      "meta": {
        "count": 42,
        "successCount": 40,
        "failedCount": 2,
        "event": {
          "id": 123,
          "name": "High ACoS Keywords",
          "actions": [...],
          "ad_type": 2,
          "enabled": true,
          "trigger": "acos(30d) > 50 AND clicks(30d) > 20",
          "frequency": 1,
          "created_at": "2026-03-01T10:00:00.000Z",
          "updated_at": "2026-03-19T12:00:00.000Z",
          "deleted_at": null,
          "profile_id": 381130241061574,
          "action_params": {},
          "frequency_params": {}
        }
      },
      "created_at": "2026-03-20T08:00:00.000Z",
      "updated_at": "2026-03-20T08:00:00.000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 51,
    "last_page": 3
  }
}
```

**Audit log object fields:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Audit log entry ID |
| `profile_id` | string | Amazon Advertising profile ID |
| `target_type` | string | Entity type that was acted on. Observed values include `keywords`, `campaigns`, `targets`, `recipes`. |
| `source_type` | string | What triggered the run. Observed values include `recipe` (a Recipe ran) and `bulk_action` (a Segment ran a batched action). Treat this as varied — do not hard-code a single value. |
| `source_id` | string | ID of the segment or recipe that was executed |
| `meta.count` | number | Total number of entities evaluated |
| `meta.successCount` | number | Number of entities successfully updated (camelCase, not snake_case — confirmed live 2026-05-08) |
| `meta.failedCount` | number | Number of entities that failed to update (camelCase) |
| `meta.event` | object | Snapshot of the segment/recipe at execution time. `meta.event.actions` (plural array) appears on bulk_action entries. |
| `created_at` | string | Timestamp when the run occurred |
| `updated_at` | string | Timestamp of last update to this log entry |

**Field naming note:** the `meta` object uses camelCase (`successCount`, `failedCount`) while the top-level fields use snake_case (`source_type`, `created_at`). This inconsistency is in the live API as of 2026-05-08. If a fix ships server-side, update this reference.

---

### POST /api/v5/segments/validate

Validate a segment trigger expression without executing it. Useful for checking syntax before saving.

**Required scope:** `segments:validate`

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `trigger` | string | Yes | Segment trigger expression (DSL) |
| `ad_type` | string | Yes | Entity type context for validation |

**Valid `ad_type` values:** `campaigns`, `ad_groups`, `keywords`, `targets`, `keywords_and_targets`, `ads`, `search_terms`

> **Dataset support (verified 2026-06-09):**
> - `keywords_and_targets` — fully supported on validate, preview, AND create. This is the combined dataset; deploy it as a single segment for bid management that covers both manual keywords and auto-targets. `GET /api/v5/segments` now returns `"keywords_and_targets"` correctly (the old `"unknown"` bug is fixed).
> - `ads` (Product Ads) — fully supported on validate, preview, and create. `GET` returns `"ads"` correctly (the old `"Unsupported ad type: 21"` failure is fixed). Use the literal value `ads`; `product_ads` is also accepted, but hyphenated `product-ads` is rejected by preview/create.
>
> **Frequency gaps (verified 2026-06-09, reported to eng):**
> - Segments on the UI "After every data sync" schedule are returned by `GET` as `frequency: "daily"` — that mode is not represented (`frequency_params` is null). Don't treat a GET value of `daily` as a confirmed daily schedule.
> - Read/write enum mismatch: `GET` returns `manual`, but POST/PATCH reject `manual` (and every "after every data sync" spelling) with `invalid_frequency`. Write accepts only `daily`/`weekly`/`monthly`, so "manually" and "after every data sync" can't be set via API.

**Response — Valid (200):**
```json
{
  "valid": true,
  "variables": {
    "my_var": "numeric"
  }
}
```

**Response — Invalid (422):**
```json
{
  "valid": false,
  "error": {
    "code": "parse_error",
    "message": "Unexpected token 'xyz' at position 12",
    "position": 12
  }
}
```

---

### POST /api/v5/segments/preview

Preview the entities that match a segment trigger expression. Returns paginated rows with metrics and totals.

**Required scope:** `segments:preview`

**Request body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `profile_id` | string | Yes | -- | Amazon Advertising profile ID |
| `trigger` | string | Yes | -- | Segment trigger expression (DSL) |
| `ad_type` | string | Yes | -- | Entity type to query |
| `action` | string | Yes | -- | Action to preview |
| `action_params` | object | Yes | -- | Parameters for the action |
| `page` | integer | No | 1 | Page number (must be >= 1) |
| `per_page` | integer | No | 25 | Results per page (1–100) |

**Valid `ad_type` values:** `campaigns`, `ad_groups`, `keywords`, `targets`, `keywords_and_targets`, `ads`, `search_terms` (`keywords_and_targets` and `ads` fully supported as of 2026-06-09).

**Valid `action` values:** `set_state`, `set_budget`, `set_default_bid`, `set_bid`, `create_negatives`

**`action_params` by action:**

`set_state`

| Field | Type | Default | Description |
|---|---|---|---|
| `value` | integer | 2 | 1 = enabled, 2 = paused |

`set_budget`, `set_default_bid`, `set_bid`

| Field | Type | Default | Description |
|---|---|---|---|
| `direction` | string | `"set-to-$"` | How to apply the value |
| `value` | number \| string | 0 | Dollar amount, percentage, or variable name |
| `source` | string | `"value"` | `"value"` for literal numbers, `"variable"` for a DSL variable name |

Valid `direction` values: `set-to-$`, `increase-%`, `decrease-%`, `increase-$`, `decrease-$`

When `source` is `"variable"`, `value` must be a string containing the variable name from the trigger expression.

`create_negatives` — no parameters required, pass an empty object `{}`.

**Response (200):**
```json
{
  "data": [
    {
      "campaign_name": "My Campaign",
      "ad_group_name": "My Ad Group",
      "keyword_text": "running shoes",
      "impressions": 1200,
      "clicks": 45,
      "spend": 22.50,
      "sales": 89.99,
      "acos": 25.0,
      "___my_variable": 3.5
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 142,
    "last_page": 6
  },
  "totals": {
    "cost_30d": 900.00,
    "impressions_30d": 50000,
    "clicks_30d": 1800,
    "sales_30d": 3200.00,
    "acos_30d": 28.1
  },
  "meta": {
    "time_periods": ["7d", "30d"],
    "variables": {
      "my_variable": "numeric"
    }
  }
}
```

| Field | Description |
|---|---|
| `data` | Array of matching rows. Variables defined in the trigger appear as `___variable_name`. **Note:** Only computed variables (numeric, boolean, `case()` results) are returned. String literal assignments (e.g., `let $reason = "text"`) are omitted from the API response even though they display in-app. Use `case()` expressions for string variables that need to appear in preview output (see KI-006 in V2 Syntax Reference). |
| `pagination.total` | Total matching rows across all pages |
| `totals` | Aggregate metrics across all matching rows (not just the current page). Field names include a time period suffix matching the query (e.g., `cost_30d`, `cost_lifetime`). Use `cost_*` for spend amounts. |
| `meta.variables` | Variables defined in the trigger expression and their types |

> **`totals` only populate for time windows the trigger actually references.** If the trigger contains no metric call for a window (e.g., no `spend(30d)`, `clicks(30d)`, `orders(30d)`), the matching `totals.*_30d` fields come back `0` even when the matched rows have real spend. This is expected: a trigger that matches purely on structural properties (`match type`, `state`, names) reports `total` row counts but blank metric totals. To get a dollar figure in `totals`, add the metric you want to the trigger — e.g., `let $spend_30d = spend(30d);`. Do not read a `0` total here as "no spend"; check whether the window was referenced first.
>
> **ACOS scale is inconsistent across contexts — sanity-check the magnitude.** Preview `totals.acos_30d` is **percent-scaled** (`28.1` means 28.1%), while row-level `acos` and ACOS values derived in `let` variables come back as **decimals** (`0.281`). The campaign-object `acos` field is also a decimal (`0.314`, not `31.4`). When you do ratio math on a row variable (e.g., `evaluation_acos / target_acos`), it only works if the operand is the decimal form (~0.28), not the percent form. If an ACOS value is ~1–100, treat it as a percent; if it's ~0–1, treat it as a decimal.

---

### GET /api/v5/segments

List all segments for a profile.

**Required scope:** `segments:read`

**Required header:** `profileid: <Amazon Advertising profile ID>`

**Response (200):**
```json
{
  "data": [
    {
      "id": "123",
      "profile_id": "3456789012345678",
      "name": "High ACoS Keywords",
      "enabled": true,
      "ad_type": "keywords",
      "trigger": "acos(30d) > 50 AND clicks(30d) > 20",
      "action": "set_bid",
      "action_params": {
        "direction": "decrease-%",
        "value": 15,
        "source": "value"
      },
      "frequency": "daily",
      "last_run": "2026-03-19T12:00:00.000Z",
      "created_at": "2026-03-01T10:00:00.000Z",
      "updated_at": "2026-03-19T12:00:00.000Z"
    }
  ]
}
```

**Segment object fields:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Segment ID (numeric string) |
| `profile_id` | string | Amazon Advertising profile ID |
| `name` | string | Segment name |
| `enabled` | boolean | Whether the segment is currently active |
| `ad_type` | string | Entity type the segment applies to (`keywords`, `targets`, `keywords_and_targets`, `ads`, `campaigns`, `ad_groups`, `search_terms`). Returns the correct value for all datasets (the old `"unknown"` bug for K&T / Product Ads is fixed). |
| `trigger` | string | DSL trigger expression |
| `action` | string | Action to perform on matching entities |
| `action_params` | object | Parameters for the action |
| `frequency` | string | API returns `daily`, `weekly`, `monthly`, or `manual`. **Known bug:** "After every data sync" segments are returned as `daily` (mode not represented). See API Behavior Notes. |
| `last_run` | string \| null | Timestamp of the last execution |
| `created_at` | string | Creation timestamp |
| `updated_at` | string | Last update timestamp |

---

### GET /api/v5/segments/:id

Get a single segment by ID.

**Required scope:** `segments:read`

**Required header:** `profileid: <Amazon Advertising profile ID>`

**Response (200):**
```json
{
  "data": {
    "id": "351793",
    "profile_id": "...",
    "name": "...",
    "enabled": false,
    "ad_type": "search_terms",
    "trigger": "...",
    "action": "create_negatives",
    "action_params": {},
    "frequency": "daily",
    "last_run": null,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

The segment object is wrapped in a `data` envelope (same convention as the list endpoint). Returns `404` if not found.

---

### POST /api/v5/segments

Create a new segment.

**Required scope:** `segments:write`

**Request body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `profile_id` | string | Yes | -- | Amazon Advertising profile ID |
| `name` | string | Yes | -- | Segment name (max 255 characters) |
| `trigger` | string | Yes | -- | Segment trigger expression (DSL) |
| `ad_type` | string | Yes | -- | Entity type |
| `action` | string | Yes | -- | Action to perform |
| `action_params` | object | No | `{}` | Parameters for the action |
| `frequency` | string | No | `"daily"` | How often to run. **Write accepts only `daily`, `weekly`, `monthly`.** Cannot set `manual` / "manually" or "after every data sync" (UI-only modes; `manual` is rejected on write even though GET returns it). |
| `enabled` | boolean | No | `true` | Whether the segment should be active. **Copilot convention: always pass `false` on create.** The API-level default is `true`, but the Copilot deploys every new segment disabled and enables it only on explicit user confirmation — see docs/copilot.md → Deployment Safety Protocol. |

**Response (200, observed 2026-05-08):**
```json
{
  "data": {
    "id": "351793",
    "profile_id": "...",
    "name": "...",
    "enabled": false,
    "ad_type": "...",
    ...
  }
}
```

The segment object is wrapped in a `data` envelope. Returns `422` if the trigger expression is invalid. Older documentation referenced a `201 Created` status; live testing on 2026-05-08 returned `200` with the envelope shown above. Treat both as success.

> **`keywords_and_targets` on create — supported (verified 2026-06-09, re-confirmed in live testing 2026-06-15):** The create endpoint accepts `"keywords_and_targets"` as `ad_type`. Deploy bid management that covers both manual keywords and auto-targets as a **single** segment with this `ad_type` — do NOT split into two segments. The old "split into separate `keywords` and `targets` segments" workaround is obsolete; an earlier edition of this doc carried a "not accepted on create" limitation that was wrong. Validate, preview, AND create all accept `keywords_and_targets`.

> **Known limitation — empty 201 response:** In some cases (particularly when the segment name contains non-ASCII characters like em-dashes), the API returns `201 Created` but the response body is empty or unparseable. This does NOT necessarily mean the segment failed to create — check via `GET /api/v5/segments` before retrying. Blind retries create duplicates. Workaround: use ASCII-only segment names.

---

### PATCH /api/v5/segments/:id

Update an existing segment. Only fields included in the request body are updated.

**Required scope:** `segments:write`

**Required header:** `profileid: <Amazon Advertising profile ID>`

All fields are optional — include only what you want to change. Returns the updated segment object (wrapped in a `data` envelope, same shape as POST).

**`ad_type` in the body:** historically the API returned 422 if a PATCH didn't include `ad_type` in the body. Live testing on 2026-05-08 showed PATCH succeeding without `ad_type` for name-only changes. The behavior may differ for trigger or enabled-state changes — Copilot convention is to always include `ad_type` in PATCH bodies as a defensive habit, regardless of what's changing. This is cheap, safe, and matches the historical claim if the server-side validation comes back.

---

### DELETE /api/v5/segments/:id

Delete a segment (soft-delete). The segment is disabled and marked as deleted.

**Required scope:** `segments:write`

**Required header:** `profileid: <Amazon Advertising profile ID>`

Returns `{ "success": true }` on success, `404` if not found.

---

### Custom Fields

User-defined typed fields on ad entities, settable via the API and readable in the Segments DSL as `custom.<key>` (including `is_null(custom.<key>)`). Use them to attach business data the ad console doesn't have — profit margins, product lifecycle phase, inventory or seasonality flags, labels — and then reference that data in segment logic. See `reference/V2_SYNTAX_REFERENCE.md` for DSL usage and the `enrich-account` skill for the write workflow.

**Scopes:** `custom_fields:read` / `custom_fields:write` — selectable at key creation, deliberately separate: read never implies write. If a call returns `403`, the user's key was created without the custom-fields scopes; they need a new key from https://app.merchjar.com/api-keys with all scopes enabled.

**All endpoints require the `profileid` header.**

**Entity types:** `campaign`, `ad_group`, `target` (keywords & targets), `ad`.
**Data types (integer in requests):** `1` = number, `2` = boolean, `3` = string.
**Quotas:** 50 definitions per profile + entity type, 100,000 values per profile + entity type. Check the catalog counts before creating definitions or bulk-writing values.

#### GET /api/v5/custom-fields/catalog/:entityType — scope `custom_fields:read`

Definitions + quota counts for one entity type. Returns `definitions[]` (each with `definition_id`, `key` like `cf_<slug>`, `name`, `data_type`, `version`), `definition_count`/`limit`, `value_count`/`limit`, and a catalog `version`. Supports ETag/If-None-Match.

#### POST /api/v5/custom-fields/definitions — scope `custom_fields:write`

Body: `{ "entity_type": "campaign", "name": "...", "description": "..."|null, "data_type": 3 }` → `201 { definition }`. The `key` (used in DSL as `custom.<key>`) is generated from the name; re-creating a soft-deleted name gets a suffixed key (`_2`, `_3`, ...).

#### PATCH /api/v5/custom-fields/definitions/:definitionId — scope `custom_fields:write`

Body: `{ "entity_type", "expected_version", "name", "description"? }`. Optimistic concurrency via `expected_version` — fetch the current version from the catalog first.

#### DELETE /api/v5/custom-fields/definitions/:definitionId — scope `custom_fields:write`

Body: `{ "entity_type", "expected_version", "disable_dependants"?: bool }`. Soft-deletes the definition; returns it with `deleted_at` set plus `disabled_dependants[]` — the segments that referenced the field. **Deleting a field can disable live segments.** Always check for dependants and warn the user before deleting.

#### GET /api/v5/custom-fields/values/:entityType?entity_id=... — scope `custom_fields:read`

Values for the given entity ids (`entity_id` repeated, or `entity_ids=a,b`), keyed `values[entity_id][field_key]`.

#### POST /api/v5/custom-fields/values/:entityType/snapshot — scope `custom_fields:read`

Body `{ "entity_ids": [...] }` — bounded body-based read for large selections.

#### GET /api/v5/custom-fields/values/:entityType/definition/:definitionId — scope `custom_fields:read`

All values for one field, paginated (`limit` 1-200, `after_entity_id`, `next_cursor`). Also handy for discovering entity ids.

#### POST /api/v5/custom-fields/values/:entityType/bulk — scope `custom_fields:write`

Body: `{ "mutations": [{ "field_definition_id", "entity_id", "operation": "set"|"clear", "value"?, "expected_version"? }], "source_reference"?: "<audit tag, max 100 chars>" }`. `set` requires `value` (string; booleans as booleans for type 2; **numbers are sent as strings**); `clear` must omit it. Returns updated values + the new `value_count`.

**Copilot convention: always send `source_reference`** on every bulk write (e.g., `mj-copilot: margin enrichment 2026-08-26`). It lands in the per-entity audit history and is how the user traces what the Copilot changed and why. A write without a source_reference is an unattributed write — don't do it.

#### GET /api/v5/custom-fields/values/:entityType/:entityId/history — scope `custom_fields:read`

Full audit trail per entity: `operation`, `value`, actor, `source_type` (1 = UI, 2 = API), `source_reference`, timestamps. Filters: `definition_id`, `before_id`, `limit` 1-200. Use this to read back and verify writes.

#### POST /api/v5/custom-fields/history/:historyId/rollback — scope `custom_fields:write`

Body: `{ "entity_type", "expected_version": string|null }`. Reverts one history entry.

#### CSV bulk (async jobs)

For large value sets: `POST /custom-fields/csv/imports/:entityType` (Content-Type `text/csv`, max 25 MiB, `?dry_run=true|false`, write scope) → `202 { job }` · `POST /csv/exports/:entityType` (read) · `GET /csv/jobs/:jobId` · `POST /csv/jobs/:jobId/cancel` (write) · `GET /csv/jobs/:jobId/errors` and `/download` (read, returns CSV). **Always run an import with `dry_run=true` first** and show the user the result before the real import.

**Gotcha:** there is no `GET /campaigns` endpoint in v5 — it returns a bare `401` (not a scope error) even with a full-scope key. To discover entity ids, use segment preview results or the values-by-definition endpoint above.

---

### Segment schedules

Clock-based scheduling for a segment (the "Scheduled" workflow in the app). The segment must use `frequency: manual` (by design: a scheduled segment runs on its clock, not after every sync) and cannot be a negative type. All calls take the `profileid` header.

| Endpoint | Scope | Notes |
|---|---|---|
| `GET /segments/:id/schedule/timezones` | `segments:read` | Full IANA timezone list for the picker |
| `GET /segments/:id/schedule` | `segments:read` | Current schedule, or empty if none |
| `PUT /segments/:id/schedule` | `segments:write` | Body: `{ "kind": "cron", "timezone": "America/New_York", "cron_expression": "0 9 * * *" }` or `{ "kind": "once", "timezone": "...", "run_once_at": "<ISO-8601>" }` |
| `POST /segments/:id/schedule/preview` | `segments:write` | Validates a proposed schedule and returns its next occurrences without saving |
| `DELETE /segments/:id/schedule` | `segments:write` | Removes the schedule |

`PATCH /segments/:id` with `paused: true` pauses future scheduled runs without disabling the segment; `enabled: false` also skips them.

---

### GET /api/v5/audit-logs/:id/items

**Required scope:** `audit_logs:read` · **Required header:** `profileid`

The per-entity change rows for one audit-log entry (one segment run). Filter with `target_type` (`campaigns`, `ad_groups`, `product_ads`, `keywords`, `targets`, `search_terms`, `placements`, negative types, ...). Paginated. Use this when the user asks "what exactly did that run change" rather than the aggregate counts on `/audit-logs`.

---

### GET /api/v5/history/:entity_type/:entity_id

**Required scope:** `history:read` · **Required header:** `profileid`

Per-entity bid/budget change history, newest first, paginated. `entity_type` is one of `campaigns` (budget changes), `ad_groups` (default bid), `keywords`, `targets` (bid). Each row carries the change type (for example `BID_AMOUNT`), previous and new value, and timestamp. This is separate from the segment audit log: it answers "how has this keyword's bid moved over time" for one entity id.

---

### Entity creation (Sponsored Products)

Create-only endpoints that proxy Amazon Ads v1 batch creates. There is no public update, archive, or delete: cleanup happens in the Merch Jar or Amazon UI. Always create in `state: PAUSED` and tell the user what was created and where.

| Endpoint | Scope | Body key | Status |
|---|---|---|---|
| `POST /campaigns` | `campaigns:write` | `campaigns[]` | **Known broken (Sep 2026):** the strict schema omits Amazon-required `budgets`, `marketplaceScope`, `startDateTime`, so every valid request fails at Amazon with a 400. Do not offer campaign creation until this is fixed; create the campaign in the app instead. |
| `POST /ad-groups` | `ad_groups:write` | `adGroups[]` | **Known broken (Sep 2026):** schema omits Amazon-required `bid`. Same failure mode. |
| `POST /targets` | `targets:write` | `targets[]` | Working. Keyword targets (exact / broad / phrase), theme targets (show as "keyword group" in the Amazon console), product targets (need an eligible, not-already-targeted ASIN), and **campaign-level negative keywords** (this endpoint, not `/negative-targets`). |
| `POST /negative-targets` | `negative-targets:write` | `negativeTargets[]` | Working. Ad-group-level negative **product** targets only (ASIN, `PRODUCT_EXACT`). Amazon archives negatives rather than pausing them; the app may display them as paused. |
| `POST /product-ads` | `ads:write` | `productAds[]` | Working. Needs an eligible, non-duplicate ASIN (or SKU with `productIdType: SKU`). |

Rules that apply to all five:

- **Schemas are strict.** Undeclared fields (including `profile_id` in the body) are rejected with `400 invalid_request` before Amazon is called. Get the exact item schema from https://merchjar.com/api/openapi.json; do not improvise fields.
- **Batch of 1 to 1,000 items per request.** Amazon's per-index results come back as-is.
- **HTTP 200 does not mean success.** The 200 body is Amazon's raw batch envelope with `success[]`, `partialSuccess[]`, and `error[]` arrays. Read `error[]` per item and report failures (for example `DUPLICATE`, `PRODUCT_INELIGIBLE`) to the user in plain language. A `502` means the request may or may not have reached Amazon.
- **No idempotency and no automatic retry.** If the outcome is unknown, check the app (or segment preview) for the entity before re-sending; blind retries create duplicates.
- **Eventual consistency.** Created entities appear in browse data and previews after the next projection, not instantly.
- `campaignId` / `adGroupId` are forwarded to Amazon unchecked: send them as decimal strings, never as JavaScript numbers (ids exceed 2^53).

---

## Error Reference

All error responses use a consistent envelope:

```json
{
  "error": {
    "code": "<error_code>",
    "message": "<human-readable message>"
  }
}
```

| Code | HTTP Status | Description |
|---|---|---|
| `unauthorized` | 401 | Missing, malformed, or revoked API key |
| `forbidden` | 403 | Key does not own the profile, or is missing the required scope |
| `rate_limited` | 429 | Too many requests; wait and retry |
| `invalid_trigger` | 400 | Trigger expression failed to compile |
| `invalid_ad_type` | 400 | Unrecognized ad_type value |
| `invalid_action` | 400 | Unrecognized action value |
| `invalid_frequency` | 400 | Unrecognized frequency value |
| `not_found` | 404 | Segment not found or does not belong to the authenticated profile |
| `missing_profile_id` | 400 | Profile ID header is missing |
| `invalid_id` | 400 | Segment ID is not a valid numeric string |
| `parse_error` | 422 | Trigger expression has a syntax error (validate endpoint) |
| `internal_error` | 500 | Unexpected server error |

---

## Examples

**Validate a trigger expression:**
```bash
curl -X POST https://app.merchjar.com/api/v5/segments/validate \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger": "impressions(30d) > 100 AND acos(30d) > 40",
    "ad_type": "keywords"
  }'
```

**Preview keywords with a bid decrease:**
```bash
curl -X POST https://app.merchjar.com/api/v5/segments/preview \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "3456789012345678",
    "trigger": "acos(30d) > 50 AND clicks(30d) > 20",
    "ad_type": "keywords",
    "action": "set_bid",
    "action_params": {
      "direction": "decrease-%",
      "value": 15,
      "source": "value"
    }
  }'
```

**Preview setting budget from a variable:**
```bash
curl -X POST https://app.merchjar.com/api/v5/segments/preview \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "3456789012345678",
    "trigger": "LET $ideal_budget = sales(30d) / 30 * 0.3; spend(7d) > 0",
    "ad_type": "campaigns",
    "action": "set_budget",
    "action_params": {
      "direction": "set-to-$",
      "value": "ideal_budget",
      "source": "variable"
    }
  }'
```

**Preview creating negative keywords from search terms:**
```bash
curl -X POST https://app.merchjar.com/api/v5/segments/preview \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "3456789012345678",
    "trigger": "clicks(30d) > 10 AND sales(30d) = 0",
    "ad_type": "search_terms",
    "action": "create_negatives",
    "action_params": {}
  }'
```

**List all segments for a profile:**
```bash
curl https://app.merchjar.com/api/v5/segments \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "profileid: 3456789012345678"
```

**Create a new segment:**
```bash
curl -X POST https://app.merchjar.com/api/v5/segments \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "3456789012345678",
    "name": "Pause Zero-Sales Campaigns",
    "trigger": "spend(30d) > 100 AND sales(30d) = 0",
    "ad_type": "campaigns",
    "action": "set_state",
    "action_params": { "value": 2 },
    "frequency": "daily",
    "enabled": true
  }'
```

**Update a segment:**
```bash
curl -X PATCH https://app.merchjar.com/api/v5/segments/123 \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "Content-Type: application/json" \
  -H "profileid: 3456789012345678" \
  -d '{
    "name": "Updated Segment Name",
    "enabled": false
  }'
```

**Delete a segment:**
```bash
curl -X DELETE https://app.merchjar.com/api/v5/segments/123 \
  -H "Authorization: Bearer mj_live_abc123def456" \
  -H "profileid: 3456789012345678"
```

---

## API Behavior Notes

Field-level gotchas discovered through production use. These prevent the AI from re-learning the same lessons every session.

| Issue | Detail | Workaround |
|---|---|---|
| Profile spend in cents | `ad_spend_30d` and `ad_spend_30d_usd` return cent values (e.g., `617700` = $6,177) | Divide by 100 before display |
| PATCH requires ad_type | `PATCH /segments/:id` returns 422 without `ad_type` in the body | Always include `ad_type` when patching |
| Frequency: "after every data sync" → `daily` | Segments on the UI "After every data sync" schedule are returned by GET as `frequency: "daily"`; the mode is not represented and `frequency_params` is null | Known bug (reported to eng 2026-06). Don't assume a GET value of `daily` means a true daily schedule. |
| Frequency: read/write enum mismatch | GET returns `manual`, but POST/PATCH reject `manual` (and every "after every data sync" spelling) with `invalid_frequency`. Write accepts only `daily`/`weekly`/`monthly`. | Known bug (reported to eng 2026-06). Cannot set "manually" or "after every data sync" via API; cannot re-save a `manual` segment without changing its frequency. |
| Campaign ACOS is decimal | `acos` field stores 0.314, not 31.4 | Compute manually: `cost / sales * 100` |
| Campaign cost/sales are strings | Numeric fields returned as strings | Use `parseFloat()` before arithmetic |
| Campaign date filtering | `start_date` / `end_date` params are silently ignored | Use `from` and `to` params |
| Campaign ID field | No `id` field on campaign objects | Use `campaign_id` |
| Response array key | Campaign list uses `data` key | Don't look for `campaigns` key |
| Chrome extension: `=` signs | Return values containing `=` trigger content filter block | Return pipe-delimited or pre-processed data |
| Chrome extension: base64 | `btoa()` return values are blocked | Avoid base64 encoding in return values |
| Audit log granularity | Only aggregate counts per segment run — no entity-level detail | Use Amazon Ads console for entity-level audit trail |
