"""Optional Amazon default-template context. Never add its metrics to search terms."""
import csv
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import hashlib
from pathlib import Path
import re


def read_context(path, account_id, currency, required):
    path = Path(path)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Context template missing columns: {sorted(missing)}')
        original = list(reader)
    rows = [r for r in original if r['Advertiser account ID'].strip().removeprefix('="').removesuffix('"') == account_id
            and r['Budget currency'] == currency]
    if not rows:
        raise ValueError('Context report has no matching account and currency')
    starts, ends = [], []
    for row in rows:
        start, end = [datetime.strptime(s, '%b %d, %Y').date() for s in row['Date range'].split(' - ')]
        if start > end:
            raise ValueError('Context report has reversed dates')
        starts.append(start); ends.append(end)
    return rows, {'source_path': str(path.resolve()), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'rows':len(rows), 'observed_start':min(starts).isoformat(), 'observed_end':max(ends).isoformat()}


def product_context(path, account_id, currency, brand, marketplace):
    required = ['Advertiser account ID','Budget currency','Date range','Campaign ID','Ad group ID',
                'Advertised product ID','Advertised product brand','Advertised product marketplace']
    rows, receipt = read_context(path, account_id, currency, required)
    owned, by_group, brands = set(), defaultdict(set), defaultdict(set)
    product_details = defaultdict(lambda: defaultdict(set))
    missing_ids = []
    for row in rows:
        asin = row['Advertised product ID'].upper().strip()
        if not re.fullmatch(r'(?:B[A-Z0-9]{9}|[0-9]{10})', asin):
            if row['Advertised product marketplace'] == marketplace:
                missing_ids.append({'title':row.get('Advertised product name', '').strip(),
                                    'product_id':asin})
            continue
        reported_brand = row['Advertised product brand'].casefold().strip()
        # Require an explicit marketplace match; a blank field is not coverage evidence.
        if row['Advertised product marketplace'] == marketplace:
            brands[asin].add(reported_brand)
            if reported_brand == brand.casefold().strip():
                owned.add(asin)
                for field, column in [('title','Advertised product name'), ('parent_asin','Advertised product parent ID'),
                                      ('category','Advertised product category'), ('subcategory','Advertised product subcategory')]:
                    value = row.get(column, '').strip()
                    if value: product_details[asin][field].add(value)
        by_group[(row['Campaign ID'], row['Ad group ID'])].add(asin)
    conflicted = {a for a in owned if any(b and b != brand.casefold().strip() for b in brands[a])}
    owned -= conflicted
    receipt.update({'brand':brand,'marketplace':marketplace,'owned_asins':sorted(owned),
                    'rows_without_valid_asin':len(missing_ids),
                    'products_without_valid_asin':sorted({r['title'] for r in missing_ids if r['title']}),
                    'limitations':([f'{len(missing_ids)} product-report rows have no valid ASIN. They are excluded from ownership matching; supply their ASINs to include them.'] if missing_ids else []),
                    'conflicted_asins':sorted(conflicted),'coverage':'Advertised subset, not complete catalog',
                    'product_count':len(owned), 'all_observed_product_count':len(set().union(*by_group.values())) if by_group else 0,
                    'catalog_products':[{'asin':asin, **{key:sorted(values) for key,values in product_details[asin].items()}}
                                        for asin in sorted(owned)],
                    'products_by_ad_group':[{'campaign_id':c.strip().removeprefix('="').removesuffix('"'),
                                            'ad_group_id':g.strip().removeprefix('="').removesuffix('"'),
                                            'asins':sorted(a & owned)} for (c,g),a in sorted(by_group.items())]})
    return receipt, by_group


def targeting_context(path, account_id, currency, classify, aliases, reference, products_by_group=None):
    required = ['Advertiser account ID','Budget currency','Date range','Campaign ID','Ad group ID',
                'Targeting','Targeting match type','Target ID','Target bid','Target status']
    rows, receipt = read_context(path, account_id, currency, required)
    patterns, brand_groups, other_groups = defaultdict(set), set(), set()
    inventory = defaultdict(list)
    all_targets = defaultdict(list)
    products_by_group = products_by_group or {}
    for row in rows:
        if row['Target status'] != 'ENABLED':
            continue
        group = row['Campaign ID'],row['Ad group ID']
        all_targets[group].append({'target_id':row.get('Target ID','').strip().removeprefix('="').removesuffix('"'),
            'text':row['Targeting'], 'match_type':row['Targeting match type'],
            'target_type':row.get('Target type'), 'reported_bid':row.get('Target bid') or None,
            'reported_state':row['Target status']})
        if row['Targeting match type'] not in ('EXACT','PHRASE','BROAD'):
            continue
        key = (' '.join(row['Targeting'].casefold().split()),row['Targeting match type'])
        group = row['Campaign ID'],row['Ad group ID']
        patterns[key].add(group)
        category, _ = classify(row['Targeting'], aliases, reference)
        inventory[group].append({'target_id':row.get('Target ID','').strip().removeprefix('="').removesuffix('"'),
            'text':row['Targeting'], 'match_type':row['Targeting match type'], 'category':category,
            'reported_bid':row.get('Target bid') or None, 'reported_state':row['Target status']})
        if category == 'brand_query': brand_groups.add(group)
        elif category == 'other_query': other_groups.add(group)
    repeated, shared = [], []
    for (term, match), groups in patterns.items():
        if len(groups) < 2: continue
        record = {'term':term,'match':match,'ad_groups':len(groups)}
        repeated.append(record)
        counts = Counter(asin for g in groups for asin in products_by_group.get(g,set()))
        common = sorted(a for a, n in counts.items() if n > 1)
        if common: shared.append({**record,'shared_advertised_asins':common})
    receipt.update({'repeated_keyword_match_count':len(repeated),'shared_product_overlap_count':len(shared),
                    'mixed_keyword_ad_groups':len(brand_groups & other_groups),
                    'overlap_candidates':shared,'repeated_keywords':repeated,
                    'status_counts':dict(Counter(r['Target status'] for r in rows)),
                    'targets_by_ad_group':[{'campaign_id':c.strip().removeprefix('="').removesuffix('"'),
                        'ad_group_id':g.strip().removeprefix('="').removesuffix('"'),
                        'brand_and_other_keywords':(c,g) in brand_groups & other_groups,
                        'reported_enabled_keywords':inventory[(c,g)], 'reported_enabled_targets':targets}
                        for (c,g),targets in sorted(all_targets.items())],
                    'negative_coverage':'Not established by this template',
                    'interpretation':'Potential overlap in reported enabled targets, not proof of current delivery or waste'})
    return receipt
