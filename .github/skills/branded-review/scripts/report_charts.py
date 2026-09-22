"""Text-search share comparison, independent of ASIN and unknown traffic."""
from decimal import Decimal, ROUND_HALF_UP

def percent(value):
    return str(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)) + '%'


def chart(report):
    groups = {g['category']:g for g in report['groups']}
    brand, other = groups['brand_query'], groups['other_query']
    shares, rows = {}, []
    for key, label in [('spend', 'Ad spend'), ('sales', 'Attributed sales')]:
        a, b = Decimal(brand[key]), Decimal(other[key])
        total = a + b
        if a < 0 or b < 0 or total <= 0:
            rows.append(f'<div class="mix-row"><span class="mix-label">{label}</span><p class="mix-empty">No positive total available for this comparison.</p></div>')
            continue
        share = a/total*100
        shares[key] = share
        left, right = percent(share), percent(Decimal(100)-share)
        # Keep tiny marks accurate; put their values beneath the bar rather than widening them.
        narrow = min(share, 100-share) < 8
        alternative = f'<div class="mix-exact"><span>Branded {left}</span><span>Non-branded {right}</span></div>' if narrow else ''
        rows.append(f'<div class="mix-row"><span class="mix-label">{label}</span><div class="mix-bar" role="img" aria-label="Text-search {label.lower()}: {left} branded, {right} non-branded"><span class="mix-segment brand" style="width:{share:.10f}%">{left if not narrow else ""}</span><span class="mix-segment nonbrand" style="width:{100-share:.10f}%">{right if not narrow else ""}</span></div>{alternative}</div>')
    finding = ''
    if len(shares) == 2:
        finding = f'<p class="mix-insight">Brand searches account for <strong>{percent(shares["spend"])} of spend</strong> and <strong>{percent(shares["sales"])} of attributed sales</strong> in the text-search split.</p>'
    return '<section class="spend-sales" aria-labelledby="mix-title"><h2 id="mix-title">Where spend and sales come from</h2><p class="chart-scope">Share of text-search spend and attributed sales</p><div class="mix-key"><span><i aria-hidden="true"></i>Branded</span><span><i aria-hidden="true"></i>Non-branded</span></div>'+''.join(rows)+finding+'<p class="mix-footnote">ASIN traffic, unreported terms and terms awaiting review stay outside this comparison.</p></section>'


