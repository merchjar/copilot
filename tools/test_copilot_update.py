"""Offline transactional update checks using real Copilot release trees."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills/manage-library/scripts/update_copilot.py'
spec = importlib.util.spec_from_file_location('updater', SOURCE)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def export_pack(ref, destination):
    names = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', ref, 'copilot-pack'], cwd=ROOT,
        text=True, encoding='utf-8').splitlines()
    for full in names:
        relative = full.removeprefix('copilot-pack/')
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(subprocess.check_output(['git', 'show', f'{ref}:{full}'], cwd=ROOT))


class UpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = json.loads((ROOT / 'manifest.json').read_text())['pack_version']
        cls.manifest_path = ROOT / f'release/copilot-update-v{cls.version}.json'
        cls.archive_path = ROOT / f'release/copilot-update-v{cls.version}.zip'
        cls.manifest, cls.payloads = updater.load_release_files(cls.manifest_path, cls.archive_path)
        cls.fixtures = ROOT / 'tmp' / ('update-fixtures-' + uuid.uuid4().hex)
        cls.fixtures.mkdir(parents=True)
        export_pack('v1.2.2', cls.fixtures / 'v1.2.2')
        export_pack('13d4457fbe62f72deed01a612e793cccc4b743d3', cls.fixtures / 'v1.2.4')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.fixtures)

    def setUp(self):
        self.folder = ROOT / 'tmp' / ('update-' + uuid.uuid4().hex)
        self.folder.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.folder)

    def old(self, ref='v1.2.2'):
        name = 'v1.2.4' if ref.startswith('13d4457') else 'v1.2.2'
        shutil.copytree(self.fixtures / name, self.folder, dirs_exist_ok=True)
        return self.folder

    def current(self):
        shutil.copytree(ROOT / 'copilot-pack', self.folder, dirs_exist_ok=True)
        return self.folder

    def snapshot(self):
        return {p.relative_to(self.folder).as_posix(): p.read_bytes()
                for p in self.folder.rglob('*') if p.is_file()}

    def test_actual_v122_to_current_preserves_user_and_does_not_add_optional_skill(self):
        self.old()
        config = (self.folder / 'user/MJ_COPILOT_CONFIG.md').read_bytes()
        result = updater.apply_update(self.folder, self.manifest, self.payloads)
        self.assertTrue(result['applied'])
        self.assertEqual((self.folder / 'user/MJ_COPILOT_CONFIG.md').read_bytes(), config)
        self.assertTrue((self.folder / 'skills/manage-library/SKILL.md').is_file())
        self.assertFalse((self.folder / 'skills/campaign-naming-cleanup').exists())
        self.assertTrue((self.folder / '.gemini/skills/manage-library/SKILL.md').is_file())
        self.assertTrue((self.folder / '.github/skills/manage-library/SKILL.md').is_file())

    def test_current_release_is_noop(self):
        self.current()
        _, report, _, _ = updater.plan_update(self.folder, self.manifest, self.payloads)
        self.assertFalse(report['add'])
        self.assertFalse(report['replace'])
        self.assertFalse(report['conflicts'])

    def test_individual_skill_includes_dependency_only(self):
        self.old()
        old_agents = (self.folder / 'AGENTS.md').read_bytes()
        result = updater.apply_update(
            self.folder, self.manifest, self.payloads, ['create-campaigns'])
        self.assertTrue(result['applied'])
        self.assertEqual(result['scope'], ['create-campaigns', 'merchjar-connect'])
        self.assertEqual((self.folder / 'AGENTS.md').read_bytes(), old_agents)
        self.assertIn('version: "1.3"', (self.folder / 'skills/create-campaigns/SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('version: "1.5"', (self.folder / 'skills/merchjar-connect/SKILL.md').read_text(encoding='utf-8'))

    def test_optional_naming_installs_into_fresh_default_copilot_with_dependency(self):
        self.old()
        self.assertFalse((self.folder / 'skills/campaign-naming-cleanup').exists())
        result = updater.apply_update(
            self.folder, self.manifest, self.payloads, ['campaign-naming-cleanup'])
        self.assertTrue(result['applied'])
        self.assertEqual(result['scope'], ['campaign-naming-cleanup', 'merchjar-connect'])
        self.assertIn('version: "0.4.0"',
                      (self.folder / 'skills/campaign-naming-cleanup/SKILL.md').read_text(encoding='utf-8'))
        self.assertTrue((self.folder / '.agents/skills/campaign-naming-cleanup/SKILL.md').is_file())
        self.assertTrue((self.folder / '.claude/skills/campaign-naming-cleanup/SKILL.md').is_file())

    def test_installed_optional_skill_updates_but_absent_optional_does_not_install(self):
        self.old('13d4457fbe62f72deed01a612e793cccc4b743d3')
        private = self.folder / 'user/campaign-naming.json'
        private.write_text('{"schema_version":1,"conventions":[{"known":"prior-model-error"}]}\n')
        private_bytes = private.read_bytes()
        self.assertIn('version: "0.3.0"',
                      (self.folder / 'skills/campaign-naming-cleanup/SKILL.md').read_text(encoding='utf-8'))
        result = updater.apply_update(self.folder, self.manifest, self.payloads)
        self.assertTrue(result['applied'])
        self.assertIn('version: "0.4.0"',
                      (self.folder / 'skills/campaign-naming-cleanup/SKILL.md').read_text(encoding='utf-8'))
        self.assertEqual(private.read_bytes(), private_bytes)

    def test_brand_review_installs_without_connection_and_preserves_saved_work(self):
        self.current()
        before = self.snapshot()
        result = updater.apply_update(self.folder, self.manifest, self.payloads, ['branded-review'])
        self.assertTrue(result['applied'])
        self.assertEqual(result['scope'], ['branded-review'])
        for path, contents in before.items():
            if path.startswith('user/') or path.endswith('merchjar-connect/SKILL.md'):
                self.assertEqual((self.folder / path).read_bytes(), contents)
        for mirror in ['skills', '.agents/skills', '.claude/skills', '.github/skills', '.gemini/skills']:
            self.assertIn('version: "2.0.0"', (self.folder / mirror / 'branded-review/SKILL.md').read_text(encoding='utf-8'))
        saved = self.folder / 'skills/branded-review/workspace/brand-reference.json'
        saved.parent.mkdir()
        saved.write_text('{"brand":"Example","approved":true}')
        repeated = updater.apply_update(self.folder, self.manifest, self.payloads, ['branded-review'])
        self.assertFalse(repeated['conflicts'])
        self.assertEqual(saved.read_text(), '{"brand":"Example","approved":true}')
        _, report, _, _ = updater.plan_update(self.folder, self.manifest, self.payloads, ['branded-review'])
        self.assertFalse(report['add'])
        self.assertFalse(report['replace'])
        with zipfile.ZipFile(ROOT / f'merch-jar-copilot-pack-v{self.version}.zip') as archive:
            self.assertFalse(any('/skills/branded-review/' in p for p in archive.namelist()))

    def test_custom_skill_and_newer_official_skill_are_preserved(self):
        self.current()
        naming_source = ROOT / 'skills/campaign-naming-cleanup'
        shutil.copytree(naming_source, self.folder / 'skills/campaign-naming-cleanup')
        custom = self.folder / 'skills/my-own-skill/SKILL.md'
        custom.parent.mkdir()
        custom.write_text('---\nname: my-own-skill\ndescription: Mine\n---\nKeep me\n')
        naming = self.folder / 'skills/campaign-naming-cleanup/SKILL.md'
        naming.write_text(naming.read_text(encoding='utf-8').replace(
            'version: "0.4.0"', 'version: "9.0.0"'), encoding='utf-8')
        result = updater.apply_update(self.folder, self.manifest, self.payloads)
        self.assertTrue(result['applied'])
        self.assertEqual(result['newer_skills_preserved'], ['campaign-naming-cleanup'])
        self.assertIn('version: "9.0.0"', naming.read_text(encoding='utf-8'))
        self.assertIn('Keep me', custom.read_text(encoding='utf-8'))

    def test_local_edit_with_unchanged_vendor_file_is_preserved(self):
        self.old()
        path = self.folder / 'skills/audit-log/SKILL.md'
        path.write_text(path.read_text(encoding='utf-8') + '\nLocal note\n', encoding='utf-8')
        result = updater.apply_update(self.folder, self.manifest, self.payloads)
        self.assertTrue(result['applied'])
        self.assertIn('skills/audit-log/SKILL.md', result['customized_preserved'])
        self.assertTrue(path.read_text(encoding='utf-8').endswith('Local note\n'))

    def test_overlapping_edit_blocks_all_writes(self):
        self.old()
        path = self.folder / 'skills/create-campaigns/SKILL.md'
        path.write_text(path.read_text(encoding='utf-8') + '\nCustomer edit\n', encoding='utf-8')
        before = self.snapshot()
        result = updater.apply_update(self.folder, self.manifest, self.payloads)
        self.assertTrue(result['conflicts'])
        self.assertFalse(result['applied'])
        self.assertEqual(before, self.snapshot())

    def test_corrupt_archive_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'checksum'):
            updater.release_payloads(self.manifest, self.archive_path.read_bytes() + b'broken')

    def test_interrupted_update_restores_every_changed_file(self):
        self.old()
        before = self.snapshot()
        with self.assertRaisesRegex(OSError, 'interrupted'):
            updater.apply_update(self.folder, self.manifest, self.payloads, fail_after=0)
        after = self.snapshot()
        for path, data in before.items():
            self.assertEqual(after[path], data)
        self.assertFalse(any(path not in before and not path.startswith('.merchjar-backups/')
                             and not path.startswith('user/library-updates/') for path in after))

    def test_post_write_verification_failure_restores_files_and_receipt(self):
        self.old()
        before = self.snapshot()
        with patch.object(updater.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'inventory')):
            with self.assertRaises(subprocess.CalledProcessError):
                updater.apply_update(self.folder, self.manifest, self.payloads)
        after = self.snapshot()
        for path, data in before.items():
            self.assertEqual(after[path], data)
        self.assertFalse((self.folder / '.merchjar-installation.json').exists())
        self.assertFalse(list((self.folder / 'user/library-updates').glob('*.json')))

    def test_manager_bootstrap_then_replacement_manager_runs_check(self):
        self.old()
        result = updater.apply_update(
            self.folder, self.manifest, self.payloads, ['manage-library'])
        self.assertTrue(result['applied'])
        installed = self.folder / 'tools/update_copilot.py'
        self.assertEqual(installed.read_bytes(), SOURCE.read_bytes())
        command = [sys.executable, str(installed), 'check', '--manifest-file',
                   str(self.manifest_path), '--archive-file', str(self.archive_path),
                   '--destination', str(self.folder), '--skill', 'manage-library']
        check = subprocess.run(command, cwd=self.folder, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        report = json.loads(check.stdout)
        manager = next(x for x in report['skills'] if x['id'] == 'manage-library')
        self.assertEqual(manager['status'], 'current')

    def test_update_manifest_never_contains_private_state(self):
        paths = {x['path'] for x in self.manifest['files']}
        self.assertFalse(any(path.startswith('user/') for path in paths))
        self.assertNotIn('installed-skills.json', paths)
        self.assertFalse(any('campaign-naming' in path and not path.startswith(
            ('skills/', '.agents/', '.claude/', '.gemini/', '.github/')) for path in paths))

    def test_default_zip_excludes_optional_naming_but_update_archive_includes_it(self):
        full_zip = ROOT / f'merch-jar-copilot-pack-v{self.version}.zip'
        with zipfile.ZipFile(full_zip) as archive:
            names = set(archive.namelist())
        self.assertFalse(any('/skills/campaign-naming-cleanup/' in name for name in names))
        update_paths = {item['path'] for item in self.manifest['files']}
        self.assertIn('skills/campaign-naming-cleanup/SKILL.md', update_paths)
        self.assertNotIn('campaign-naming-cleanup', self.manifest['defaultSkills'])


if __name__ == '__main__':
    unittest.main()
