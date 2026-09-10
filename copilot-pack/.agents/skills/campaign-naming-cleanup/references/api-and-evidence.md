# API and evidence notes

Use the installed Merch Jar Connect client and current public contract. The notes below describe verified surfaces, not a replacement endpoint catalog.

## Read-only inventory

Campaign, ad-group, product-ad and target reads can use POST /api/v5/segments/preview with datasets `campaigns`, `ad_groups`, `ads` and `keywords_and_targets`. Include profile_id, trigger, action, action_params, page and per_page. A preview with action set_state and action_params {"value": 2} is a read-only preview; it does not pause anything.

Do not assume GET /campaigns exists. Use the connection skill's supported trigger syntax. Campaign-name filtering can narrow child datasets; use returned campaign IDs to retain exact identity. The `ads` dataset can be large, so scope requests by campaign and paginate. Do not assume `asin` or `campaign id` are valid DSL properties.

Campaign rows include campaign_id, name, state, budget and campaign_settings. Product Ad rows expose campaign_id, ad_group_id and creative_products_product_id / creative_products_product_id_type. The ASIN in those product-ad fields is an advertised product. Target rows expose targeting and match-type information; inspect the actual returned fields instead of assuming old campaign labels describe them.

Aggregate advertised ASINs across all relevant Product Ads/ad groups. Keep paused product associations visible in a paused campaign audit, and distinguish active/paused/archived associations rather than silently picking one. If the association set differs by state, expose that distinction before naming.

Track page progress and deduplicate by entity ID. Pagination totals can lag newly created objects: a live read returned more rows than the total metadata. If row counts and total disagree, reconcile coverage with subsequent pages/current reads and do not report total metadata as verified inventory. Stop and report repeated/no-progress pages.

GET /api/v5/segments with the profileid header reads the available Segment definitions. Inspect name selectors and the current enabled state. This is not a guarantee that every external or legacy dependency is discoverable.

## Change names

PATCH /api/v5/campaigns/{id}, profileid header, body {"name": "approved name"}.

The September 10 fetched contract allows 1–255 characters. Check the live contract if it changes. Inspect per-item success/error/partialSuccess envelopes; an HTTP success alone is insufficient.

Preview/readback queries must find both old and proposed names and then reconcile exact campaign IDs. Renaming can invalidate a name-based lookup, so retain the ID map before the first write. Preserve budget, state, placement adjustments and strategy.

This skill neither creates automations nor enables campaigns. It performs reviewed one-time name changes.

## Data-led naming boundaries

Campaign targeting mode does not establish the full set of match types or business purpose. A product-target ASIN is not the advertised ASIN. Product titles may require a trusted catalog or user mapping; no title is better than an invented one. Existing historical Product Ads do not prove that an ASIN remains eligible for creating new ads.
