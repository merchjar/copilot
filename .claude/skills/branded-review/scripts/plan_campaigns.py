"""Read-only planning evidence. No account writes or API payload generation."""
import argparse
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from analyze_search_terms import empty_metrics, add, present, normalize, rule_matches
from migration_plan import build_migration, migration_markdown
from structure_plan import build_structure, needs_asins
from brand_exclusions import draft as draft_exclusions


def _build_plan_evidence(report, pilot_group=None, product_groups=None):
    groups = {}
    targeting = report.get('context',{}).get('targeting',{})
    target_groups = {(g['campaign_id'],g['ad_group_id']):g for g in targeting.get('targets_by_ad_group',[])}
    for row in report['rows']:
        key = (row['campaign_id'], row['ad_group_id'])
        if not all(key):
            continue
        group = groups.setdefault(key, {'campaign_id':key[0], 'ad_group_id':key[1],
            'campaign_name':row['campaign_name'], 'ad_group_name':row['ad_group_name'],
            'metrics':defaultdict(empty_metrics), 'terms':{}})
        metrics = {k:Decimal(row[k]) for k in empty_metrics()}
        add(group['metrics'][row['category']], metrics)
        tkey = (row['category'],normalize(row['query']))
        term = group['terms'].setdefault(tkey, {'query':row['query'], 'metrics':empty_metrics()})
        add(term['metrics'],metrics)
    queue = []
    for key,g in groups.items():
        brand, other = g['metrics']['brand_query'],g['metrics']['other_query']
        if brand['clicks'] > 0 and other['clicks'] > 0:
            queue.append({k:g[k] for k in ('campaign_id','ad_group_id','campaign_name','ad_group_name')} |
                         {'brand':present(brand),'nonbrand':present(other),
                          'targeting_evidence':target_groups.get(key)})
    queue.sort(key=lambda x:(-Decimal(x['brand']['spend']),x['campaign_id'],x['ad_group_id']))
    if pilot_group:
        selected = next((x for x in queue if (x['campaign_id'],x['ad_group_id']) == tuple(pilot_group)),None)
        if not selected: raise ValueError('Selected pilot has no observed brand/non-brand mix in this report')
    else:
        selected = None
    destinations = []
    exclusions = draft_exclusions(report)
    structure = build_structure(report, product_groups)
    if selected:
        g = groups[(selected['campaign_id'],selected['ad_group_id'])]
        context = report.get('context',{}).get('products',{})
        products = next((p['asins'] for p in context.get('products_by_ad_group',[])
            if (p['campaign_id'],p['ad_group_id']) == (selected['campaign_id'],selected['ad_group_id'])),[])
        for category,role in [('brand_query','Branded'),('other_query','Non-brand')]:
            terms = [{'text':t['query'],'match_type':'EXACT','status':'proposed',**present(t['metrics'])}
                     for (c,q),t in g['terms'].items() if c == category]
            terms.sort(key=lambda x:(-Decimal(x['sales']),-Decimal(x['spend']),x['text']))
            destinations.append({'local_key':role.lower(),'role':role,'method':'KW','targeting':'Exact',
                'proposed_name':f"{report['brand']} | {role} | Pilot",
                'naming_status':'Recommendation; resolve saved convention before approval',
                'product_candidates':products,'product_status':'Historical group evidence; confirm grouping and current eligibility',
                'proposed_ad_groups':[{'advertised_asins':[asin], 'keyword_status':'Review relevance for this ASIN'} for asin in products],
                'keyword_candidates':terms[:10],'other_keyword_candidates':max(0,len(terms)-10),
                'selection_basis':'Top 10 by attributed sales, then spend, within this source group; requires relevance review',
                'daily_budget':None,'bid':None,'goal_acos':None,'state':'PAUSED','status':'proposed', 'action':'create'})
            if role == 'Non-brand':
                destinations[-1].update({'action':'retain-existing', 'campaign_id':selected['campaign_id'],
                    'proposed_ad_groups':[],
                    'ad_group_id':selected['ad_group_id'], 'proposed_name':selected['campaign_name'],
                    'method':'retain-current-targeting', 'targeting':None, 'state':None,
                    'selection_basis':'Keep existing non-brand coverage and history; these queries are review evidence, not new-target instructions'})
            else:
                selected_asins=set(products)
                scoped_groups=[{**ag,'advertised_asins':sorted(selected_asins.intersection(ag['advertised_asins']))}
                    for ag in structure['branded_ad_groups'] if selected_asins.intersection(ag['advertised_asins'])]
                candidates=[{'text':k['term'],'match_type':match,'status':'proposed'}
                    for k in structure['shared_brand_keywords'] for match in k['match_types']]
                destinations[-1].update({'targeting':'Phrase' if structure['options']['brand_match']=='phrase' else 'Exact + Phrase',
                    'proposed_ad_groups':scoped_groups, 'keyword_candidates':candidates,'other_keyword_candidates':0,
                    'selection_basis':'Approved shared brand terms in the selected product scope. Use the complete product structure for campaign budgets and ad groups; missing product grouping remains unresolved.'})
    plan = {'schema':'brand-campaign-plan/2','status':'structure proposal; settings and migration gates unresolved',
        'source':{k:report[k] for k in ('account_id','brand','currency','source_sha256','observed_start','observed_end')},
        'destination_profile_id':None,'recommended_strategy':'new-brand-retain-nonbrand' if queue else 'measure-first',
        'rationale':'Plan branded coverage across the known catalog first. Build new branded campaigns, verify delivery, then convert suitable existing campaigns to non-brand with reviewed exclusions. Review own-product defense separately. The first rollout group is a subset of this plan, not the whole recommendation.' if queue else 'No qualifying mixed ad group was observed; check the product structure and current coverage before recommending changes.',
        'product_structure':structure,
        'pilot_source':selected,'destinations':destinations,'review_queue':queue,
        'targeting_basis':{'available':bool(targeting),'observed_start':targeting.get('observed_start'),
            'observed_end':targeting.get('observed_end'),
            'use':'Reported structure only; no query-to-target attribution or complete current negatives'},
        'brand_negative_candidates':[{'term':r['value'],'match_type':r['match_type'],
            'status':'review required','scope':'proposed non-brand destination only',
            'reason':r['basis']} for r in exclusions['entries'] if r['type']=='KEYWORD'],
        'owned_asin_negative_candidates':[r for r in exclusions['entries'] if r['type']=='PRODUCT'],
        'held_negative_terms':exclusions['held_terms'],
        'exclusion_catalog':exclusions['catalog'],
        'legacy_action':'Keep existing campaigns running. After replacement delivery and approval, exclude brand traffic and retain these campaigns for non-brand; move owned-product traffic separately.',
        'pending':['Confirm strategy and pilot scope','Confirm products and query relevance','Resolve naming convention',
            'Choose separate performance goals','Choose budget allocation and bids',
            'Read current destination configuration and negatives','Review exact paused-creation manifest'],
        'cutover':['Construct approved destinations paused','Verify products, targets, budgets and states',
            'Human enables intended destinations and checks readiness','Apply separately approved source exclusions',
            'Measure actual query mix after processing and attribution delay'],
        'approval':None,'receipts':[]}
    if not selected:
        plan['pending'].insert(0, 'No pilot chosen automatically. Review the full product grouping, then select a relevant group using current activity and coverage.')
    plan['migration']=build_migration(report,groups,queue,selected)
    plan['revision']=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
    return plan


