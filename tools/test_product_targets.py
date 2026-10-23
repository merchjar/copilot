import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/create-campaigns/scripts/product_targets.py'
spec = importlib.util.spec_from_file_location('product_targets', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ASIN = 'B0AAAAAAA1'
# Strict item shapes from https://merchjar.com/api/openapi.json (POST /targets), retrieved 2026-10-23.
PRODUCT_KEYS = {'adGroupId', 'adProduct', 'negative', 'state', 'targetType', 'targetDetails'}


def ad(group, product, campaign='Launch'):
    return dict(ad_group_id=group, creative_products_product_id=product, ad_group_name='g' + group,
                campaign_name=campaign)


def term(group, text, orders, sales='20', clicks='4', cost='2.00'):
    return dict(ad_group_id=group, search_term=text, orders_60d=orders, sales_60d=sales,
                clicks_60d=clicks, cost_60d=cost)


class SeedTest(unittest.TestCase):
    def setUp(self):
        # Group 1 advertises only ASIN; group 2 shares ASIN with another product; group 3 is unrelated.
        self.ads = [ad('1', ASIN), ad('2', ASIN), ad('2', 'B0BBBBBBB2'), ad('3', 'B0CCCCCCC3')]

    def test_asin_terms(self):
        self.assertEqual(m.asin_term('b07kw6rmxq'), 'B07KW6RMXQ')
        self.assertEqual(m.asin_term('014303943x'), '014303943X')
        for text in ('waterproof', 'b07kw6rmx', 'running shoes', 'a07kw6rmxq', '', None):
            self.assertIsNone(m.asin_term(text))

    def test_product_specific_seeds_ranked_with_cpc(self):
        rows = [term('1', 'b0ddddddd4', 1), term('1', 'b0eeeeeee5', 3, '60', '10', '5.00'),
                term('1', 'b0ddddddd4', 1, '10', '2', '1.00'), term('1', 'garden gnome', 5),
                term('1', 'b0fffffff6', 0)]
        result = m.seeds(rows, self.ads, ASIN, '60d')
        self.assertEqual([s['asin'] for s in result['seeds']], ['B0EEEEEEE5', 'B0DDDDDDD4'])
        self.assertEqual(result['seeds'][1]['orders'], '2')
        self.assertEqual(result['seeds'][1]['cpc'], '0.50')
        self.assertEqual(result['product_ad_groups'], ['1'])

    def test_shared_group_evidence_is_not_a_seed(self):
        result = m.seeds([term('2', 'b0ddddddd4', 4)], self.ads, ASIN, '60d')
        self.assertEqual(result['seeds'], [])
        self.assertEqual(result['shared_group_asins'][0]['asin'], 'B0DDDDDDD4')
        self.assertEqual(result['shared_ad_groups'][0]['products'], 2)

    def test_partial_ads_confirm_sharing_but_not_single_product_groups(self):
        rows = [term('1', 'b0ddddddd4', 2), term('2', 'b0eeeeeee5', 2)]
        result = m.seeds(rows, self.ads, ASIN, '60d', ads_complete=False)
        self.assertEqual(result['seeds'], [])
        self.assertEqual(result['unconfirmed_ad_groups'], ['1'])
        self.assertEqual([g['ad_group_id'] for g in result['shared_ad_groups']], ['2'])
        self.assertEqual(sorted(s['asin'] for s in result['shared_group_asins']), ['B0DDDDDDD4', 'B0EEEEEEE5'])

    def test_self_owned_unrelated_and_threshold(self):
        rows = [term('1', ASIN.lower(), 9), term('1', 'b0bbbbbbb2', 2), term('3', 'b0ddddddd4', 7),
                term('1', 'b0eeeeeee5', 1)]
        result = m.seeds(rows, self.ads, ASIN, '60d', owned=['B0BBBBBBB2'], min_orders=2)
        self.assertEqual(result['seeds'], [])
        self.assertEqual([o['asin'] for o in result['owned_asins']], ['B0BBBBBBB2'])
        self.assertEqual(result['rows_outside_product_groups'], 1)

    def test_existing_targets_are_flagged(self):
        targets = [dict(ad_group_id='1', target_details_asin='B0DDDDDDD4', target_details_match_type='PRODUCT_EXACT',
                        state='ENABLED'),
                   dict(ad_group_id='1', target_details_asin='B0EEEEEEE5', target_details_match_type='PRODUCT_EXACT',
                        state='ARCHIVED'),
                   dict(ad_group_id='3', target_details_asin='B0EEEEEEE5', target_details_match_type='PRODUCT_SIMILAR')]
        result = m.seeds([term('1', 'b0ddddddd4', 1), term('1', 'b0eeeeeee5', 1)], self.ads, ASIN, '60d',
                         target_rows=targets)
        flags = {s['asin']: s['already_targeted'] for s in result['seeds']}
        self.assertEqual(flags, {'B0DDDDDDD4': ['PRODUCT_EXACT'], 'B0EEEEEEE5': []})

    def test_window_must_match_rows(self):
        with self.assertRaisesRegex(ValueError, 'orders_30d'):
            m.seeds([term('1', 'b0ddddddd4', 1)], self.ads, ASIN, '30d')

    def test_incomplete_pagination_is_rejected(self):
        root = SCRIPT.parents[3] / 'tmp' / ('product-targets-' + uuid.uuid4().hex)
        root.mkdir(parents=True)
        try:
            page = root / 'page.json'
            page.write_text(json.dumps({'data': {'data': [ad('1', ASIN)],
                                                 'pagination': {'page': 1, 'total': 2}}}))
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                m.load_rows([page])
            self.assertEqual(m.load_rows([page], allow_partial=True)[1], False)
            page.write_text(json.dumps({'data': [ad('1', ASIN)], 'pagination': {'page': 1, 'total': 1}}))
            rows, complete = m.load_rows([page])
            self.assertEqual((len(rows), complete), (1, True))
        finally:
            shutil.rmtree(root)


class TargetBodyTest(unittest.TestCase):
    def test_exact_and_expanded_items_are_strict_and_paused(self):
        for match in ('PRODUCT_EXACT', 'PRODUCT_SIMILAR'):
            out = m.target_items('355344875938094', match, ['b0ddddddd4', 'B0EEEEEEE5'])
            items = out['body']['targets']
            self.assertEqual(set(out['body']), {'targets'})
            for item in items:
                self.assertEqual(set(item), PRODUCT_KEYS)
                self.assertEqual(item['state'], 'PAUSED')
                self.assertIs(item['negative'], False)
                self.assertNotIn('bid', json.dumps(item))
                self.assertEqual(set(item['targetDetails']['productTarget']),
                                 {'matchType', 'productId', 'productIdType'})
            self.assertEqual(items[0]['targetDetails']['productTarget']['productId'], 'B0DDDDDDD4')
            self.assertEqual([i['index'] for i in out['index']], [0, 1])

    def test_category_item_uses_live_nesting(self):
        item = m.target_items('355344875938094', asins=(), category_ids=['7141123011'])['body']['targets'][0]
        self.assertEqual(item['targetType'], 'PRODUCT_CATEGORY')
        self.assertEqual(item['targetDetails'], {'productCategoryTarget': {'matchType': 'MULTISIGNAL_BROAD',
            'productCategoryRefinement': {'productCategoryRefinement': {'productCategoryId': '7141123011'}}}})

    def test_rejections(self):
        bad = [dict(ad_group_id=355344875938094, match_type='PRODUCT_EXACT', asins=[ASIN]),
               dict(ad_group_id='1', match_type='PRODUCT_COMPLEMENTS', asins=[ASIN]),
               dict(ad_group_id='1', match_type='PRODUCT_EXACT', asins=[ASIN, ASIN.lower()]),
               dict(ad_group_id='1', match_type='PRODUCT_EXACT', asins=['NOTANASIN']),
               dict(ad_group_id='1', match_type='PRODUCT_EXACT', asins=[ASIN], category_ids=['1']),
               dict(ad_group_id='1', match_type='PRODUCT_EXACT'),
               dict(ad_group_id='1', match_type='PRODUCT_EXACT', asins=['B0%08d' % i for i in range(1001)])]
        for case in bad:
            with self.assertRaises(ValueError):
                m.target_items(case['ad_group_id'], case['match_type'], case.get('asins', ()),
                               case.get('category_ids', ()))

    def test_bid_patches(self):
        out = m.bid_patches([dict(target_id='123', bid='0.45')], 'lab-1023')
        self.assertEqual(out, [dict(target_id='123', idempotency_key='lab-1023-bid-123',
                                    body={'bid': {'bid': 0.45}})])
        for bad in ([dict(target_id='123', bid='0.455')], [dict(target_id='0', bid='1')],
                    [dict(target_id='1', bid='1'), dict(target_id='1', bid='2')], [dict(target_id='1', bid='-1')]):
            with self.assertRaises(ValueError):
                m.bid_patches(bad, 'lab')

    def test_cli_reports_errors_without_traceback(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'targets', '--ad-group-id', '1',
                                 '--match-type', 'PRODUCT_EXACT', '--asins', 'bad'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Invalid ASIN', json.loads(result.stdout)['error'])


if __name__ == '__main__':
    unittest.main()
