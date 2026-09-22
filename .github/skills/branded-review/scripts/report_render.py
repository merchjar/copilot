"""Compact offline executive report using the reviewed Merch Jar website assets."""
import base64
from datetime import date
from decimal import Decimal
from html import escape
from pathlib import Path
from report_charts import chart


def asin_section(report, money):
    groups = {g['category']:g for g in report['groups']}
    owned, other = groups['owned_asin'], groups['asin_unknown']
    total = {k: Decimal(str(owned[k])) + Decimal(str(other[k])) for k in ('spend','sales','rows')}
    products = report.get('context', {}).get('products', {})
    complete = products.get('catalog_complete') is True
    identified = complete or products.get('product_count', 0) > 0 or owned['rows'] > 0
    has_rows = total['rows'] > 0
    other_title = 'Other ASINs' if complete else 'Other / unknown ASINs'
    cards = []
    for key, title, values in [('owned','Your ASINs',owned), ('other',other_title,other), ('all','All ASINs',total)]:
        missing = key != 'all' and not identified and has_rows
        if missing:
            body = '<strong class="asin-empty">Need ASIN list</strong><p class="asin-caption">Ownership data needed to split the total</p>'
        else:
            spend, sales = Decimal(str(values['spend'])), Decimal(str(values['sales']))
            value = f'{spend/sales:.1%}' if sales > 0 else 'No sales'
            if not values['rows']: value = 'No ASIN traffic'
            body = f'<strong class="asin-value">{value}</strong><p class="asin-caption">ACoS · Reported ASIN rows</p><dl class="asin-metrics"><div><dt>Ad spend</dt><dd>{money(spend)}</dd></div><div><dt>Attributed sales</dt><dd>{money(sales)}</dd></div></dl>'
        ownership_note = '<p class="ownership-note">May include your products missing from the list.</p>' if key == 'other' and identified and not complete and has_rows else ''
        cards.append(f'<article class="asin-card asin-{key}" data-ownership="{"needed" if missing else "available"}"><h3>{title}</h3>{body}{ownership_note}</article>')
    if not has_rows:
        note = 'No ASIN rows were reported in this search-term data.'
        badge = 'No ASIN traffic'
    elif not identified:
        note = "Add your brand's ASIN list or Amazon's Advertised product report to separate your products from the remaining ASIN traffic."
        badge = 'Add ownership data'
    elif complete:
        note = 'Other ASINs are outside your supplied complete brand catalog. This does not establish that every one is a competitor.'
        badge = 'Complete catalog supplied'
    else:
        note = 'Add the full brand ASIN list to resolve the remaining ownership matches.'
        badge = 'Partial ownership list'
    from structure_plan import asin_help
    help_html = asin_help() if not complete and not report.get('privacy') else ''
    return f'''<section class="asin-section" aria-labelledby="asin-heading"><div class="asin-heading"><h2 id="asin-heading">ASIN traffic</h2><span>{badge}</span></div><div class="asin-grid">{''.join(cards)}</div><div class="asin-guidance"><p class="asin-goal">Set separate goals for own-product defense and other product targeting.</p><p class="asin-note">{escape(note)} These rows stay separate from branded and non-branded text searches.</p>{help_html}</div></section>'''


