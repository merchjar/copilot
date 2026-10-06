"""Branded versus non-branded share of ALL reported traffic, using the same buckets as the cards."""
from decimal import Decimal, ROUND_HALF_UP
from report_buckets import buckets


def percent(value):
    return str(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)) + '%'


def shares(report):
    """Spend and revenue shares per bucket over the overall search-term total (branded + non-branded + held).
    Book accounts with KENP data count revenue as sales basis plus KENP royalties."""
    b = buckets(report)
    kenp = bool(b['branded'].get('kenp'))
    revenue = (lambda x: Decimal(x['kenp']['sales_basis']) + Decimal(x['kenp']['royalties'])) if kenp else (lambda x: Decimal(x['sales']))
    result = {}
    for key, value in (('spend', lambda x: Decimal(x['spend'])), ('revenue', revenue)):
        parts = {name: value(b[name]) for name in ('branded', 'non_branded', 'held')}
        total = sum(parts.values(), Decimal(0))
        if any(v < 0 for v in parts.values()) or total <= 0:
            result[key] = None
        else:
            result[key] = {name: v / total * 100 for name, v in parts.items()}
    return result, kenp


def chart(report):
    data, kenp = shares(report)
    revenue_label = 'Sales + KENP royalties' if kenp else 'Attributed sales'
    held_any = any(d and d['held'] > 0 for d in data.values())
    rows = []
    for key, label in (('spend', 'Ad spend'), ('revenue', revenue_label)):
        d = data[key]
        if d is None:
            rows.append(f'<div class="mix-row"><span class="mix-label">{label}</span><p class="mix-empty">No positive total available for this comparison.</p></div>')
            continue
        segments = [('brand', 'Branded', d['branded']), ('nonbrand', 'Non-branded', d['non_branded']), ('held', 'Held for review', d['held'])]
        segments = [s for s in segments if s[2] > 0 or s[0] != 'held']
        # Keep tiny marks accurate; put their values beneath the bar rather than widening them.
        narrow = any(0 < share < 8 for *_, share in segments)
        aria = ', '.join(f'{percent(share)} {name.lower()}' for _, name, share in segments)
        bar = ''.join(f'<span class="mix-segment {cls}" style="width:{share:.10f}%">{percent(share) if not narrow and share > 0 else ""}</span>'
                      for cls, _, share in segments)
        exact = ('<div class="mix-exact">' + ''.join(f'<span>{name} {percent(share)}</span>' for _, name, share in segments) + '</div>') if narrow else ''
        rows.append(f'<div class="mix-row"><span class="mix-label">{label}</span><div class="mix-bar" role="img" aria-label="{label}: {aria}">{bar}</div>{exact}</div>')
    finding = ''
    if data['spend'] and data['revenue']:
        revenue_words = 'of sales and KENP royalties' if kenp else 'of attributed sales'
        finding = (f'<p class="mix-insight">Branded accounts for <strong>{percent(data["spend"]["branded"])} of ad spend</strong> and '
                   f'<strong>{percent(data["revenue"]["branded"])} {revenue_words}</strong> across all reported traffic.</p>')
    held_key = '<span class="key-held"><i aria-hidden="true"></i>Held for review</span>' if held_any else ''
    scope = 'Share of all reported ad spend and ' + ('sales plus KENP royalties' if kenp else 'attributed sales')
    return ('<section class="spend-sales" aria-labelledby="mix-title"><h2 id="mix-title">Where spend and sales come from</h2>'
            f'<p class="chart-scope">{scope}</p><div class="mix-key"><span><i aria-hidden="true"></i>Branded</span>'
            f'<span><i aria-hidden="true"></i>Non-branded</span>{held_key}</div>' + ''.join(rows) + finding +
            '<p class="mix-footnote">Same buckets as the cards: branded includes ads on your own products, non-branded includes '
            'other searches and other ASINs.</p></section>')
