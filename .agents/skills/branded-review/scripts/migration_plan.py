"""Read-only destination architecture, coverage map and migration readiness."""
from decimal import Decimal
from analyze_search_terms import present, empty_metrics, add


CUTOVER_GATES = {
    'scope_and_products_verified': 'Verify product grouping, source/destination IDs and product eligibility.',
    'negative_inventory_verified': 'Read current campaign and ad-group negatives with complete scoped coverage.',
    'configuration_readback_verified': 'Read back destination products, targets, budgets, bids and states.',
    'human_enabled': 'The human has enabled the intended replacement destinations.',
    'destination_delivery_reviewed': 'Review actual destination delivery; a paused/created object is insufficient.',
    'replacement_coverage_reviewed': 'Verify the selected traffic has a relevant eligible destination; retain discovery and product coverage.',
    'recent_baseline_ready': 'Establish a recent comparable product-scope baseline with attribution maturity understood.',
    'within_approved_overlap_budget': 'Review combined old/new spend against the approved transition budget.',
    'monitoring_and_rollback_agreed': 'Agree observation windows, performance floors, stop conditions and scoped rollback.',
    'scope_impact_reviewed': 'Confirm the proposed exclusion will not cut off unmigrated sibling groups or product lines.',
    'specific_source_change_approved': 'Obtain approval for these exact source exclusions or state changes.',
}


def assess_cutover(evidence):
    missing = [key for key in CUTOVER_GATES if evidence.get(key) is not True]
    return {'status': 'hold' if missing else 'ready-for-manual-cutover-review',
            'missing': missing, 'automatic_execution': False}


