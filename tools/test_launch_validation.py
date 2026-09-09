import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'skills/create-campaigns/scripts/validate_launch.py'
spec=importlib.util.spec_from_file_location('launch',path)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def plan(budget='5', total='150'):
    return dict(marketplace='DE',currency='EUR',ad_product='SPONSORED_PRODUCTS',
                budget_basis='per-campaign',approved_configured_total=total,
                campaigns=[dict(daily_budget=budget,default_bid='0.17',target_bids=['0.50']) for _ in range(30)])

class LaunchValidationTest(unittest.TestCase):
    def test_thirty_campaigns_five_each(self):
        self.assertEqual(m.validate(plan())['configured_total'],'150')
    def test_total_five_cannot_be_spread_across_thirty(self):
        with self.assertRaisesRegex(ValueError,'below'): m.validate(plan('0.17','5.10'))
    def test_no_silent_total_increase(self):
        with self.assertRaisesRegex(ValueError,'approved'): m.validate(plan('1','5'))
    def test_ambiguous_scope_requires_resolution(self):
        p=plan(); p['budget_basis']='daily'
        with self.assertRaisesRegex(ValueError,'scope'): m.validate(p)
    def test_bid_bounds_and_precision(self):
        for bad in ['0.01','1000.01','NaN','0.175']:
            p=plan(); p['campaigns'][0]['default_bid']=bad
            with self.assertRaises(ValueError): m.validate(p)
    def test_do_not_apply_eur_limits_to_other_marketplaces(self):
        p=plan(); p['marketplace']='JP'; p['currency']='JPY'
        with self.assertRaisesRegex(ValueError,'limits'): m.validate(p)

if __name__=='__main__': unittest.main()
