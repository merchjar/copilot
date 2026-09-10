# Choosing a naming convention

Research checked September 10, 2026. These are recommended design choices, not an Amazon-required field order. Amazon's [getting-started guide](https://advertising.amazon.com/library/guides/getting-started-with-sponsored-ads) emphasizes names that are easy to find. Practitioner approaches vary: [Ad Badger](https://www.adbadger.com/blog/amazon-campaign-name-guide/) emphasizes product identification; [AMALYZE](https://amalyze.com/resources/guides/advertising/amazon-ppc-naming-campaigns-ad-groups) uses format/targeting and places varying detail at the ad-group level. Use those tradeoffs rather than imposing their abbreviations or strategies.

## Choose the first field by how the user works

Offer two or three relevant options with the same real campaign. Recommend one using the account and the user's stated priority. Existing good conventions deserve preservation. Do not force every account through all options.

| Option | Example template | When useful | Cost |
|---|---|---|---|
| Product / ASIN first | `{asin} | {targeting}` or `{product} | {asin} | {targeting}` | Operator scans and compares campaigns product by product | Product labels need a trusted source; multi-product campaigns need a separate group pattern |
| Targeting / confirmed purpose first | `{targeting} | {asin}` or `{purpose} | {asin} | {targeting}` | Operator works an account by targeting type or a confirmed business objective | Purpose cannot be inferred from match type; product lookup is less prominent |
| Brand / portfolio first | `{brand} | {asin} | {targeting}` | Several brands or exported cross-account views need context | Adds noise within a single-brand account; changing portfolio membership can make labels stale |

Examples show order, not a required number of fields. They are compact cleanup options. For an ongoing convention, start with the reusable taxonomy below, then simplify it to fit the user's needs. Human product labels remain optional.

## An ongoing taxonomy

A useful starting proposal is `{ad_product} | {asin} | {purpose} | {method}`, with `{group}` replacing `{asin}` for multiple advertised products. This is a design recommendation, not a universal best practice or an instruction to change campaign structure. Explain the fields together so the user can choose a system in one pass:

| Field | Meaning and suggested labels | Evidence or choice |
|---|---|---|
| Ad product | The advertising format, such as SP for an actual Sponsored Products campaign | Actual format; a vocabulary example does not imply support for creating other ad products |
| Product | Full advertised ASIN, or an approved group label for multiple products | Verified association for existing campaigns; planned advertised products for creation |
| Purpose | The business job; propose a small relevant set such as Discovery, Sales, Defense, Competitor | User intent or previously confirmed context; these are choices, not facts inferred from targets |
| Method | Auto, KW (manual keywords), PT (product targeting), Mixed | Actual campaign mode and complete relevant target evidence |
| Optional match detail | Broad, Phrase, Exact, or an accurate mixed label | Add at campaign level when useful and consistent across it; ad-group detail otherwise stays separate |
| Optional context | Marketplace, brand, confirmed theme or stable variant | Include when it helps how the user scans or exports data |

An illustrative name is `SP | B0828NCLVB | Discovery | KW`. Label it illustrative until the advertised product, method and purpose for a real campaign are established. An Exact and a Broad keyword campaign both use method KW; a match-specific convention can include `{targeting}` separately. Do not claim that everyone should have one match type per campaign or that choosing a name authorizes restructuring ad groups.

Offer an overlapping purpose vocabulary only when the user has a clear distinction for those terms. A broader taxonomy does not solve collisions by itself. If several campaigns have the same confirmed job and configuration, preserve distinctions or propose stable variants; do not conclude that they should be consolidated. Missing purpose can remain unresolved while the convention is saved. Put suggested purpose and confirmation status in separate columns, leaving proposed names free of emoji and review annotations.

Save approved field vocabularies in the shared contract's `field_values`, rather than leaving them only in chat. Keep unsupported or unconfirmed group labels out of real examples. An advertised ASIN set does not establish a shared product family, and a product-targeted ASIN does not establish competitor ownership.

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

When choosing an ongoing convention, lead with the taxonomy and a clearly illustrative example, then ground it with a small scoped sample when the user also asks about existing names. Full inventory and dependency review belong to preparing the complete rename mapping. A request specifically for a full audit still receives full coverage.

Show representative campaigns, including one exception, and explain the useful tradeoff in a sentence. Accept a simple preference such as use the core, ASIN first, or keep our existing order. Resolve only missing facts that affect the proposal, grouping shared decisions rather than interviewing the user about every row, then complete the requested mapping.

Include the future-use decision naturally: ask whether to use the selected convention for new campaigns in this account. Once approved, save it through the shared preference helper and verify it can be loaded. The same preference should be used by the updated creation skill, without asking the user to reconstruct it next time.
