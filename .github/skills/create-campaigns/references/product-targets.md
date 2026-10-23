# Product-target ad groups

Research and Exact each hold a keyword group and a product-target group. This file covers where product-target seeds come from, how to build the requests and how to read the result back. Load Connect's API reference for everything else.

## Seeds from search terms that sold

A search term that is an ASIN (`b07kw6rmxq`) means the ad appeared on that product's detail page. Books show a 10-character ISBN instead.

1. Preview `search_terms` with the lookback the user approved, for example `orders(60d) >= 1`, and save every page. Scope it with `campaign name contains` when the account is large.
2. Preview `ads` for the same campaigns and save the pages. Product Ads carry the advertised ASIN in `creative_products_product_id`; `asin` is not a DSL property, so filter by campaign, never by ASIN.
3. Optionally preview `targets` for the same campaigns, to show seeds the product already targets.
4. Run the offline helper:

```text
python scripts/product_targets.py seeds --asin ASIN --window 60d --search-terms ST_PAGE.json [...] --ads ADS_PAGE.json [...] [--targets TARGET_PAGE.json ...] [--owned ASIN,ASIN] [--min-orders 1]
```

The output separates:

- `seeds`: ASINs that sold in ad groups advertising only this product, ranked by orders, with sales, clicks, cost, cost per click and any existing product target on them (`already_targeted`).
- `shared_group_asins`: ASINs that sold in groups shared with other products. The search-term report has no product column, so a sale there can't be tied to this product. Show them as evidence; use them only if the user picks them.
- `owned_asins`: ASINs the user advertises elsewhere (from `--owned`). Targeting your own listing is a separate purpose, so ask.
- `unconfirmed_ad_groups`: groups that looked single-product on a partial ads pull. Two products on any page prove a group is shared; one product proves nothing until every page is read. Read the remaining pages before treating these as product-specific.

Search-term pages must be complete; the helper rejects missing pages. The advertised ASIN is never a seed.

## Category IDs

There is no category lookup in the Merch Jar API. A `targets` preview shows existing category targets in `target_details_product_category_id` and `target_details_product_category_resolved`. Use those, or an ID the user gives. Never guess.

## Requests

Build product-target bodies with the helper; it emits the strict schema, always PAUSED, without a bid:

```text
python scripts/product_targets.py targets --ad-group-id GROUP_ID --match-type PRODUCT_EXACT --asins B0...,B0...
python scripts/product_targets.py targets --ad-group-id GROUP_ID --match-type PRODUCT_SIMILAR --asins B0...,B0...
python scripts/product_targets.py targets --ad-group-id GROUP_ID --category-ids 1981397031
```

Each result has `body` (send as `POST /api/v5/targets` with `--profileid`) and `index` (map each response item's `index` back to the ASIN or category). One product item looks like this:

```json
{"adGroupId":"34427817396613","adProduct":"SPONSORED_PRODUCTS","negative":false,"state":"PAUSED","targetType":"PRODUCT","targetDetails":{"productTarget":{"matchType":"PRODUCT_EXACT","productId":"B07YFHG3PD","productIdType":"ASIN"}}}
```

Category items nest `productCategoryRefinement` twice, as the live contract requires, and carry `matchType: MULTISIGNAL_BROAD`. Amazon's response writes the ASIN as `productTarget.product.productId`; read IDs from `target.targetId` by `index`, never by position.

Verified: exact and expanded product targets in a product-target group beside a keyword group, US lab, October 23, 2026. Category target created and resolved to its name in Amazon, DE lab, September 7, 2026; Merch Jar showed that category's label blank.

## Bids

A created target has no bid of its own and inherits the group default; a preview shows that effective bid in `bid`. For a different approved bid, send `PATCH /api/v5/targets/TARGET_ID` with `{"bid":{"bid":0.50}}`, `--profileid` and an `--idempotency-key`. The helper builds these from a list of `{target_id, bid}`:

```text
python scripts/product_targets.py bids --file APPROVED_BIDS.json --key-prefix BATCH_KEY
```

The PATCH body takes currency units, and its response echoes `bid.bid` in currency units; the state stays PAUSED (verified October 23, 2026). Per the live contract, `GET /targets/:id` reports `bid` in minor units (125 means 1.25) and `null` while the target inherits the default; convert before comparing.

## Readback and enabling

With `targets:read`, read every target with `GET /api/v5/targets/TARGET_ID`. Without it, preview `keywords` and `targets` scoped to the new campaign names and match `target_id`, `ad_group_id`, `target_details_asin`, `target_details_match_type`, `state` and `bid`. Read campaigns, ad groups and Product Ads by preview the same way. Rows can be present while `pagination.total` reads 0; count rows.

Enable only what the approved plan says, children first: targets (`PATCH /targets/:id` with `{"state":"ENABLED"}`), then ad groups and Product Ads, then campaigns last through Connect's bulk-action route. An enabled empty group still serves nothing.
