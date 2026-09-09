import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
import shutil
import uuid

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/create-campaigns/scripts/campaign_structures.py'
spec = importlib.util.spec_from_file_location('structures', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@contextmanager
def scratch():
    root = SCRIPT.parents[3] / 'tmp'
    root.mkdir(exist_ok=True)
    path = root / ('structure-test-' + uuid.uuid4().hex)
    path.mkdir()
    try:
        yield path
    finally:
        assert path.resolve().parent == root.resolve()
        shutil.rmtree(path)


def definition(identity='launch', scope='global', default=True):
    return dict(id=identity, name=identity, scope=scope, purposes=['launch'], default=default,
                grouping='per-product', roles=[dict(id='auto', mode='auto-combined', job='Discovery')],
                naming='{asin} - {role}', budget_policy=dict(basis='fresh-batch-total', weights={'auto': 1}),
                bid_defaults={}, keyword_policy='defer-manual',
                provenance=dict(confirmed_at='2026-09-08T12:00:00Z', instruction='Save my launch setup'))


class StructuresTest(unittest.TestCase):
    def test_placeholder_policy_survives_fresh_session(self):
        with scratch() as folder:
            path = Path(folder) / 'campaign-structures.json'
            config = definition()
            config['keyword_policy'] = 'paused-placeholders'
            _, revision = m.read_store(path)
            m.mutate(path, revision, config)
            result = subprocess.run([sys.executable, str(SCRIPT), 'select', '--store', str(path),
                                     '--profile', '123', '--purpose', 'launch'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            selected = json.loads(result.stdout)['selected']
            self.assertEqual(selected['keyword_policy'], 'paused-placeholders')
            self.assertNotIn('replace me', path.read_text())

    def test_intake(self):
        result = m.intake('\ufeffASIN\n"b000000001"\nB000000001\nbad\n0123456789\n')
        self.assertEqual(result, dict(asins=['B000000001', '0123456789'],
                                     duplicates=['B000000001'], invalid=['BAD']))
        self.assertEqual(m.intake('B000000001, B000000002\nB000000003')['asins'],
                         ['B000000001', 'B000000002', 'B000000003'])

    def test_lifecycle_fresh_process_and_config_preservation(self):
        with scratch() as folder:
            path = Path(folder) / 'campaign-structures.json'
            config = Path(folder) / 'MJ_COPILOT_CONFIG.md'
            config.write_text('Synthetic configuration, no credential\nOther preference: keep\n')
            before = config.read_bytes()
            _, revision = m.read_store(path)
            data, revision = m.mutate(path, revision, definition())
            result = subprocess.run([sys.executable, str(SCRIPT), 'select', '--store', str(path),
                                     '--profile', '123', '--purpose', 'launch'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['selected']['id'], 'launch')
            edited = definition()
            edited['name'] = 'New name'
            data, revision = m.mutate(path, revision, edited)
            self.assertEqual(data['structures'][0]['name'], 'New name')
            data, _ = m.mutate(path, revision, remove='launch')
            self.assertEqual(data['structures'], [])
            self.assertEqual(config.read_bytes(), before)

    def test_precedence_choices_and_no_mutation(self):
        data = m.validate(dict(schema_version=1, structures=[definition(), definition('local', 'profile:123')]))
        before = copy.deepcopy(data)
        self.assertEqual(m.select(data, '123', 'launch')['selected']['id'], 'local')
        self.assertEqual(m.select(data, '456', 'launch')['selected']['id'], 'launch')
        self.assertEqual(m.select(data, '123', 'launch', 'launch')['selected']['id'], 'launch')
        self.assertEqual(data, before)
        for s in data['structures']:
            s['default'] = False
        self.assertEqual(len(m.select(data, '123', 'launch')['choices']), 2)
        self.assertIsNone(m.select(data, '123', 'discovery')['selected'])

    def test_bad_storage_and_stale_write_preserved(self):
        with scratch() as folder:
            path = Path(folder) / 'store.json'
            for content in ('', '{bad', '{"schema_version":2,"structures":[]}'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    m.mutate(path, 'old', definition())
                self.assertEqual(path.read_text(), content)
            path.unlink()
            _, revision = m.read_store(path)
            _, new_revision = m.mutate(path, revision, definition())
            with self.assertRaises(ValueError):
                m.mutate(path, revision, definition('second'))
            self.assertEqual(m.read_store(path)[1], new_revision)

    def test_schema_rejects_batch_amount_and_competing_defaults(self):
        s = definition()
        s['budget_policy']['amount'] = 90
        with self.assertRaises(ValueError):
            m.validate(dict(schema_version=1, structures=[s]))
        with self.assertRaises(ValueError):
            m.validate(dict(schema_version=1, structures=[definition(), definition('other')]))
        s = definition()
        s['bid_defaults'] = {'EUR': {'auto': 'NaN'}}
        with self.assertRaises(ValueError):
            m.validate(dict(schema_version=1, structures=[s]))


if __name__ == '__main__':
    unittest.main()
