"""Render conceptual campaign roles and a gradual transition. No account reads or writes."""
import argparse
import base64
import json
from collections import defaultdict
from decimal import Decimal
from html import escape
from pathlib import Path
from report_delivery import report_artifact
from structure_plan import structure_html, lists_html


def inventory(report):
    """Observed traffic only; names never invent product families or live setup."""
    groups = {}
    for row in report.get('rows', []):
        key = row.get('campaign_id') or '(missing campaign ID)'
        group = groups.setdefault(key, {'name': row.get('campaign_name') or key, 'classes': set(), 'spend': Decimal(0),
                                       'metrics':defaultdict(lambda: {'spend':Decimal(0), 'sales':Decimal(0), 'sales_known':True})})
        group['classes'].add(row['category'])
        group['spend'] += Decimal(row['spend'])
        metrics=group['metrics'][row['category']]
        metrics['spend'] += Decimal(row['spend'])
        metrics['sales'] += Decimal(row.get('sales',0))
        metrics['sales_known'] = metrics['sales_known'] and 'sales' in row
    products = defaultdict(set)
    for group in report.get('context', {}).get('products', {}).get('products_by_ad_group', []):
        products[group['campaign_id']].update(group['asins'])
    labels = [('brand_query', 'Brand searches', 'brand'), ('other_query', 'Other searches', 'nonbrand'),
              ('owned_asin', 'Your ASINs', 'own'), ('asin_unknown', 'ASIN ownership unknown', ''),
              ('missing_query', 'Unreported terms', ''), ('brand_review', 'Brand name to review', '')]
    lines = []
    currency=report.get('currency','USD')
    def money(value): return f'${value:,.0f}' if currency=='USD' else f'{value:,.0f} {escape(currency)}'
    def cell(metrics):
        note = f"{metrics['spend']/metrics['sales']:.1%} ACoS" if metrics['sales'] else 'No attributed sales'
        if not metrics['sales_known']: note='Sales not supplied'
        if not metrics['spend'] and not metrics['sales']: note='No reported spend or sales'
        return money(metrics['spend'])+'<small>'+note+'</small>'
    for key, group in sorted(groups.items(), key=lambda item: (-item[1]['metrics']['brand_query']['spend'], -item[1]['spend'], str(item[0]))):
        mixed = {'brand_query', 'other_query'}.issubset(group['classes'])
        chips = ''.join(f'<span class="chip {style}">{label}</span>' for category, label, style in labels if category in group['classes'])
        count = f'{len(products[key])} in product report' if products[key] else 'Not mapped'
        brand, other=group['metrics']['brand_query'],group['metrics']['other_query']
        asin=group['metrics']['owned_asin']['spend']+group['metrics']['asin_unknown']['spend']
        unresolved=group['spend']-brand['spend']-other['spend']-asin
        lines.append(f'''<tr data-campaign="{escape(group['name'].lower(), quote=True)}" data-mixed="{str(mixed).lower()}" data-brand-spend="{brand['spend']}" data-total-spend="{group['spend']}"><td class="campaign-name" data-label="Campaign">{escape(group['name'])}<details class="campaign-id"><summary>Products &amp; traffic detail</summary><small>{count} · Campaign {escape(str(key))}</small><div class="chips">{chips}</div></details></td><td data-label="Brand spend">{cell(brand)}</td><td data-label="Non-brand spend">{cell(other)}</td><td data-label="ASIN spend">{money(asin)}<small>Your ASINs {money(group['metrics']['owned_asin']['spend'])}<br>Other / unknown {money(group['metrics']['asin_unknown']['spend'])}</small></td><td data-label="Total spend">{money(group['spend'])}<small>{money(unresolved)} unreported / review</small></td></tr>''')
    period = escape(f'{report.get("observed_start", "Unknown start")} to {report.get("observed_end", "unknown end")}')
    return f'''<details class="section inventory-disclosure" id="inventory"><summary>Where branded spend sits across {len(groups)} campaigns</summary><div class="inventory-body">
<p class="sub">Start with the campaigns receiving the most branded spend. Compare brand, non-brand and ASIN traffic before choosing a rollout group.</p>
<p class="note">Search-term history: {period}. Product counts come from the supplied product report and may be incomplete or cover different dates. This table does not establish current targets or negatives.</p>
<div class="inventory-tools"><input id="campaign-search" type="search" placeholder="Find a campaign" aria-label="Find a campaign"><div class="campaign-filters" role="group" aria-label="Campaign traffic filter"><button type="button" data-campaign-filter="all" aria-pressed="true">All campaigns</button><button type="button" data-campaign-filter="mixed" aria-pressed="false">Brand + other searches</button></div><label>Sort by <select id="campaign-sort"><option value="brandSpend">Branded spend</option><option value="totalSpend">Total spend</option></select></label><span id="visible-count" aria-live="polite"></span></div>
<div class="table-scroll"><table><thead><tr><th>Existing campaign</th><th>Brand spend</th><th>Non-brand spend</th><th>ASIN spend</th><th>Total spend</th></tr></thead><tbody>{''.join(lines)}</tbody></table></div><button type="button" class="quiet-button" id="more-campaigns">Show more campaigns</button>
<p class="note" style="margin-top:12px">Next, use the connected account to group campaigns by their actual advertised products and check what can stay. A campaign name alone does not decide its group.</p></div></details>'''


def render(report=None, embedded=False, product_groups=None):
    assets = Path(__file__).resolve().parents[1] / 'assets'
    html = (assets / 'campaign-map.html').read_text(encoding='utf-8')
    html = html.replace('INVENTORY_DATA', inventory(report) if report else '')
    html = html.replace('INVENTORY_SCRIPT', (assets/'inventory.js').read_text(encoding='utf-8'))
    html = html.replace('PRODUCT_STRUCTURE', structure_html(report, product_groups) if report else '')
    html = html.replace('SAVED_LISTS', lists_html(report) if report else '')
    if not embedded:
        html = html.replace('<body>', '<body class="standalone-map">')
        html = html.replace('</style>', (assets/'report-theme.css').read_text(encoding='utf-8')+(assets/'planning.css').read_text(encoding='utf-8')+'</style>', 1)
        html = html.replace('</body>', '<script>'+(assets/'planning-builder.js').read_text(encoding='utf-8')+'</script></body>')
    return html.replace('FONT_DATA', base64.b64encode((assets / 'inter.woff2').read_bytes()).decode()).replace(
        'LOGO_DATA', base64.b64encode((assets / 'merchjar-logo.webp').read_bytes()).decode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html-output', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, help='Optional saved analysis for an observed-campaign inventory; may contain private names')
    args = parser.parse_args()
    output = args.html_output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = json.loads(args.analysis.read_text(encoding='utf-8')) if args.analysis else None
    output.write_text(render(report), encoding='utf-8')
    print(json.dumps({'scope': 'Conceptual structure, not live account configuration',
                      'report_artifact': report_artifact(output), 'account_changes': 0}))