def build_suggestions(report, product_groups=None):
    """Free upload output: role-level guidance, no account-specific change design."""
    classes = {row['category'] for row in report['rows']}
    mixed = {'brand_query', 'other_query'}.issubset(classes)
    return {'schema': 'brand-structure-suggestions/1', 'mode': 'standalone',
        'status': 'report and structural suggestions; detailed planning requires Merch Jar',
        'source': {k: report[k] for k in ('account_id','brand','currency','source_sha256','observed_start','observed_end')},
        'product_structure':build_structure(report, product_groups),
        'suggestions': [
            'Review separate goals and campaign budgets for branded and non-branded traffic.' if mixed else
            'The supplied evidence does not establish a need to restructure; keep measuring before proposing changes.',
            'Retain useful discovery and product targeting when considering a cleaner structure.',
            'Use a gradual transition so existing coverage remains available while replacements are evaluated.'],
        'next_step': ('Upload your brand ASIN list or Amazon Ads’ Advertised product report to split ASIN traffic and plan product groups.' if needs_asins(report) else
            'Use the available Merch Jar connection to inspect current products, targets and negatives, then refine the proposed structure.' if report.get('connection') or report.get('connection_context',{}).get('state') in ('verified','configured_unverified') else
            'Connect Merch Jar to inspect current products, targets and negatives, then develop the detailed campaign and transition plan.'),
        'account_changes': False}


