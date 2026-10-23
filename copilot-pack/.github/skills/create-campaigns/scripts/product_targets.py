"""Offline product-target planning: seeds from saved preview rows, strict paused target bodies
and post-create bid patches. No API calls; the agent sends the bodies through Connect."""
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

ID = re.compile(r'[1-9][0-9]*')
ASIN = re.compile(r'[A-Z0-9]{10}')
MATCH_TYPES = ('PRODUCT_EXACT', 'PRODUCT_SIMILAR')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def asin_term(term):
    """Return the ASIN a search term names, or None. Amazon reports product-page matches as the
    lowercase ASIN: modern ASINs start with B0; books use a 10-character ISBN."""
    value = str(term or '').strip().upper()
    if re.fullmatch(r'B0[A-Z0-9]{8}', value) or re.fullmatch(r'[0-9]{9}[0-9X]', value):
        return value
    return None


def rows_of(page):
    # Accept a raw preview response, its {data: {...}} wrapper, or a bare row list.
    if isinstance(page, list):
        return page
    if isinstance(page.get('data'), dict):
        page = page['data']
    require(isinstance(page.get('data'), list), 'Not a preview response page')
    return page['data']


def number(row, key):
    value = row.get(key)
    if value in (None, ''):
        return Decimal('0')
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f'Non-numeric {key}')


def seeds(search_rows, ad_rows, asin, window, owned=(), min_orders=1, ads_complete=True, target_rows=()):
    asin = asin.strip().upper()
    require(ASIN.fullmatch(asin), 'Advertised ASIN must be 10 letters or digits')
    require(re.fullmatch(r'[0-9a-z_]+', window), 'Window must match the preview key suffix, e.g. 60d')
    owned = {a.strip().upper() for a in owned if a.strip()} - {asin}
    groups = {}
    for row in ad_rows:
        group = str(row.get('ad_group_id') or '')
        product = str(row.get('creative_products_product_id') or '').upper()
        require(ID.fullmatch(group) and product, 'Ad rows need ad_group_id and creative_products_product_id')
        groups.setdefault(group, dict(name=row.get('ad_group_name'), campaign=row.get('campaign_name'),
                                      products=set()))['products'].add(product)
    mine = {g: v for g, v in groups.items() if asin in v['products']}
    # Two products prove a shared group from any page; one product proves nothing on partial pages.
    looks_single = {g for g, v in mine.items() if v['products'] == {asin}}
    single = looks_single if ads_complete else set()
    # Existing positive product targets in this product's groups are overlap to resolve, not new seeds.
    existing = {}
    for row in target_rows:
        target, group = str(row.get('target_details_asin') or '').upper(), str(row.get('ad_group_id') or '')
        if target and group in mine and str(row.get('state') or '').upper() != 'ARCHIVED':
            existing.setdefault(target, set()).add(str(row.get('target_details_match_type') or 'UNKNOWN'))
    orders_key = 'orders_' + window
    found, shared, own, skipped = {}, {}, {}, 0
    for row in search_rows:
        require(orders_key in row, f'Search-term rows lack {orders_key}; preview the same window')
        group = str(row.get('ad_group_id') or '')
        if group not in mine:
            skipped += 1
            continue
        target = asin_term(row.get('search_term'))
        orders = number(row, orders_key)
        if not target or target == asin or orders < min_orders:
            continue
        bucket = own if target in owned else found if group in single else shared
        entry = bucket.setdefault(target, dict(asin=target, orders=Decimal('0'), sales=Decimal('0'),
                                               clicks=Decimal('0'), cost=Decimal('0'), ad_groups=[]))
        for field in ('orders', 'sales', 'clicks', 'cost'):
            entry[field] += number(row, f'{field}_{window}')
        if group not in entry['ad_groups']:
            entry['ad_groups'].append(group)

    def ranked(bucket):
        out = []
        for entry in sorted(bucket.values(), key=lambda e: (-e['orders'], -e['sales'], e['asin'])):
            clicks = entry['clicks']
            entry = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in entry.items()}
            entry['cpc'] = str((Decimal(entry['cost']) / clicks).quantize(Decimal('0.01'))) if clicks else None
            entry['already_targeted'] = sorted(existing.get(entry['asin'], ()))
            out.append(entry)
        return out

    return dict(asin=asin, window=window, min_orders=str(min_orders),
                ads_complete=ads_complete, product_ad_groups=sorted(single),
                unconfirmed_ad_groups=sorted(looks_single - single),
                shared_ad_groups=[dict(ad_group_id=g, name=v['name'], campaign=v['campaign'],
                                       products=len(v['products'])) for g, v in sorted(mine.items())
                                  if g not in looks_single],
                seeds=ranked(found), shared_group_asins=ranked(shared), owned_asins=ranked(own),
                rows_outside_product_groups=skipped)


