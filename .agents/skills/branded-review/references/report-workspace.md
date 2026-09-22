# One report throughout the transition

The default report has three tabs. Deliver it as soon as the search-term analysis is useful. Do not make the user ask separately for a visual proposal.

1. **Performance:** lead with a data-specific finding beside the Campaign plan action. Keep branded ACoS, non-branded ACoS and overall ACoS together without decorative bars. Pair the text-search columns visually and treat overall as a quieter reference; clarify its scope beside the numbers. A smaller white ASIN card follows the same order: your ASINs, other/unknown ASINs, then all ASINs, each with ACoS, spend and sales. Without ownership evidence, show the ASIN total and two “Need ASIN list” placeholders. Prompt for the brand's ASIN list or Amazon's Advertised product report. A partial list leaves unmatched ASINs unknown, with that limitation beside their result and a request for the complete catalog. Never relabel unmatched ASINs as competitors. A supplied complete catalog permits “Other ASINs,” which still does not prove a competitor relationship. When no ASIN traffic exists, show that without requesting an unnecessary upload. Keep the separate-goals note brief. Collapse methodology and spelling examples; show unresolved spend on the disclosure summary.
2. **Campaign plan:** included without a connection. Show the proposed route: keep existing campaigns running, add branded and own-product defense campaigns, then retain suitable existing campaigns for non-brand after separate delivery reviews. Use muted teal for brand searches, warm stone for other searches, slate for owned-product defense and ink for totals across every tab. Reserve lime for takeaways and next actions. Align all six cards in columns 2 and 3 at equal height on desktop; let mobile content flow naturally. Keep supporting negative-list detail and the searchable historical campaign inventory in disclosures. Provide visible All campaigns and Brand + other searches filter buttons with accurate counts. Wrap campaign names and use stacked inventory rows on mobile, with IDs in secondary detail. The inventory is not a live configuration map. A clean account may need only measurement; present the proposal as optional, not a mandatory rebuild.
3. **Setup & progress:** emphasize the next outstanding action from saved evidence, with later steps subordinate and one short request to copy into Copilot. Use an available Merch Jar connection or offer setup once. Read the current products, targets and negatives; resolve actual campaigns, settings and changes. Save the detailed plan and each product group's progress here. Read-only connections can plan and check progress, but cannot apply changes. The copy button only copies text, and the displayed next step never authorizes or advances account work.

Use ordinary prompts such as “Help me generate a brand report,” “Plan the changes for my account,” and “Check how the new campaigns are doing.” Keep the helpers and file management behind the scenes.

Performance includes a spend-versus-attributed-sales share chart for classified text searches only. ASIN, blank and unresolved rows stay outside this chart. Use the compact ASIN comparison beneath it. **Your brand lists** shows editable aliases, spelling rules and owned ASINs. Its drafts do not change metrics; follow [report-preferences.md](report-preferences.md) when edits return to Copilot. Privacy reports omit identifying list data.

## Choose and retain the private workspace

Keep two locations distinct: the authorized session root determines which connection may be inspected; the private report workspace holds customer data and output. A shell directory change does not change either location.

Use an existing private workspace when present. In a full project, prefer a private output folder outside managed skill resources. If only the skill folder is accessible, use its dedicated `workspace/` subfolder. Keep customer files out of scripts, references, assets and examples. During an update, preserve the private workspace before replacing installed resources; never distribute it inside a skill download.

Adding the full Copilot authorizes checking that newly supplied root. Keep the same report, reference, catalog, state and baseline paths. Do not move or duplicate them just because the connection root changed. On each refresh, pass the currently authorized root to `--workspace`; never search a parent or global configuration to infer expanded access.

## Update the same artifact

The upload and connected report commands now save the HTML, a `.workspace.json` progress file and a `.workspace.baseline.json` copy of the original analysis. Keep all three in a private, user-owned output directory. Keep the approved brand reference, owned-ASIN catalog, exclusion list and account receipts alongside them. These are working files, not additional attachments the user must manage in chat.

Reuse the same absolute HTML path and `--state` path when adding product data, changing reviewed rules or refreshing performance. The first analysis is preserved and each new analysis gets a dated snapshot entry. Different periods are explicitly not a like-for-like comparison. Do not claim a before/after improvement without matching scope, attribution maturity and a suitable comparison period. A rule/catalog change requires renewed plan review. A different account or brand needs a separate report.

For an existing analysis or a progress-only update:

```text
python scripts/report_workspace.py --analysis PRIVATE/analysis.json --html-output OUTPUT/review.html --state PRIVATE/review.workspace.json --workspace AUTHORIZED_ROOT
```

Add `--evidence PRIVATE/check/progress.json` to save a verified connected check. Preserve the existing state; do not manufacture progress by overwriting it. Use the returned absolute report artifact for delivery. An older HTML file can be upgraded from its existing analysis without recalculating or altering the saved brand reference.

Before a pilot, follow [product-structure.md](product-structure.md) and add `--product-groups PRIVATE/product-groups.json`. The report saves the proposed full grouping and shows campaign/ad-group counts, included ASINs and held products. The same saved terms/ASINs are visible on both planning tabs. A changed brand/catalog definition moves the prior grouping into `prior_product_groups` and requires reconciliation; it never silently drops changed products. Saved rollout details remain separate from the full product proposal and do not establish account-wide coverage.

