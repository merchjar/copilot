---
name: create-campaigns
description: Help choose, review and create a campaign structure from pasted ASINs or a one-column file, staged paused by default with explicitly approved launch states. Use when creating launch campaigns, adding product discovery, following a supplied campaign structure, or saving and reusing campaign setup preferences. Existing-account restructuring and Smart Campaign rules are separate workflows.
license: Proprietary. Use requires an active Merch Jar account; see LICENSE in the repo root.
compatibility: Merch Jar Connect and account access. Python 3.9+ for local input and preference helpers; conversation-only fallback when persistent files are unavailable.
metadata:
  version: "1.0"
  tags: "campaigns, creation, launch, asin, preferences"
  goal: "set-up"
  risk: "state"
  requires-skills: "merchjar-connect"
  requires-scopes: "profiles:read, segments:preview, campaigns:write, ad_groups:write, ads:write, targets:write"
  produces: "an approved campaign structure with reconciled creation receipts, explicit delivery states and missing launch inputs"
  last-updated: "2026-09-08"
---

# Create campaigns

Read `merchjar-connect` first. Use its client, configuration discovery and current API reference for all reads and writes. In a pack these are `tools/merchjar_client.py` and `reference/MJ_API_REFERENCE.md`; standalone, they are inside `../merchjar-connect/`. Do not create another API client. Load the current creation contract through Connect before preparing requests.

## Start with what the user supplied

Accept pasted ASINs or a single-column text/CSV file, with or without an ASIN header. Use `scripts/campaign_structures.py intake --file PATH` (or `--text TEXT`) to normalize case and deduplicate. Show invalid entries and duplicates alongside the valid count. Never silently drop invalid products from a plan. For a spreadsheet, read its single column as text, preserving leading zeros, then pass the values through the same intake. No settings columns are required. Format validity does not establish eligibility.

Resolve the account using Connect and the conversation. Read fresh marketplace/currency, protected items and profile context. Never infer marketplace from ASINs. Read saved structures alongside the active configuration using [preferences.md](references/preferences.md). Extract the purpose, grouping, structure, budgets, bids and seeds already supplied. Inspect only relevant existing campaign/product coverage through supported read paths, including pagination. Names alone do not establish preferences, and account history does not prove current product eligibility. Report incomplete coverage as unknown.

## Choose the entry path

- Explicit structure now: use it and resolve omissions or unsupported choices.
- Selected named structure: apply it, with current explicit overrides.
- Matching profile default, otherwise global default: briefly state which setup applies and continue to unresolved inputs. No extra default-confirmation round.
- Several applicable structures with no default: offer names and purposes for selection.
- One applicable structure without a default: offer it; do not silently turn it into a default.
- No applicable structure: ask whether the user already has a structure or wants help choosing one.
- The user already requested guidance: start guiding; skip that entry question.

Saved structures are planning shortcuts. They never authorize a new batch. If purpose is unknown and applicability is ambiguous, resolve purpose before selecting a default.

## Guide unresolved decisions

Keep questions short, normally one decision at a time. Begin with purpose if unknown: first launch, more discovery, or testing known targets. Establish separate product budgets versus products grouped for a shared advertising purpose. A shared upload alone is no reason to group them.

Explain each proposed campaign's job and the relevant tradeoff. The bounded first path is one combined Auto campaign per product, optionally broad Research and Exact with real seeds or the paused-placeholder path below, each with one group and Product Ad. Auto supplies discovery; broad explores around supplied terms; Exact tests specified terms. Use only the roles that fit this user. Combined Auto uses fewer objects than splitting automatic groups; split Auto offers separate campaign budgets but requires separate execution acceptance.

This candidate has not passed fresh live interaction acceptance. Do not promise split-auto execution, grouped-product execution, product-target campaigns or empty manual groups as verified by this skill. Explain the limitation and offer a supported narrower plan only with the user's agreement.

For a requested complete structure that includes manual campaigns but has no real keywords, propose building those campaigns now with clearly labeled dummy keywords. Generate `replace me broad` with BROAD match in Research and `replace me exact` with EXACT match in Exact. Include the appropriate Product Ad in each manual group. Do not ask the user to type dummy terms or supply spreadsheet columns, and do not silently drop the manual campaigns or block on keyword research. Default to staging all entities PAUSED. If the user requests enabled campaigns, propose enabling the campaign, ad group and Product Ad while leaving every dummy keyword PAUSED. Dummy text is valid keyword input; it is not a reason to refuse parent enablement or claim Amazon prohibits it. Explain that these manual groups have no serving positive keyword until real keywords are enabled. Real existing targets may still serve, so verify the entire group before making a no-delivery claim. An explicit request for dummy keywords already selects this path; do not ask again. If the user declines placeholders or explicitly prefers Auto first, defer manual roles as requested. Real supplied seeds take precedence over generated placeholders. Never describe dummy terms as research or performance recommendations.

