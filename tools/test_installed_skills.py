"""Checks for local discovery, deduplication and changed content, with no API calls."""
import importlib.util
from pathlib import Path
import shutil
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inventory', ROOT / 'skills/manage-library/scripts/installed_skills.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.folder = ROOT / 'tmp' / ('inventory-' + uuid.uuid4().hex)
        self.folder.mkdir(parents=True)
        assert self.folder.resolve().parent == (ROOT / 'tmp').resolve()
        self.addCleanup(shutil.rmtree, self.folder)
        (self.folder / 'skills/example').mkdir(parents=True)
        (self.folder / 'skills/example/SKILL.md').write_text(
            '---\nname: example\ndescription: Example\nmetadata:\n  version: "1.0"\n  requires-skills: "connect"\n---\nBody\n', encoding='utf-8')

    def test_mirrors_not_counted_and_missing_dependency_reported(self):
        shutil.copytree(self.folder / 'skills', self.folder / '.agents/skills')
        result = inventory.inspect(self.folder)
        self.assertEqual(len(result['skills']), 1)
        self.assertEqual(result['skills'][0]['missing_dependencies'], ['connect'])
        self.assertEqual(result['skills'][0]['version'], '1.0')
        self.assertEqual(result['skills'][0]['update_status'], 'not_checked')

    def test_actual_files_override_any_stale_index(self):
        (self.folder / 'installed-skills.json').write_text('{"skills": []}', encoding='utf-8')
        (self.folder / 'skills/connect').mkdir()
        (self.folder / 'skills/connect/SKILL.md').write_text('Custom skill without metadata', encoding='utf-8')
        entries = {x['id']: x for x in inventory.inspect(self.folder)['skills']}
        self.assertEqual(entries['example']['missing_dependencies'], [])
        self.assertIsNone(entries['connect']['version'])

    def test_references_are_fingerprinted_and_config_not_read(self):
        ref = self.folder / 'skills/example/context.md'
        ref.write_text('one', encoding='utf-8')
        before = inventory.inspect(self.folder)
        (self.folder / 'user').mkdir()
        (self.folder / 'user/config.md').write_text('PRIVATE_FIXTURE_SENTINEL', encoding='utf-8')
        ref.write_text('two', encoding='utf-8')
        after = inventory.inspect(self.folder)
        self.assertNotEqual(before['skills'][0]['files_sha256'], after['skills'][0]['files_sha256'])
        self.assertNotIn('PRIVATE_FIXTURE_SENTINEL', str(after))


if __name__ == '__main__':
    unittest.main()
