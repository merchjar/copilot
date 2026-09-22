# Report intake

Start with the original export. Do not require a custom template before inspecting the supplied data. XLSX, CSV and TSV support depends on the client's actual file tools; preserve ASINs and entity IDs as text.

## Minimum review

Request the default Search term template and the brand names in scope. In the Amazon Ads reporting template chooser, select Search term → Use template, select the intended account and date range, generate, wait for completion and download the original CSV. Use the existing templates; do not ask the operator to create a custom template. Confirm available account/ad-product filters instead of inventing columns. Retain any marketplace, timezone, attribution and export metadata the template supplies. Recent conversions remain provisional rather than requiring an unexplained universal delay.

Read the actual export period and current template options; older report-specific lookback statements must not become onboarding limits for this workflow. Some reported search terms are ASINs; preserve them separately. Missing or suppressed query detail does not establish full account coverage.

## Additional inputs

| File | Use | Limitation |
|---|---|---|
| Matching campaign report | Reconcile account/campaign totals with search-term coverage | Same dates, currency, ad product and attribution required |
| Brand-owned ASIN list or Seller Central listings export | Establish candidate ownership and product context | A seller may list other brands; confirm ownership and child-variation coverage |
| Default Advertised product template | Brand, ASIN, marketplace and campaign/ad-group product associations | Advertised subset; request when product-row coverage matters, not for every first run |
| Default Targeting template, if already supplied or requested for a specific observation | Reported target text/ID, match type, bid and state | Does not establish complete negatives or live eligibility. Detailed planning uses Merch Jar current reads |

For Seller Central, look for All Listings Report in Inventory Reports. UI labels and available columns differ; do not invent an exact menu path you have not verified for that account. A pasted list is a valid alternative. Retain leading zeros, deduplicate marketplace+ASIN and keep SKU mappings. Distinguish advertised, targeted and purchased ASIN columns.

Ask for Seller Central data only when non-advertised products or unresolved ownership materially affect the next decision. The Advertised product template is the easier default enrichment when it supplies the necessary brand/marketplace fields. Unmatched ASINs remain unknown, not competitors.

For current configuration and negatives, guide Merch Jar connection and follow [negative-inventory.md](negative-inventory.md). Do not request Bulk operations downloads. The Targeting performance template cannot establish negative absence. If the user has already provided a configuration workbook, use it only as supporting observation; it does not replace the connected detailed-planning path or query performance.

When supporting exports cover a different period, use them for product identity and reported structure only. Never add their spend to the search-term total or use them to validate a different-period total. If search terms lack Target ID, a query cannot be assigned to one keyword merely by joining on ad-group ID or text. Repeated keywords can be legitimate across products; strengthen an overlap candidate with shared advertised-product evidence, and check current negatives/eligibility through Merch Jar before proposing application.

If a bulk workbook contains customer search-term rows with spend and sales, those can supply the analysis. If it only has keyword/target totals, use it for structure and request the missing search-term report. Never substitute target text for the shopper's query.

## Normalize before calculation

Filter to the selected advertiser account and currency before aggregating. Literal `="..."` wrappers around IDs are text formatting, not formulas to execute. Default templates can supply Total cost and Sales (total attributed sales), plus promoted/halo subsets; do not sum all sales columns together. Ad product, marketplace and attribution window may be absent. Preserve blank queries as unreported-query rows instead of guessing their identity or treating them as totals. Row date ranges may vary; do not infer daily granularity or the report's exact configuration from their envelope.

Keep raw values and source file/sheet/row. Map: ad product, account, marketplace, currency, date range, campaign/ad-group/target IDs when supplied, customer query or ASIN, spend, clicks, impressions, attributed sales and purchases. Missing optional fields remain missing. Missing sales prevents ACoS; it does not prevent a labeled spend-only review.

Record which sales column was selected: attribution window, click/view basis, total versus same-SKU/halo, and attribution model. Do not add 7-day and 14-day sales, total and subset sales, or last-touch and multi-touch metrics. Do not blend incompatible report partitions. Do not average row ACoS.

Detect summary rows, repeated/overlapping exports and daily-versus-summary duplication. Use source identity and grain to establish duplicates; identical-looking performance values alone are not proof. Keep an exclusions/coverage receipt. Do not silently discard conflicts, malformed monetary values, negative adjustments or unknown IDs. Avoid one-to-many joins that duplicate spend. Aggregate metric tables separately before any join.

## Sources

Checked 2026-09-20: [console reporting](https://advertising.amazon.com/library/guides/advertising-console), [SP search-term report](https://advertising.amazon.com/help/G3HEFZYWZF84NPS9), [report and bulk-file purposes](https://advertising.amazon.com/library/guides/measure-improve-campaigns), [SB reports](https://advertising.amazon.com/library/guides/sponsored-brands-what-to-know). A real-export acceptance run still determines the supported headers and client-specific instructions.
