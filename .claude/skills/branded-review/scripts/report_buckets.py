"""Reporting buckets over ALL search-term traffic. Calculation only; classification is unchanged.

Branded = brand searches + ad traffic on the user's own products (own-product defense stays its own line).
Non-branded = other searches + ad traffic on other or unknown ASINs.
Held = possible name variants awaiting review + unreported search terms, outside both cards.
Branded + non-branded + held = overall, exactly, over the same search-term population.
"""
from decimal import Decimal

import kdp

METRIC_KEYS = ('spend', 'sales', 'clicks', 'purchases', 'impressions')


def _d(value):
    return Decimal(str(value))


def _ratio(numerator, denominator):
    return float(numerator / denominator) if denominator > 0 else None


def is_books(report):
    return bool(report.get('kenp')) or report.get('kdp', {}).get('status') in ('detected', 'confirmed')


def owned_identified(report):
    groups = {g['category']: g for g in report['groups']}
    return groups['owned_asin']['rows'] > 0 or report.get('context', {}).get('products', {}).get('product_count', 0) > 0


def labels(report):
    books = is_books(report)
    brand = report.get('brand') or 'your brand'
    identified = owned_identified(report)
    if books:
        own, other = 'Ads on your own books', ('Ads on other books' if identified else 'Ads on other books or unknown ASINs')
    else:
        own, other = 'Ads on your own products', ('Ads on other products' if identified else 'Ads on other or unknown ASINs')
    return {'brand_query': f'Searches for {brand}', 'owned_asin': own, 'other_query': 'Other searches',
            'asin_unknown': other, 'brand_review': 'Possible name variants held for review',
            'missing_query': 'Unreported search terms'}


MEMBERS = {'branded': ('brand_query', 'owned_asin'), 'non_branded': ('other_query', 'asin_unknown'),
           'held': ('brand_review', 'missing_query')}


def _bucket(groups, members, names, kenp):
    totals = {k: sum((_d(groups[c][k]) for c in members), Decimal(0)) for k in METRIC_KEYS}
    result = {**{k: str(v) for k, v in totals.items()}, 'acos': _ratio(totals['spend'], totals['sales']),
              'cpc': _ratio(totals['spend'], totals['clicks']), 'purchase_rate': _ratio(totals['purchases'], totals['clicks']),
              'rows': sum(groups[c]['rows'] for c in members), 'components': []}
    if kenp:
        k = {f: sum((_d(groups[c]['kenp'][f]) for c in members), Decimal(0)) for f in ('royalties', 'pages_read', 'sales_basis')}
        result['kenp'] = kdp.present(totals['spend'], k['royalties'], k['pages_read'], k['sales_basis'])
    for c in members:
        g = groups[c]
        component = {'category': c, 'label': names[c], 'rows': g['rows'], 'spend': str(g['spend']), 'sales': str(g['sales']),
                     'acos': g['acos']}
        if kenp:
            component['kenp'] = g['kenp']
        result['components'].append(component)
    return result


def buckets(report):
    groups = {g['category']: g for g in report['groups']}
    kenp = bool(report.get('kenp')) and all(g.get('kenp') for g in report['groups'])
    names = labels(report)
    result = {name: _bucket(groups, members, names, kenp) for name, members in MEMBERS.items()}
    parts = sum((_d(result[n]['spend']) for n in MEMBERS), Decimal(0))
    result['overall'] = {k: report['totals'][k] for k in ('spend', 'sales', 'acos')}
    if kenp and report['totals'].get('kenp'):
        result['overall']['kenp'] = report['totals']['kenp']
    result['reconciled'] = parts == _d(report['totals']['spend']) and all(
        sum((_d(result[n][k]) for n in MEMBERS), Decimal(0)) == _d(report['totals'][k]) for k in METRIC_KEYS)
    result['owned_catalog'] = owned_identified(report)
    result['definition'] = ('Branded = brand searches + ads on your own products. Non-branded = other searches + ads on other '
                            'or unknown ASINs. Held = name variants awaiting review + unreported search terms. '
                            'Branded + non-branded + held = overall search-term total.')
    return result
