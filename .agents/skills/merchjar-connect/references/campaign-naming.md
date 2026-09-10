# Shared campaign naming preferences

Naming cleanup establishes the convention; every campaign-authoring skill should consume it. A naming convention governs names, not campaign grouping, budgets, bids or targeting structure. Those settings remain in the separate `campaign-structures.json` store.

## Location and scope

Use Connect's client `find_config()` to locate the active configuration without printing its contents. Store `campaign-naming.json` alongside it, normally `user/campaign-naming.json` in a pack or `~/.merchjar/campaign-naming.json` standalone. Honor an explicitly selected configuration path. If credentials came only from the environment and no configuration exists, establish a private preference location with the user; do not silently bind settings to a different account. No secrets belong in this file. Preserve it on Library updates. It is local memory, shared by clients using the same files, not cloud synchronization.

`scripts/campaign_naming.py` provides offline inspect, resolve, save and render operations. Use file inputs, never shell-interpolated JSON. Paths below are relative to this skill; STORE means the resolved private path.

```text
python scripts/campaign_naming.py inspect --store STORE
python scripts/campaign_naming.py resolve --store STORE --profile PROFILE_ID
python scripts/campaign_naming.py save --store STORE --revision INSPECTED_HASH --definition PRIVATE_DEFINITION_JSON
python scripts/campaign_naming.py render --store STORE --profile PROFILE_ID --facts PRIVATE_FACTS_JSON
```

The store contains `schema_version: 1` and `conventions: []`. Each entry has the required fields below and may have `field_values`:

- `scope`: `profile:DECIMAL_ID` or `global`. One active convention per scope. Recommend the selected profile; global requires the user's explicit choice.
- `name`: readable convention name.
- `single_asin`, `multi_asin`: templates. Supported tokens: `{asin}`, `{product}`, `{group}`, `{targeting}`, `{method}`, `{purpose}`, `{market}`, `{ad_product}`, `{portfolio}`, `{brand}`, `{theme}`, `{variant}`. Multi-ASIN cannot use `{asin}`. Propose only fields supported by facts or confirmed context. Method and targeting/match detail are distinct fields; preserve the approved meaning.
- Optional `field_values`: approved allowed labels by token, for example `{"method":["Auto","KW","PT","Mixed"],"purpose":["Discovery","Sales","Defense","Competitor"]}`. Values are nonempty lists of unique nonempty strings. Omit constraints the user has not chosen. The renderer checks used fields against these lists after any caller-applied abbreviations. It does not classify or confirm the facts. Older stores without this field remain supported by Connect 1.5; older helpers do not support this extension or `{method}` and must be updated before reuse.
- `vocabulary`: approved abbreviations/labels as a string-to-string map, e.g. `{"Exact":"EX","Product targeting":"PT"}`. The calling skill applies this map to canonical targeting values using an exact, case-sensitive lookup; absent keys keep the canonical value. The renderer does not classify targeting or infer purpose.
- `rules`: five nonempty instructions keyed `product_labels`, `missing_product`, `mixed_targeting`, `collisions`, `dates`. Record the user's actual choices, including ASIN-only if selected. Keep product title maps and per-campaign suffix assignments in their appropriate private context/receipts rather than storing live entity data here.
- `provenance`: `confirmed_at` and `instruction`, recording the user's save/default decision without credentials.

For example, an approved product-first convention might use `{asin} | {targeting}` and `MULTI | {group} | {targeting}`. This is an example, not a saved user default. Preserve account-specific meaningful tags and labels.

## Save and maintain

Make saving a normal outcome of this workflow. Alongside the proposed convention, ask naturally whether to use it for future campaigns in this account. An explicit remember/default instruction is sufficient; do not ask again. Rename approval alone does not authorize a durable default. Saving a convention does not approve any live campaign changes, and can succeed even when some existing rows stay unresolved. Report the two outcomes separately.

Inspect before saving, show replacements when necessary, and pass the inspected revision. The helper preserves other scopes, locks cooperating writers and atomically replaces the file. A stale revision, malformed/unknown schema, or existing lock stops the write. Reconcile it without deleting user data or resetting the store. Other editors can still race the helper; never claim protection against arbitrary simultaneous filesystem edits.

Before saving, compare the serialized definition to the user's accepted proposal: field meanings and order, vocabulary, single/multi-product rules and scope. Do not substitute a different field to fit the schema. Required exception instructions can say unresolved/hold for review; they must not invent user choices such as consolidate duplicates. After saving, resolve the same profile again and render representative names, including a manual keyword example when a method field is used: it should show KW even when its match type is Exact. Compare that result to the accepted example and show the actual path and effective convention. Reuse it in the next session without another default-confirmation round. One-off naming overrides apply only to the current plan unless the user asks to update the default. A later convention change does not itself authorize mass renames of previously created campaigns.

## Contract for creation and other skills

Before generating campaign names, resolve the selected profile's convention, falling back to global. Apply precedence:

1. Explicit naming instruction for this operation.
2. Saved profile naming convention, otherwise saved global convention.
3. Naming embedded in the selected legacy campaign structure.
4. A recommendation when nothing is saved.

A request to use a named launch structure alone does not override the separately saved naming convention. If its embedded naming differs, state that its campaign setup will use the account naming convention. An explicit instruction to use that structure's names is a one-time override; disclose the deviation without silently changing the default. Keep an unresolved conflict visible before plan approval.

Use actual planned advertised ASINs, trusted labels and known targeting in creation; use verified existing associations in cleanup. `render` accepts a facts object with `asins` plus required token values and returns one name. Missing facts and invalid/long names require resolution. It does not validate the truth of supplied facts, approve API writes or detect collisions across a batch. The caller checks final names against the entire proposed batch and existing scope, preserves stable differentiators, and reports deviations in the normal reviewable plan.

The original shared contract/helper ships in Connect 1.4 or later. The method token and optional field vocabularies require Connect 1.5; Creation 1.3 consumes those meanings explicitly. Creation 1.2 consumes the original contract without requiring the optional Campaign Naming skill; earlier Creation 1.1 candidates depend on that optional skill. Installing only naming does not update older consumers. Check actual local versions, disclose incompatible consumers, and give the saved preference path rather than claiming integration from saved text alone.

Canonical targeting values for callers: planned `auto-combined` becomes `Auto`, `keyword-broad` becomes `Broad`, and `keyword-exact` becomes `Exact`. Observed keyword-only campaigns use `Broad`, `Phrase` or `Exact` when homogeneous, and `Mixed keywords` when multiple match types exist. Product-target-only campaigns use `Product targeting`; mixed keyword/product configurations use `Mixed targeting`. Read automatic mode from actual configuration, not an old label. Empty or incomplete targeting needs review, not an invented value. Apply the vocabulary lookup to this canonical value before passing `targeting` to the renderer. Purpose, product, market and group values retain their separately confirmed meanings.

Canonical `method` values are separate: automatic campaign mode is `Auto`; manual keyword-only targeting is `KW`, regardless of Broad/Phrase/Exact mix; manual product-target-only is `PT`; a verified manual keyword/product mix is `Mixed`. An empty or incomplete manual target set has no confirmed method. For creation use the actual planned target types. Do not infer purpose from any of these values. The renderer requires `method` explicitly when the approved template includes it; passing `targeting: Exact` alone cannot satisfy it.
