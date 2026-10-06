"""Focused release regressions for the optional upload-based skill.

KDP fixtures are synthetic: the author, series, titles and ASINs are fictional.
"""
import contextlib
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/branded-review'
sys.path.insert(0, str(SKILL / 'scripts'))
from report_context import product_context
from analyze_search_terms import analyze, REQUIRED
from report_render import render_performance
import connected_report
import kdp
from cli_paths import cli_path
import argparse
import re

BASE = ['Budget currency', 'Date range', 'Advertiser account ID', 'Advertiser account name', 'Campaign ID',
        'Campaign name', 'Ad group ID', 'Ad group name', 'Search term', 'Total cost', 'Sales', 'Clicks',
        'Purchases', 'Impressions']
# query, spend, sales, KENP royalties, KENP pages read
BOOK_ROWS = [
    ('mara quillon', '20', '30', '25', '5000'),
    ('saltglass chronicles book 2', '10', '15', '20', '4000'),
    ('ember of the tidewell', '5', '10', '0', '0'),
    ('home again', '8', '0', '4', '800'),
    ('epic fantasy books', '60', '40', '50', '10000'),
    ('rowan ashcombe', '30', '12', '6', '1200'),
    ('B0FICT0002', '9', '9', '3', '600'),
    ('099999999x', '4', '0', '0', '0'),
    ('', '2', '0', '1.5', '300'),
]
BOOK_REFERENCE = {
    'schema': 'brand-reference/1', 'account_id': 'book-account', 'brand': 'Mara Quillon', 'currency': 'USD',
    'account_type': 'kdp',
    'rules': [
        {'term': 'mara quillon', 'match': 'phrase', 'status': 'approved', 'kind': 'author'},
        {'term': 'saltglass chronicles', 'match': 'phrase', 'status': 'approved', 'kind': 'series'},
        {'term': 'ember of the tidewell', 'match': 'phrase', 'status': 'approved', 'kind': 'title'},
        {'term': 'home again', 'match': 'exact', 'status': 'proposed', 'kind': 'title'},
    ],
    'exceptions': [],
    'competitors': [{'term': 'rowan ashcombe', 'match': 'phrase', 'status': 'approved', 'kind': 'author'}],
}
HEADER_VARIANTS = [
    ('Estimated KENP royalties (14 days)', 'Kindle Edition Normalized Pages (KENP) Read (14 days)'),
    ('KENP Royalties', 'KENP Read'),
    ('Estimated KENP Royalties', 'KENP pages read'),
    ('kindleEditionNormalizedPagesRoyalties14d', 'kindleEditionNormalizedPagesRead14d'),
]


def write_report(folder, rows, kenp_headers=None, account='book-account', name='Book sample'):
    path = Path(folder) / 'search-terms.csv'
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(BASE + list(kenp_headers or []))
        for i, (query, spend, sales, royalties, pages) in enumerate(rows):
            line = ['USD', 'Sep 01, 2026 - Sep 30, 2026', account, name, '101', 'Books', '201', 'Series one', query,
                    spend, sales, '10', '1', '100']
            writer.writerow(line + ([royalties, pages] if kenp_headers else []))
    return path


def groups(report):
    return {g['category']: g for g in report['groups']}


