---
name: campaign-naming-cleanup
description: Choose and save an account's campaign naming convention, audit existing Amazon campaign names against real products and targeting, and apply reviewed renames through Merch Jar. Use when cleaning up names, choosing naming standards or saving ongoing naming preferences. Campaign restructuring is separate.
license: Proprietary. Requires an active Merch Jar subscription.
metadata:
  version: "0.3.0"
  tags: "campaigns, naming, cleanup, preferences"
  goal: "set-up"
  risk: "state"
  produces: "reviewed campaign renames and a saved account naming convention"
  last-updated: "2026-09-10"
  compatibility: "Merch Jar Copilot with merchjar-connect"
  requires-skills: "merchjar-connect"
  requires-scopes: "profiles:read, segments:preview, segments:read, campaigns:write"
---

# Campaign Naming

Support choosing or changing a convention, saving it without renaming existing campaigns, applying reviewed renames, and checking later departures. Load the shared preference contract and helper from `merchjar-connect` 1.4 or later. A naming check reads the saved convention first and never starts a fresh convention-selection process unless the user requests it. Existing names can be consistent without a saved convention. Report deliberate exceptions and missing evidence separately from confirmed departures; do not promise continuous monitoring.

Store durable rename mappings and stable per-campaign suffix/exception choices under `campaign-naming-records/` beside the active private config, grouped by profile ID. Read relevant prior records on later checks. Keep IDs, original/applied names, the convention revision and user-approved exceptions; do not use temporary files or chat history as the sole persistence. Saving a convention alone does not require campaign writes.

Help the user make an existing account easier to navigate and establish the naming convention future campaign creation will use. Ground names in actual advertised products and targeting, guide a useful convention, apply reviewed names, and save the user's approved preference.

Read the installed `merchjar-connect` skill for credential discovery, the API client, current contract and runtime instructions. If it is unavailable, explain that this skill extends the Merch Jar Copilot and needs its connection capability. Never ask the user to put credentials into this skill.

Campaign renaming is supported through PATCH with the name field; discovery uses Segment preview. Read [references/api-and-evidence.md](references/api-and-evidence.md) for verified mechanics. Resolve real discrepancies against the current contract, rather than treating known rename support as an unknown feature every session.

## Establish the account and inspect

Use the account the user selected. Respect exclusions and existing protection rules. Default a naming audit to active and paused campaigns; state that archived campaigns are excluded. Resolve ambiguous account selection before writes.

Resolve the shared naming preference using [references/preferences.md](references/preferences.md). A selected account convention is the starting point; do not ask the user to choose again unless they want to revise it. Inventory campaigns, related ad groups, advertised Product Ads and positive targets. Use the actual API, not screenshots or old names alone, to determine product associations and targeting. Use retrieved target data before recommending names or diagnosing overlap.

Read [references/api-and-evidence.md](references/api-and-evidence.md) for the query/readback mechanics and evidence pitfalls.

Produce a compact findings summary with coverage counts: campaigns inspected, default/inconsistent names, misleading labels, multiple-ASIN campaigns, missing associations and mixed targeting. Retrieve all pages for the scope; distinguish a sample from a complete inventory.

For every proposed rename, retain:

- Profile and campaign IDs as strings, current name and state.
- Advertised ASIN set, its Product Ad source and completeness.
- Observed targeting/match types and supporting ad-group/target IDs.
- User-supplied product labels or purpose, identified as supplied context.
- Proposed name, rationale, unresolved questions and dependency flags.

Do not infer "winner", "brand defense", "competitor" or "research" from a name or match type alone. Distinguish objective targeting labels (Exact, Broad, Product targeting) from a business purpose the user confirms. An old date is a candidate for removal, not proof it is irrelevant.

## Guide the convention

Read [references/naming-conventions.md](references/naming-conventions.md) for researched options and tradeoffs. If the user asks to choose a structure first, briefly explain the relevant options and then inspect enough real campaigns to ground the recommendation. Do not turn a naming choice into a campaign-restructuring questionnaire. If they want cleanup, inspect first and lead with a recommendation. Keep the initial choice to two or three relevant examples; the user need not design a template.

Start from the user's stated priorities. When they want ASINs in names, include the full verified advertised ASIN for single-ASIN campaigns. It is a stable product identifier. Suggest a short product label only when a verified catalog title or supplied mapping supports it.

