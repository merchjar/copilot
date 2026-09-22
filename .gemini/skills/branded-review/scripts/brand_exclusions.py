"""Draft a reusable non-branded exclusion list. Offline; never applies negatives."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re


def normalized(text):
    return ' '.join(text.casefold().split())


def draft(report, catalog=None, existing=None):
    products = report.get('context', {}).get('products', {})
    scope = {'account_id': report['account_id'], 'brand': report['brand'], 'marketplace': products.get('marketplace')}
    reference = report.get('brand_reference', {})
    candidates = {}
    for term in reference.get('aliases', [report['brand']]):
        if term.strip(): candidates[normalized(term)] = {'match_type': 'PHRASE', 'basis': 'Confirmed brand name'}
    for alias in reference.get('aliases', [report['brand']]):
        compact = re.sub(r'[\s\-\u2010-\u2015]', '', normalized(alias))
        if not compact: continue
        pattern = re.compile(r'(?<!\w)' + r'[\s\-\u2010-\u2015]*'.join(re.escape(c) for c in compact) + r'(?!\w)')
        for query in {normalized(r.get('query', '')) for r in report.get('rows', []) if r.get('category') == 'brand_query'}:
            for match in pattern.finditer(query):
                candidates.setdefault(normalized(match.group()), {'match_type':'PHRASE', 'basis':'Observed spacing/hyphen spelling of confirmed brand; negative use needs review'})
    held = []
    for rule in reference.get('rules', []):
        term = normalized(rule['term'])
        if rule.get('status') == 'approved' and rule.get('match') in ('phrase', 'exact'):
            candidates[term] = {'match_type': rule['match'].upper(), 'basis': 'Reviewed brand reference; negative use still needs approval'}
        else:
            held.append({'value': term, 'status': 'held', 'reason': 'Rejected or unconfirmed brand term, or classification rule without a directly equivalent negative match'})
            if rule.get('status') == 'rejected': candidates.pop(term, None)
    owned = set(products.get('owned_asins', [])) - set(products.get('conflicted_asins', []))
    catalog_info = {'complete': products.get('catalog_complete') is True, 'coverage': 'Supplied brand catalog' if products.get('catalog_complete') else 'Advertised subset', 'source_sha256': products.get('source_sha256'),
                    'observed_start': products.get('observed_start'), 'observed_end': products.get('observed_end')}
    if catalog is not None:
        if catalog.get('scope') != scope: raise ValueError('Catalog account, brand and marketplace must match the report')
        if not catalog.get('source') or not catalog.get('ownership_verified'): raise ValueError('Catalog needs a source and verified brand ownership')
        owned = set(catalog['owned_asins'])
        catalog_info = {'complete': catalog.get('complete') is True, 'coverage': 'Supplied brand catalog', 'source': catalog['source']}
    if any(not re.fullmatch(r'(?:B[A-Z0-9]{9}|[0-9]{10})', str(asin)) for asin in owned):
        raise ValueError('Invalid ASIN in owned-product input')
    entries = [{'type': 'KEYWORD', 'value': term, **data, 'status': 'proposed'} for term, data in sorted(candidates.items())]
    entries += [{'type': 'PRODUCT', 'value': asin, 'match_type': 'PRODUCT_EXACT', 'status': 'proposed',
                 'basis': 'Confirmed owned ASIN; separate from keyword negatives'} for asin in sorted(owned)]
    if existing is not None:
        if existing.get('scope') != scope: raise ValueError('Cannot reuse another account, brand or marketplace list')
        prior = {(e['type'], e['value'], e['match_type']): copy.deepcopy(e) for e in existing['entries']}
        for entry in entries:
            prior.setdefault((entry['type'], entry['value'], entry['match_type']), entry)
        entries = sorted(prior.values(), key=lambda e: (e['type'], e['value'], e['match_type']))
        # A shorter input does not delete saved products, but cannot prove freshness/completeness either.
        catalog_info['prior_entries_preserved'] = True
    result = {'schema': 'brand-exclusion-list/1', 'scope': scope, 'status': 'proposal; not applied',
        'applies_to': 'New non-branded campaigns and existing campaigns being converted to non-branded',
        'does_not_apply_to': ['branded campaigns', 'own-product defense campaigns'],
        'catalog': catalog_info, 'entries': entries, 'held_terms': held,
        'rules': {'new_campaigns': 'Read latest approved revision; apply supported entries and verify before enablement',
                  'existing_brand_exclusions': 'Wait for corresponding branded campaign delivery and approved source change',
                  'existing_product_exclusions': 'Wait for own-product defense delivery, unless stopping this traffic is explicitly approved',
                  'unsupported_entries': 'Record not applicable or unresolved; never invent unsupported negative types/scopes',
                  'updates': 'New catalog terms remain proposed; compare existing coverage before approved application'},
        'account_changes': False}
    result['revision'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def markdown(result):
    keywords = [e for e in result['entries'] if e['type'] == 'KEYWORD']
    products = [e for e in result['entries'] if e['type'] == 'PRODUCT']
    out = ['# Proposed negative list for non-branded campaigns', '',
           'Use this list when setting up a new non-branded campaign. For existing campaigns, wait until the matching branded or own-product defense campaigns are receiving traffic. Nothing has been applied.', '',
           '## Brand terms', '', '| Term | Match | Review |', '|---|---|---|']
    for entry in keywords:
        value = entry['value'].replace('|', '\\|').replace('\n', ' ')
        out.append(f'| {value} | {entry["match_type"]} | {entry["status"]} |')
    out += ['', '## Owned products', '', f'{len(products)} confirmed ASINs are included as product-negative candidates in the saved JSON.',
            'Catalog coverage: ' + ('supplied as complete for this brand and marketplace.' if result['catalog']['complete'] else 'partial. Supply a complete brand ASIN list to cover products missing from the advertised subset.'), '',
            'Competitor and unknown-owner ASINs are excluded from this brand list. ASIN exclusions are product negatives, not keyword negatives.', '',
            '## Keep it current', '', 'Save the reviewed list with this account. New names or products are proposed for review; saved approvals and exclusions are preserved. Read the latest approved revision for every new non-branded campaign. Updating the file does not update Amazon campaigns.', '',
            'Use supported entries for the specific campaign type and scope. Record anything not applicable or still unresolved; verify the actual negatives before enabling. Existing unrelated negatives remain in place.', '']
    if result['held_terms']:
        out += ['Held for separate review: ' + ', '.join(e['value'] for e in result['held_terms']), '']
    return '\n'.join(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--existing', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding='utf-8')) if p else None
    result = draft(read(args.analysis), read(args.catalog), read(args.existing))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(result), encoding='utf-8')
    print(json.dumps({'proposal': str(args.output.resolve()), 'keyword_entries': sum(e['type']=='KEYWORD' for e in result['entries']),
                      'product_entries': sum(e['type']=='PRODUCT' for e in result['entries']), 'catalog_complete': result['catalog']['complete'], 'account_changes': False}))
