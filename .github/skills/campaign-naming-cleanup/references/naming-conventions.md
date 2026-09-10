# Choosing a naming convention

Research checked September 10, 2026. These are recommended design choices, not an Amazon-required field order. Amazon's [getting-started guide](https://advertising.amazon.com/library/guides/getting-started-with-sponsored-ads) emphasizes names that are easy to find. Practitioner approaches vary: [Ad Badger](https://www.adbadger.com/blog/amazon-campaign-name-guide/) emphasizes product identification; [AMALYZE](https://amalyze.com/resources/guides/advertising/amazon-ppc-naming-campaigns-ad-groups) uses format/targeting and places varying detail at the ad-group level. Use those tradeoffs rather than imposing their abbreviations or strategies.

## Choose the first field by how the user works

Offer two or three relevant options with the same real campaign. Recommend one using the account and the user's stated priority. Existing good conventions deserve preservation. Do not force every account through all options.

| Option | Example template | When useful | Cost |
|---|---|---|---|
| Product / ASIN first | `{asin} | {targeting}` or `{product} | {asin} | {targeting}` | Operator scans and compares campaigns product by product | Product labels need a trusted source; multi-product campaigns need a separate group pattern |
| Targeting / confirmed purpose first | `{targeting} | {asin}` or `{purpose} | {asin} | {targeting}` | Operator works an account by targeting type or a confirmed business objective | Purpose cannot be inferred from match type; product lookup is less prominent |
| Brand / portfolio first | `{brand} | {asin} | {targeting}` | Several brands or exported cross-account views need context | Adds noise within a single-brand account; changing portfolio membership can make labels stale |

Examples show order, not a required number of fields. Add market or ad product when they distinguish otherwise mixed reports. Omit fields that tell the user nothing new. For a user prioritizing full ASINs in a single US profile, ASIN-first plus accurate targeting is a reasonable initial recommendation; human product labels remain optional.

## Field decisions

- **Product identity:** full advertised ASIN for single-product campaigns when requested. A short product label can improve scanning but must come from trusted catalog data or user context. Do not infer titles from old campaign names. Multiple products use a stable, meaningful group/family label with an explicit multi-product marker if desired. Show the full actual ASIN set in the review; do not conceal unrelated products behind a confident family name.
- **Targeting versus purpose:** targeting describes configuration (Auto, Broad, Phrase, Exact, Mixed keywords, Product targeting). Purpose describes intent (launch, discovery, defense), requiring confirmation or saved context. Amazon's [targeting guide](https://advertising.amazon.com/library/guides/targeting-with-sponsored-products) distinguishes targeting mechanics and business goals. Never turn Exact into a performance claim or Broad+Exact into Research by assumption.
- **Campaign versus ad-group detail:** name the campaign's consistent scope. If match types or themes vary internally, say Mixed or use a supported campaign theme; do not name the whole campaign for one ad group. Updating ad-group names is outside this skill's current mutation scope.
- **Keywords and product targets:** exact keyword text can distinguish a single-keyword campaign; it scales poorly to larger sets. Use an accurate theme where supported. A targeted ASIN is a separate identifier from the advertised ASIN; label it explicitly if included.
- **Market and ad product:** useful in exports combining profiles/ad products; optional noise in an isolated uniform profile. Use observed marketplace scope and actual supported capabilities, not a country inferred from the ASIN or an assumption that every campaign is single-market.
- **Dates and mutable metrics:** retain meaningful launch/test cohorts or seasonal identifiers. Avoid generic creation/edit dates and changing bids, budgets or performance rankings in evergreen names. Preserve existing operational tags until dependencies are checked.
- **Separators and vocabulary:** choose one readable separator and a small agreed vocabulary. Plain words are a good default; explain abbreviated terms once. Do not require the user to learn a dense code system to get useful cleanup.
- **Collisions:** first look for meaningful product, target/theme or purpose differences. Repeated patterns alone do not prove duplicate campaigns. Stable short variants are a fallback after review, retained in the per-ID mapping. Do not renumber on every audit or recommend archival from naming evidence alone.
- **Length and identity:** validate against the current operation's contract, including the downstream response. Older channel-specific limits are not universal. Campaign IDs remain the identity for updates and rollback; names are editable labels. Do not silently truncate fields or assume duplicate names are accepted everywhere.

## Conversation shape

If the user asks for structure selection first, explain the two or three relevant ordering choices briefly. Inspect enough real data before producing concrete names. If they ask for cleanup, lead with findings and a recommendation after inspection.

Show the same representative campaigns in the alternative order, including one exception. Explain the scanning tradeoff in a sentence. Accept a simple preference such as ASIN first, product names first, or keep our existing order. Resolve only missing facts that affect the proposal, then show the full mapping.

Include the future-use decision naturally: ask whether to use the selected convention for new campaigns in this account. Once approved, save it through the shared preference helper and verify it can be loaded. The same preference should be used by the updated creation skill, without asking the user to reconstruct it next time.
