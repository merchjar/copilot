# Report, planning and creation handoff

Brand Traffic Review owns traffic classification, the recommended separation strategy and legacy cutover. Connect owns API access and the shared naming preference. Campaign Naming guides a new convention when needed. Create Campaigns constructs the approved destination entities. These are components of the same conversation.

Build the full product-group proposal first using [product-structure.md](product-structure.md). Begin with a shared branded campaign budget, category ad groups and approved brand Phrase terms; use the user's selected grouping and match choices. Separate own-product defense shows explicit ads versus targets. Suitable existing campaigns remain for non-brand. A historical first wave is not the whole account plan. Read-only configuration for one group does not verify the others. Pass the reviewed advertised products, exact group membership and positive targets to Create Campaigns; preserve the user's choices instead of restarting its generic launch defaults.

The planner's `brand-campaign-plan/2` is a structure proposal, not an execution manifest. Review its `migration.end_state_roles`, complete `coverage_ledger`, staged waves, transition settings and cutover gates before construction. Its default is a new branded candidate plus a retained existing non-brand campaign. Respect each destination's `action`; never send a `retain-existing` entry through create. Query evidence does not replace current discovery or product targeting. Convert only the approved new entities into the creation manifest. Existing-source exclusions require their own delivery/coverage gates and authorization.

Use Connect 1.5+ for detailed planning and Creation 1.3+ for construction. Campaign Naming 0.4.0+ is optional; an existing naming convention can be consumed directly by Connect's offline helper. Check installed versions. Uploaded-report analysis and structural suggestions need none of these components.

## Build the planning evidence

Without connection, run `scripts/plan_campaigns.py --analysis PRIVATE/analysis.json --output PRIVATE/suggestions.json --markdown OUTPUT/suggestions.md` only when a separate suggestion artifact is useful. It returns `brand-structure-suggestions/1`, with role-level suggestions and the connection next step. It does not return destinations, keyword seeds, a negative list or a cutover ledger. A short chat suggestion is usually enough.

For detailed planning, first use Connect to resolve the profile and successfully read the required current campaigns, groups, Product Ads, positive targets and negatives. Retain private JSON response receipts, including every page. Verify both campaign and group negative scopes, keyword/product types, parent states and export/report account mapping. A read permission error or incomplete initial sync is a setup gap, not a reason to ask for bulk files.

Use the [current-configuration read examples in connected.md](connected.md). Campaigns, ad groups and Product Ads are read through segment preview, which is permitted in a read-only session despite using POST. Do not stop after listing profiles and counting targets, or claim configuration is unavailable because there is no GET campaigns endpoint.

Save an agent-authored `brand-connected-context/1` JSON beside the private read receipts. Required fields: `provider: "merchjar"`, `source_account_id` matching the analysis, `profile_id` as a string, `currency`, `account_mapping_verified: true`, `retrieved_at` as an ISO timestamp with timezone, and `scope` containing the successfully read `campaign_ids` and `ad_group_ids`. Its `reads` object has `campaigns`, `ad_groups`, `product_ads`, `targets` and `negatives`. Each entry records `status: "complete"`, exact `profile_id`, `pagination_complete: true`, `receipt_file`, SHA-256 `sha256` of that file, and verified integer `rows`. A verified empty result also needs `empty_verified: true`. Never manufacture this receipt from an uploaded file, an API key's presence or an error response.

Then run `scripts/plan_campaigns.py --analysis PRIVATE/analysis.json --connected-context PRIVATE/connected-context.json --output PRIVATE/campaign-plan.json --markdown OUTPUT/campaign-plan.md`. The helper validates identity, declared coverage and receipt hashes before returning detailed historical planning evidence. This is a local consistency check, not API authentication or proof that the receipts are fresh or semantically complete. The skill must inspect current responses and reconcile the historical candidates against them before presenting the detailed plan. No account objects are created, budgets invented or keywords automatically approved.

The helper selects no pilot automatically. An explicitly supplied historical source group can support a first review after the full structure is proposed. Same-ad-group product associations are candidates; a multiple-product group does not establish which product converted for a query. Keep approved brand Phrase terms as the starting branded targets. Review products and current eligibility before construction. Source periods and current configuration may differ.

Use this evidence to write the final plan, not as an instruction to duplicate every mixed campaign. A pilot can be broadened after review. Keep the complete queue available without putting it into the executive report.