class BrandReviewReleaseTests(unittest.TestCase):
    def test_unidentified_products_are_disclosed_without_guessing_ownership(self):
        base = {'Advertised product marketplace':'AMAZON.COM', 'Advertised product brand':'Example',
                'Campaign ID':'1', 'Ad group ID':'2', 'Advertised product name':'Bottle'}
        rows = [{**base, 'Advertised product ID':'B000000001'},
                {**base, 'Advertised product ID':'', 'Advertised product name':'Travel bottle'},
                {**base, 'Advertised product ID':'invalid'},
                {**base, 'Advertised product ID':'', 'Advertised product marketplace':'AMAZON.CA'}]
        with patch('report_context.read_context', return_value=(rows, {})):
            receipt, _ = product_context('unused', 'account', 'USD', 'Example', 'AMAZON.COM')
        self.assertEqual(receipt['owned_asins'], ['B000000001'])
        self.assertEqual(receipt['rows_without_valid_asin'], 2)
        self.assertEqual(receipt['products_without_valid_asin'], ['Bottle', 'Travel bottle'])
        self.assertIn('2 product-report rows', receipt['limitations'][0])

    def test_optional_connection_metadata_does_not_force_connect_installation(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        skill = next(s for s in manifest['skills'] if s['id'] == 'branded-review')
        self.assertEqual(skill['connection_mode'], 'optional')
        self.assertFalse(skill['requires_skills'])
        self.assertIn('merchjar-connect', skill['connected_skills'])


class KdpAccountTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='kdp-test-'))
        self.addCleanup(shutil.rmtree, self.folder, True)

    def book_report(self, headers=HEADER_VARIANTS[0], reference=BOOK_REFERENCE, **kwargs):
        source = write_report(self.folder, BOOK_ROWS, headers)
        return analyze(source, 'Book sample', 'USD', 'Mara Quillon', [], reference, **kwargs)

    def test_kdp_detected_from_kenp_columns_with_both_acos_figures(self):
        report = self.book_report()
        g = groups(report)
        self.assertEqual(report['kdp']['status'], 'detected')
        self.assertTrue(report['kdp']['kenp_included'])
        # Standard ACoS is unchanged: spend / attributed sales.
        self.assertAlmostEqual(g['brand_query']['acos'], 35 / 55)
        self.assertAlmostEqual(g['other_query']['acos'], 90 / 52)
        # ACoS incl. KENP = spend / (attributed sales + estimated KENP royalties).
        self.assertAlmostEqual(g['brand_query']['kenp']['acos_incl_kenp'], 35 / (55 + 45))
        self.assertAlmostEqual(g['other_query']['kenp']['acos_incl_kenp'], 90 / (52 + 56))
        self.assertAlmostEqual(report['totals']['kenp']['acos_incl_kenp'], 148 / 225.5)
        self.assertEqual(report['kenp']['formula'], kdp.FORMULA)
        self.assertEqual(report['kenp']['values'], 'reported')
        html = render_performance(report)
        self.assertIn('KENP royalties', html)
        self.assertNotIn('Blended ACoS', html)
        self.assertNotIn('\u2014', html)

    def test_kdp_report_leads_with_acos_including_kenp(self):
        html = render_performance(self.book_report())
        cards = re.findall(r'<h2><i aria-hidden="true"></i>([^<]+)</h2>\s*<div class="number">([^<]+)</div>', html)
        self.assertEqual(cards, [('Branded ACoS incl. KENP', '35.0%'), ('Non-branded ACoS incl. KENP', '83.3%'),
                                 ('Overall ACoS incl. KENP', '65.6%')])
        sales_only = re.findall(r'<span>ACoS \(sales only\)</span><strong>([^<]+)</strong>', html)
        self.assertEqual(sales_only, ['63.6%', '173.1%', '127.6%'])
        self.assertIn('<h2>Including KENP royalties, non-branded ACoS is 83.3%, versus 65.6% overall.</h2>', html)
        self.assertIn('Sales-only ACoS, without KENP royalties: 173.1% non-branded, 127.6% overall.', html)
        self.assertIn('Sales + KENP royalties', html)
        self.assertIn('ACoS incl. KENP · Reported ASIN rows', html)

    def test_kenp_header_variants_are_recognized(self):
        for headers in HEADER_VARIANTS:
            with self.subTest(headers=headers):
                report = self.book_report(headers)
                self.assertEqual(report['kenp']['royalties_column'], headers[0])
                self.assertEqual(report['kenp']['pages_column'], headers[1])
                self.assertEqual(report['totals']['kenp']['royalties'], '109.5')
                self.assertEqual(report['totals']['kenp']['pages_read'], '21900')

    def test_several_kenp_windows_need_an_explicit_choice(self):
        fields = BASE + ['Estimated KENP royalties (7 days)', 'Estimated KENP royalties (14 days)', 'KENP read (14 days)']
        with self.assertRaises(ValueError):
            kdp.kenp_columns(fields)
        self.assertEqual(kdp.kenp_columns(fields, royalties='Estimated KENP royalties (14 days)'),
                         ('Estimated KENP royalties (14 days)', 'KENP read (14 days)'))
        self.assertEqual(kdp.kenp_columns(BASE + ['Sales (14 days)', 'Units ordered']), (None, None))

    def test_royalties_reconcile_across_classes_to_the_source_total(self):
        report = self.book_report()
        by_class = sum(Decimal(g['kenp']['royalties']) for g in report['groups'])
        source = sum(Decimal(r[3]) for r in BOOK_ROWS)
        self.assertEqual(by_class, source)
        self.assertEqual(Decimal(report['totals']['kenp']['royalties']), source)
        self.assertEqual(sum(Decimal(r['kenp_royalties']) for r in report['rows']), source)
        self.assertIn('kenp_royalties', report['reconciliation']['metrics_checked'])

    def test_book_brand_reference_holds_everyday_titles_and_labels_competitor_authors(self):
        report = self.book_report()
        rows = {r['query']: r for r in report['rows']}
        self.assertEqual(rows['saltglass chronicles book 2']['category'], 'brand_query')
        self.assertEqual(rows['saltglass chronicles book 2']['reason'], 'Approved series rule: saltglass chronicles')
        self.assertEqual(rows['home again']['category'], 'brand_review')
        self.assertIn('Proposed title rule', rows['home again']['reason'])
        self.assertEqual(rows['rowan ashcombe']['category'], 'other_query')
        self.assertEqual(rows['rowan ashcombe']['reason'], 'Confirmed competitor author: rowan ashcombe')
        self.assertEqual(report['competitor_queries']['spend'], '30')
        self.assertEqual(rows['099999999x']['category'], 'asin_unknown')
        bad = json.loads(json.dumps(BOOK_REFERENCE))
        bad['rules'][2]['match'] = 'contains_compact'
        with self.assertRaises(ValueError):
            self.book_report(reference=bad)

    def test_ordinary_product_account_is_never_detected_as_kdp(self):
        rows = [('northstar gear backpack', '40', '400', '0', '0'), ('hiking backpack', '80', '200', '0', '0'),
                ('0306406152', '5', '0', '0', '0'), ('B000000001', '10', '50', '0', '0')]
        reference = {'account_id': 'product-account', 'brand': 'Northstar Gear', 'currency': 'USD', 'rules': [], 'exceptions': []}
        for headers in (None, HEADER_VARIANTS[0]):
            with self.subTest(kenp_columns=bool(headers)):
                source = write_report(self.folder, rows, headers, 'product-account', 'Gear sample')
                report = analyze(source, 'Gear sample', 'USD', 'Northstar Gear', [], reference)
                self.assertNotIn('kdp', report)
                self.assertNotIn('kenp', report)
                self.assertTrue(all('kenp' not in g for g in report['groups']))
                self.assertNotIn('incl. KENP', render_performance(report))

    def test_isbn_advertised_products_only_prompt_a_question(self):
        source = write_report(self.folder, [(q, s, v, '0', '0') for q, s, v, _, _ in BOOK_ROWS])
        products = self.folder / 'products.csv'
        products.write_text('Advertiser account ID,Budget currency,Date range,Campaign ID,Ad group ID,Advertised product ID,'
                            'Advertised product brand,Advertised product marketplace\n'
                            'book-account,USD,"Sep 01, 2026 - Sep 30, 2026",101,201,099999999X,Mara Quillon,AMAZON.COM\n'
                            'book-account,USD,"Sep 01, 2026 - Sep 30, 2026",101,201,B0FICT0001,Mara Quillon,AMAZON.COM\n', encoding='utf-8')
        report = analyze(source, 'Book sample', 'USD', 'Mara Quillon', [], advertised_products=products, marketplace='AMAZON.COM')
        self.assertEqual(report['kdp']['status'], 'possible')
        self.assertFalse(report['kdp']['kenp_included'])
        self.assertIn('099999999X', report['context']['products']['owned_asins'])
        self.assertNotIn('kenp', report)

    def test_confirmed_book_account_without_kenp_columns_discloses_the_gap(self):
        source = write_report(self.folder, BOOK_ROWS)
        report = analyze(source, 'Book sample', 'USD', 'Mara Quillon', [], account_type='kdp')
        self.assertEqual(report['kdp']['status'], 'confirmed')
        self.assertNotIn('kenp', report)
        self.assertTrue(any('excludes Kindle Unlimited' in x for x in report['limitations']))

    def test_not_split_panel_makes_the_cards_add_up_to_overall(self):
        from report_unsplit import items
        report = self.book_report()
        html = render_performance(report)
        panel = re.search(r'<section class="unsplit".*?</section>', html, re.S).group(0)
        self.assertIn('Branded $35 + non-branded $90 + not split $23 = overall $148 ad spend.', panel)
        for label in ('ASIN targeting (ownership unknown)', 'Possible brand variants, held for review', 'Unreported search terms'):
            self.assertIn(label, panel)
        self.assertIn('ACoS incl. KENP', panel)
        parts = {p['key']: p for p in items(report)}
        self.assertEqual(parts['asin_unknown']['spend'] + parts['brand_review']['spend'] + parts['missing_query']['spend'], Decimal(23))
        self.assertEqual(parts['asin_unknown']['royalties'], Decimal(3))
        self.assertEqual(parts['asin_unknown']['acos'], f'{13 / 12:.1%}')

    def test_not_split_panel_separates_own_product_asins_when_a_catalog_exists(self):
        source = write_report(self.folder, BOOK_ROWS, HEADER_VARIANTS[0])
        catalog = {'scope': {'account_id': 'book-account', 'brand': 'Mara Quillon', 'marketplace': 'AMAZON.COM'},
                   'source': 'test', 'ownership_verified': True, 'owned_asins': ['B0FICT0002'], 'complete': False}
        report = analyze(source, 'Book sample', 'USD', 'Mara Quillon', [], BOOK_REFERENCE | {'marketplace': 'AMAZON.COM'},
                         marketplace='AMAZON.COM', catalog=catalog)
        panel = re.search(r'<section class="unsplit".*?</section>', render_performance(report), re.S).group(0)
        self.assertIn('Your own books', panel)
        self.assertIn('Other books or unknown ASINs', panel)
        self.assertIn('Ads shown on your own book pages or targeting your books.', panel)
        self.assertNotIn('own-product ASINs', panel)
        self.assertNotIn('ownership unknown)', panel)

    def test_negative_campaign_difference_reads_naturally(self):
        report = self.book_report()
        report['account_totals'] = {**report['totals'], 'spend': '100', 'sales': '116'}
        panel = re.search(r'<section class="unsplit".*?</section>', render_performance(report), re.S).group(0)
        self.assertIn('<strong>-$48</strong>', panel)
        self.assertIn('not split $23 - campaign difference $48 = overall $100 ad spend.', panel)
        self.assertNotIn('$-', render_performance(report))

    def test_report_with_only_text_searches_has_no_not_split_panel(self):
        rows = [('northstar gear backpack', '40', '400', '0', '0'), ('hiking backpack', '80', '200', '0', '0')]
        source = write_report(self.folder, rows, None, 'product-account', 'Gear sample')
        report = analyze(source, 'Gear sample', 'USD', 'Northstar Gear', [])
        self.assertNotIn('class="unsplit"', render_performance(report))

    def test_author_initials_punctuation_matches_the_confirmed_name(self):
        from analyze_search_terms import classify
        for query in ('k.a. tucker books', 'k.a tucker kindle', 'the simple wild k.a. tucker', 'k. a. tucker', 'k a tucker', 'ka tucker'):
            with self.subTest(query=query):
                self.assertEqual(classify(query, ['KA Tucker'])[0], 'brand_query')
                self.assertEqual(classify(query, ['K.A. Tucker'])[0], 'brand_query')
        self.assertEqual(classify('k.a. tucker', ['KA Tucker'])[1], 'Initials equivalent of confirmed name: KA Tucker')
        for query in ('kayla tucker books', 'k.a. tuckers', 'tucker'):
            self.assertNotEqual(classify(query, ['KA Tucker'])[0], 'brand_query')
        self.assertEqual(classify('north.star gear', ['Northstar Gear'])[0], 'other_query')
        rule = {'term': 'ka tucker', 'match': 'phrase', 'status': 'approved', 'kind': 'author'}
        reference = {'rules': [rule], 'exceptions': []}
        self.assertEqual(classify('k.a. tucker kindle', ['Someone Else'], reference)[0], 'brand_query')

    def test_initials_variants_are_disclosed_as_automatic(self):
        source = write_report(self.folder, [('k.a. tucker books', '10', '20', '1', '100'), ('romance books', '5', '5', '0', '0')],
                              HEADER_VARIANTS[0])
        report = analyze(source, 'Book sample', 'USD', 'KA Tucker', [])
        decision = next(d for d in report['brand_decisions'] if d['automatic'])
        self.assertEqual(decision['reason'], 'Initials punctuation and spacing included automatically')
        self.assertEqual(decision['examples'], ['k.a. tucker books'])

    def test_privacy_presentation_keeps_kenp_numbers_without_identity(self):
        from privacy_report import presentation
        report = self.book_report()
        hidden = presentation(report)
        self.assertEqual(groups(hidden)['brand_query']['kenp'], groups(report)['brand_query']['kenp'])
        text = json.dumps(hidden)
        for private in ('mara', 'saltglass', 'rowan', 'B0FICT0002', 'book-account'):
            self.assertNotIn(private, text.lower() if private.islower() else text)
        self.assertIn('ACoS incl. KENP', render_performance(hidden))

    def test_non_kdp_output_matches_the_previous_release(self):
        """The bundled product example must produce byte-identical analysis and HTML to the v1.2.7 skill."""
        try:
            files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', 'v1.2.7', 'skills/branded-review'],
                                            cwd=ROOT, text=True).splitlines()
        except (OSError, subprocess.CalledProcessError):
            self.skipTest('v1.2.7 tag unavailable')
        old = self.folder / 'old'
        for name in files:
            target = old / Path(name).relative_to('skills/branded-review')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(['git', 'show', f'v1.2.7:{name}'], cwd=ROOT))
        outputs = {}
        for label, skill in (('old', old), ('new', SKILL)):
            out = self.folder / label
            out.mkdir(exist_ok=True)
            examples = SKILL / 'examples'
            subprocess.check_output([sys.executable, '-X', 'utf8', str(skill / 'scripts/analyze_search_terms.py'),
                str(examples / 'search-terms.csv'), '--advertiser', 'Northstar Gear sample', '--currency', 'USD',
                '--brand', 'Northstar Gear', '--brand-reference', str(examples / 'brand-reference.json'),
                '--advertised-products', str(examples / 'advertised-products.csv'), '--marketplace', 'AMAZON.COM',
                '--targeting', str(examples / 'targeting.csv'),
                '--json-output', str(out / 'analysis.json'), '--html-output', str(out / 'report.html')], cwd=self.folder)
            outputs[label] = ((out / 'analysis.json').read_text(encoding='utf-8'), (out / 'report.html').read_text(encoding='utf-8'))
        self.assertEqual(outputs['old'][0], outputs['new'][0])
        # Intended page differences only: the embedded list editor also accepts ISBN-10 IDs ending in X, and
        # every report now shows the "Not split yet" panel (with its stylesheet) so the cards add up to Overall.
        old_html = outputs['old'][1].replace('(?:B[A-Z0-9]{9}|[0-9]{10})', '(?:B[A-Z0-9]{9}|[0-9]{9}[0-9X])')
        new_html = outputs['new'][1]
        css = (SKILL / 'assets/unsplit.css').read_text(encoding='utf-8')
        panel = re.search(r'<section class="unsplit".*?</section>', new_html, re.S).group(0)
        self.assertIn('Branded $40 + non-branded $80 + not split $20 = overall $140 ad spend.', panel)
        self.assertIn('Your own-product ASINs', panel)
        self.assertEqual(old_html, new_html.replace(css, '', 1).replace(panel, '', 1))


