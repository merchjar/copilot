"""Complete known-product proposal. Proposed grouping never establishes live eligibility."""
from html import escape
import re
from brand_exclusions import draft as exclusion_draft
from target_proposal import parent_asin, product_ad_groups, query_evidence, keyword_candidates, defense_proposal
from planning_options import settings, architecture, brand_ad_groups


def build_structure(report, grouping=None):
    products = report.get('context', {}).get('products', {})
    owned = set(products.get('owned_asins', []))
    details = {p['asin']:p for p in products.get('catalog_products', [])}
    grouping = grouping or {'groups':[]}
    if not isinstance(grouping, dict) or not isinstance(grouping.get('groups'), list):
        raise ValueError('Product grouping needs a groups list')
    if grouping.get('account_id', report.get('account_id')) != report.get('account_id'):
        raise ValueError('Product groups belong to another account')
    if grouping.get('marketplace') and grouping['marketplace'] != products.get('marketplace'):
        raise ValueError('Product groups belong to another marketplace')
    assigned, names, groups = set(), set(), []
    options=settings(grouping)
    mode=options['brand_ad_groups']
    evidence=query_evidence(report)
    shared_input=grouping.get('shared_brand_keywords',list(dict.fromkeys([report['brand'],*report.get('brand_reference',{}).get('aliases',[])])))
    if any(isinstance(t,dict) and t.get('advertised_asins') for t in shared_input):
        raise ValueError('Shared brand keywords apply across the proposal. Keep product-scoped line terms in the detailed connected plan.')
    matches=['PHRASE'] if options['brand_match']=='phrase' else ['EXACT','PHRASE']
    shared=keyword_candidates([{**(t if isinstance(t,dict) else {'term':t}),'match_types':matches} for t in shared_input],owned,evidence)
    for item in grouping['groups']:
        name = item.get('name', '').strip()
        asins = item.get('asins', [])
        if not name or name.casefold() in names or not asins or not isinstance(asins, list):
            raise ValueError('Each product group needs a unique name and nonempty ASIN list')
        if any(not isinstance(a,str) or not re.fullmatch(r'(?:B[A-Z0-9]{9}|[0-9]{10})',a) for a in asins):
            raise ValueError('Product groups need valid ASINs')
        if len(set(asins)) != len(asins) or assigned.intersection(asins):
            raise ValueError('Each ASIN belongs to one primary branded group; review overlaps separately')
        if set(asins) - owned:
            raise ValueError('Product groups contain ASINs outside the confirmed owned list')
        if not item.get('reason', '').strip():
            raise ValueError('Explain why each group shares a budget and goal')
        names.add(name.casefold()); assigned.update(asins)
        ad_groups=brand_ad_groups(asins,details,mode)
        groups.append({'name':name, 'asins':sorted(asins), 'reason':item['reason'],
            'status':'proposed, eligibility and grouping need review',
            'campaign_name':f"{report['brand']} | {name} | Brand" if options['brand_campaigns']=='category' else f"{report['brand']} | Brand",
            'action':'create-new-branded', 'ad_groups':ad_groups,
            'targeting_method':'KEYWORD',
            'keyword_plan':{'match_types':matches, 'status':'proposed; review approved brand terms and product relevance',
                'brand_name_example':report['brand'],
                'selection':'Approved brand names and spellings; category names organize products, not keywords',
                'targets_finalized':False},
            'keyword_candidates':[],
            'defense':defense_proposal(report['brand'],name,asins,details,ad_groups),
            'other_products':'Retain existing coverage; separate only for a distinct goal or a verified gap'})
    held = sorted(owned - assigned)
    result={'schema':'brand-product-structure/1', 'catalog_complete':products.get('catalog_complete') is True,
        'known_products':len(owned), 'assigned_products':len(assigned), 'held_products':held,
        'proposed_branded_campaigns':len(groups), 'proposed_branded_ad_groups':sum(len(g['ad_groups']) for g in groups),
        'proposed_defense_campaigns':len(groups),'proposed_total_campaigns':len(groups)*2,
        'proposed_defense_ad_groups':sum(len(g['ad_groups']) for g in groups),
        'ad_group_mode':mode, 'shared_brand_keywords':shared,
        'parent_coverage':{'with_parent':sum(bool(parent_asin(details.get(a,{}))) for a in owned),
            'without_parent':sum(not parent_asin(details.get(a,{})) for a in owned),
            'parents':len({parent_asin(details.get(a,{})) for a in owned}-{None}),
            'variation_ad_groups':sum(len(product_ad_groups(g['asins'],details,'parent_family')) for g in groups)},
        'grouping_complete_for_known_products':bool(owned) and not held,
        'groups':groups, 'product_details':details, 'execution_ready':False,
        'eligibility':'Ownership does not establish current inventory, eligibility or whether a product should be advertised',
        'default':'One branded campaign with related-category ad groups; offer independent budgets and finer product groups',
        'legacy_default':'Retain suitable existing campaigns for non-brand after reviewed replacement delivery and exclusions',
        'pilot_selected':False}
    result.update(architecture(result,options,grouping))
    return result


def needs_asins(report):
    products = report.get('context', {}).get('products', {})
    return not products.get('owned_asins') and any(g.get('category') in ('owned_asin','asin_unknown') and
        int(g.get('rows',0)) > 0 for g in report.get('groups',[]))