The reusable `paused-placeholders` policy records permission to propose this staging method, not actual keyword strings or permission to create or enable. Generate fresh per-batch terms and include them in the approved manifest. A saved structure must not cause automatic enabling or reuse of dummy terms as real launch seeds.

Read current and durable budget policies before asking for an amount. Distinguish total batch, per product and per campaign. Recompute for the current ASIN count and chosen roles, including any one-time role omissions. Show the configured sum in account currency; it is not a guaranteed daily spending ceiling. Reuse allocation ratios, never a prior batch's amount. Currency-scoped bids apply only to the same currency. Identify proposed bid assumptions or cite available evidence. Rehearsal amounts are not production defaults.

Ask for budget scope in ordinary language with the campaign count visible: “What daily budget would you like per campaign? We're creating 30 campaigns.” Accept an explicit total instead. An answer such as “5 euros daily” is ambiguous; show the per-campaign amount and batch total and resolve the meaning before allocation. Never silently multiply a total, raise it to minimums, or confuse budget with a bid. Validate currency precision and each proposed campaign budget/default bid/target bid against current marketplace-specific Amazon limits before plan approval and again before creation. See [launch-validation.md](references/launch-validation.md). If the total cannot support the selected campaign count, explain the minimum feasible total and offer fewer campaigns or a higher total for the user to choose. Platform minimums are different from recommended launch budgets.

Show ad-group names as well as campaign names. Use readable role names, for example `{asin} | Auto`, `{asin} | Research`, `{asin} | Exact`, unless the user has supplied a naming convention. Do not invent unexplained abbreviations or translate stored names. If an interface appears to translate `Auto` into `Car`, compare the stored name before diagnosing or renaming it.

## One complete plan, then approval

Present account/marketplace/currency, valid and excluded products, campaign jobs and grouping, campaign and ad-group names, campaign budgets and total, bids and their basis, seeds/match types or deferred roles, overlap, eligibility unknowns and deviations from saved preferences. Show final states separately for campaigns, ad groups, Product Ads and targets. Default to paused; any requested enablement must be explicit in this plan, including whether Auto targeting will serve. Show counts and a compact per-product preview; save a complete private manifest for inspection. Resolve overlap before creation; attaching children to existing campaigns requires explicit inclusion in this plan.

Let the user revise conversationally. Obtain approval of the resulting plan before any account write, even if general config permits other workflows without approval. Material product, scope or budget changes invalidate old approval. Do not treat campaign creation approval as permission to save preferences, enable serving or configure Smart Campaign rules.

## Create and reconcile

Follow Connect's current entity creation guidance, not guessed request fields. Prepare body files and private receipts separate from preferences. Assign local request keys per product/role/entity. Map each response's item index to the original request and exact returned decimal-string IDs; never zip successes positionally onto all requests or coerce IDs through floating point. Create children only for confirmed successful parents, with explicit paused states.

Resolve the current account-local date from the profile's IANA time zone immediately before campaign creation. Do not reuse yesterday's manifest timestamp or substitute the operator's local date. Follow the endpoint's current start-date semantics; if a valid start requires changing the user's intended launch date, obtain that decision. A definite per-item `DATE_CANNOT_BE_IN_PAST` rejection can be corrected only for those rejected items after reconciliation, never by blindly replaying successful or unknown items.

If the approved plan includes enablement, reconcile the complete paused structure first. Keep dummy keywords paused, enable only the approved children, and enable their parent campaigns last. Read back exact states and explain effective delivery. Do not expand a request to enable manual parents into permission to enable Auto campaigns, real targets or unrelated objects. This is campaign state management; Smart Campaign automation rules remain a separate workflow requiring human enablement.

For combined Auto follow Connect's automatic creation flags. Reconcile generated automatic groups rather than POSTing duplicates. Generated groups may be individually enabled under paused parents; distinguish that from effective delivery. Preserve every success, partial success, error and unknown result. HTTP success is not per-item success; a timeout, 502 or empty projection is not proof of no creation. Stop dependent work on uncertain parents. Reconcile through available authoritative readback before any retry; if that access is unavailable, report the unresolved items and stop them.

Read back exact product-parent associations, campaign budgets, default/target bids and states. Compare with the approved manifest. An inconsistent total, delayed projection or missing generated-target view stays unresolved until verified. Never call an unverified batch ready to launch. Report verified created counts, failures, unknowns, deferred inputs and where the user can inspect results. Cleanup is a separate, explicitly scoped action against receipt IDs; protect existing items and never reuse old manifests. Renaming, merging or archiving existing coverage is separate work.

## Remembering and examples

Only save after an explicit remember/default/update instruction. Clarify ambiguous scope; creation approval alone does not authorize saving. Offer to remember a reusable choice at most once without delaying creation, and respect a decline. See [preferences.md](references/preferences.md) for validated storage and [conversations.md](references/conversations.md) for short illustrative flows.
