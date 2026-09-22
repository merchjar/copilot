"""Validate user-returned report edits and save scoped preferences. No account calls."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from report_interactions import preferences


def read_draft(path):
    """Read JSON, or the single inert draft in an explicitly exported report. Never execute HTML."""
    text = path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() not in ('.html', '.htm'):
        return json.loads(text)
    class DraftReader(HTMLParser):
        def __init__(self):
            super().__init__(); self.blocks=[]; self.active=False
        def handle_starttag(self, tag, attrs):
            attrs=dict(attrs)
            if tag=='script' and attrs.get('id')=='brand-list-draft':
                if attrs.get('type')!='application/json': raise ValueError('Invalid embedded draft type')
                self.blocks.append(''); self.active=True
        def handle_data(self, data):
            if self.active: self.blocks[-1]+=data
        def handle_endtag(self, tag):
            if tag=='script': self.active=False
    parser=DraftReader(); parser.feed(text)
    if len(parser.blocks)!=1: raise ValueError('Use Save report with changes; this file has no unique embedded draft')
    return json.loads(parser.blocks[0])


def expand_delta(expected, edits):
    """Reconstruct against the fingerprinted current baseline; omitted fields stay unchanged."""
    allowed={'schema','simulation','status','scope','marketplace','report_source_sha256','baseline_sha256','changes'}
    if set(edits)!=allowed: raise ValueError('Unsupported fields in preference changes')
    for key in ('scope','marketplace','report_source_sha256','baseline_sha256'):
        if edits.get(key)!=expected[key]: raise ValueError('Draft is stale or belongs to a different report, account or marketplace')
    changes=edits.get('changes')
    permitted={'add_names','remove_names','add_asins','remove_asins','add_rules','remove_rules','catalog_complete'}
    if not isinstance(changes,dict) or set(changes)-permitted: raise ValueError('Unsupported preference changes')
    proposed=deepcopy(expected['baseline'])
    for field,container,key in [('names',proposed['brand_reference'],'aliases'),('asins',proposed,'owned_asins'),('rules',proposed['brand_reference'],'rules')]:
        added=changes.get('add_'+field,[]); removed=changes.get('remove_'+field,[])
        if not isinstance(added,list) or not isinstance(removed,list): raise ValueError('Changes must be lists')
        values=container.setdefault(key,[])
        for value in removed:
            if value not in values: raise ValueError('Removed item is missing from the original list')
            values.remove(value)
        for value in added:
            if value in values: raise ValueError('Added item is already in the list')
            values.append(value)
    if 'catalog_complete' in changes: proposed['catalog_complete']=changes['catalog_complete']
    return {**expected,'simulation':edits['simulation'],'status':edits['status'],'proposed':proposed}


def names(value):
    if not isinstance(value,list) or any(not isinstance(x,str) or not x.strip() for x in value):
        raise ValueError('Brand names must be nonempty strings')
    cleaned=[x.strip() for x in value]
    if len({x.casefold() for x in cleaned}) != len(cleaned):
        raise ValueError('Remove duplicate brand names')
    return cleaned


def asins(value):
    if not isinstance(value,list) or any(not isinstance(x,str) or not re.fullmatch(r'(?:B[A-Z0-9]{9}|[0-9]{10})',x) for x in value):
        raise ValueError('Owned ASINs must be valid uppercase ASINs')
    if len(set(value)) != len(value): raise ValueError('Remove duplicate ASINs')
    return sorted(value)


def prepare(report, edits, saved_reference=None, saved_catalog=None):
    if report.get('privacy') or report.get('simulation') or edits.get('simulation') is not False:
        raise ValueError('Privacy presentations and simulations cannot update real preferences')
    expected=preferences(report)
    if edits.get('schema')=='brand-review-preferences-draft/2':
        edits=expand_delta(expected,edits)
    if edits.get('schema') != expected['schema'] or edits.get('status') != 'draft_not_applied':
        raise ValueError('Unsupported preference draft')
    for key in ('scope','marketplace','report_source_sha256','baseline_sha256','baseline'):
        if edits.get(key) != expected[key]:
            raise ValueError('Draft is stale or belongs to a different report, account or marketplace')
    base=expected['baseline'];proposed=edits.get('proposed')
    if not isinstance(proposed,dict) or set(proposed)!=set(base):
        raise ValueError('Unsupported fields in preference draft')
    ref=proposed['brand_reference']
    if not isinstance(ref,dict): raise ValueError('Invalid brand reference')
    if {k:v for k,v in ref.items() if k not in ('aliases','rules')} != {k:v for k,v in base['brand_reference'].items() if k not in ('aliases','rules')}:
        raise ValueError('This editor changes names and rules only; saved exceptions and metadata must be preserved')
    aliases=names(ref.get('aliases'))
    if report['brand'].casefold() not in {x.casefold() for x in aliases}:
        raise ValueError('Keep the primary brand; change account brand scope separately')
    rules=ref.get('rules',[])
    if not isinstance(rules,list): raise ValueError('Invalid spelling rules')
    clean_rules=[]
    for rule in rules:
        if not isinstance(rule,dict) or not isinstance(rule.get('term'),str) or not rule['term'].strip():
            raise ValueError('Every rule needs a term')
        if rule.get('match','phrase') not in ('phrase','exact','contains_compact') or rule.get('status') not in ('approved','proposed','rejected'):
            raise ValueError('Unsupported rule match or status')
        if rule in base['brand_reference'].get('rules',[]):
            clean_rules.append(deepcopy(rule))
        else:
            clean_rules.append({'term':rule['term'].strip(),'match':rule.get('match','phrase'),
                'status':rule['status'],'source':'User-requested report-list edit',
                'updated_at':datetime.now(timezone.utc).isoformat()})
    owned=asins(proposed['owned_asins'])
    if type(proposed['catalog_complete']) is not bool or (proposed['catalog_complete'] and not owned):
        raise ValueError('A complete catalog needs ASINs and an explicit completeness choice')
    market=expected['marketplace']
    if (owned or base['owned_asins']) and not market:
        raise ValueError('Confirm marketplace before editing ownership data')
    identity={**expected['scope'],'marketplace':market}
    saved_reference=deepcopy(saved_reference or {})
    for key in ('account_id','brand','currency','marketplace'):
        if key in saved_reference and saved_reference[key] != identity[key]:
            raise ValueError('Saved reference belongs to a different scope')
    for key in ('aliases','rules','exceptions'):
        if key in saved_reference and saved_reference[key] != base['brand_reference'].get(key,[]):
            raise ValueError('Saved reference is newer than this report; refresh before applying the draft')
    reference={**deepcopy(base['brand_reference']),**saved_reference,'schema':'brand-reference/1',**identity,
               'aliases':aliases,'rules':clean_rules,'owned_asin_count':len(owned)}
    catalog_scope={k:identity[k] for k in ('account_id','brand','marketplace')}
    if saved_catalog:
        if saved_catalog.get('scope')!=catalog_scope or sorted(saved_catalog.get('owned_asins',[]))!=base['owned_asins'] or (saved_catalog.get('complete') is True)!=base['catalog_complete']:
            raise ValueError('Saved catalog differs from this report; refresh before applying the draft')
    removed=set(base['owned_asins'])-set(owned)
    excluded=(set((saved_catalog or {}).get('excluded_asins',[]))|removed)-set(owned)
    catalog={**deepcopy(saved_catalog or {}),'scope':catalog_scope,'source':'User-reviewed list from Brand Traffic Review',
             'ownership_verified':True,'complete':proposed['catalog_complete'],'owned_asins':owned,
             'excluded_asins':sorted(excluded)}
    summary={'names_added':len(set(aliases)-set(base['brand_reference'].get('aliases',[]))),
             'names_removed':len(set(base['brand_reference'].get('aliases',[]))-set(aliases)),
             'rules_changed':rules!=base['brand_reference'].get('rules',[]),
             'asins_added':len(set(owned)-set(base['owned_asins'])), 'asins_removed':len(removed),
             'complete_catalog':catalog['complete']}
    return reference,catalog,summary


def save_pair(outputs):
    """Stage both validated files and restore prior bytes if replacement fails."""
    prior={path:path.read_bytes() if path.exists() else None for path in outputs}
    staged={}
    try:
        for path,data in outputs.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.brand-list-',delete=False) as stream:
                stream.write((json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
                staged[path]=Path(stream.name)
        for path,temp in staged.items():os.replace(temp,path)
    except Exception:
        for path,data in prior.items():
            if data is not None:path.write_bytes(data)
            elif path.exists():path.unlink()
        raise
    finally:
        for temp in staged.values():
            if temp.exists():temp.unlink()


def check_destinations(skill_root, destinations):
    for dest in destinations:
        if skill_root in dest.parents and skill_root/'workspace' not in dest.parents:
            raise ValueError('Save preferences outside installed resources, or in the dedicated workspace folder')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('analysis','changes','reference','catalog'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--apply',action='store_true',help='Save the user-requested changes after validation')
    a=p.parse_args()
    paths=[getattr(a,k).expanduser().resolve() for k in ('analysis','changes','reference','catalog')]
    analysis,changes,reference,catalog=paths
    if len(set(paths))!=4:raise ValueError('Inputs and preference files need distinct paths')
    read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
    report=read(analysis)
    reserved={Path(report['source_path']).resolve()} if report.get('source_path') else set()
    reserved.update(Path(v['source_path']).resolve() for v in report.get('context',{}).values() if isinstance(v,dict) and v.get('source_path'))
    if {reference,catalog}&reserved:raise ValueError('Preferences must not overwrite source exports')
    check_destinations(Path(__file__).resolve().parents[1], (reference,catalog))
    new_ref,new_catalog,summary=prepare(report,read_draft(changes),read(reference) if reference.exists() else None,read(catalog) if catalog.exists() else None)
    if a.apply:save_pair({reference:new_ref,catalog:new_catalog})
    print(json.dumps({'validated':True,'saved':a.apply,'changes':summary,'account_changes':False,
        'next_step':'Recalculate the report with the saved reference and catalog, preserve its baseline, and review affected campaign proposals.' if a.apply else 'Apply when the user has requested these list edits; then recalculate the report.'}))


if __name__=='__main__':main()
