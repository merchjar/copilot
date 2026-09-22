"""Build a separate identity-redacted HTML presentation; preserve original metrics."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import re

from analyze_search_terms import LABELS, METRICS, present
from report_render import render


def numeric(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Presentation metrics must be finite numbers')
    return result


def count(value):
    result = numeric(value)
    if result < 0 or result != result.to_integral_value():
        raise ValueError('Presentation counts must be nonnegative integers')
    return int(result)


def metrics(row):
    # Recalculate all ratios; do not copy free-form fields or supplied labels.
    return present({k: numeric(row[k]) for k in METRICS})


def presentation(report):
    currency = report['currency']
    if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('Expected a three-letter currency code')
    by_class = {g['category']: g for g in report['groups']}
    if set(by_class) != set(LABELS) or len(by_class) != len(report['groups']):
        raise ValueError('Unknown or duplicate traffic categories')
    result = {
        'privacy': True, 'advertiser': 'Account identity hidden', 'currency': currency,
        'selected_rows': count(report['selected_rows']),
        'mixed_campaign_count': count(report.get('mixed_campaign_count', 0)),
        'totals': metrics(report['totals']),
        'groups': [{'category': k, 'label': label, 'rows': count(by_class[k]['rows']),
                    **metrics(by_class[k])} for k, label in LABELS.items()],
        'brand_reference': {'aliases': ['Confirmed brand terms (hidden)'], 'rules': []},
        'terms': [], 'context': {},
        'limitations': ['Identifying text and exact dates are hidden. Original metrics are preserved.',
                        'This presentation does not establish current bidding goals, negatives or profitability.'],
    }
    # Keep the review warning without carrying any proposed term through.
    if any(r.get('status') == 'proposed' for r in report.get('brand_reference', {}).get('rules', [])):
        result['brand_reference']['rules'] = [{'term': 'Proposed terms (hidden)', 'status': 'proposed'}]
    if by_class['brand_review']['rows']:
        result['terms'] = [{'category': 'brand_review', 'query': 'Review examples hidden'}]
    context = report.get('context', {})
    if 'products' in context:
        result['context']['products'] = {'product_count': count(context['products']['product_count'])}
        if context['products'].get('kind') == 'saved_catalog':
            result['context']['products'].update({'kind':'saved_catalog',
                'catalog_complete':context['products'].get('catalog_complete') is True})
    if 'targeting' in context:
        result['context']['targeting'] = {k: count(context['targeting'][k]) for k in
                                         ('mixed_keyword_ad_groups', 'shared_product_overlap_count')}
    if report.get('connection'):
        result['connection'] = True
        result['account_totals'] = metrics(report['account_totals'])
        result['account_coverage'] = {'search_to_campaign_delta': {
            'spend': str(numeric(report['account_coverage']['search_to_campaign_delta']['spend']))}}
    return result


def write_presentation(analysis, output):
    source, dest = Path(analysis).resolve(), Path(output).resolve()
    if source == dest or dest.exists():
        raise ValueError('Privacy output must be a new, separate file; original files are never replaced')
    report = json.loads(source.read_text(encoding='utf-8-sig'))
    html = render(presentation(report))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('x', encoding='utf-8') as stream:
        stream.write(html)
    return dest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis', required=True)
    p.add_argument('--html-output', required=True)
    args = p.parse_args()
    dest = write_presentation(args.analysis, args.html_output)
    from report_delivery import report_artifact
    print(json.dumps({'message': 'Separate privacy presentation created. Original files unchanged.',
                      'report_artifact': report_artifact(dest)}))


if __name__ == '__main__':
    main()
