"""Read-only Merch Jar report through the installed Connect client.

Only GET /profiles and POST /segments/preview are called. No account writes.
"""
import argparse
import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time
from analyze_search_terms import analyze, METRICS, REQUIRED, LABELS, empty_metrics, present
import kdp
from report_render import render
from report_delivery import report_artifact


def metric_fields(start,end):
    suffix=f'{start}_to_{end}'
    return {k:f'{v}_{suffix}' for k,v in {'spend':'cost','sales':'sales','clicks':'clicks','purchases':'orders','impressions':'impressions'}.items()}


# Book (KDP) fields returned by segment previews; the adjusted values apply the account's Ad Impact Multipliers.
KDP_FIELDS=('pages_read','estimated_royalties','adjusted_sales','adjusted_pages_read','adjusted_estimated_royalties')
KENP_COLUMNS={'royalties':'Estimated KENP royalties','pages':'KENP pages read','sales':'KENP sales basis'}


def kdp_fields(start,end):
    return {k:f'{k}_{start}_to_{end}' for k in KDP_FIELDS}


def same_totals(first,current):
    """Page-global totals must describe one population. Integer counts compare exactly; decimal amounts
    tolerate float summation noise in the last digits (36185.15999999996 versus 36185.15999999992)."""
    if not isinstance(first,dict) or not isinstance(current,dict): return first==current
    if set(first)!=set(current): return False
    for k,a in first.items():
        b=current[k]
        if isinstance(a,bool) or isinstance(b,bool) or not isinstance(a,(int,float)) or not isinstance(b,(int,float)):
            if a!=b: return False
        elif isinstance(a,int) and isinstance(b,int):
            if a!=b: return False
        elif not math.isclose(a,b,rel_tol=0,abs_tol=1e-4):
            return False
    return True


def kdp_sums(rows,reported,start,end):
    """Sum optional KDP fields and reconcile each to the preview's global total. Absent fields stay absent."""
    out={}
    for name,f in kdp_fields(start,end).items():
        if f not in (reported or {}): continue
        values=[r.get(f) for r in rows]
        total=Decimal(str(reported[f]))
        if any(v is None for v in values):
            if total: raise ValueError(f'Missing metric {f}')
            out[name]=Decimal(0); continue
        out[name]=sum((Decimal(str(v)) for v in values),Decimal(0))
        if not out[name].is_finite() or abs(out[name]-total) > Decimal('0.005'):
            raise ValueError(f'Preview {name} does not reconcile to its global total')
    return out