def render_performance(report):
    assets = Path(__file__).resolve().parent.parent/'assets'
    font = base64.b64encode((assets/'inter.woff2').read_bytes()).decode('ascii')
    logo = base64.b64encode((assets/'merchjar-logo.webp').read_bytes()).decode('ascii')
    groups = {g['category']:g for g in report['groups']}
    money = lambda x: f"${Decimal(x):,.0f}" if report['currency']=='USD' else f"{Decimal(x):,.0f} {escape(report['currency'])}"
    pct = lambda x: f'{x:.1%}' if x is not None else 'No sales'
    privacy = bool(report.get('privacy'))
    if privacy:
        period, period_note = 'Identity hidden', 'Original metrics · Dates hidden'
    else:
        start = date.fromisoformat(report['observed_start']); end = date.fromisoformat(report['observed_end'])
        period = f"{start:%b} {start.day}, {start.year} – {end:%b} {end.day}, {end.year}"
        period_note = 'Reported activity dates'
    cards = [('Branded ACoS','brand','Matched brand terms',groups['brand_query']),
             ('Non-branded ACoS','nonbrand','Other text searches',groups['other_query']),
             ('Overall ACoS','account','Same-period campaigns' if report.get('account_totals') else 'All rows in this report',report.get('account_totals',report['totals']))]
    card_html = ''
    for label, cls, caption, row in cards:
        card_html += f'''<article class="score {cls}"><h2><i aria-hidden="true"></i>{label}</h2>
<div class="number">{pct(row['acos'])}</div><p class="caption">{caption}</p>
<dl><div><dt>Ad spend</dt><dd>{money(row['spend'])}</dd></div><div><dt>Attributed sales</dt><dd>{money(row['sales'])}</dd></div></dl></article>'''
    brand, other, total = groups['brand_query'],groups['other_query'],report.get('account_totals',report['totals'])
    if other['acos'] is not None and total['acos'] is not None:
        finding=f"Non-branded ACoS is {other['acos']:.1%}, versus {total['acos']:.1%} overall."
    else:
        finding='The available sales do not support a complete ACoS comparison.'
    outside = sum(Decimal(g['spend']) for g in report['groups'] if g['category'] not in ('brand_query','other_query'))
    total_spend=Decimal(report['totals']['spend'])
    coverage=f"{money(outside)} ({outside/total_spend:.1%}) sits outside the text-search split." if total_spend else 'No spend was reported.'
    rules=report['brand_reference'].get('rules',[])
    approved=', '.join(r['term'] for r in rules if r.get('status')=='approved') or ', '.join(report['brand_reference']['aliases'])
    proposed=', '.join(r['term'] for r in rules if r.get('status')=='proposed') or 'Review observed spelling variants.'
    variants=[t for t in report['terms'] if t['category']=='brand_review']
    examples=', '.join(t['query'] for t in variants[:6]) or 'None detected.'
    review_notice = ''
    review_summary = ''
    if variants:
        pending = groups['brand_review']
        review_notice = f"<p><b>Brand review:</b> {money(pending['spend'])} spend and {money(pending['sales'])} sales remain outside the text split. Examples: {escape(examples)}. Review these spellings and any model-only names before finalizing the split.</p>"
        review_summary = f"<span class=\"review-summary\">{money(pending['spend'])} spend awaiting brand confirmation</span>"
    elif any(r.get('status') == 'proposed' for r in rules):
        review_summary = '<span class="review-summary">Brand rules under review</span>'
    breakdown=''.join(f"<tr><th>{escape(g['label'])}</th><td>{g['rows']:,}</td><td>{money(g['spend'])}</td><td>{money(g['sales'])}</td></tr>" for g in report['groups'])
    context=report.get('context',{}); support=''
    if 'products' in context:
        p=context['products']
        product_period = '' if privacy else f" from {p['observed_start']} to {p['observed_end']}"
        if p.get('kind') == 'saved_catalog':
            coverage_note = 'Complete catalog as supplied.' if p.get('catalog_complete') else 'Partial catalog; additional owned products may be missing.'
            support+=f"<p><b>Saved product list:</b> {p['product_count']} verified owned ASINs. {coverage_note} Product matches are kept separate from branded searches.</p>"
        else:
            support+=f"<p><b>Advertised products:</b> {p['product_count']} brand-matched ASINs{product_period}. This is an advertised subset, not the full catalog. Product matches are kept separate from branded searches.</p>"
    if 'targeting' in context:
        t=context['targeting']
        target_period = '' if privacy else f" {t['observed_start']} to {t['observed_end']}."
        support+=f"<p><b>Targeting:</b>{target_period} {t['mixed_keyword_ad_groups']} ad groups contain both brand and other keywords among reported enabled targets. {t['shared_product_overlap_count']} repeated keyword/match combinations also share advertised products. These are review candidates; current negatives and delivery still need checking.</p>"
    limits=''.join(f'<li>{escape(x)}</li>' for x in report['limitations'])
    website=report['brand_reference'].get('website')
    website_link=f'<a href="{escape(website,quote=True)}">Brand website</a>' if website and website.startswith(('https://','http://')) else ''
    css=(assets/'report.css').read_text(encoding='utf-8')+(assets/'report-refinements.css').read_text(encoding='utf-8')
    connected=bool(report.get('connection'))
    board_note='Branded and non-branded cover text searches. Overall includes all reported traffic, including ASINs and unreported terms.'
    if connected: board_note += ' Overall uses same-period campaign data.'
    else: board_note += ' Full-account coverage is unverified.'
    account_note='The account total has not been checked against a same-period campaign report.'
    if connected:
        gap=report['account_coverage']['search_to_campaign_delta']['spend']
        account_note=f"Same-period campaign spend differs from reported search-term spend by {money(gap)}. This gap is not assigned to either query class."
    source_note = 'Source details hidden in this presentation.' if privacy else f"Source: {escape(Path(report['source_path']).name)}"
    footer_note = 'Identity hidden · Original metrics preserved · No account changes' if privacy else 'Local report · No account changes'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(report['advertiser'])} | Brand Traffic Review</title>
