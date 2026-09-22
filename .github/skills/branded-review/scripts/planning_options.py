"""Campaign grouping choices and scoped draft import. No account execution."""
from copy import deepcopy
from html.parser import HTMLParser
import argparse
import hashlib
import json
from pathlib import Path
from target_proposal import product_ad_groups

DEFAULTS = {'brand_campaigns':'shared', 'brand_ad_groups':'category',
            'brand_match':'phrase', 'defense_campaigns':'shared', 'defense_pairing':'related'}
ALLOWED = {'brand_campaigns':('shared','category'),
           'brand_ad_groups':('category','parent_family','single_asin','all_products'),
           'brand_match':('phrase','exact_phrase'), 'defense_campaigns':('shared','category'),
           'defense_pairing':('related','cross_sell','all_products')}


def settings(grouping=None):
    grouping=grouping or {}
    value=grouping.get('planning_options',{})
    if not isinstance(value,dict) or set(value)-set(DEFAULTS):raise ValueError('Unknown planning options')
    result={**DEFAULTS,**value}
    if 'planning_options' not in grouping and grouping.get('ad_group_mode'):
        result['brand_ad_groups']=grouping['ad_group_mode']
    for key,values in ALLOWED.items():
        if result[key] not in values:raise ValueError('Invalid planning choice: '+key)
    if result['brand_ad_groups']=='all_products' and result['brand_campaigns']!='shared':
        raise ValueError('All products in one ad group needs one shared branded campaign')
    if result['defense_pairing']=='all_products' and result['defense_campaigns']!='shared':
        raise ValueError('A whole-catalog defense group needs one shared defense campaign')
    return result


def scope(report):
    return {key:report.get(key) for key in ('account_id','brand','currency','source_sha256')} | {
        'marketplace':report.get('context',{}).get('products',{}).get('marketplace')}


def baseline(report,grouping):
    data={'scope':scope(report),'groups':grouping or {'groups':[]},
          'reference':report.get('brand_reference',{}),'products':report.get('context',{}).get('products',{})}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def brand_ad_groups(asins, details, mode):
    if mode in ('category','all_products'):
        return [{'asin':asins[0] if len(asins)==1 else None,'advertised_asins':sorted(asins),'parent_asin':None}]
    return product_ad_groups(asins,details,mode)


def architecture(structure, options, grouping):
    groups=structure['groups'];details=structure['product_details']
    all_asins=sorted(a for g in groups for a in g['asins'])
    branded=[]
    for g in groups:
        for i,ag in enumerate(brand_ad_groups(g['asins'],details,options['brand_ad_groups'])):
            branded.append({**ag,'name':g['name'] if options['brand_ad_groups']=='category' else g['name']+' · '+str(i+1),
                            'category':g['name']})
    if options['brand_ad_groups']=='all_products' and all_asins:
        branded=[{'name':'All products','category':'All products','advertised_asins':all_asins,'parent_asin':None}]
    defense=[]
    if options['defense_pairing']=='cross_sell':
        for pair in grouping.get('defense_pairings',[]):
            ads=pair.get('advertised_asins',[]);targets=pair.get('target_asins',[])
            if not pair.get('name') or not pair.get('reason') or not ads or not targets:
                raise ValueError('Cross-sell groups need a name, reason, advertised ASINs and target ASINs')
            if any(not isinstance(v,list) or len(v)!=len(set(v)) or set(v)-set(all_asins) for v in (ads,targets)):
                raise ValueError('Cross-sell products must belong to the assigned owned catalog')
            defense.append({**pair,'category':pair['name'],'status':'Proposed pairing; compatibility needs review'})
    elif options['defense_pairing']=='all_products' and all_asins:
        defense=[{'name':'All owned products','category':'All products','advertised_asins':all_asins,
                  'target_asins':all_asins,'status':'Proposed whole-catalog pool; relevance needs review'}]
    else:
        defense=[{'name':g['name'],'category':g['name'],'advertised_asins':g['asins'],
                  'target_asins':g['asins'],'status':'Proposed same-category pool; review every eligible pairing'} for g in groups]
    bc=len(groups) if options['brand_campaigns']=='category' else int(bool(branded))
    dc=len(defense) if options['defense_campaigns']=='category' else int(bool(defense))
    return {'options':options,'branded_ad_groups':branded,'defense_ad_groups':defense,
            'proposed_branded_campaigns':bc,'proposed_branded_ad_groups':len(branded),
            'proposed_defense_campaigns':dc,'proposed_defense_ad_groups':len(defense),
            'proposed_total_campaigns':bc+dc,'defense_pairing_pending':options['defense_pairing']=='cross_sell' and not defense}


def apply_draft(report,grouping,draft):
    if report.get('simulation') or report.get('privacy') or draft.get('simulation'):
        raise ValueError('Demo or privacy choices cannot update a real plan')
    if draft.get('schema')!='brand-planning-draft/1' or draft.get('scope')!=scope(report):
        raise ValueError('Planning draft belongs to another report or account')
    if draft.get('baseline_sha256')!=baseline(report,grouping):
        raise ValueError('Planning draft is stale; export choices from the current report')
    if not isinstance(draft.get('options'),dict) or set(draft['options'])!=set(DEFAULTS):
        raise ValueError('Planning draft needs all five choices')
    result=deepcopy(grouping or {'groups':[]})
    result['planning_options']=settings({'planning_options':draft.get('options')})
    result.pop('ad_group_mode',None)
    from structure_plan import build_structure
    build_structure(report,result)
    return result


def read_draft(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    if text.lstrip().startswith('{'):return json.loads(text)
    class Reader(HTMLParser):
        def __init__(self):super().__init__();self.active=False;self.items=[]
        def handle_starttag(self,tag,attrs):
            if tag=='script' and dict(attrs).get('id')=='planning-draft':
                self.active=True;self.items.append('')
        def handle_endtag(self,tag):
            if tag=='script':self.active=False
        def handle_data(self,data):
            if self.active:self.items[-1]+=data
    reader=Reader();reader.feed(text)
    if len(reader.items)!=1:raise ValueError('Saved HTML needs exactly one planning draft')
    return json.loads(reader.items[0])


def main():
    p=argparse.ArgumentParser(description='Validate report choices and save a proposed grouping. No API calls.')
    p.add_argument('--analysis',type=Path,required=True);p.add_argument('--product-groups',type=Path,required=True)
    p.add_argument('--draft',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve() in {a.analysis.resolve(),a.draft.resolve()}:raise ValueError('Output cannot replace report inputs')
    report=json.loads(a.analysis.read_text(encoding='utf-8'));grouping=json.loads(a.product_groups.read_text(encoding='utf-8'))
    result=apply_draft(report,grouping,read_draft(a.draft))
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'product_groups':str(a.output.resolve()),'plan_review_required':True,'account_changes':False}))


if __name__=='__main__':main()
