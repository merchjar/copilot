# Merch Jar planning and execution

Load the installed current merchjar-connect skill only for requested connected work. Use its API client and private configuration. Read the live [OpenAPI contract](https://merchjar.com/api/openapi.json) and relevant installed API/DSL references before building requests. A local source copy may be older than the live contract.

Before offering installation/connection, reuse established session context and inspect the authorized project root, not a shell directory changed to run a helper. `connection_context.py` checks only that accessible root and does not override an already established connection elsewhere that the user has authorized. A CSV-based report can have an available connection. Configured credentials mean verify the existing connection; an access failure means name the exact missing capability. Neither situation means ask the user to add an already available Copilot folder.

Reporting needs `profiles:read` and `segments:preview`. The current target/negative listing additionally needs `targets:read`, which older keys may lack even when reporting works. Creation uses the scopes declared by each current endpoint, including `campaigns:write`, `ad_groups:write`, `ads:write` and `targets:write`; product-negative creation uses `negative-targets:write`. On a missing-scope 403, name the specific scope and guide a private configuration update through Connect. Do not treat the error as absent endpoint support, print credentials or ask the user to paste a key into the report. Finish the report and structural suggestions; detailed planning stays pending until the required reads succeed.

## Read path

The reason to connect is current configuration for a detailed campaign/negative/transition plan, followed by an approved implementation path. Reuse the reviewed brand reference. Offer connection after the useful free report, or optionally during an export wait. Do not request bulk downloads or generate bulk-upload sheets as an alternative path.

| Upload-only result | What the connection can add |
|---|---|
| Period-specific report from CSV | Requested historical reads with consistent selected periods, subject to sync/coverage verification |
| Targeting-template snapshot | Fresh supported target/negative reads, entity identity and configuration context for a concrete change plan |
| Advertised subset from product template | Supported Product Ad/campaign/ad-group context, verified at runtime; not a complete Seller Central catalog promise |
| Suggested campaign roles | Detailed campaign/negative/transition plan, followed by approved supported creation and readback |
| Suggested separate goals | Reviewed automation logic and repeatable measurement; new automations disabled for human enablement |

Verify returned fields and scope before promising a specific data join. File support for an ad product does not establish connected execution support.

Resolve the named profile, marketplace, currency and timezone. Read historical search terms through read-only segment preview with `action: set_state` and `action_params: {"value": 2}`. This endpoint does not execute a state change. Do not use `create_negatives` for a historical performance pull: it filters out already-negated rows and their prior spend.

Use the bundled read-only adapter with the installed Connect client:

```text
python scripts/connected_report.py --client PATH/merchjar-connect/scripts/merchjar_client.py --profile SELECTED_ID --start YYYY-MM-DD --end YYYY-MM-DD --brand "Brand name" --output-dir PRIVATE/read --html-output OUTPUT/review.html
```

It lists accessible profiles, reads every search-term and campaign preview page for one exact date range, validates page counts and global metric totals, and passes normalized search terms through the same classifier/renderer used for uploads. The account card uses same-period campaign totals; any coverage gap remains visible and is never labeled non-brand. Preview money fields are currency units, unlike profile summary spend fields in cents. Inspect a changed response schema instead of guessing a conversion.

Optional `--brand-reference PATH` reuses saved rules. An uploaded reference must first have its account-to-profile mapping verified and stored as `merchjar_profile_id`; the adapter refuses an unverified mapping. It saves private raw read receipts and normalized data. No key is copied and it has no write endpoint. A read error stops the report; preserve the receipts and diagnose before a fresh consistent pull.

For an empty result it generates an explicit zero-activity coverage report, without inventing performance or campaign seeds. The executable adapter supports the current Sponsored Products preview shape. Other ad products require a verified adapter and separate partition.

The example bodies in queries.json are read-only preview templates, not fixed reporting-date policy. Substitute the selected consistent period and profile. Follow all pages, respect rate limits, inspect actual metric fields and reconcile totals. Do not repeat page-global totals in the row sum. Data availability does not prove freshness or attribution maturity.

Read fresh configuration using supported entity/preview paths. `GET /targets` accepts `negative`, campaign/ad-group filters, paging and serving state; omission of `negative` includes both. Verify campaign-level negative coverage empirically before assuming one listing is complete. Resolve a read-coverage gap through connection permissions, sync status or supported scope, not a bulk export detour. Record successful current reads in the private connected-context receipt described in handoff.md before running the detailed planner.

### Current configuration is available through read-only preview

There is no `GET /campaigns` route in v5. That does not mean campaign configuration is unavailable. Use `POST /api/v5/segments/preview` with `ad_type` set to `campaigns`, `ad_groups`, or `ads` (Product Ads). A POST to this preview endpoint reads data; it does not execute the supplied action. Do not request write access or disable a read-only guard to use it.

Start with a small access probe, writing this body to a private JSON file and replacing the selected profile:

```json
{"profile_id":"SELECTED_PROFILE","trigger":"1 = 1","ad_type":"campaigns","action":"set_state","action_params":{"value":2},"page":1,"per_page":1}
```

```text
python PATH/merchjar_client.py request POST /api/v5/segments/preview --body-file PRIVATE/campaign-probe.json
```

The installed client expects the full `/api/v5/...` path. Preview uses `profile_id` in the JSON body, not an omitted profile or a different account's header. After the probe, scope reads to the proposed product group, for example with a verified campaign-name filter, join by returned IDs, and follow all pages. Scope Product Ad reads by campaign to avoid unnecessary account-wide work. Inspect actual fields for budgets, targeting mode, campaign settings, parent states and advertised products; do not promise a field the response lacks.

If a read fails, retain the exact method, path, profile, sanitized error and response status. Distinguish an invalid request, local guard rejection and server scope denial. A sample success establishes access only. An inventory count of negatives does not establish which proposed exclusions are already covered.

## Contract checked 2026-09-20

| Operation | Contract facts |
|---|---|
| POST /campaigns, /ad-groups, /product-ads | Sponsored Products creation; use current schema and selected profile |
| POST /targets | Positive targets plus separate negative KEYWORD branches accepting campaignId or adGroupId. Use verified EXACT/PHRASE behavior; BROAD in the enum is not proof Amazon permits negative broad |
| POST /negative-targets | Body key targets; negative product branch, adGroupId, PRODUCT_EXACT ASIN |
| GET /targets | Current positive/negative target listing; complete pagination required |
| POST /bulk-actions | Existing-entity changes, including negative entity types; not an arbitrary negative-create route |

Schema presence is not live end-to-end acceptance. Do not promise Sponsored Brands writes or campaign-level ASIN-negative creation through these endpoints. Recheck future support rather than assuming it ships on a date.

Reuse create-campaigns for supported construction details and saved naming/structure choices. It explicitly excludes existing-account restructuring as its main workflow. This skill owns destination mapping, legacy eligibility and negatives. Do not install or bundle every optional skill for upload-only use.

## Execution evidence

Prepare a reviewable manifest, then obtain only missing authorization for that exact operation. Stage new campaigns, ad groups, Product Ads and targets paused as appropriate; document generated target own-state versus effective parent state. Automations remain disabled, and a human enables them.

Check item-level results and read back IDs, associations, budgets, bids and states. No automatic create retries: an empty projection or timeout can conceal successful creation. Preserve partial success and block dependent writes on unknown parents. Do not mark a campaign ready without a product association and applicable eligibility checks.

This release focuses on traffic classification, reporting, separate goals and control of branded spend. NTB field discovery and conversion-path integration are not connection prerequisites or implementation tasks.

For real-account testing, analysis source and execution destination are independent inputs. Never send source-customer IDs into a lab account, copy another seller's Product Ads blindly, or claim a proxy proves actual delivery/performance. Use lab-eligible ASINs and freshly created lab IDs, and retain a mapping. A customer analysis permission does not establish permission to publish its data.
