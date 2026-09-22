"""Brand-list display and draft editing without account access."""
from copy import deepcopy
from html import escape
from pathlib import Path
import hashlib
import json
import re

ASSETS = Path(__file__).resolve().parents[1]/"assets"


def inline_json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def preferences(report, simulation=False):
    ref = deepcopy(report['brand_reference'])
    products = report.get('context', {}).get('products', {})
    base = {'brand_reference': ref, 'owned_asins': sorted(products.get('owned_asins', [])),
            'catalog_complete': products.get('catalog_complete') is True}
    return {'schema': 'brand-review-preferences-draft/1', 'simulation': simulation,
            'scope': {k: report.get(k) for k in ('account_id', 'brand', 'currency')},
            'marketplace': products.get('marketplace') or ref.get('marketplace'),
            'report_source_sha256': report.get('source_sha256'),
            'baseline_sha256': hashlib.sha256(json.dumps(base, sort_keys=True).encode()).hexdigest(),
            'baseline': base}


def editor(report, simulation=False):
    if report.get('privacy'):
        return '<section class="brand-lists privacy-list"><h2>Your brand lists</h2><p>Brand terms and ASINs are hidden in this privacy copy. Review or edit them in your private report.</p></section>'
    data = preferences(report, simulation)
    ref = data['baseline']['brand_reference']
    names = len(ref.get('aliases', []))
    count = len(data['baseline']['owned_asins'])
    return f'''<details id="brand-lists" class="brand-lists"><summary>Your brand lists <span>{names} names · {count} ASINs · View or edit</span></summary>
<div class="list-editor"><p class="list-intro">These lists define this report. Edit a draft here, then send the changes to Copilot to update your saved preferences and recalculate the report.</p>
<p class="list-status" id="list-status" role="status">Showing the lists used in this report.</p>
<div class="list-columns"><section><h3>Brand names &amp; product lines</h3><p>Primary brand: <strong>{escape(report['brand'])}</strong>. Case, spaces and hyphens are already handled.</p>
<label for="brand-aliases">Included names, one per line</label><textarea id="brand-aliases" rows="8" spellcheck="false"></textarea>
<p class="field-note">Keep only names that identify your brand. Generic product descriptions do not belong here.</p>
<h3>Additional spellings for this report</h3><p class="field-note">Choose which searches count as branded here. Proposed campaign negatives are shown separately in Campaign plan, using Amazon's Negative phrase and Negative exact match types.</p><div id="brand-rules"></div><button type="button" class="quiet-button" id="add-brand-rule">Add a term</button>
<div id="saved-exceptions"></div></section>
<section><h3>Your ASINs <span id="asin-list-count"></span></h3><p>Paste your owned ASINs, one per line. Spaces and commas work too.</p>
<label for="owned-asins">Owned ASIN list</label><textarea id="owned-asins" rows="12" spellcheck="false"></textarea>
<label class="catalog-checkbox"><input id="catalog-complete" type="checkbox">This is the full ASIN list for this brand and marketplace</label>
<p class="field-note">An advertised-product report is usually a partial list. Products missing from it stay unknown.</p></section></div>
<p id="list-errors" class="list-errors" role="alert"></p><div class="list-actions"><button type="button" class="button" id="copy-list-changes">Copy changes for Copilot</button><button type="button" class="quiet-button" id="save-report-changes">Save report with changes</button><button type="button" class="quiet-button" id="download-list-changes">Download changes only</button><button type="button" class="quiet-button" id="reset-list-draft">Reset draft</button></div>
<p class="field-note">Edits do not change the numbers above or apply campaign negatives. Copilot checks the changes, saves the lists and refreshes this report.</p>
<textarea id="list-copy-fallback" aria-label="Changes to copy into Copilot" rows="8" readonly hidden></textarea></div></details>
<script id="brand-list-data" type="application/json">{inline_json(data)}</script>'''


def enhance(html, report):
    html = html.replace('<details id="basis">', editor(report, report.get('simulation') is True)+'<details id="basis">', 1)
    html = html.replace('Brand terms &amp; report coverage', 'Report coverage &amp; methodology', 1)
    js = (ASSETS/'list-editor.js').read_text(encoding='utf-8')
    return html.replace('</body>', '<script>'+js+'</script></body>')