def validate_connected_context(report, context, receipt_dir):
    """Validate a saved read receipt, not credentials or permission to mutate an account."""
    if context.get('schema') != 'brand-connected-context/1' or context.get('provider') != 'merchjar':
        raise ValueError('Detailed planning requires current Merch Jar read evidence')
    if context.get('account_mapping_verified') is not True or context.get('source_account_id') != report['account_id']:
        raise ValueError('Verify the report-account to Merch Jar profile mapping first')
    profile = context.get('profile_id')
    if not isinstance(profile, str) or not profile or context.get('currency') != report['currency']:
        raise ValueError('Connected profile and currency must match the reviewed account')
    known_profile = report.get('connection', {}).get('profile_id')
    if known_profile and str(known_profile) != profile:
        raise ValueError('Connected context belongs to a different profile')
    stamp = datetime.fromisoformat(context.get('retrieved_at', '').replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Connected read time must include a timezone')
    scope = context.get('scope', {})
    if not scope.get('campaign_ids') or not scope.get('ad_group_ids'):
        raise ValueError('Current reads must identify the selected campaign and ad-group scope')
    receipts = {}
    for kind in ('campaigns','ad_groups','product_ads','targets','negatives'):
        read = context.get('reads', {}).get(kind, {})
        if (read.get('status') != 'complete' or read.get('profile_id') != profile or
                read.get('pagination_complete') is not True):
            raise ValueError(f'Current Merch Jar {kind} reads are incomplete; keep structural suggestions')
        if type(read.get('rows')) is not int or read['rows'] < 0:
            raise ValueError(f'Connected {kind} needs a verified row count')
        path = Path(read.get('receipt_file', ''))
        if not path.is_absolute():
            path = Path(receipt_dir) / path
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != read.get('sha256'):
            raise ValueError(f'Connected {kind} receipt changed or is missing its checksum')
        payload = json.loads(raw)
        if not isinstance(payload, (list, dict)):
            raise ValueError(f'Connected {kind} receipt is not a JSON read response')
        if isinstance(payload, dict) and (payload.get('error') or payload.get('errors')):
            raise ValueError(f'Connected {kind} receipt contains an API error')
        if read.get('rows') == 0 and read.get('empty_verified') is not True:
            raise ValueError(f'Empty {kind} needs verified coverage, not an API error')
        receipts[kind] = {'sha256': read['sha256'], 'receipt_file': str(path)}
    return {'profile_id': profile, 'retrieved_at': context['retrieved_at'], 'scope': scope,
            'receipts': receipts, 'authorization': 'Read evidence only; no account changes approved'}


def build_plan(report, pilot_group=None, connected_context=None, receipt_dir='.', product_groups=None):
    if connected_context is None:
        return build_suggestions(report, product_groups)
    evidence = validate_connected_context(report, connected_context, receipt_dir)
    plan = _build_plan_evidence(report, pilot_group, product_groups)
    selected = plan['pilot_source']
    if selected and (selected['campaign_id'] not in evidence['scope']['campaign_ids'] or
                     selected['ad_group_id'] not in evidence['scope']['ad_group_ids']):
        raise ValueError('Selected pilot is outside the successfully read configuration scope')
    plan['mode'] = 'connected'
    plan['connection_evidence'] = evidence
    plan['destination_profile_id'] = evidence['profile_id']
    plan['status'] = 'connected planning evidence; refine against current read receipts before approval'
    # Historical query candidates remain historical; current receipts must be reconciled by the skill.
    plan['pending'].insert(0, 'Reconcile historical candidates against current products, targets, negatives and sibling scope')
    plan.pop('revision', None)
    plan['revision'] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    return plan


def structure_markdown(structure):
    s=structure
    lines=['## Product coverage before the first rollout', '', 'Create new branded coverage and keep existing campaigns running during the transition.', '',
        f"{s['known_products']} known owned ASINs; {s['proposed_branded_campaigns']} proposed branded keyword campaigns ({s['proposed_branded_ad_groups']} ad groups) and {s['proposed_defense_campaigns']} own-product defense campaigns ({s['proposed_defense_ad_groups']} ad groups); {len(s['held_products'])} products awaiting grouping.",
        'Ad-group arrangement: '+s['ad_group_mode']+'. Shared keyword candidates: '+', '.join(k['term'] for k in s['shared_brand_keywords'])+'.',
        'Catalog completeness: '+('complete as supplied' if s['catalog_complete'] else 'partial or unverified')+'. Eligibility and the final advertising selection still need review.', '']
    for group in s['groups']:
        name=group['name'].replace('|',' / ')
        lines.append(f"- **{name}:** {len(group['asins'])} advertised products. Branded campaign budgets: {s['options']['brand_campaigns']}. {group['reason']}")
        for k in group['keyword_candidates']:
            lines.append('  - Keyword: '+k['term']+' ('+'/'.join(k['match_types'])+'), '+k['evidence']+'. Products to review: '+(', '.join(k['advertised_asins']) if k['advertised_asins'] else 'select relevant products in this category')+'.')
    for defense in s['defense_ad_groups']:
        lines.append('- Defense group '+defense['name']+': advertise '+', '.join(defense['advertised_asins'])+'; target '+', '.join(defense['target_asins'])+'. Review relevance of every combination.')
    if s['defense_pairing_pending']:lines.append('Cross-sell pairings are pending; propose compatible ads and targets before counting those campaigns.')
    if not s['known_products']: lines.append('Next: add the brand ASIN list or Advertised product report, preferably with product names.')
    elif s['held_products']: lines.append('Unassigned products remain visible in the report; propose their groups before presenting the account-wide structure as finished.')
    lines += ['', 'Branded ad groups advertise products against the shared brand keywords. Own-product defense groups advertise products against the owned-ASIN targets listed above, in separate Product targeting campaigns. Review the actual products, targets, bids and budgets before creation.',
        'Create new branded coverage first and keep existing campaigns running while it gets established. Reuse an already dedicated branded destination only after verifying its intended products and targeting; brand-heavy performance alone does not justify converting a mixed legacy campaign.',
        'Review own-product defense independently. Retain other-product targeting; create a separate home only for a distinct budget/goal or a verified coverage gap. Do not label unmatched ASINs competitors.', '']
    return lines


def negative_coverage(proposed, existing):
    """Conservative lexical coverage; scopes must already be resolved by exact IDs.

    Unknown platform variants remain a review decision, not inferred equivalence.
    """
    for old in existing:
        if old.get('state') not in ('ENABLED',1): continue
        if old.get('type') != proposed.get('type'): continue
        if old.get('profile_id') != proposed.get('profile_id'): continue
        if old.get('campaign_id') != proposed.get('campaign_id'): continue
        old_group = old.get('ad_group_id')
        if old_group and old_group != proposed.get('ad_group_id'): continue
        if old.get('match_type') == proposed.get('match_type') and normalize(old['value'])==normalize(proposed['value']):
            return {'status':'already-covered','existing_id':old['id']}
        if proposed['type']=='KEYWORD' and old.get('match_type')=='PHRASE' and proposed.get('match_type') in ('EXACT','PHRASE'):
            # Whitespace-delimited phrase only. Do not assume classifier punctuation/compact matching equals Amazon.
            words, needle = normalize(proposed['value']).split(),normalize(old['value']).split()
            if any(words[i:i+len(needle)]==needle for i in range(len(words)-len(needle)+1)):
                return {'status':'already-covered','existing_id':old['id']}
    return {'status':'not-covered-in-supplied-snapshot','existing_id':None}


def markdown(plan):
    def safe(s): return str(s).replace('|',' / ').replace('\n',' ')
    if plan.get('mode') == 'standalone':
        return '\n'.join(['# Campaign structure suggestions', '',
            f"**{safe(plan['source']['brand'])}**", '',
            *['- ' + item for item in plan['suggestions']], '', *structure_markdown(plan['product_structure']), plan['next_step'], '',
            'Your report and brand rules remain usable without connecting. No account changes have been made.', ''])
    out=['# Campaign separation plan','',f"**{safe(plan['source']['brand'])}** · {plan['source']['observed_start']} to {plan['source']['observed_end']}",'',
         'Proposed plan. No account changes have been made.','',plan['rationale'],'',
         *structure_markdown(plan['product_structure']), *migration_markdown(plan['migration']),
         '## First-wave evidence to review','',plan['legacy_action'], '']
    if plan['pilot_source']:
        p=plan['pilot_source']; out += [f"Start by reviewing **{safe(p['campaign_name'])} / {safe(p['ad_group_name'])}**.",
            f"Source campaign `{p['campaign_id']}`, ad group `{p['ad_group_id']}`.",'']
        scope=plan['migration']['first_wave_scope_review']
        if scope['product_candidates']:
            out += [f"The selected product candidates also appear across {len(scope['shared_product_groups'])} mapped source groups in the supplied product snapshot. Review those sources together before defining the wave, preserving distinct ad products, business intent and other products sharing those groups. Shared products do not automatically justify consolidation.",'']
        evidence=p.get('targeting_evidence')
        if evidence:
            keywords=evidence['reported_enabled_keywords']
            types=', '.join(sorted({t['match_type'] for t in keywords}))
            mix='Both branded and other keywords are present.' if evidence['brand_and_other_keywords'] else 'The supplied keyword inventory does not show both classes.'
            out += [f"Targeting context: {len(keywords)} reported enabled keyword rows ({types}). {mix} Individual keyword bids can differ. Review this structure before choosing new destinations; queries are not attributed to specific targets.",'']
        out += [
            '| Campaign | Action | Product candidates | Query evidence to review | Budget / bid / goal |',
            '|---|---|---|---|---|']
        for d in plan['destinations']:
            terms=', '.join(safe(t['text']) for t in d['keyword_candidates'][:4])
            products=', '.join(d['product_candidates'][:4]) or 'Needs product evidence'
            out.append(f"| {safe(d['proposed_name'])} | {d['action']} | {products} | {terms} | To decide |")
        out += ['', 'These candidates are only part of the wave. Create the branded destination and retain the existing campaign for non-brand after reviewed exclusions. Preserve useful auto, keyword and product targeting. Names, products and keywords require review: a model query may refer to a different product. Historical query sales do not establish query-to-product relevance.', '']
    out += ['## Decisions before creation','']+[f'- {x}' for x in plan['pending']]
    out += ['','## Current readiness','', 'This is a structure proposal. It is not ready for account execution. Current negative coverage and the migration gates above remain open.']
    out += ['','## Full review queue','',f"{len(plan['review_queue'])} ad groups with both branded and other text clicks. Prioritized by branded spend; the complete evidence is in the companion JSON.",'',
            'With Merch Jar connected, the next step is checking current setup and building a concrete paused-creation manifest. Keep this plan if you want to return later.','']
    return '\n'.join(out)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',required=True);p.add_argument('--output',required=True);p.add_argument('--markdown',required=True)
    p.add_argument('--pilot-group',nargs=2,metavar=('CAMPAIGN_ID','AD_GROUP_ID'))
    p.add_argument('--connected-context',help='Private receipt for successful current Merch Jar configuration reads')
    p.add_argument('--product-groups',type=Path,help='Proposed product groups spanning the known owned list')
    a=p.parse_args()
    paths=[Path(a.analysis).resolve(),Path(a.output).resolve(),Path(a.markdown).resolve()]
    if len(set(paths))!=3: raise ValueError('Input and output paths must differ')
    context_path = Path(a.connected_context).resolve() if a.connected_context else None
    if context_path and context_path in paths[1:]:
        raise ValueError('Connected context and output paths must differ')
    report=json.loads(paths[0].read_text(encoding='utf-8-sig'))
    context=json.loads(context_path.read_text(encoding='utf-8-sig')) if context_path else None
    if context:
        receipts = [(Path(r['receipt_file']) if Path(r['receipt_file']).is_absolute() else context_path.parent / r['receipt_file']).resolve()
                    for r in context.get('reads', {}).values() if r.get('receipt_file')]
        if any(p in paths[1:] for p in receipts):
            raise ValueError('Read receipts and output paths must differ')
    grouping=json.loads(a.product_groups.read_text(encoding='utf-8')) if a.product_groups else None
    plan=build_plan(report,a.pilot_group,context,context_path.parent if context_path else '.',grouping)
    for path in paths[1:]: path.parent.mkdir(parents=True,exist_ok=True)
    paths[1].write_text(json.dumps(plan,indent=2),encoding='utf-8');paths[2].write_text(markdown(plan),encoding='utf-8')
    print(json.dumps({'status':plan['status'],'mode':plan['mode']}))


if __name__=='__main__': main()
