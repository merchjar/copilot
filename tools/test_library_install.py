"""Offline checks for the installer bundled in every default Copilot pack."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills/manage-library/scripts/install_skill.py'
spec = importlib.util.spec_from_file_location('installer', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def package():
    content = {
        'skills/example/SKILL.md': b'Example skill',
        'skills/merchjar-connect/SKILL.md': b'Connection skill',
        'tools/merchjar_client.py': b'# existing client',
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name, data in content.items():
            archive.writestr(name, data)
    data = output.getvalue()
    manifest = {'schema': 1, 'kind': 'skill', 'id': 'example',
                'archiveSha256': hashlib.sha256(data).hexdigest(),
                'files': [{'path': n, 'archivePath': n, 'sha256': hashlib.sha256(v).hexdigest()}
                          for n, v in content.items()]}
    return manifest, data


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'Copilot with spaces'
        (self.root / 'tools').mkdir(parents=True)
        (self.root / 'AGENTS.md').write_text('Existing operating instructions')
        (self.root / 'tools/merchjar_client.py').write_bytes(b'# existing client')
        (self.root / 'user').mkdir()
        (self.root / 'user/preferences.json').write_text('{"mySetting": true}')
        self.manifest, self.archive = package()
        self.files = installer.payloads(self.manifest, self.archive)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_dry_run_apply_and_repeat_preserve_user_files(self):
        original = self.snapshot()
        self.assertTrue(installer.install(self.root, self.files)['add'])
        self.assertEqual(original, self.snapshot())
        self.assertTrue(installer.install(self.root, self.files, True)['applied'])
        for name, data in original.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        for runtime in installer.RUNTIMES:
            self.assertEqual((self.root / runtime / 'skills/example/SKILL.md').read_bytes(), b'Example skill')
        self.assertEqual(installer.install(self.root, self.files, True)['add'], [])

    def test_conflict_blocks_every_write(self):
        (self.root / 'tools/merchjar_client.py').write_text('Local customization')
        before = self.snapshot()
        self.assertTrue(installer.install(self.root, self.files, True)['conflicts'])
        self.assertEqual(before, self.snapshot())

    def test_line_endings_are_preserved_but_content_edits_block(self):
        target = self.root / 'tools/merchjar_client.py'
        target.write_bytes(b'# client\r\n# next line\r\n')
        self.files['tools/merchjar_client.py'] = b'# client\n# next line\n'
        self.assertTrue(installer.install(self.root, self.files, True)['applied'])
        self.assertEqual(target.read_bytes(), b'# client\r\n# next line\r\n')
        target.write_bytes(b'# customized client\r\n# next line\r\n')
        self.assertTrue(installer.install(self.root, self.files, True)['conflicts'])

    def test_bad_checksum_and_missing_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError, 'checksum'):
            installer.payloads(self.manifest, self.archive + b'changed')
        self.manifest['files'] = self.manifest['files'][:-1]
        with self.assertRaisesRegex(ValueError, 'dependency'):
            installer.payloads(self.manifest, self.archive)

    def test_protected_and_traversal_paths_rejected(self):
        for name in ('../outside', 'user/config.md', 'AGENTS.md', '.agents/skills/other/SKILL.md'):
            manifest = json.loads(json.dumps(self.manifest))
            manifest['files'][0]['path'] = name
            with self.assertRaises(ValueError):
                installer.payloads(manifest, self.archive)

    def test_failed_write_removes_only_new_files(self):
        original = self.snapshot()
        real_open = Path.open
        count = 0
        def fail_on_second(path, mode='r', *args, **kwargs):
            nonlocal count
            if mode == 'xb':
                count += 1
                if count == 2:
                    raise OSError('Simulated disk failure')
            return real_open(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', fail_on_second):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                installer.install(self.root, self.files, True)
        self.assertEqual(original, self.snapshot())

    def test_default_pack_contains_same_executable_installer(self):
        for prefix in ('skills', '.agents/skills', '.claude/skills'):
            target = ROOT / 'copilot-pack' / prefix / 'manage-library/scripts/install_skill.py'
            self.assertEqual(target.read_bytes(), SOURCE.read_bytes())
            compile(target.read_bytes(), str(target), 'exec')


if __name__ == '__main__':
    unittest.main()