def collect(client,key,profile,ad_type,start,end,folder,pause=time.sleep,kdp_receipt=None):
    fields=metric_fields(start,end)
    trigger=' or '.join(f'{f}({start}..{end}) > 0' for f in ('impressions','spend','sales'))
    rows=[]; first=None; page=1
    while True:
        body={'profile_id':profile,'ad_type':ad_type,'trigger':trigger,'action':'set_state',
              'action_params':{'value':2},'per_page':100,'page':page}
        result=client.request_json('POST','/api/v5/segments/preview',key,body=body)
        if folder:
            (folder/f'{ad_type}-page-{page}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        meta=result.get('pagination',{})
        if meta.get('page')!=page or not isinstance(meta.get('total'),int) or not isinstance(meta.get('last_page'),int):
            raise ValueError('Unsupported or missing preview pagination')
        if first is None: first={'total':meta['total'],'last_page':meta['last_page'],'totals':result.get('totals')}
        if (meta['total'],meta['last_page']) != (first['total'],first['last_page']) or not same_totals(first['totals'],result.get('totals')):
            raise ValueError('Preview population changed during pagination; retain receipts and refresh consistently')
        batch=result.get('data')
        if not isinstance(batch,list) or (not batch and page < meta['last_page']):
            raise ValueError('Incomplete preview page')
        for r in batch:
            if str(r.get('profile_id')) != profile: raise ValueError('Preview contains a different profile')
            for f in fields.values():
                if f not in r or r[f] is None: raise ValueError(f'Missing metric {f}')
                if not Decimal(str(r[f])).is_finite(): raise ValueError('Nonfinite preview metric')
        rows.extend(batch)
        if page >= max(1,meta['last_page']): break
        pause(2.1);page+=1
    if len(rows)!=first['total']: raise ValueError('Preview row count does not reconcile')
    grain=('campaign_id','ad_group_id','search_term') if ad_type=='search_terms' else ('campaign_id',)
    identities=[tuple(r.get(f) for f in grain) for r in rows]
    if len(set(identities))!=len(identities): raise ValueError('Duplicate preview identity; do not double count')
    totals={k:sum((Decimal(str(r[f])) for r in rows),Decimal(0)) for k,f in fields.items()}
    for k,f in fields.items():
        reported=(first['totals'] or {}).get(f)
        if reported is None:
            if rows: raise ValueError(f'Missing preview aggregate {f}')
        elif abs(totals[k]-Decimal(str(reported))) > (Decimal('0.005') if k in ('spend','sales') else Decimal(0)):
            raise ValueError(f'Preview {k} does not reconcile to its global total')
    if kdp_receipt is not None:
        kdp_receipt.update(kdp_sums(rows,first['totals'],start,end))
    return rows,totals


def kenp_plan(sums,force=False):
    """Choose the KENP basis for connected data. Adjusted values are preferred; raw values are a disclosed fallback."""
    activity=any(sums.get(k) for k in ('pages_read','estimated_royalties','adjusted_pages_read','adjusted_estimated_royalties'))
    if not (activity or force) or 'estimated_royalties' not in sums and 'adjusted_estimated_royalties' not in sums:
        return None
    adjusted='adjusted_estimated_royalties' in sums and 'adjusted_sales' in sums
    disclosures=[]
    multipliers={}
    if adjusted:
        for label,raw,adj in (('KENP royalties','estimated_royalties','adjusted_estimated_royalties'),
                              ('KENP pages read','pages_read','adjusted_pages_read'),('Sales','sales','adjusted_sales')):
            if sums.get(raw) and adj in sums:
                multipliers[label]=float(sums[adj]/sums[raw])
        active={k:v for k,v in multipliers.items() if abs(v-1)>0.0005}
        if active:
            disclosures.append('Merch Jar Ad Impact Multipliers other than 1 are in effect: '+', '.join(f'{k} x{v:.2f}' for k,v in active.items())+
                               ' (effective rate from adjusted versus reported totals). ACoS incl. KENP uses the adjusted values; standard ACoS uses reported sales.')
        else:
            disclosures.append('ACoS incl. KENP uses Merch Jar adjusted sales and adjusted KENP royalties. No multiplier other than 1 changed these totals.')
    else:
        disclosures.append('Adjusted values were unavailable, so ACoS incl. KENP uses reported sales and reported KENP royalties.')
    return {'adjusted':adjusted,'multipliers':multipliers,'disclosures':disclosures,
            'fields':{'royalties':'adjusted_estimated_royalties' if adjusted else 'estimated_royalties',
                      'pages':'adjusted_pages_read' if adjusted and 'adjusted_pages_read' in sums else 'pages_read',
                      'sales':'adjusted_sales' if adjusted else 'sales'}}


def normalize_rows(rows,profile,start,end,account_id,kenp=None):
    fields=metric_fields(start,end)
    names={**{k:f for k,f in kdp_fields(start,end).items()},'sales':fields['sales']}
    period=f"{date.fromisoformat(start):%b %d, %Y} - {date.fromisoformat(end):%b %d, %Y}"
    for r in rows:
        yield {'Budget currency':profile['currency_code'],'Date range':period,
               'Advertiser account ID':account_id,'Advertiser account name':profile.get('nickname') or profile['name'],
               'Campaign ID':str(r['campaign_id']),'Campaign name':r.get('campaign_name',''),
               'Ad group ID':str(r.get('ad_group_id') or ''),'Ad group name':r.get('ad_group_name',''),
               'Search term':r.get('search_term') or '',**{METRICS[k]:str(r[f]) for k,f in fields.items()},
               **({KENP_COLUMNS[k]:str(r.get(names[f]) if r.get(names[f]) is not None else 0) for k,f in kenp['fields'].items()} if kenp else {})}


def empty_report(source,profile,brand,start,end,reference=None):
    zero=present(empty_metrics())
    return {'schema':'brand-traffic-review/connected','brand':brand,'advertiser':profile.get('nickname') or profile['name'],
        'currency':profile['currency_code'],'account_id':str(profile['profile_id']),
        'source_path':str(source.resolve()),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'source_rows':0,'selected_rows':0,'excluded_other_scope_rows':0,'campaign_count':0,'ad_group_count':0,
        'observed_start':start,'observed_end':end,'brand_reference':{'aliases':[brand],'rules':(reference or {}).get('rules',[]),'website':(reference or {}).get('website')},
        'context':{},'totals':zero,'groups':[{'category':k,'label':v,'rows':0,**zero} for k,v in LABELS.items()],
        'mixed_campaign_count':0,'campaigns':[],'terms':[],'rows':[],'limitations':[]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--client',required=True,help='Installed merchjar-connect/scripts/merchjar_client.py')
    p.add_argument('--profile',required=True);p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    p.add_argument('--brand',required=True);p.add_argument('--brand-reference');p.add_argument('--output-dir',required=True)
    p.add_argument('--html-output',required=True)
    p.add_argument('--state',help='Existing private progress file for this same report')
    p.add_argument('--catalog',help='Reuse the scoped verified owned-ASIN catalog')
    p.add_argument('--marketplace',help='Marketplace matching the saved brand reference and catalog')
    p.add_argument('--account-type',choices=['kdp'],help='The user confirmed this account advertises books (KDP)')
    a=p.parse_args()
    if not a.profile.isdecimal(): raise ValueError('Use a resolved Merch Jar profile ID')
    if date.fromisoformat(a.start)>date.fromisoformat(a.end): raise ValueError('Reversed reporting dates')
    client_path=Path(a.client).resolve()
    spec=importlib.util.spec_from_file_location('installed_merchjar_client',client_path)
    client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
    key=client.load_api_key()
    profiles=client.request_json('GET','/api/v5/profiles',key)['data']
    profile=next((x for x in profiles if str(x['profile_id'])==a.profile),None)
    if profile is None: raise ValueError('Selected profile is not accessible with this connection')
    reference=json.loads(Path(a.brand_reference).read_text(encoding='utf-8-sig')) if a.brand_reference else None
    account_id=a.profile
    if reference:
        if str(reference.get('merchjar_profile_id'))!=a.profile:
            raise ValueError('Reference needs a verified merchjar_profile_id mapping before connected reuse')
        if reference.get('currency')!=profile['currency_code'] or reference.get('brand')!=a.brand:
            raise ValueError('Reference currency or brand differs')
        account_id=reference['account_id']
    folder=Path(a.output_dir).resolve();folder.mkdir(parents=True,exist_ok=True)
    source=folder/'connected-search-terms.csv'
    html_path=Path(a.html_output).resolve()
    reserved={client_path,folder/'analysis.json',source}
    if a.brand_reference: reserved.add(Path(a.brand_reference).resolve())
    if a.catalog: reserved.add(Path(a.catalog).resolve())
    from report_workspace import write_workspace, output_paths
    if set(output_paths(html_path,a.state)) & reserved:
        raise ValueError('Workspace output must not overwrite a source, client or reference')
    search_kdp,campaign_kdp={},{}
    rows,totals=collect(client,key,a.profile,'search_terms',a.start,a.end,folder,kdp_receipt=search_kdp)
    time.sleep(2.1)
    campaigns,campaign_totals=collect(client,key,a.profile,'campaigns',a.start,a.end,folder,kdp_receipt=campaign_kdp)
    kenp=kenp_plan({**search_kdp,'sales':totals['sales']},force=a.account_type=='kdp') if rows else None
    with source.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=REQUIRED+(list(KENP_COLUMNS.values()) if kenp else []));w.writeheader()
        w.writerows(normalize_rows(rows,profile,a.start,a.end,account_id,kenp))
    catalog=json.loads(Path(a.catalog).read_text(encoding='utf-8')) if a.catalog else None
    kenp_spec={**KENP_COLUMNS,'source':'Merch Jar connection','values':'adjusted' if kenp['adjusted'] else 'reported',
               'disclosures':kenp['disclosures'],'activity_label':'Merch Jar data reports KENP page reads'} if kenp else None
    report=analyze(source,profile.get('nickname') or profile['name'],profile['currency_code'],a.brand,[],reference,
        marketplace=a.marketplace,catalog=catalog,account_type=a.account_type,kenp_columns=kenp_spec) if rows else empty_report(source,profile,a.brand,a.start,a.end,reference)
    report['schema']='brand-traffic-review/connected'
    report['account_id']=account_id
    report['account_totals']=present(campaign_totals)
    report['account_coverage']={'source':'Same-profile, same-period campaign preview','campaign_rows':len(campaigns),
        'search_to_campaign_delta':{k:str(campaign_totals[k]-totals[k]) for k in totals},
        'reconciled':campaign_totals==totals}
    if kenp and 'kenp' in report:
        f=kenp['fields']
        if not all(k in campaign_kdp or k=='sales' for k in f.values()):
            raise ValueError('Campaign preview lacks the KDP fields used for search terms')
        report['account_totals']['kenp']=kdp.present(campaign_totals['spend'],campaign_kdp[f['royalties']],
            campaign_kdp.get(f['pages'],Decimal(0)),campaign_totals['sales'] if f['sales']=='sales' else campaign_kdp[f['sales']])
        report['kenp']['multipliers']=kenp['multipliers']
        report['kenp']['fields']=f
        report['account_coverage']['kenp_royalties_delta']=str(campaign_kdp[f['royalties']]-Decimal(report['totals']['kenp']['royalties']))
    report['connection']={'profile_id':a.profile,'marketplace_id':profile.get('marketplace_id'),'timezone':profile.get('timezone'),
        'currency':profile['currency_code'],'read_at':datetime.now(timezone.utc).isoformat(),
        'source':'Read-only Segment previews','monetary_units':'Account currency units from preview metric fields; no cents conversion',
        'normalization':'Connected rows mapped to the shared calculation schema; not an Amazon console export'}
    report['limitations']=['Connected search-term and campaign totals are independently reconciled to each preview population.',
        'Differences between search terms and campaigns remain visible; never allocate the gap to non-brand.',
        'Data freshness and attribution maturity depend on source sync; recent sales can change.',
        'Connected report does not itself establish complete product ownership or current negative coverage.']
    saved=write_workspace(report,html_path,a.state)
    (folder/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'profile_id':a.profile,'rows':len(rows),'campaigns':len(campaigns),'totals':report['totals'],
                      'account_coverage':report['account_coverage'],'account_changes':0,
                      **saved}))


if __name__=='__main__': main()