START, END = '2026-09-01', '2026-09-30'


def preview_row(index, query, spend, sales, kdp_values=None, campaign=False):
    f = connected_report.metric_fields(START, END)
    row = {'profile_id': '77', 'campaign_id': str(100 + (index if campaign else 0)), 'campaign_name': 'Books',
           f['spend']: spend, f['sales']: sales, f['clicks']: 10, f['purchases']: 1, f['impressions']: 100}
    if not campaign:
        row.update({'ad_group_id': '201', 'ad_group_name': 'Series one', 'search_term': query})
    for name, value in (kdp_values or {}).items():
        row[f'{name}_{START}_to_{END}'] = value
    return row


def preview_pages(rows, per_page=2):
    pages = [rows[i:i + per_page] for i in range(0, len(rows), per_page)] or [[]]
    keys = {k for r in rows for k in r if k.endswith(f'{START}_to_{END}')}
    totals = {k: sum(r[k] for r in rows) for k in sorted(keys)}
    return [{'data': page, 'totals': dict(totals), 'meta': {},
             'pagination': {'page': n, 'per_page': per_page, 'total': len(rows), 'last_page': len(pages) if rows else 0}}
            for n, page in enumerate(pages, 1)]


class ConnectedKdpTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='kdp-connected-'))
        self.addCleanup(shutil.rmtree, self.folder, True)

    def run_connected(self, search_rows, campaign_rows, extra=(), ads=None):
        responses = {'search_terms': preview_pages(search_rows), 'campaigns': preview_pages(campaign_rows)}
        if ads is not None:
            ad_rows = [{'profile_id': '77', 'ad_id': str(900 + i), 'creative_products_product_id': asin,
                        'creative_products_product_id_type': 'ASIN'} for i, asin in enumerate(ads)]
            responses['ads'] = preview_pages(ad_rows, per_page=2)
        (self.folder / 'responses.json').write_text(json.dumps(responses), encoding='utf-8')
        client = self.folder / 'fake_client.py'
        client.write_text(
            'import json\nfrom pathlib import Path\n'
            'R=json.loads((Path(__file__).parent/"responses.json").read_text())\n'
            'def load_api_key(): return "local-test-placeholder"\n'
            'def request_json(method, path, key, profileid=None, body=None, idempotency_key=None):\n'
            '    if method == "GET": return {"data": [{"profile_id": "77", "name": "Book sample", "currency_code": "USD"}]}\n'
            '    assert body["action"] == "set_state"\n'
            '    return R[body["ad_type"]][body["page"] - 1]\n', encoding='utf-8')
        argv = ['connected_report.py', '--client', str(client), '--profile', '77', '--start', START, '--end', END,
                '--brand', 'Mara Quillon', '--output-dir', str(self.folder / 'read'),
                '--html-output', str(self.folder / 'report.html'), *extra]
        with patch.object(sys, 'argv', argv), patch.object(connected_report.time, 'sleep'), \
                contextlib.redirect_stdout(io.StringIO()):
            connected_report.main()
        report = json.loads((self.folder / 'read/analysis.json').read_text(encoding='utf-8'))
        return report, (self.folder / 'report.html').read_text(encoding='utf-8')

    def book_rows(self, adjusted=True):
        def values(royalties, pages, sales):
            base = {'pages_read': pages, 'estimated_royalties': royalties}
            if adjusted:
                base.update({'adjusted_sales': sales, 'adjusted_pages_read': pages * 1.25,
                             'adjusted_estimated_royalties': royalties * 1.25})
            return base
        search = [preview_row(0, 'mara quillon', 20.0, 30.0, values(20.0, 4000, 30.0)),
                  preview_row(0, 'epic fantasy books', 60.0, 40.0, values(40.0, 8000, 40.0)),
                  preview_row(0, 'B0FICT0002', 9.0, 9.0, values(4.0, 800, 9.0))]
        campaigns = [preview_row(1, '', 89.0, 79.0, values(64.0, 12800, 79.0), campaign=True)]
        return search, campaigns

    def test_connected_kdp_uses_adjusted_values_and_discloses_multipliers(self):
        report, html = self.run_connected(*self.book_rows(), ads=['B0FICT0002', 'B0FICT0002', '099999999X'])
        g = groups(report)
        self.assertEqual(report['kenp']['values'], 'adjusted')
        self.assertEqual(report['kenp']['fields']['royalties'], 'adjusted_estimated_royalties')
        self.assertAlmostEqual(g['brand_query']['acos'], 20 / 30)
        self.assertAlmostEqual(g['brand_query']['kenp']['acos_incl_kenp'], 20 / (30 + 25))
        self.assertAlmostEqual(g['other_query']['kenp']['acos_incl_kenp'], 60 / (40 + 50))
        self.assertAlmostEqual(report['account_totals']['kenp']['acos_incl_kenp'], 89 / (79 + 80))
        self.assertAlmostEqual(report['kenp']['multipliers']['KENP royalties'], 1.25)
        disclosure = ' '.join(report['kenp']['disclosures'])
        self.assertIn('Ad Impact Multipliers other than 1 are in effect', disclosure)
        self.assertIn('KENP royalties x1.25', disclosure)
        self.assertIn('KENP royalties x1.25', html)
        self.assertEqual(report['kdp']['status'], 'detected')

    def test_connected_kdp_falls_back_to_reported_values_and_says_so(self):
        report, html = self.run_connected(*self.book_rows(adjusted=False), ads=['B0FICT0002'])
        self.assertEqual(report['kenp']['values'], 'reported')
        self.assertAlmostEqual(groups(report)['brand_query']['kenp']['acos_incl_kenp'], 20 / (30 + 20))
        self.assertIn('Adjusted values were unavailable', ' '.join(report['kenp']['disclosures']))
        self.assertIn('Adjusted values were unavailable', html)

    def test_connected_kdp_reads_product_ads_as_the_owned_catalog(self):
        report, html = self.run_connected(*self.book_rows(), ads=['B0FICT0002', 'B0FICT0002', '099999999X', ''])
        products = report['context']['products']
        self.assertEqual(products['owned_asins'], ['099999999X', 'B0FICT0002'])
        self.assertEqual(products['catalog_label'], 'advertised titles')
        self.assertFalse(products['catalog_complete'])
        self.assertTrue(any("KDP account's 4 Product Ads (2 advertised ASINs)" in x for x in report['limitations']))
        rows = {r['query']: r for r in report['rows']}
        self.assertEqual(rows['B0FICT0002']['category'], 'owned_asin')
        self.assertIn('ASINs from this KDP account', html)
        self.assertIn('Your own books', html)
        pages = sorted(p.name for p in (self.folder / 'read').glob('ads-page-*.json'))
        self.assertEqual(pages, ['ads-page-1.json', 'ads-page-2.json'])
        body = json.loads((self.folder / 'read/ads-page-1.json').read_text(encoding='utf-8'))
        self.assertEqual(body['data'][0]['creative_products_product_id'], 'B0FICT0002')

    def test_connected_product_account_with_zero_kdp_fields_is_unchanged(self):
        zero = {'pages_read': 0, 'estimated_royalties': 0, 'adjusted_sales': 30.0, 'adjusted_pages_read': 0,
                'adjusted_estimated_royalties': 0}
        search = [preview_row(0, 'northstar gear backpack', 20.0, 30.0, zero)]
        report, html = self.run_connected(search, [preview_row(1, '', 20.0, 30.0, zero, campaign=True)])
        self.assertNotIn('kenp', report)
        self.assertNotIn('kdp', report)
        self.assertNotIn('kenp', report['account_totals'])
        self.assertNotIn('incl. KENP', html)
        with (self.folder / 'read/connected-search-terms.csv').open(encoding='utf-8') as stream:
            self.assertEqual(next(csv.reader(stream)), REQUIRED)
        # Product accounts: advertised products do not prove ownership, so Product Ads are not read.
        self.assertFalse(list((self.folder / 'read').glob('ads-page-*.json')))
        self.assertNotIn('products', report['context'])

    def test_connected_royalty_total_must_reconcile(self):
        search, campaigns = self.book_rows()
        pages = preview_pages(search)
        for page in pages:
            page['totals'][f'adjusted_estimated_royalties_{START}_to_{END}'] += 5
        client = type('Client', (), {'request_json': staticmethod(lambda *a, **k: pages[k['body']['page'] - 1])})
        with self.assertRaises(ValueError):
            connected_report.collect(client, 'unused', '77', 'search_terms', START, END, None,
                                     pause=lambda _: None, kdp_receipt={})