<style>@font-face{{font-family:Reviewed Inter;src:url(data:font/woff2;base64,{font}) format('woff2');font-weight:100 900;font-style:normal;font-display:swap}}{css}</style></head><body>
<header><div class="wrap head"><img alt="Merch Jar" width="762" height="150" src="data:image/webp;base64,{logo}"><span>Brand Traffic Review</span></div></header>
<main class="wrap"><div class="intro"><div><p class="eyebrow">{escape(report['advertiser'])} · {escape(report['currency'])}</p><h1>Branded vs. non-branded</h1></div><p class="period">{period}<br><span>{period_note}</span></p></div>
<section class="takeaway"><div><h2>{finding}</h2><p>Give branded demand and broader searches separate goals.</p></div><button class="button" type="button" data-report-go="plan">Open campaign plan →</button></section>
<section class="board" aria-label="ACoS comparison"><div class="comparison-labels"><span>Text searches</span><span>All reported traffic</span></div><div class="scores">{card_html}</div><p class="board-note">{board_note}</p></section>
{chart(report)}
{asin_section(report,money)}
<details id="basis"><summary>Brand terms &amp; report coverage {review_summary}</summary><div class="detail-body">
<p>{coverage} Product rows and terms awaiting review remain separate.</p>{review_notice}
<p><b>Included:</b> {escape(approved)}. Case, spacing and hyphens are normalized within whole brand names. Saved exceptions and exclusions take precedence.</p>
<p><b>Proposed names, held for review:</b> {escape(proposed)}.</p><p><b>Observed review examples:</b> {escape(examples)}. {website_link}</p>
<p>Confirm brand and product-line terms with the skill before treating this as the final split. Keep the approved brand reference for the next report. Generic product descriptions are not automatically branded.</p>
<div class="table-scroll"><table><thead><tr><th>Traffic</th><th>Rows</th><th>Ad spend</th><th>Attributed sales</th></tr></thead><tbody>{breakdown}</tbody></table></div>
<p>ACoS = total spend ÷ total attributed sales. Amounts above are rounded for display; calculations use the original amounts. All {report['selected_rows']:,} search-term rows reconcile. {account_note}</p>{support}
<p>Supporting template metrics are not added to search-term metrics. Different date ranges can supply identity context, but cannot validate the same-period account total.</p><ul>{limits}</ul>
<p class="source">{source_note}</p></div></details>
<footer>Prepared with Merch Jar · {footer_note}</footer></main></body></html>'''


def render(report, workspace=None):
    from report_workspace import compose
    return compose(render_performance(report), report, workspace)