## Naming integration

Resolve `campaign-naming.json` beside the active Connect configuration using `campaign_naming.py resolve`, then render proposed names from real planned facts. Follow Connect's shared preference contract. Profile convention precedes global, which precedes a legacy structure's naming. Explicit one-time instructions take precedence without changing stored defaults.

Pass `method: KW` for manual keyword destinations and their actual `targeting` (for example Exact). Pass the agreed `purpose`, brand, market and actual advertised ASINs only when known. Apply stored vocabulary as specified by Connect. If the convention omits purpose and creates collisions between brand and non-brand, propose stable role suffixes for this plan; do not rewrite the default. Names and ad-group names appear in the approval table.

An uploaded-report account ID is not automatically a Merch Jar profile ID. Resolve the mapping with account/marketplace evidence before reading preferences or making requests. A proxy rehearsal must use independent destination products, terms and IDs. Source-account assumptions never become someone else's defaults.

## Explicit plan supplied to Create Campaigns

Keep a private JSON manifest using the following information (the AI assembles it from conversation; the user does not fill a template):

- `analysis`: selected source account, file hash/date or API receipt, brand-reference revision.
- `destination`: verified Merch Jar profile ID as a string, marketplace, currency, timezone; whether this is a proxy.
- `strategy`: measure-only, dedicated-brand, parallel, new-nonbrand or cleanup-in-place; chosen scope and rationale.
- `goals`: separate branded/non-brand intent and target values with confirmed/proposed status. Unknown values stay null.
- `campaigns`: stable local keys, new/existing IDs, role, campaign and ad-group names, actual products/SKUs and eligibility evidence, positive seeds/match types, budgets and bids with their basis, individual states, naming preference revision.
- `exclusions`: keyword/product value, match type, exact campaign/ad-group destination, current coverage status, example affected queries and cutover dependency. Classification permission is not exclusion permission.
- `brand_exclusion_list`: saved account/marketplace list path, approved revision, applied entry IDs, already-covered entries, unsupported/not-applicable entries and unresolved exceptions. Every new non-brand campaign resolves this list through [brand-exclusions.md](brand-exclusions.md); it never applies to branded or own-product defense campaigns.
- `legacy`: exact retained IDs and proposed changes, including none; before/after configured budget totals.
- `approval`: exact reviewed revision and operation scope. Separate paused construction from source exclusions, enablement and saved preferences.
- `receipts`: stable local-key-to-returned-ID mapping, per-item response, readback state and unresolved outcomes.

Creation takes this as the explicit-structure entry path. Reuse its current launch validation, account-local dates and per-item result handling. Do not save a special-purpose separation plan over a user's general launch defaults. Use real supported keyword seeds; unknown seeds remain unresolved rather than silently inserting dummy keywords into a promised separation result.

## Exclusion and cutover ownership

New non-brand destinations can carry reviewed branded negatives during paused construction. Legacy exclusions remain pending until the new destination is ready and their own scope is approved. Verify current keyword negatives including broader phrase coverage. Treat own-ASIN traffic separately and confirm whether to exclude it. Never apply campaign-level ASIN negatives through an endpoint supporting only ad-group scope.

The offline `negative_coverage(proposed, existing)` helper in `scripts/plan_campaigns.py` checks confirmed normalized snapshots conservatively. Resolve profile/scope and filter by verified own and parent states before calling it; the helper compares the supplied normalized state and does not fetch parents. Each item carries `profile_id`, `campaign_id`, optional `ad_group_id`, `type` (KEYWORD or PRODUCT), `value`, `match_type`, and `state`; existing items also carry `id`. A campaign negative can cover child groups, but a sibling-group negative cannot. The helper recognizes exact normalized matches and whitespace-delimited phrase coverage, not every Amazon close variant. `not-covered-in-supplied-snapshot` becomes a missing-negative finding only after complete fresh listing coverage is established. API permission errors or incomplete pages never become an empty negative list.

Record each request before sending. A timeout or partial response makes affected results unknown; stop their dependents and reconcile exact IDs before retry. On a rerun, reuse confirmed created objects and skip already-covered negatives. HTTP success does not prove creation, effective delivery or successful migration.

The final receipt distinguishes: plan ready, created paused, eligible/ready, enabled by human, source exclusions applied, and observed traffic separated. Do not collapse those states into “done.”
