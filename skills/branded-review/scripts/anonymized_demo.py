"""Allowlist real performance into a fictional identity; never copy raw free text."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from privacy_report import presentation

BRAND = 'Alder Auto'
ALIASES = ['Alder Auto', 'Alder Auto US', 'DA10', 'DA16', 'DA22', 'R1200',
           'Shift-CS', 'Shift-S', 'Mount16', 'Air16', 'Foam Pro']
NAMES = ['Auto - All products', 'Research_Manual', 'Polishers | Broad | Main',
         'Alder Auto - Search', 'Polishing pads - Manual', 'Test - Accessories',
         'Catalog_Auto', 'Towels / Research', 'Foam cannons - Keywords',
         'Brushes - Products', 'Garage storage - Search', 'Manual_All',
         'Polishers - Exact', 'Auto - New products', 'Detailing kits', 'Test_Phrase']


def shifted(value):
    if not value:return None
    return (date.fromisoformat(value)-timedelta(days=21)).isoformat()


def make_demo(source, product_groups=None):
    result = presentation(source)
    result.pop('privacy')
    result.update({'advertiser':BRAND, 'brand':BRAND, 'account_id':'alder-auto-demo',
                   'simulation':True,
                   'observed_start':shifted(source['observed_start']),
                   'observed_end':shifted(source['observed_end']),
                   'source_path':'alder-auto-search-terms.csv',
                   'connection_context':{'state':'unavailable'},
                   'limitations':['Performance totals and traffic mix come from an anonymized account. Names, identifiers and dates have been replaced.',
                                  'Setup progress and proposed campaign changes are simulated. No account changes occurred.']})
    result.pop('connection', None)
    ref = source.get('brand_reference', {})
    aliases = [ALIASES[i] if i < len(ALIASES) else f'Alder Line {i+1}' for i,_ in enumerate(ref.get('aliases', []))]
    if not aliases: aliases=[BRAND]
    rules=[]
    for i,rule in enumerate(ref.get('rules', [])):
        assert rule.get('match','phrase') in ('phrase','exact','contains_compact')
        assert rule['status'] in ('approved','proposed','rejected')
        rules.append({'term':['aldar auto','alderauto','alder autto'][i] if i<3 else f'Alder variant {i+1}',
                      'match':rule.get('match','phrase'),'status':rule['status'],'source':'Demo brand spelling'})
    exceptions=[]
    for i,rule in enumerate(ref.get('exceptions', [])):
        assert rule['category'] in ('brand_query','other_query','brand_review')
        assert rule.get('match','phrase') in ('phrase','exact','contains_compact')
        assert rule['status'] in ('approved','proposed','rejected')
        exceptions.append({'term':f'Alder exception {i+1}','category':rule['category'],
                           'match':rule.get('match','phrase'),'status':rule['status']})
    result['brand_reference']={'aliases':aliases,'rules':rules,'exceptions':exceptions,
                               'status':'Demo names replacing the saved brand definitions'}
    candidates=['alderautox polisher', 'aldra auto foam cannon', 'alder car care', 'alderauto da16pro', 'aldr auto pads', 'alder auto kit pro']
    review_count=sum(t['category']=='brand_review' for t in source.get('terms', []))
    result['terms']=[{'category':'brand_review','query':t} for t in candidates[:min(review_count,6)]]

    # Preserve each campaign's actual traffic classes and spend, never its names or IDs.
    campaign_spend=defaultdict(Decimal)
    grouped=defaultdict(Decimal)
    grouped_sales=defaultdict(Decimal)
    for row in source.get('rows', []):
        key=str(row.get('campaign_id') or '(missing campaign ID)')
        campaign_spend[key]+=Decimal(row['spend'])
        grouped[(key,row['category'])]+=Decimal(row['spend'])
        grouped_sales[(key,row['category'])]+=Decimal(row.get('sales',0))
    ordered=sorted(campaign_spend,key=lambda key:(-campaign_spend[key],key))
    campaign_ids={key:f'demo-campaign-{i+1:03}' for i,key in enumerate(ordered)}
    names={key:f'{NAMES[i%len(NAMES)]} {i+1:03}' for i,key in enumerate(ordered)}
    result['rows']=[{'campaign_id':campaign_ids[key],'campaign_name':names[key],
                     'category':category,'spend':str(spend),'sales':str(grouped_sales[(key,category)])} for (key,category),spend in grouped.items()]

    products=source.get('context', {}).get('products', {})
    all_asins=set(products.get('owned_asins', []))
    for group in products.get('products_by_ad_group', []): all_asins.update(group['asins'])
    asin_map={asin:f'B0AR{i+1:06}' for i,asin in enumerate(sorted(all_asins))}
    assert not set(asin_map.values()) & all_asins
    if products:
        sanitized=result['context']['products']
        sanitized.update({'brand':BRAND,'marketplace':'AMAZON.COM',
            'observed_start':shifted(products['observed_start']), 'observed_end':shifted(products['observed_end']),
            'owned_asins':[asin_map[a] for a in products.get('owned_asins', [])],
            'catalog_complete':products.get('catalog_complete') is True,
            'products_by_ad_group':[{'campaign_id':campaign_ids[str(g['campaign_id'])],
                 'ad_group_id':f'demo-adgroup-{i+1:03}', 'asins':[asin_map[a] for a in g['asins']]}
                 for i,g in enumerate(products.get('products_by_ad_group', [])) if str(g['campaign_id']) in campaign_ids]})
    if product_groups:
        from structure_plan import build_structure
        from target_proposal import parent_asin
        structure=build_structure(source,product_groups)
        # Group labels and titles are generated afresh; raw free text never enters the demo.
        labels=['Tool parts','Detailing brushes','Towels and wash mitts','Polishing pads',
                'Applicators','Garage storage','Garage tools','Polishers','Wash tools',
                'Detailing kits','Car-care liquids','Inspection lights','Car dryers']
        keyword_labels=[['backing plate','backing pad','rotary extension'],['detailing brushes','wheel brush','tire brush','brush'],
            ['drying towel','microfiber towel','drying towels','wash mitt'],['polishing pads','polisher pads','pads'],
            ['clay bar','detailing clay','clay pad','applicator'],['bottle holder','spray bottle holder','polisher holder','brush holder','foam cannon holder'],
            ['detailing seat','gloves'],['polisher','polishers','dual action polisher','rotary polisher','mini polisher','P15 polisher','P21 polisher','P8 polisher'],
            ['foam cannon','car wash foam cannon','spray bottle','bucket'],['detailing kits','wash kit'],['car wash soap'],
            ['inspection light','paint correction light','light'],['blower','air blower']]
        demo_groups=[]
        for i,g in enumerate(structure['groups']):
            name=labels[i] if i<len(labels) else f'Product family {i+1}'
            demo_groups.append({'name':name,'asins':[asin_map[a] for a in g['asins']],
                'keyword_candidates':[{'term':f'{BRAND} {keyword_labels[i][n] if i<len(keyword_labels) and n<len(keyword_labels[i]) else name.lower()+" selection "+str(n+1)}',
                    'advertised_asins':[asin_map[a] for a in k['advertised_asins']],
                    'match_types':k['match_types'],'reason':'Fictional demonstration of a product-specific keyword proposal'}
                    for n,k in enumerate(g['keyword_candidates'])],
                'reason':'Proposed related products sharing a branded budget; review before creation.'})
        result['demo_product_groups']={'account_id':result['account_id'],'marketplace':'AMAZON.COM','groups':demo_groups,
            'planning_options':structure['options'],'shared_brand_keywords':[BRAND,'AlderAuto']}
        by_asin={a:g['name'] for g in demo_groups for a in g['asins']}
        source_details={p['asin']:p for p in products.get('catalog_products',[])}
        parents=sorted({parent_asin(p) for p in source_details.values()}-{None})
        parent_map={p:f'B0PV{i+1:06}' for i,p in enumerate(parents)}
        result['context']['products']['catalog_products']=[{'asin':asin_map[a],'title':[f"Alder Auto {by_asin.get(asin_map[a],'product to review')} {i+1:03}"],
            'parent_asin':[parent_map[parent_asin(source_details[a])]] if a in source_details and parent_asin(source_details[a]) else []}
            for i,a in enumerate(sorted(asin_map))]
    targeting=source.get('context', {}).get('targeting')
    if targeting:
        result['context']['targeting'].update({'observed_start':shifted(targeting['observed_start']),
                                              'observed_end':shifted(targeting['observed_end'])})
    result['source_sha256']=hashlib.sha256(json.dumps({'brand':BRAND,'totals':result['totals'],'campaigns':len(ordered)},sort_keys=True).encode()).hexdigest()
    result['demo_pilot']={'source_campaign':names[ordered[0]] if ordered else 'Discovery - All products','products':'Polishers',
                          'branded_campaign':'Alder Auto | Polishers | Brand',
                          'defense_campaign':'Alder Auto | Polishers | Own products'}
    validate(source,result)
    return result


def validate(source,result):
    assert result['totals']==presentation(source)['totals']
    assert result['groups']==presentation(source)['groups']
    def inventory(report):
        groups=defaultdict(lambda:{'classes':set(),'spend':Decimal(0)})
        for row in report['rows']:
            group=groups[row['campaign_id']]
            group['classes'].add(row['category']);group['spend']+=Decimal(row['spend'])
        return sorted((tuple(sorted(g['classes'])),g['spend']) for g in groups.values())
    assert inventory(source)==inventory(result)
    assert len(source.get('context',{}).get('products',{}).get('owned_asins',[]))==len(result.get('context',{}).get('products',{}).get('owned_asins',[]))
    def counts(report):
        by_campaign=defaultdict(set)
        for group in report.get('context',{}).get('products',{}).get('products_by_ad_group',[]):
            by_campaign[group['campaign_id']].update(group['asins'])
        ids={row['campaign_id'] for row in report['rows']}
        return sorted(len(by_campaign[key]) for key in ids)
    assert counts(source)==counts(result)
    text=json.dumps(result).lower()
    assert source['account_id'].lower() not in text
    assert source['brand'].lower() not in text
    assert all(asin.lower() not in text for asin in source.get('context',{}).get('products',{}).get('owned_asins',[]))


def verify_html(source, html):
    """Scan literal HTML, embedded draft data and template scenes, not just visible text."""
    lower=html.lower()
    forbidden={source['account_id'],source['brand'],source.get('source_path','')}
    forbidden.update(source.get('context',{}).get('products',{}).get('owned_asins',[]))
    from target_proposal import parent_asin
    forbidden.update(parent_asin(p) for p in source.get('context',{}).get('products',{}).get('catalog_products',[]) if parent_asin(p))
    for row in source['rows']:
        if len(str(row['campaign_id']))>=8:forbidden.add(str(row['campaign_id']))
        # Short generic words may be legitimate copy; distinctive names are checked.
        if len(row.get('campaign_name',''))>=10: forbidden.add(row['campaign_name'])
    if source.get('brand_reference',{}).get('website'): forbidden.add(source['brand_reference']['website'])
    for term in forbidden:
        if term and term.lower() in lower:
            raise AssertionError('A source identifier remains in the demo HTML')
    import re
    assert not re.search(r'(?i)[a-z]:[\\/]+users[\\/]', html)
    return {'performance_metrics_preserved':True,'campaign_mix_preserved':True,
            'owned_asins':len(source.get('context',{}).get('products',{}).get('owned_asins',[])),
            'campaigns':len({r['campaign_id'] for r in source['rows']}),
            'identity_scan':'pass','progress':'simulated','account_requests':0}