def build_migration(report, groups, queue, selected):
    context = report.get('context', {})
    products = {(p['campaign_id'], p['ad_group_id']): p['asins']
                for p in context.get('products', {}).get('products_by_ad_group', [])}
    targets = {(p['campaign_id'], p['ad_group_id']): p
               for p in context.get('targeting', {}).get('targets_by_ad_group', [])}
    mixed = {(p['campaign_id'], p['ad_group_id']) for p in queue}
    selected_key = (selected['campaign_id'], selected['ad_group_id']) if selected else None
    unmapped = [r for r in report['rows'] if not r.get('campaign_id') or not r.get('ad_group_id')]
    unmapped_metrics = empty_metrics()
    for row in unmapped:
        add(unmapped_metrics, {k: Decimal(row[k]) for k in unmapped_metrics})
    ledger = []
    for key, group in sorted(groups.items()):
        observed = {k: present(v) for k, v in group['metrics'].items()
                    if any(Decimal(n) != 0 for n in v.values())}
        config = targets.get(key, {})
        entries = config.get('reported_enabled_targets', config.get('reported_enabled_keywords', []))
        methods = sorted({r['match_type'] for r in entries if r.get('match_type')})
        routes = []
        if 'brand_query' in observed:
            routes.append({'traffic': 'branded queries', 'destination_role': 'branded',
                           'legacy_action': 'Narrow only the approved scope after replacement delivery and cutover review'})
        if 'other_query' in observed:
            routes.append({'traffic': 'non-brand queries', 'destination_role': 'nonbrand-proven + nonbrand-discovery',
                           'legacy_action': 'Retain relevant discovery; promote reviewed queries without deleting unreviewed coverage'})
        if 'owned_asin' in observed:
            routes.append({'traffic': 'own-product traffic', 'destination_role': 'own-product-defense',
                           'legacy_action': 'Retain until dedicated defense is delivering, then review owned-ASIN exclusions on non-brand sources'})
        if any(k in observed for k in ('asin_unknown','missing_query','brand_review')):
            routes.append({'traffic': 'product, blank or unresolved rows', 'destination_role': 'retain-pending-role-review',
                           'legacy_action': 'Preserve until intent and appropriate product/unknown coverage are mapped'})
        ledger.append({**{k: group[k] for k in ('campaign_id','ad_group_id','campaign_name','ad_group_name')},
                       'product_candidates': products.get(key, []), 'observed_classes': observed,
                       'reported_target_methods': methods, 'routes': routes,
                       'wave': 'first-wave-review' if key == selected_key else ('later-wave-review' if key in mixed else 'retain-and-review'),
                       'destination_ids': [], 'source_change_approved': False,
                       'disposition': 'Keep running as configured pending a reviewed role and scoped transition'})
    roles = [
        {'role':'branded', 'name':'Branded coverage',
         'purpose':'Relevant brand and model demand for a coherent product group',
         'construction':'Stage new branded campaigns paused for relevant product groups; preserve any already suitable branded destinations',
         'legacy_destination':'Narrow corresponding legacy brand eligibility only after this destination can serve'},
        {'role':'nonbrand-proven', 'name':'Non-brand proven keywords',
         'purpose':'Reviewed generic/competitor queries with useful evidence and separate goals',
         'construction':'Prefer keeping existing campaigns and their history; build new ones where a specific gap warrants it',
         'legacy_destination':'After branded delivery, review brand exclusions and retain useful current targeting'},
        {'role':'nonbrand-discovery', 'name':'Non-brand discovery',
         'purpose':'Continue useful broad, phrase and automatic discovery',
         'construction':'Prefer retaining suitable existing discovery; build a replacement if independent budget or grouping requires it',
         'legacy_destination':'Apply reviewed brand exclusions only to migrated scopes after the brand destination is ready'},
        {'role':'own-product-defense', 'name':'Own-product defense',
         'purpose':'Ads targeting confirmed owned ASINs, measured separately from branded search and competitor products',
         'construction':'Use dedicated defense campaigns with relevant advertised products and their own goal',
         'legacy_destination':'Exclude own ASINs from non-brand sources only after defense delivery or an explicit decision to stop that traffic'},
        {'role':'product-and-unresolved', 'name':'Other product targeting and unknown traffic',
         'purpose':'Review other-brand product targeting separately; unknown ownership remains unknown',
         'construction':'Retain or separate deliberately by product role; blank or unknown rows are not generic searches',
         'legacy_destination':'Hold unclassified coverage until mapped; no blanket pause or keyword-only replacement'},
    ]
    waves = [
        {'stage':'Map the finished structure', 'action':'Confirm product groups, reusable campaigns, every source role and a recent baseline.',
         'advance_when':'Source-to-role coverage is reviewed, current negatives known and transition settings agreed.'},
        {'stage':'Build branded campaigns first', 'action':'Create the approved branded campaigns paused. Keep existing campaigns and their targeting; prepare own-product defense as a separate step.',
         'advance_when':'Readback confirms the intended products, targets, budgets, bids and exclusions; source campaigns unchanged.'},
        {'stage':'Establish replacement delivery', 'action':'Human enables the selected wave; review old and new campaigns together within an agreed overlap budget.',
         'advance_when':'Relevant destinations actually serve and have adequate coverage; insufficient delivery holds the wave.'},
        {'stage':'Keep existing campaigns for non-brand', 'action':'Apply reviewed brand exclusions for this wave after branded delivery. Preserve campaign IDs, history and useful targeting. Owned-ASIN exclusions wait for defense readiness.',
         'advance_when':'All cutover gates pass and these source changes are approved. Negatives do not transfer traffic automatically.'},
        {'stage':'Observe, then repeat', 'action':'Compare combined product-scope sales/orders, spend and query mix against the agreed baseline and limits.',
         'advance_when':'After sufficient mature data, the operator accepts the wave; otherwise hold or use scoped rollback.'},
        {'stage':'Use the saved list for new non-brand campaigns', 'action':'Resolve the latest approved brand-term and owned-ASIN list during each new campaign setup, apply supported entries and read back before enablement.',
         'advance_when':'Any missing catalog coverage, unsupported exclusion or exception is visible and resolved for this campaign. Updating a saved list does not update live campaigns.'},
    ] if selected else []
    selected_products = set(products.get(selected_key, []))
    cohort = [{k: row[k] for k in ('campaign_id','ad_group_id','campaign_name','ad_group_name')}
              for row in ledger if selected_products.intersection(row['product_candidates'])]
    return {'purpose':'A clean finished structure reached through reviewed product-group waves',
            'grouping_status':'Product-group boundaries need review; source ad-group count is not a target campaign count',
            'end_state_roles':roles, 'coverage_ledger':ledger, 'waves':waves,
            'first_wave_scope_review':{'product_candidates':sorted(selected_products), 'shared_product_groups':cohort,
                'status':'Review all relevant sources before defining the wave; shared products alone do not approve consolidation',
                'checks':['Current product eligibility and relevance','Ad product and distinct business/targeting intent',
                          'Other products and sibling groups affected by a proposed source exclusion']},
            'unmapped_query_rows':{'rows':len(unmapped), 'metrics':present(unmapped_metrics),
                'action':'Preserve unresolved coverage; missing parent IDs cannot become an executable source scope'},
            'configuration_only_groups':[{'campaign_id':c,'ad_group_id':g,
                'action':'Retain; this configuration scope lacks mapped search-term evidence'}
                for c,g in sorted(set(targets)-set(groups))],
            'transition_settings':{'budget_basis':None,'combined_transition_budget':None,'brand_goal_acos':None,
                'nonbrand_goal_acos':None,'baseline_period':None,'observation_period':None,
                'sales_or_order_floor':None,'spend_limit':None,'rollback_authorization':None},
            'cutover_gates':CUTOVER_GATES, 'cutover_readiness':assess_cutover({}),
            'rollback':{'trigger':'Use agreed combined-sales/orders, spend or delivery stop conditions; no universal threshold',
                'action':'Hold later waves; review removal of only newly applied source exclusions and restoration of recorded source states/budgets; pause or adjust replacement objects only within approved scope',
                'limits':'Changes require exact receipts and fresh state; rollback may have processing delay and cannot guarantee prior performance'},
            'completion':'Relevant branded/non-brand query coverage is observed separately, retained roles are explicit, and redundant legacy objects are reviewed; campaign creation alone is not completion'}