def target_items(ad_group_id, match_type=None, asins=(), category_ids=()):
    """Strict POST /targets items for one product-target ad group, always PAUSED."""
    require(isinstance(ad_group_id, str) and ID.fullmatch(ad_group_id), 'Ad group ID must be a decimal string')
    require(bool(asins) != bool(category_ids), 'Supply either ASINs or category IDs for one batch')
    base = dict(adGroupId=ad_group_id, adProduct='SPONSORED_PRODUCTS', negative=False, state='PAUSED')
    items, index, seen = [], [], set()
    if asins:
        require(match_type in MATCH_TYPES, 'Product targets use PRODUCT_EXACT or PRODUCT_SIMILAR')
        for value in asins:
            value = value.strip().upper()
            require(ASIN.fullmatch(value), f'Invalid ASIN: {value[:20]}')
            require(value not in seen, f'Duplicate ASIN: {value}')
            seen.add(value)
            items.append(dict(base, targetType='PRODUCT', targetDetails=dict(productTarget=dict(
                matchType=match_type, productId=value, productIdType='ASIN'))))
            index.append(dict(index=len(index), kind='product', match_type=match_type, asin=value))
    else:
        require(match_type in (None, 'CATEGORY'), 'Category targets take no product match type')
        for value in category_ids:
            value = str(value).strip()
            require(re.fullmatch(r'[0-9]+', value), f'Invalid category ID: {value[:20]}')
            require(value not in seen, f'Duplicate category ID: {value}')
            seen.add(value)
            # The live contract nests the refinement object twice; this exact shape created a
            # category target in Amazon on September 7, 2026.
            items.append(dict(base, targetType='PRODUCT_CATEGORY', targetDetails=dict(productCategoryTarget=dict(
                matchType='MULTISIGNAL_BROAD',
                productCategoryRefinement=dict(productCategoryRefinement=dict(productCategoryId=value))))))
            index.append(dict(index=len(index), kind='category', category_id=value))
    require(1 <= len(items) <= 1000, 'A batch holds 1 to 1,000 targets')
    return dict(body=dict(targets=items), index=index)


def bid_patches(targets, prefix):
    """PATCH /targets/:id bodies for approved bids that differ from the group default."""
    require(re.fullmatch(r'[A-Za-z0-9-]{1,40}', prefix), 'Use a short letters/digits/hyphen key prefix')
    out, seen = [], set()
    for t in targets:
        target_id, bid = str(t.get('target_id', '')), t.get('bid')
        require(ID.fullmatch(target_id) and target_id not in seen, 'Target IDs must be unique decimal strings')
        seen.add(target_id)
        try:
            amount = Decimal(str(bid))
        except InvalidOperation:
            raise ValueError('Invalid bid')
        require(amount.is_finite() and amount > 0 and amount == amount.quantize(Decimal('0.01')),
                'Bids must be positive with cent precision')
        out.append(dict(target_id=target_id, idempotency_key=f'{prefix}-bid-{target_id}'[:64],
                        body=dict(bid=dict(bid=float(amount)))))
    return out


def load_rows(paths, allow_partial=False):
    # A missing ads page could make a shared ad group look product-specific, so partial ads pages
    # are reported as such; search-term pages must be complete.
    rows, totals = [], set()
    for path in paths:
        page = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        inner = page.get('data') if isinstance(page, dict) and isinstance(page.get('data'), dict) else page
        if isinstance(inner, dict) and isinstance(inner.get('pagination'), dict):
            totals.add(inner['pagination'].get('total'))
        rows.extend(rows_of(page))
    require(len(totals) <= 1, 'Pages come from different previews')
    complete = not totals or totals == {len(rows)}
    require(complete or allow_partial, 'Incomplete pagination; pass every page of the preview')
    return rows, complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('seeds', help='ASINs that sold in the product\'s own search terms')
    p.add_argument('--asin', required=True)
    p.add_argument('--window', required=True, help='preview window suffix, e.g. 60d')
    p.add_argument('--search-terms', nargs='+', required=True, help='saved search_terms preview pages')
    p.add_argument('--ads', nargs='+', required=True,
                   help='saved ads preview pages covering those ad groups (partial pages prove only sharing)')
    p.add_argument('--targets', nargs='*', default=[], help='saved targets preview pages for the same groups')
    p.add_argument('--owned', default='', help='comma-separated ASINs the user advertises elsewhere')
    p.add_argument('--min-orders', type=int, default=1)
    p = sub.add_parser('targets', help='strict paused POST /targets body for one ad group')
    p.add_argument('--ad-group-id', required=True)
    p.add_argument('--match-type', choices=MATCH_TYPES)
    p.add_argument('--asins', default='')
    p.add_argument('--category-ids', default='')
    p = sub.add_parser('bids', help='PATCH /targets/:id bodies from a JSON list of {target_id, bid}')
    p.add_argument('--file', type=Path, required=True)
    p.add_argument('--key-prefix', required=True)
    args = parser.parse_args()
    split = lambda text: [v for v in re.split(r'[\s,]+', text) if v]
    try:
        if args.command == 'seeds':
            ad_rows, complete = load_rows(args.ads, allow_partial=True)
            target_rows = load_rows(args.targets)[0] if args.targets else []
            result = seeds(load_rows(args.search_terms)[0], ad_rows, args.asin, args.window,
                           split(args.owned), args.min_orders, complete, target_rows)
        elif args.command == 'targets':
            result = target_items(args.ad_group_id, args.match_type, split(args.asins), split(args.category_ids))
        else:
            result = bid_patches(json.loads(args.file.read_text(encoding='utf-8-sig')), args.key_prefix)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({'error': str(error)[:200]}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
