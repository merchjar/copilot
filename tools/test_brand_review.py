"""Focused release regressions for the optional upload-based skill."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/branded-review/scripts'))
from report_context import product_context


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


if __name__ == '__main__':
    unittest.main()