The interactive planner changes budget/ad-group choices and defense pairing in a local draft. Import Copy choices or Save report with choices through `planning_options.py`, then pass the updated grouping file to the same report. Setup & progress shows the existing/proposed/next-action transition alongside the saved rollout evidence. A draft change flags the saved actions for review; it does not advance campaign progress.

`--workspace` refreshes local connection availability in the presentation. It makes no API call, does not change source analysis or its baseline, and does not create a performance snapshot by itself. Configured credentials still require a successful scoped read before detailed planning or progress claims.

An HTML file is a saved view. Opening it does not fetch data, watch campaigns or apply anything. On a requested follow-up, Copilot makes fresh reads and regenerates the same file. A recurring check would require a separate user-requested scheduler; this skill does not create one.

## Reusing the product list

Both upload and connected report helpers accept `--catalog PRIVATE/owned-asins.json --marketplace MARKETPLACE`. This normalized private catalog uses the same scope as the exclusion-list helper:

```json
{
  "scope": {"account_id": "selected-upload-account", "brand": "Example Brand", "marketplace": "AMAZON.COM"},
  "source": "Owner-confirmed catalog, with original file retained privately",
  "ownership_verified": true,
  "complete": false,
  "owned_asins": ["B000000001"]
}
```

Normalize supplied list columns yourself and verify ownership, account and marketplace. Do not ask customers to author JSON. An advertised-product subset stays partial; absent products are not automatically competitors. Preserve prior confirmed ASINs and flag conflicts or removals for review. Reuse the catalog and brand reference on connected refreshes instead of silently dropping their classifications. For file-to-API reuse, verify and save `merchjar_profile_id` in the scoped brand reference. Do not guess that mapping from an account name.

## Connected progress evidence

After a successful scoped read using Connect, normalize the actual receipts into a progress bundle. The helper validates local consistency and hashes, not Amazon authentication or the correctness of the agent's interpretation. Inspect the raw results yourself. Never set a check true merely to advance the display.

Required bundle fields:

- `identity` and `rules_hash`: copy from the saved workspace; they bind the check to the current account, currency, brand and rules.
- `profile_id` (string), `account_mapping_verified: true`, `checked_at` (ISO timestamp with timezone), `read_only` (boolean).
- `plan_revision` and `plan_reviewed`: current proposal revision and whether its products, coverage and transition have been reviewed. This is not account-write approval.
- `receipts`: `{file, sha256, profile_id}` objects. Store receipts under the bundle's folder and link exact raw reads or execution/readback records. Never include credentials or authorization headers.
- `current_plan`: optional rows with `existing_campaign`, `products`, `change`, `next_action`. Use human-readable values supported by the current account reads. Keep exact IDs in the detailed private plan.
- `current_campaigns`: optional checked campaign records with string `id`, `name`, `state` (ENABLED/PAUSED/ARCHIVED) and `receipt_indexes` linking configuration reads. The transition view labels these states as of the saved check. Missing records are unknown, not proof that campaigns are absent or paused.
- `waves`: the full set of saved product groups, including earlier groups, each with stable `id`, readable `name`, `source_campaign_ids`, and separate `branded` and `defense` objects when relevant.

Each role links `receipt_indexes` and stores actual `campaign_ids`, `created` and `enabled_by_human`. Do not equate a paused create receipt with enablement. An `observation` records `impressions`, `spend`, `sales`, `period_start`, `period_end`, `data_through`, `checked_at`, `complete` and `after_launch`. Only include an observation for the exact destination IDs and a complete post-launch period; allow for reporting delay and recent attribution changes. The default display asks for a fresh check when the saved read is over 24 hours old or source data is more than one calendar day behind. That freshness rule is not a performance threshold.

Progress distinguishes not created, paused, awaiting a check, no impressions, delivery started, and ready to review negatives. Impressions alone never establish readiness. Before the last state, record evidence-backed `checks` for `products_verified`, `negative_coverage_verified`, `replacement_coverage_reviewed`, `observation_window_reviewed`, `combined_results_reviewed` and `rollback_agreed`. Agree an appropriate observation period and business criteria in the actual plan; there is no universal impressions, sales or ACoS cutoff. Brand and defense can reach different states.

“Ready to review” is a recommendation for the next decision. Applying changes still requires the reviewed exact plan and the applicable authorization. Use Naming and Create Campaigns for their existing roles. After approved source exclusions, set `negatives_verified` only with a complete `negative_readback` containing exact `ids`, `source_campaign_ids`, `checked_at` and `complete: true`, linked to the saved readback receipts. This records the check's date rather than claiming those settings remain unchanged forever. Continue to measure combined results and actual traffic separation; negatives do not guarantee traffic transfer.

Keep the reusable negative list updated through [brand-exclusions.md](brand-exclusions.md). New non-brand campaigns use its latest approved entries, supported types and reviewed exceptions before human enablement. Updating a list file does not apply negatives to existing campaigns.
