# Launch validation

Before approval, distinguish a campaign daily budget from a per-click bid and confirm whether an amount applies to each campaign, each product or the entire batch. Show both per-campaign allocations and their sum. Use decimal arithmetic in the currency's supported precision; do not round thirty EUR 0.1667 allocations up into an unapproved total.

Run `python scripts/validate_launch.py PLAN.json` against an agent-prepared monetary plan before writes. This is internal data, never an extra spreadsheet required from the user. Fields: `marketplace`, `currency`, `ad_product`, resolved `budget_basis` (`batch-total`, `per-campaign`, `per-product`), `approved_configured_total`, and `campaigns` containing `daily_budget`, `default_bid`, optional `target_bids`. For other marketplaces supply `verified_limits` with `quantum`, `min_budget`, `min_bid`, `max_bid`, `source`, `checked_at`. The helper verifies amounts and the total; it does not verify API bodies, authorization, dates, entity states or live creation. Keep those checks in the workflow.

For DE/EUR Sponsored Products, use EUR 1 per campaign as the documented baseline minimum daily budget and EUR 0.02–1,000 as the published base-bid range. Thus EUR 5 total cannot fund thirty campaigns at the baseline minimum; EUR 5 each means EUR 150 configured total. EUR 0.17 is a valid base bid, not a valid daily campaign budget. Check the current account/API constraints, including strategy-specific limits, before writing. Do not apply these numbers to another marketplace or ad product.

Sources checked September 8, 2026:

- [Amazon Ads FAQ](https://advertising.amazon.com/en-us/resources/faq): minimum Sponsored Products budget of USD 1 or local-currency equivalent.
- [Amazon's German getting-started document](https://g-ec2.images-amazon.com/images/G/03/AmsVss/AMS_getting_started_DE_German._V288802605_.pdf): EUR 1 daily minimum. This is an older product guide, corroborated by EUR 1 campaign creation in the September 7 test; re-check live constraints when they differ.
- [Amazon Ads API limits](https://advertising.amazon.com/API/docs/en-us/concepts/limits) and [Amazon's global API guide](https://m.media-amazon.com/images/S/aapn-assets-prod/41ec89d2-a402-4116-bc7d-884a7bbaafd2): marketplace/ad-product bid limits, including DE/EUR Sponsored Products 0.02–1,000. Limits can change; do not infer missing currencies or dynamic bidding multipliers from the base-bid table.
- [Amazon's starting guide](https://advertising.amazon.com/library/guides/getting-started-with-sponsored-ads): its EUR 10 launch recommendation is guidance, not the API minimum.

If a currency/marketplace limit is unknown, resolve it from the current official limit table or supported validation response before writes. Never replace it with a marketing recommendation, guess an exchange-rate conversion, or tell the user the entire workflow is impossible. Keep the requested structure and explain the specific missing validation.

Budget and bid values accepted during creation must be compared with exact-ID readback, not merely a success HTTP status. Any mismatch stays unresolved. For launches, derive the current date in the profile's IANA time zone immediately before submission and check the final start date.
