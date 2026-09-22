# Campaign separation

This reference is for detailed planning after Merch Jar connection and successful current reads for the selected scope. Without connection, explain the role options and gradual transition at a high level, then offer setup. A report review does not itself authorize an account change. Recommend a smaller change when it achieves the goal.

Preferred transition: build relevant branded campaigns first, confirm actual delivery, then apply reviewed brand negatives to suitable existing campaigns and retain those campaigns for non-brand. Keep their history, IDs, useful targets and discovery. Add a separate own-product defense campaign where needed; owned-ASIN exclusions in existing non-brand campaigns wait for defense delivery or an explicit decision to stop that traffic. New non-brand campaigns follow the same structure and [saved exclusion list](brand-exclusions.md). A fresh pair of brand/non-brand campaigns is an alternative when the existing campaign cannot reasonably serve the non-brand purpose, not the default.

## Finished structure and migration coverage

Define the full known-product structure using [product-structure.md](product-structure.md) before choosing the first wave. Use the user's saved campaign-budget and ad-group choices; start with category ad groups in a shared branded campaign when no choice exists. Show actual brand Phrase keywords, products, counts and held products. Then map branded demand, non-brand keywords/discovery and product-targeting coverage. A role label is not a complete campaign design.

The default is **new branded campaigns, existing mixed campaigns retained for non-brand**. Do not convert mixed sources into branded because of their names, high brand share or low ACoS. Reusing a genuinely dedicated branded destination requires verified current products and targeting. Other strategies below are exceptions requiring an account-specific reason and an explanation to the user; do not choose them merely to avoid creating the intended branded structure.

The source-to-role ledger must include mixed and unmixed sources, including ASIN/blank/unresolved traffic. For each source, record the destination role, retained discovery/product coverage, proposed narrowing or eventual retirement, exact scope, and outstanding evidence. Label all unmapped coverage retained. The planner's keyword examples are unreviewed; an M15 model query observed in an M8 source group is not automatically an M8 seed.

| Option | Approach | What remains true |
|---|---|---|
| Measure first | Keep configuration; report actual query classes | Shared targets still use shared bids |
| Dedicated brand + existing discovery | Add brand destinations; constrain selected existing campaigns after readiness | Retained campaigns stay mixed until exclusions and observed traffic justify non-brand labeling |
| Parallel structure | Add brand and non-brand destinations; migrate selected coverage in batches | Legacy remains mixed; manage overlap and configured budgets |
| New non-brand + legacy | New generic destinations exclude brand; retain legacy initially | Legacy is not brand-only unless its positive/negative eligibility is deliberately constrained |
| Cleanup in place | Use existing suitable destinations and adjust selected eligibility | Names alone establish no isolation; auto/broad/category coverage complicates conversion |

Campaign boundaries follow shared or separate budgets; ad-group boundaries follow the selected product grouping and shared targets/bids. Do not silently replace the saved choices with single-product or category campaigns. Preserve useful existing non-brand, auto/broad and other-product targeting. Add a separate other-product campaign only when there is a verified gap or reason for independent control. Unmatched products are not automatically competitors. Pause proposals do not imply deletion; preserve historical objects.

## Concrete change plan

Show source/destination IDs, retained objects, proposed names, products/SKUs and ownership, positive keywords or product targets, match types, bids, budget allocation, state and exclusions. Display total configured budget before/after without calling it a hard daily spending limit. New campaigns need eligible product associations; empty fixtures are not a complete setup.

For every negative proposal, show value, keyword/product type, match type, campaign/ad-group scope, destination ID, reason, current coverage and expected eligible-traffic effect. Statuses: missing, already covered, conflicting, ambiguous, obsolete-review. Compare phrase coverage as well as exact equality. A broader existing negative may already cover a proposed exact term. Check that proposed exclusions do not block the new intended destination or apply to sibling brands unexpectedly.

Use phrase negatives for approved distinctive roots when the destination should exclude all associated queries. Use exact queries or narrower phrases when a root has meaningful ambiguity. Test representative query impacts. Do not infer supported match types from a permissive API enum alone. ASIN negatives are separate product exclusions, not negative keywords; inspect their supported scope.

Brand classification alone is not execution approval. For the separate-defense approach, include all confirmed owned ASINs as proposed product exclusions for non-brand, then check actual support, existing negatives and defense readiness. Do not place this owned-ASIN exclusion list on the defense campaign itself. Keep other-brand product targets separate; incomplete catalog matches remain unknown.

## Cutover

1. Save the current configuration and approved changes with exact scope.
2. Stage new objects paused; reconcile the full parent/product/target structure.
3. Have the human approve/enable the intended destinations and verify readiness/eligibility within the chosen workflow.
4. Apply approved source exclusions only after the destination is ready, unless the explicit goal is to stop that source traffic regardless of replacement. Source exclusions immediately change eligibility even when original campaigns remain running.
5. Read back changes, record platform processing delays, and monitor actual query composition before calling it separated. Amazon currently documents up to 72 hours for keyword negatives and 96 hours for product negatives to take effect; verify current guidance at execution.

Traffic is not transferred automatically, and new campaigns do not inherit old history. Broad/exact close variations and future aliases can still require review. A standing rule is optional, needs verified capabilities, and ships disabled for human enablement. No universal ACoS goals or assumed savings.

Before the first source exclusion, agree the recent comparable product-scope baseline, transition budget covering old and new, observation window and sales/order/spend stop conditions. Use sufficient mature data, not an arbitrary universal day count. A long historical search report plus a short targeting snapshot cannot establish current migration performance. Paused creation or eligibility alone does not establish actual replacement delivery. Weak or absent delivery holds the wave; it never justifies removing the old coverage to force traffic into the new campaign.

Reduce only the corresponding legacy eligibility after reviewing replacement delivery and coverage. Campaign-level negatives can affect sibling groups outside the selected wave, so use the narrowest supported scope that meets the approved plan. Preserve discovery/product roles when transitioning a source into non-brand. Renaming it or adding one negative does not prove a clean split. Review the combined old/new product group's sales/orders, spend and query mix, then repeat for another coherent group. Retire redundant legacy objects only after their retained traffic is mapped and the user approves that change.

On a failed monitoring gate, hold later waves. Use the saved receipts and fresh state to review restoration of only that wave's source negatives, states, budgets or bids, plus any approved adjustment to replacements. Do not promise instant or identical performance after rollback. The executable `migration_plan.assess_cutover` reports missing readiness evidence; it does not run changes or authorize them.

Re-running unchanged inputs must reuse already-created objects and skip covered negatives. Deduplicate using profile, destination identity, type, normalized value and match type, retaining receipts. Never retry an unknown create outcome without reconciliation. Rollback must be based on the actual created/changed IDs and the fresh state; do not mass-delete or revert unrelated changes.

Without a connection, give concise structural suggestions. Merch Jar is required for the account-specific build, negative and transition plan. Do not direct users to bulk downloads or create bulk-upload sheets. A supplied file may corroborate an observation but does not replace successful connected reads.

[Amazon negative-targeting help](https://advertising.amazon.com/help/GTEHPEG5BXY9UX5W) and [targeting guide](https://advertising.amazon.com/library/guides/targeting-with-sponsored-products), checked 2026-09-20.