def conversation_action(report):
    """Return the useful next input/action with the report receipt so agents cannot miss it."""
    available=bool(report.get('connection')) or report.get('connection_context',{}).get('state') in ('verified','configured_unverified')
    if needs_asins(report):
        unknown=next(g for g in report['groups'] if g['category']=='asin_unknown')
        return {'action':'read_available_products' if available else 'request_asin_list',
            'unresolved_asin_spend':unknown['spend'], 'currency':report['currency'],
            'say':'Explain the unresolved ASIN spend. Use the available connection to check advertised products.' if available else
                  'Explain the unresolved ASIN spend and recommend uploading the brand ASIN list or Amazon Ads default Advertised product report. Product names also support campaign grouping.',
            'catalog_caveat':'Advertised products are only a partial catalog; do not call unmatched ASINs competitors.'}
    if report.get('context',{}).get('products',{}).get('owned_asins'):
        return {'action':'propose_full_product_structure',
                'say':'Propose the whole known-product structure with brand Phrase keywords and visual grouping choices. Explain shared versus separate budgets and defense ads versus targets before a rollout. See product-structure.md.'}
    return {'action':'review_structure','say':'Explain the available campaign proposal and the next useful decision; use existing connection context before offering setup.'}


def asin_help():
    return '''<details class="asin-help"><summary>How to add your ASINs</summary><p>Upload a list of ASINs that belong to this brand and marketplace, or upload Amazon Ads' default <b>Advertised product</b> report. Include product names if you have them so Copilot can suggest useful campaign groups.</p><p>In Amazon Ads, open <b>Measurement &amp; reporting → Reporting</b>, choose the <b>Advertised product</b> template, select this account and a recent reporting period, then generate and download the CSV. Attach it in the same conversation and say, “Add my products to the report.”</p><p>This report covers advertised products. For the full brand catalog, paste or upload your own ASIN list, including products not currently advertised. With Merch Jar available, Copilot can also check advertised products through the connection; that is still not proof of a complete catalog.</p></details>'''


def lists_html(report):
    if report.get('privacy'): return ''
    ref = report.get('brand_reference', {})
    names = list(dict.fromkeys([report.get('brand',''), *ref.get('aliases',[])]))
    names = [n for n in names if n]
    rules = [r for r in ref.get('rules',[]) if r.get('status') == 'approved']
    terms = ''.join(f'<span class="list-term">{escape(n)}</span>' for n in names)
    labels={'phrase':'Search contains this phrase','exact':'Only this search','contains_compact':'Joined or spaced spelling'}
    extra = ''.join(f'<li>{escape(r["term"])} <small>({labels.get(r.get("match","phrase"),"Review matching")})</small></li>' for r in rules)
    keywords=[e for e in exclusion_draft(report)['entries'] if e['type']=='KEYWORD']
    negative_rows=''.join(f'<li><span>{escape(e["value"])}</span><small>Negative {"phrase" if e["match_type"]=="PHRASE" else "exact"}</small></li>' for e in keywords)
    negative_html=f'<h3 class="negative-heading">Proposed negative keywords</h3><p>For non-branded campaigns, after the new branded campaigns are delivering.</p><ul class="negative-keyword-list">{negative_rows}</ul><p><b>Negative phrase</b> excludes searches containing the brand phrase, including longer searches. <b>Negative exact</b> is a narrower option for a specific search. Amazon may also match close variations; review spellings before applying.</p>' if keywords else '<p>No negative keywords are ready to propose. Confirm the brand names first.</p>'
    exceptions = [r for r in ref.get('exceptions',[]) if r.get('status')=='approved']
    exceptions_html = '<details><summary>Saved exceptions</summary><ul>'+''.join(f'<li>{escape(r["term"])}: {escape(r.get("category","review"))}</li>' for r in exceptions)+'</ul></details>' if exceptions else ''
    owned = sorted(set(report.get('context', {}).get('products', {}).get('owned_asins', [])))
    complete = report.get('context', {}).get('products', {}).get('catalog_complete') is True
    asin_preview = ' '.join(f'<code>{escape(a)}</code>' for a in owned[:6])
    all_asins = '<details><summary>View all '+str(len(owned))+' ASINs</summary><div class="saved-asin-list">'+' '.join(f'<code>{escape(a)}</code>' for a in owned)+'</div></details>' if len(owned)>6 else ''
    return f'''<section class="saved-lists"><h2>Review the lists used in this plan</h2><div class="saved-list-columns"><div><h3>Brand names and product lines</h3><div class="list-terms">{terms}</div>{'<details><summary>How additional spellings count in this report</summary><ul>'+extra+'</ul></details>' if extra else ''}{exceptions_html}{negative_html}<p class="field-note">The report groups case, spacing and hyphen variants together. That does not automatically add those spellings as Amazon negatives.</p></div><div><h3>Your product ASINs</h3><p><b>{len(owned)} owned ASINs</b> · {'Complete catalog as supplied' if complete else 'Partial list' if owned else 'List needed'}</p><div class="saved-asin-preview">{asin_preview}</div>{all_asins}<p>Use these as <b>negative product targets</b> in non-branded campaigns where supported, after separate own-product defense delivery has been reviewed. ASINs are product exclusions, not Negative phrase keywords.</p>{asin_help() if not complete else ''}</div></div><p>All negatives above are proposals. Saving these lists does not apply them to campaigns.</p><button type="button" class="quiet-button" data-edit-brand-lists>Review or edit these lists</button></section>'''


def structure_html(report, grouping=None):
    if report.get('privacy'): return ''
    from planning_view import render
    return render(report, grouping, build_structure(report, grouping))