def migration_markdown(migration):
    out = ['## Intended finished structure', '',
           'Apply these roles to coherent product groups. Reuse suitable campaigns; the review queue is not the number of campaigns to create.', '',
           '| Role | Purpose | Treatment |', '|---|---|---|']
    for role in migration['end_state_roles']:
        out.append(f"| {role['name']} | {role['purpose']} | {role['construction']} |")
    out += ['', '## Staged transition', '']
    for i, wave in enumerate(migration['waves'], 1):
        out += [f"{i}. **{wave['stage']}.** {wave['action']} Advance when: {wave['advance_when']}", '']
    if not migration['waves']:
        out += ['No migration wave is proposed from the current evidence. Review existing roles before deciding changes.', '']
    out += ['## What happens to existing coverage', '',
            f"The companion JSON maps {len(migration['coverage_ledger'])} source ad groups to proposed roles. All start retained; none is approved for pause or exclusion.", '',
            f"{migration['unmapped_query_rows']['rows']} query rows lack a complete campaign/ad-group identity; {len(migration['configuration_only_groups'])} configuration groups have no mapped query evidence. Preserve these unresolved scopes.", '',
            'Brand coverage moves only after its relevant destination is serving. Keep useful non-brand discovery. Product-targeting and unresolved traffic keep their existing coverage until their role is reviewed. Campaign-level negatives need a check for effects on sibling groups outside the wave.', '',
            '## Monitoring and rollback', '',
            'Before cutover, agree a recent comparable baseline, combined old/new budget, observation period, sales/order floor and spend limit. Those values are still to confirm. Judge the whole product group, not the attractive ACoS of a new campaign alone.', '',
            'If replacement delivery is weak or the agreed limits fail, hold later waves and review restoring only the changes recorded for that wave. Keep the original IDs, bids, budgets, states and negatives. Restoration has processing delays and cannot guarantee the old performance.', '',
            '**Cutover status: hold.** Current configuration, actual replacement delivery, monitoring limits and exact source-change approval must be verified before exclusions. Paused creation does not satisfy these gates.', '']
    return out
