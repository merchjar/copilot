"""Reviewable keyword candidates and owned-product defense, never an executable build."""
from collections import defaultdict
from decimal import Decimal
import re


def parent_asin(product):
    raw=product.get('parent_asin',[])
    valid={p for p in raw if isinstance(p,str) and re.fullmatch(r'(?:B[A-Z0-9]{9}|[0-9]{10})',p)}
    return next(iter(valid)) if len(valid)==1 and len(set(raw))==1 else None


def product_ad_groups(asins, details, mode):
    if mode not in ('single_asin','parent_family'): raise ValueError('Choose single_asin or parent_family ad groups')
    families=defaultdict(list)
    for asin in sorted(asins):
        parent=parent_asin(details.get(asin,{}))
        key=('parent',parent) if mode=='parent_family' and parent else ('asin',asin)
        families[key].append(asin)
    return [{'asin':values[0] if len(values)==1 else None,'advertised_asins':values,
             'parent_asin':key[1] if key[0]=='parent' else None} for key,values in families.items()]


def query_evidence(report):
    values=defaultdict(lambda:{'spend':Decimal(0),'sales':Decimal(0),'rows':0})
    for row in report.get('rows',[]):
        if row.get('category')!='brand_query' or not row.get('query'):continue
        key=' '.join(row['query'].casefold().split());value=values[key]
        value['spend']+=Decimal(str(row.get('spend',0)));value['sales']+=Decimal(str(row.get('sales',0)));value['rows']+=1
    return values


def keyword_candidates(items, allowed_asins, evidence):
    if not isinstance(items,list):raise ValueError('Keyword candidates must be a list')
    candidates=[];seen=set()
    for item in items:
        if isinstance(item,str):item={'term':item}
        term=item.get('term','').strip()
        key=' '.join(term.casefold().split())
        if not term or key in seen:raise ValueError('Keyword candidates need unique nonempty terms')
        seen.add(key)
        matches=item.get('match_types',['EXACT','PHRASE'])
        if not isinstance(matches,list) or not matches or len(set(matches))!=len(matches) or set(matches)-{'EXACT','PHRASE'}:
            raise ValueError('Branded keyword proposal supports Exact and Phrase')
        selected=item.get('advertised_asins',[])
        if not isinstance(selected,list) or len(set(selected))!=len(selected) or set(selected)-set(allowed_asins):
            raise ValueError('Keyword product selection must stay within its proposed family')
        observed=evidence.get(key)
        if item.get('basis')=='observed' and not observed:raise ValueError('Claimed observed brand keyword is absent from the report')
        candidates.append({'term':term,'match_types':matches,'advertised_asins':selected,
            'reason':item.get('reason','Review relevance for the advertised product'),
            'evidence':'Observed branded search' if observed else 'Proposed keyword; not observed in this report',
            'reported_spend':str(observed['spend']) if observed else None,
            'reported_sales':str(observed['sales']) if observed else None,
            'status':'proposed; product relevance and launch settings need review'})
    return candidates


def defense_proposal(brand, name, asins, details, ad_groups):
    pairs=[]
    for group in ad_groups:
        advertised=group['advertised_asins'];parents={parent_asin(details.get(a,{})) for a in advertised}-{None}
        related=[a for a in asins if a not in advertised and parent_asin(details.get(a,{})) in parents]
        pairs.append({'advertised_asins':advertised,'suggested_variation_targets':related,
                      'status':'review related variations' if related else 'choose relevant owned-product targets'})
    return {'campaign_name':f'{brand} | {name} | Own products','action':'propose-new-defense',
        'targeting_method':'PRODUCT','match':'specific owned ASINs; expanded targeting off in the proposed build',
        'candidate_target_asins':sorted(asins),'ad_groups':pairs,'targets_finalized':False,
        'existing_coverage':'Reuse a suitable dedicated defense campaign only after current configuration review',
        'other_asins':'Keep useful other-ASIN targeting in existing campaigns',
        'scope_note':'The family list is a target pool for review, not every ASIN assigned to every ad group'}
