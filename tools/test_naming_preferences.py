"""Offline acceptance for the naming preference candidate; never connects to an account."""
import copy
import importlib.util
from pathlib import Path
import shutil
import uuid
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('naming', ROOT / 'skills/merchjar-connect/scripts/campaign_naming.py')
naming = importlib.util.module_from_spec(spec)
spec.loader.exec_module(naming)


def definition(scope='profile:123'):
    return dict(scope=scope, name='ASIN first', single_asin='{asin} | {targeting}',
                multi_asin='MULTI | {group} | {targeting}', vocabulary={'Exact': 'EX'},
                rules=dict(product_labels='Use trusted catalog titles only when requested.',
                           missing_product='Hold for review.', mixed_targeting='Use Mixed.',
                           collisions='Preserve meaningful differences and stable suffixes.',
                           dates='Include only meaningful confirmed dates.'),
                provenance=dict(confirmed_at='2026-09-10T12:00:00Z', instruction='Use for this account.'))


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parent
        folder = parent / ('naming-check-' + uuid.uuid4().hex)
        folder.mkdir()
        assert folder.resolve().parent == parent.resolve()
        self.addCleanup(shutil.rmtree, folder)
        self.store = folder / 'campaign-naming.json'

    def put(self, item):
        return naming.save(self.store, naming.read_store(self.store)[1], item)

    def test_profile_over_global_and_preserve_other_accounts(self):
        self.put(definition('global'))
        self.put(definition('profile:456'))
        item = definition()
        item['single_asin'] = '{targeting} | {asin}'
        self.put(item)
        data, _ = naming.read_store(self.store)
        self.assertEqual(len(data['conventions']), 3)
        self.assertEqual(naming.resolve(data, '123')['single_asin'], '{targeting} | {asin}')
        self.assertEqual(naming.resolve(data, '999')['scope'], 'global')
        self.assertEqual(naming.resolve(data, '456')['scope'], 'profile:456')

    def test_stale_save_preserves_newer_user_edit(self):
        revision = naming.read_store(self.store)[1]
        self.put(definition())
        saved = self.store.read_bytes()
        with self.assertRaises(ValueError):
            naming.save(self.store, revision, definition('global'))
        self.assertEqual(saved, self.store.read_bytes())

    def test_invalid_store_is_not_reset(self):
        self.store.write_text('{"schema_version":99}', encoding='utf-8')
        before = self.store.read_bytes()
        with self.assertRaises(ValueError):
            naming.read_store(self.store)
        self.assertEqual(before, self.store.read_bytes())

    def test_lock_blocks_without_removing_foreign_lock(self):
        lock = self.store.with_name(self.store.name + '.lock')
        lock.write_text('another writer', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            self.put(definition())
        self.assertTrue(lock.exists())

    def test_reopen_and_creation_render_use_same_convention(self):
        self.put(definition())
        data, _ = naming.read_store(self.store)
        selected = naming.resolve(data, '123')
        name = naming.render(selected, {'asins': ['B0828NCLVB'], 'targeting': 'Exact'})
        self.assertEqual(name, 'B0828NCLVB | Exact')
        before = self.store.read_bytes()
        override = copy.deepcopy(selected)
        override['single_asin'] = '{targeting} | {asin}'
        self.assertEqual(naming.render(override, {'asins': ['B0828NCLVB'], 'targeting': 'Exact'}),
                         'Exact | B0828NCLVB')
        self.assertEqual(before, self.store.read_bytes())

    def test_multi_asin_never_uses_first_asin(self):
        facts = {'asins': ['B0828NCLVB', 'B0828PCHC2'], 'asin': 'B0828NCLVB',
                 'targeting': 'Mixed', 'group': 'Souvenirs'}
        self.assertEqual(naming.render(definition(), facts), 'MULTI | Souvenirs | Mixed')
        invalid = definition()
        invalid['multi_asin'] = '{asin} | {targeting}'
        with self.assertRaises(ValueError):
            naming.validate({'schema_version': 1, 'conventions': [invalid]})

    def test_unknown_facts_and_missing_products_require_review(self):
        for facts in ({'asins': []}, {'asins': ['B0828NCLVB']}, {'asins': ['invalid']}):
            with self.assertRaises(ValueError):
                naming.render(definition(), facts)

    def test_length_and_format_expression_rejected(self):
        with self.assertRaises(ValueError):
            naming.render(definition(), {'asins': ['B0828NCLVB'], 'targeting': 'x' * 256})
        for template in ('{asin.__class__}', '{asin!r}', '{asin:>1000}'):
            with self.assertRaises(ValueError):
                naming.fields(template)


if __name__ == '__main__':
    unittest.main()