Offer one recommended convention and, when the tradeoff is useful, one alternative using the same real campaigns. A possible single-ASIN format is:

`ASIN | Short product label | Targeting or confirmed purpose`

ASIN-first makes the exact product easy to find. A product-label-first option may scan better when the operator thinks in product names. Do not insist on a universal field order, a decorative prefix or an extra label when the account does not need it.

Handle exceptions explicitly:

- **Multiple ASINs:** propose a meaningful group label or short shared product-family label; show the full ASIN set in the mapping. Never select the first ASIN and present it as the whole campaign.
- **No product ads/unknown product:** flag the missing association. Ask for intended context or leave the campaign unchanged. A supplied intended ASIN is not a verified advertised association.
- **Mixed targeting:** use an accurate mixed label or an agreed purpose, rather than naming the whole campaign after one target.
- **ASIN in a product target:** this identifies the product being targeted, not necessarily the product being advertised.
- **Product label unknown:** a verified ASIN alone is preferable to inventing a title.
- **Several otherwise identical names:** inspect target sets and relevant setup before proposing a meaningful differentiator or stable short suffix. A naming collision does not prove duplicate campaigns, and matching structures do not establish business purpose. Keep suffix assignments stable across reruns. Keyword text belongs in a name only when it describes the campaign's actual narrow scope; use a supported theme or targeting label for larger target sets.

Explain choices against the actual account. Ask only the unresolved questions that affect the mapping, usually one decision at a time. Remove default names, copy suffixes, inconsistent separators and unnecessary labels where appropriate. Preserve meaningful dates, operational tags and integration identifiers. Keep names within the live contract's length limit.

Structural findings can be reported as a separate follow-up: multiple products sharing a budget, mixed targeting, empty campaigns or apparent duplication. Renaming does not fix those structures. Do not create, move, merge, pause, archive or change bids/budgets as part of this skill.

## Review dependencies and the exact changes

Inspect accessible Merch Jar Segment definitions for name-based selectors that could gain or lose matches. Include enabled rules and flag disabled rules that may be reused. A literal search can miss variables and assembled conditions; inspect the relevant trigger logic. Never change that logic silently.

State the systems and scope checked. Paused campaigns can still be referenced by name-based rules. Do not claim external tools, legacy rules or inaccessible integrations were inspected. Block rows with unresolved material name dependencies.

Show a compact old/new table with ASIN evidence, targeting, reason and unresolved flags; make the complete mapping available even when displaying only representative rows. Separate unchanged and unresolved campaigns from proposed changes.

Get approval of the concrete mapping and write scope. A request to "clean up my account" authorizes analysis and preparation, not unreviewed structural changes. Approval may cover all ready rows or a subset. Preserve earlier explicit approval while requiring a new review if the actual names or selected IDs materially change.

## Apply and verify

Save the original names and approved mapping outside credentials. Re-read the selected campaigns immediately before mutation. If a current name or relevant product/targeting association differs from the reviewed snapshot, hold that row and show the changed evidence.

PATCH only `name` on each approved campaign ID in the selected profile. Supply the required idempotency key explicitly through the client; reuse a key only for the identical request. Do not recreate campaigns or run a Segment to rename them.

Record each item's request/result. Stop on an ambiguous transport/server result and read back before any retry. For mixed success, reconcile applied/failed/unchanged IDs and retry only confirmed failures still within the approved mapping. Never call a batch atomic unless the actual endpoint guarantees it.

Read back the saved names by exact identity. Refresh the UI for a visual demonstration. Report applied, skipped, failed and unverified counts without treating a proposed table as completion. Compare unrelated settings to the baseline where the read surface supports them.

For a requested rollback, use the saved campaign IDs and original names. Restore a row only if its current name still matches the rename this operation applied; flag intervening user changes. Report rollback readback separately.

## Retain the convention

Follow [references/preferences.md](references/preferences.md) to save the approved profile convention, resolve it again and report its actual location. Treat this as the second outcome alongside existing-name cleanup. Preserve unrelated preferences and saved launch structures. If saving was declined or persistence is unavailable, say so plainly.

Confirm that the installed creation skill consumes the shared naming preference before claiming future reuse. The user's next creation request should inherit this convention, while an explicit one-time naming override remains possible and does not rewrite the default. Do not imply unsupported skills, other computers or other AI clients automatically share local files.