class PopulationRetryTests(unittest.TestCase):
    """A data sync landing mid-pull (19,437 to 19,464 rows at page 172 of 195) restarts the pull once."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='kdp-retry-')) / 'read'
        self.folder.mkdir()
        self.addCleanup(shutil.rmtree, self.folder.parent, True)

    def run_pull(self, attempts):
        responses = iter(page for attempt in attempts for page in attempt)
        client = type('Client', (), {'request_json': staticmethod(lambda *a, **k: next(responses))})
        receipt = {}
        result = connected_report.collect(client, 'unused', '77', 'search_terms', START, END, self.folder,
                                          pause=lambda _: None, pull_receipt=receipt)
        return result, receipt

    def test_population_change_restarts_once_and_keeps_aborted_receipts(self):
        rows = [preview_row(0, q, 1.0, 2.0) for q in 'abc']
        attempt1 = preview_pages(rows, per_page=2)
        attempt1[1]['pagination']['total'] = 4  # a sync added a row before page 2
        (got_rows, totals), receipt = self.run_pull([attempt1, preview_pages(rows, per_page=2)])
        self.assertEqual(len(got_rows), 3)
        self.assertEqual(totals['spend'], Decimal('3.0'))
        aborted = self.folder.parent / 'read-aborted-attempt-1'
        self.assertEqual(sorted(p.name for p in aborted.iterdir()), ['search_terms-page-1.json', 'search_terms-page-2.json'])
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ['search_terms-page-1.json', 'search_terms-page-2.json'])
        self.assertEqual(receipt['restarted_after_population_change'][0]['ad_type'], 'search_terms')

    def test_second_population_change_stops_with_the_existing_message(self):
        rows = [preview_row(0, q, 1.0, 2.0) for q in 'abc']
        def changing():
            pages = preview_pages(rows, per_page=2)
            pages[1]['pagination']['total'] = 4
            return pages
        with self.assertRaisesRegex(ValueError, 'Preview population changed during pagination'):
            self.run_pull([changing(), changing()])


class CliPathTests(unittest.TestCase):
    """Git Bash with MSYS_NO_PATHCONV=1 passes /c/Users/... through; Windows Python would write to C:\\c\\Users."""

    def test_drive_style_posix_paths_become_windows_drive_paths(self):
        self.assertEqual(cli_path('/c/Users/name/private', windows=True), Path('C:/Users/name/private'))
        self.assertEqual(cli_path('/cygdrive/d/reports/a.html', windows=True), Path('D:/reports/a.html'))
        self.assertEqual(cli_path('/c', windows=True), Path('C:/'))
        self.assertEqual(cli_path('C:/Users/name/a.html', windows=True), Path('C:/Users/name/a.html'))
        self.assertEqual(cli_path('relative/a.html', windows=True), Path('relative/a.html'))

    def test_other_root_relative_paths_are_rejected_on_windows_only(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            cli_path('/tmp/report.html', windows=True)
        self.assertEqual(cli_path('/c/Users/name', windows=False), Path('/c/Users/name'))
        self.assertEqual(cli_path('/tmp/report.html', windows=False), Path('/tmp/report.html'))


class PaginationToleranceTests(unittest.TestCase):
    """Regression: a 213-page pull aborted at page 124 when page totals differed only in trailing float digits."""

    def pages(self, second_totals):
        f = connected_report.metric_fields(START, END)
        first = {f['spend']: 36185.15999999996, f['sales']: 1.0, f['clicks']: 2, f['purchases']: 0, f['impressions']: 9,
                 f'acos_{START}_to_{END}': 0.1234567890123}
        rows = [{'profile_id': '77', 'campaign_id': '1', 'ad_group_id': '2', 'search_term': q,
                 f['spend']: s, f['sales']: 0.5, f['clicks']: 1, f['purchases']: 0, f['impressions']: i}
                for q, s, i in (('a', 18092.57999999998, 4), ('b', 18092.57999999998, 5))]
        second = {**first, **second_totals}
        return [{'data': [rows[0]], 'totals': first, 'pagination': {'page': 1, 'total': 2, 'last_page': 2}},
                {'data': [rows[1]], 'totals': second, 'pagination': {'page': 2, 'total': 2, 'last_page': 2}}]

    def collect(self, pages):
        client = type('Client', (), {'request_json': staticmethod(lambda *a, **k: pages[k['body']['page'] - 1])})
        return connected_report.collect(client, 'unused', '77', 'search_terms', START, END, None, pause=lambda _: None)

    def test_trailing_float_digits_do_not_abort_the_pull(self):
        f = connected_report.metric_fields(START, END)
        rows, totals = self.collect(self.pages({f['spend']: 36185.15999999992, f'acos_{START}_to_{END}': 0.1234567890124}))
        self.assertEqual(len(rows), 2)
        self.assertEqual(totals['spend'], Decimal('36185.15999999996'))

    def test_real_population_changes_still_abort(self):
        f = connected_report.metric_fields(START, END)
        for change in ({f['spend']: 36185.17}, {f['impressions']: 10}, {f['clicks']: 3}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.collect(self.pages(change))
        self.assertTrue(connected_report.same_totals({'x': 1.0, 'n': 3}, {'x': 1.0 + 1e-9, 'n': 3}))
        self.assertFalse(connected_report.same_totals({'x': 1.0, 'n': 3}, {'x': 1.0, 'n': 4}))
        self.assertFalse(connected_report.same_totals({'x': 1.0}, {'x': 1.0, 'y': 0}))


if __name__ == '__main__':
    unittest.main()
