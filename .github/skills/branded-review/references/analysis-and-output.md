# Classification and report contract

## Brand reference

Store private context in the report workspace selected under [report-workspace.md](report-workspace.md), including its skill-only `workspace/` option. Key it by account/marketplace and selected brand scope. Include approved names/aliases, ambiguous terms, exact-query exceptions, owned ASINs, competitor entries when known, source dates and coverage. Keep proposed entries separate from approved entries. Preserve user corrections across reimports and skill updates; resolve conflicts before replacing saved decisions.

Normalize case, Unicode, punctuation and whitespace without discarding the raw input. Use whole terms/phrases by default. An operator can approve contains matching for a distinctive root, including joined model names. Do not apply that policy to ambiguous brands such as “On.” Generic product names and inferred misspellings require review. A website supplies candidate evidence, not automatic query classification.

The conversational mechanism is a compact include/review/exclude proposal before the final split. Ask for brand name plus optional official URL; use the actual reports to surface meaningful aliases, model-only terms and exceptions. Save approved rules with provenance, matching method and account/marketplace scope. Subsequent exports reuse decisions and add only new ambiguities to review. Product-report brand and marketplace metadata can establish a catalog match, but absence from that advertised subset never proves a competing ASIN.

## Row classes

| Class | Meaning |
|---|---|
| own_brand_query | Confirmed own-brand identifier, including brand plus product/category |
| generic_query | Query without own-brand evidence or known competitor identifier, under the approved dictionary |
| competitor_query | Confirmed other-brand query without own-brand identifier |
| cross_brand_query | Own and competitor/another out-of-scope brand both present; retain both flags |
| owned_asin | Reported ASIN is confirmed owned by the selected brand in that marketplace |
| other_asin | Reported ASIN confirmed outside the selected ownership scope |
| unknown | Ambiguous query or unresolved/missing ASIN ownership |

Keep cross-brand queries separate by default; do not count the same row in two summary groups. Generic plus competitor can form a clearly labeled non-brand-query total. ASIN context remains separate from query intent; if showing a broader “brand-related” view, explicitly define its composition. An ASIN not found in a partial list remains unknown.

“Mixed” is an aggregate observation about a target/ad group/campaign containing different row classes. Unknown rows do not become non-brand. Target identity and actual placement are different facts; product targeting may serve on search pages as well as product pages. Do not infer placement solely from targeting configuration.

## Calculations and coverage

Compute ACoS = sum(spend) / sum(attributed sales), displayed as a percent. A $10/$100 row and a $90/$100 row combine to 50%, not a spend-weighted average of row ACoS. If sales is zero, show “No attributed sales” with spend retained; if sales is missing, show unavailable. Preserve negative corrections and explain why a conventional ratio may be misleading.

Each report partition has explicit population totals. Class totals including unknowns must reconcile to imported population totals. Compare a matching campaign report separately and display any difference as unresolved coverage. Never allocate the difference to non-brand, product pages, invalid traffic or waste without evidence.

Record the metric window and source; preserve source campaign/ad-group IDs. A source that lacks target IDs cannot establish a reliable query-to-target join from text alone. Do not sum target totals together with query totals because they describe overlapping activity.

## Deliverables

The review answers: how each traffic class performs; where they are mixed; whether current bids/budgets or goals treat branded traffic appropriately; and what would provide separate control. Compare CPC and purchases/clicks where available, preserving attribution and order definitions. Show unknown goals explicitly. A favorable blended ACoS can coexist with avoidable branded spend; the comparison does not by itself prove that a particular sale would have happened organically.

- A short review: scope, the material finding, coverage limits and the next useful decision.
- Classified data retaining source references, raw text, selected metric columns, class/reason and approval state.
- A reusable brand reference with unresolved entries and corrections.
- A local HTML report when file generation is available; otherwise a readable table plus export. State the actual delivered format.
- A campaign-change proposal only when requested or useful, following migration.md.

Use the same calculated values across the report and exports. The default HTML is an executive report: scope/date, branded ACoS, non-branded ACoS, account total, one takeaway and a next decision. Spend/sales sit beneath each headline number. Qualify account totals as the supplied export until independently reconciled. Keep a compact visible coverage line; place query tables, mixed-campaign details and source evidence behind a disclosure or in supporting files. Additional charts do not automatically strengthen the report. Escape customer text; do not load private data into remote scripts or add telemetry.

Default presentation reuses the actual reviewed website wordmark and Inter font, cream background and white cards. Use muted teal #95B9B1 for brand searches, warm stone #D9D7CE for non-brand, ink #22212B for totals, slate #A8B7C6 for own-product defense, lime #D8E681 for takeaways and cobalt for actions. The compact result board, spacing and hierarchy matter as much as color. The bundled renderer embeds its local assets for offline use. No fake sync controls or always-on-dashboard claim; refresh requires new inputs or a requested connected pull.

## Behavioral acceptance cases

Use actual export fixtures before release. Include brand-plus-product, ambiguous root, cross-brand comparison, owned/unknown/numeric ASIN, reseller ownership, changed catalog, zero sales, missing sales, mixed currencies, duplicate uploads, different attribution columns, pre-existing negatives and no-history data. Verify totals and review decisions, not just the wording of this file. Include cases with separate user-supplied goals and missing goals; never silently apply the demonstration's targets.
