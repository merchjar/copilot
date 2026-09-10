#!/usr/bin/env python3
"""Build the checked Copilot update archive, manifest, and old-install bootstrap."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'copilot-pack'
OUT = ROOT / 'release'
DEFAULT_SKILLS = [
    'account-review', 'audit-log', 'build-segment', 'check-segments',
    'create-campaigns', 'enrich-account', 'explain-segment', 'manage-library',
    'merchjar-connect', 'performance-check', 'review-segment', 'troubleshoot',
]
RELEASE_NOTES = {
    'account-review': 'Can recommend Campaign Naming when inconsistent names block account work.',
    'campaign-naming-cleanup': 'Responds faster, proposes a reusable taxonomy first, and preserves method separately from match type.',
    'create-campaigns': 'Reuses the saved account naming taxonomy, including the distinct Auto, KW, PT, or Mixed method.',
    'manage-library': 'Adds all-skill update checks, version-aware replacement, backups, recovery, and manager self-update.',
    'merchjar-connect': 'Adds the shared naming method field, saved vocabularies, and safer Windows API command guidance.',
}
TEXT_SUFFIXES = {'.md', '.py', '.json', '.txt', '.sh', '.toml', '.yaml', '.yml'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalized_digest(data, name):
    if Path(name).suffix.lower() in TEXT_SUFFIXES and b'\0' not in data:
        data = data.replace(b'\r\n', b'\n')
    return digest(data)


def included(relative):
    parts = Path(relative).parts
    return (parts and parts[0] != 'user' and 'campaign-naming-records' not in parts
            and '__pycache__' not in parts and Path(relative).name not in {
                'installed-skills.json', '.library-cache.json', 'campaign-naming.json',
                'campaign-naming.json.lock', 'campaign-structures.json',
                'campaign-structures.json.lock'}
            and not Path(relative).name.startswith(('.naming-', '.structures-'))
            and Path(relative).suffix != '.pyc')


def owner(relative):
    parts = Path(relative).parts
    if len(parts) >= 3 and parts[0] == 'skills':
        return 'skill:' + parts[1]
    if len(parts) >= 4 and parts[0] in ('.agents', '.claude', '.gemini', '.github') and parts[1] == 'skills':
        return 'skill:' + parts[2]
    if relative == 'tools/update_copilot.py':
        return 'skill:manage-library'
    if relative == 'tools/merchjar_client.py' or parts[0] == 'reference':
        return 'skill:merchjar-connect'
    return 'copilot'


def git_files(tag):
    names = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', tag, 'copilot-pack'], cwd=ROOT,
        text=True, encoding='utf-8').splitlines()
    result = {}
    for full in names:
        relative = full.removeprefix('copilot-pack/')
        if not included(relative):
            continue
        data = subprocess.check_output(['git', 'show', f'{tag}:{full}'], cwd=ROOT)
        result[relative] = normalized_digest(data, relative)
    return result


def parse_skills():
    result = {}
    for path in sorted((ROOT / 'skills').glob('*/SKILL.md')):
        text = path.read_text(encoding='utf-8-sig')
        version = re.search(r'^\s*version:\s*["\']?([^\s"\']+)', text, re.M)
        requires = re.search(r'^\s*requires-skills:\s*["\']?(.*?)["\']?\s*$', text, re.M)
        raw_requires = (requires.group(1) if requires else '').strip().strip('"\'')
        dependencies = [x.strip() for x in raw_requires.split(',') if x.strip()]
        if not version:
            raise ValueError('Skill lacks a version: ' + path.parent.name)
        result[path.parent.name] = {'version': version.group(1), 'requires': dependencies,
                                    'releaseNotes': RELEASE_NOTES.get(path.parent.name, '')}
    missing = [x for x in DEFAULT_SKILLS if x not in result]
    if missing:
        raise ValueError('Default skill missing: ' + ', '.join(missing))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--baseline', action='append', default=[
        '1.2.2=v1.2.2',
        '1.2.3=64466b0',
        '1.2.4=13d4457fbe62f72deed01a612e793cccc4b743d3',
    ], help='Known release baseline as VERSION=GIT_REF')
    parser.add_argument('--base-url', default='https://merchjar.com/library-install/copilot')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
        raise SystemExit('Version must be semver')
    OUT.mkdir(exist_ok=True)
    archive_name = f'copilot-update-v{args.version}.zip'
    archive_path = OUT / archive_name
    files = []
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACK.rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(PACK).as_posix()
            if not included(relative):
                continue
            data = path.read_bytes()
            archive.writestr(relative, data)
            files.append({'path': relative, 'archivePath': relative,
                          'sha256': digest(data), 'owner': owner(relative)})
    baselines = {}
    for value in dict.fromkeys(args.baseline):
        version, separator, ref = value.partition('=')
        if not separator or not re.fullmatch(r'\d+\.\d+\.\d+', version) or not ref:
            raise ValueError('Baseline must be VERSION=GIT_REF')
        baselines[version] = git_files(ref)
    manifest = {
        'schema': 1, 'kind': 'copilot-update',
        'source': args.base_url.rstrip('/') + f'/copilot-update-v{args.version}.json',
        'packVersion': args.version, 'released': date.today().isoformat(),
        'archive': archive_name, 'archiveSha256': digest(archive_path.read_bytes()),
        'defaultSkills': DEFAULT_SKILLS, 'skills': parse_skills(),
        'files': files, 'baselines': baselines,
    }
    manifest_path = OUT / f'copilot-update-v{args.version}.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    updater = PACK / 'tools/update_copilot.py'
    bootstrap = OUT / 'copilot-update-bootstrap.py'
    bootstrap.write_bytes(updater.read_bytes())
    bootstrap_meta = {
        'schema': 1, 'kind': 'copilot-update-bootstrap',
        'path': bootstrap.name, 'sha256': digest(bootstrap.read_bytes()),
        'manifest': f'copilot-update-v{args.version}.json',
    }
    (OUT / 'copilot-update-bootstrap.json').write_text(
        json.dumps(bootstrap_meta, indent=2) + '\n', encoding='utf-8')
    guide = f'''# Update the Copilot

Use this guide when the user asks to update an existing Merch Jar Copilot. This changes local Copilot files only. It does not connect to or change an ad account.

## Request to copy

> Update my Copilot from the Merch Jar Library. Keep my settings and custom skills, and tell me if anything needs my attention.

## Instructions for the Copilot

Locate the current Copilot folder containing `AGENTS.md` or `CLAUDE.md`. Do not read or print files under `user/`.

Resolve the filenames in this guide against the guide's HTTPS origin. This keeps an explicitly supplied preview on that preview origin.

Use `tools/update_copilot.py` when it exists. For an older Copilot without that file, download `copilot-update-bootstrap.py` from this guide's origin to a temporary file and verify its SHA256 is `{bootstrap_meta['sha256']}` before running it. The bootstrap is the same updater included in version {args.version}.

Run a read-only check and then a dry run against `copilot-update-v{args.version}.json` from this guide's origin. For this copied update request, continue with `--apply` when there are no conflicts. The request already authorizes the local update, backup and verification. Do not ask again merely because a required official dependency must be updated too.

For the normal whole-Copilot update, omit `--skill`. This updates the default Copilot and any already-installed official optional skills. It does not add absent optional skills. For one requested skill, use `--skill ID`; compatible dependencies are included.

After applying, refresh `installed-skills.json`, run `check` again using the installed `tools/update_copilot.py`, and report the installed and available versions, preserved customizations, conflicts, backup location and update receipt. Never describe checksum verification as a digital signature.
'''
    guide_path = OUT / f'copilot-update-v{args.version}.md'
    guide_path.write_text(guide, encoding='utf-8')
    (OUT / 'update.md').write_text(guide, encoding='utf-8')
    full_pack = ROOT / f'merch-jar-copilot-pack-v{args.version}.zip'
    if not full_pack.is_file():
        raise FileNotFoundError('Build the versioned full Copilot ZIP before update artifacts')
    shutil.copyfile(full_pack, OUT / 'merch-jar-copilot.zip')
    print(json.dumps({'manifest': str(manifest_path), 'archive': str(archive_path),
                      'bootstrap': str(bootstrap), 'guide': str(guide_path),
                      'stableGuide': str(OUT / 'update.md'),
                      'stableCopilotZip': str(OUT / 'merch-jar-copilot.zip'),
                      'files': len(files),
                      'defaultSkills': DEFAULT_SKILLS}, indent=2))


if __name__ == '__main__':
    main()
