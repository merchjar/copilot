"""The 'Not split yet' panel: spend inside Overall that is outside the branded and non-branded cards.

The visible parts add up to the Overall card: branded + non-branded + not split (+ any campaign-report
difference for connected data) = overall ad spend.
"""
from decimal import Decimal
from html import escape


def _d(value):
    return Decimal(str(value))


def _acos(spend, revenue):
    return f'{spend / revenue:.1%}' if revenue > 0 else ('No sales' if spend else 'No spend')


def items(report):
    """Return the unsplit parts as dicts with spend, sales, royalties and the ACoS shown."""
    groups = {g['category']: g for g in report['groups']}
    kenp = bool(report.get('kenp'))
    products = report.get('context', {}).get('products', {})
    owned, unknown = groups['owned_asin'], groups['asin_unknown']
    identified = owned['rows'] > 0 or products.get('product_count', 0) > 0
    complete = products.get('catalog_complete') is True
    books = kenp or report.get('kdp', {}).get('status') in ('detected', 'confirmed')
    parts = []
    if identified and books:
        parts.append(('owned_asin', 'Your own books', owned, 'Ads shown on your own book pages or targeting your books.'))
        parts.append(('asin_unknown', 'Other books' if complete else 'Other books or unknown ASINs', unknown,
                      'Product targeting outside your own titles.' if complete else 'Outside your known titles, which may be incomplete.'))
    elif identified:
        parts.append(('owned_asin', 'Your own-product ASINs', owned, 'Ads shown on your own product pages or targeting your ASINs.'))
        parts.append(('asin_unknown', 'Other ASINs' if complete else 'Other or unknown-owner ASINs', unknown,
                      'Product targeting outside your owned list.' if complete else 'Outside your owned list, which may be incomplete.'))
    else:
        parts.append(('asin_unknown', 'ASIN targeting (ownership unknown)', unknown,
                      'Product targeting. Add your ASIN list to split own-product traffic from other ASINs.'))
    parts.append(('brand_review', 'Possible brand variants, held for review', groups['brand_review'],
                  'Confirm or reject these names to move them into branded or non-branded.'))
    parts.append(('missing_query', 'Unreported search terms', groups['missing_query'], 'Amazon reported spend without a search term.'))
    result = []
    for key, label, g, note in parts:
        if not g['rows']:
            continue
        spend, sales = _d(g['spend']), _d(g['sales'])
        royalties = _d(g['kenp']['royalties']) if kenp and g.get('kenp') else None
        basis = _d(g['kenp']['sales_basis']) if kenp and g.get('kenp') else sales
        result.append({'key': key, 'label': label, 'note': note, 'rows': g['rows'], 'spend': spend, 'sales': sales,
                       'royalties': royalties, 'acos': _acos(spend, basis + (royalties or 0))})
    account = report.get('account_totals')
    if account:
        gap_spend = _d(account['spend']) - _d(report['totals']['spend'])
        gap_sales = _d(account['sales']) - _d(report['totals']['sales'])
        gap_royalties = None
        if kenp and account.get('kenp') and report['totals'].get('kenp'):
            gap_royalties = _d(account['kenp']['royalties']) - _d(report['totals']['kenp']['royalties'])
        if gap_spend or gap_sales:
            result.append({'key': 'campaign_gap', 'label': 'Campaign total not in search-term data',
                           'note': 'Same-period campaign spend that the search-term rows do not cover. It is not assigned to any class.',
                           'rows': None, 'spend': gap_spend, 'sales': gap_sales, 'royalties': gap_royalties,
                           'acos': None, 'material': abs(gap_spend) >= max(Decimal(1), _d(account['spend']) * Decimal('0.005'))})
    return result


def render(report, money):
    parts = items(report)
    if not parts:
        return ''
    groups = {g['category']: g for g in report['groups']}
    overall = report.get('account_totals', report['totals'])
    overall_spend = _d(overall['spend'])
    kenp = bool(report.get('kenp'))
    acos_label = 'ACoS incl. KENP' if kenp else 'ACoS'
    cards = []
    for part in parts:
        if part['key'] == 'campaign_gap' and not part['material']:
            continue
        share = f' · {part["spend"] / overall_spend:.0%} of overall' if overall_spend > 0 else ''
        rows = [('Attributed sales', money(part['sales']))]
        if part['royalties'] is not None:
            rows.append(('KENP royalties', money(part['royalties'])))
        if part['acos'] is not None:
            rows.append((acos_label, part['acos']))
        metrics = ''.join(f'<div><dt>{escape(k)}</dt><dd>{v}</dd></div>' for k, v in rows)
        cards.append(f'<article class="unsplit-item unsplit-{part["key"]}"><h3>{escape(part["label"])}</h3>'
                     f'<strong>{money(part["spend"])}</strong><span class="unsplit-share">Ad spend{share}</span>'
                     f'<dl>{metrics}</dl><p>{escape(part["note"])}</p></article>')
    not_split = sum((p['spend'] for p in parts if p['key'] != 'campaign_gap'), Decimal(0))
    gap = next((p['spend'] for p in parts if p['key'] == 'campaign_gap'), None)
    equation = (f"Branded {money(groups['brand_query']['spend'])} + non-branded {money(groups['other_query']['spend'])}"
                f" + not split {money(not_split)}")
    if gap is not None:
        equation += f" {'-' if gap < 0 else '+'} campaign difference {money(abs(gap))}"
    equation += f" = overall {money(overall_spend)} ad spend. Amounts are rounded."
    return (f'<section class="unsplit" aria-labelledby="unsplit-heading"><div class="unsplit-head">'
            f'<h2 id="unsplit-heading">Not split yet</h2><p>{money(not_split)} of overall spend sits outside the branded and '
            f'non-branded cards.</p></div><div class="unsplit-grid">{"".join(cards)}</div>'
            f'<p class="unsplit-sum">{equation}</p></section>')
