"""Check and apply checksum-verified Merch Jar Copilot updates.

The update manifest supplies current files plus known official release baselines.
Dry-run is the default. This script never reads account configuration or calls the
Merch Jar API.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
import zipfile

MAX_BYTES = 30 * 1024 * 1024
TEXT_SUFFIXES = {'.md', '.py', '.json', '.txt', '.sh', '.toml', '.yaml', '.yml'}
RUNTIMES = ('.agents', '.claude', '.gemini', '.github')
PROTECTED_PARTS = {'user', 'campaign-naming-records', '__pycache__'}
PROTECTED_NAMES = {
    'campaign-naming.json', 'campaign-naming.json.lock',
    'campaign-structures.json', 'campaign-structures.json.lock',
    'installed-skills.json', '.merchjar-installation.json',
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_digest(data: bytes, relative: str) -> str:
    if Path(relative).suffix.lower() in TEXT_SUFFIXES and b'\0' not in data:
        data = data.replace(b'\r\n', b'\n')
    return digest(data)


def safe_relative(value: str) -> Path:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Invalid package path')
    parts = value.split('/')
    if any(part in ('', '.', '..') for part in parts) or PurePosixPath(value).is_absolute():
        raise ValueError('Invalid package path')
    if parts[0] in PROTECTED_PARTS or any(part in PROTECTED_PARTS for part in parts):
        raise ValueError('Update manifest contains protected user state: ' + value)
    if parts[-1] in PROTECTED_NAMES or parts[-1].startswith(('.naming-', '.structures-')):
        raise ValueError('Update manifest contains protected user state: ' + value)
    return Path(*parts)


def target_path(root: Path, relative: str) -> Path:
    path = root / safe_relative(relative)
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError('Linked update paths are not supported')
    resolved = path.resolve()
    if root not in resolved.parents:
        raise ValueError('Update path leaves the selected Copilot')
    return path


def fetch(url: str, origin: str) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != origin or parsed.username or parsed.password:
        raise ValueError('Update URLs must use the same HTTPS origin as the manifest')
    request = urllib.request.Request(url, headers={
        'User-Agent': 'MerchJar-Copilot-Updater/1.0', 'Accept': '*/*'})
    with urllib.request.urlopen(request, timeout=30) as response:
        final = urllib.parse.urlsplit(response.url)
        if final.scheme != 'https' or final.netloc != origin:
            raise ValueError('Cross-origin update redirect rejected')
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Update exceeds size limit')
    return data


def parse_version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', value):
        return None
    return tuple(int(x) for x in value.split('.'))


def installed_skill_versions(root: Path) -> dict[str, str | None]:
    result = {}
    folder = root / 'skills'
    if not folder.is_dir():
        return result
    for child in folder.iterdir():
        entry = child / 'SKILL.md'
        if child.is_dir() and not child.is_symlink() and entry.is_file() and not entry.is_symlink():
            text = entry.read_text(encoding='utf-8-sig')
            match = re.search(r'^\s*version:\s*["\']?([^\s"\']+)', text, re.M)
            result[child.name] = match.group(1) if match else None
    return result


def validate_manifest(manifest: dict) -> None:
    if manifest.get('schema') != 1 or manifest.get('kind') != 'copilot-update':
        raise ValueError('Unsupported update manifest')
    if not parse_version(manifest.get('packVersion')):
        raise ValueError('Invalid update version')
    files = manifest.get('files')
    if not isinstance(files, list) or not files or len(files) > 1000:
        raise ValueError('Invalid update file inventory')
    seen = set()
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {'path', 'archivePath', 'sha256', 'owner'}:
            raise ValueError('Invalid update file entry')
        safe_relative(entry['path'])
        safe_relative(entry['archivePath'])
        if entry['path'] in seen or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
            raise ValueError('Invalid or duplicate update file')
        if entry['owner'] != 'copilot' and not re.fullmatch(r'skill:[a-z0-9-]+', entry['owner']):
            raise ValueError('Invalid update owner')
        seen.add(entry['path'])
    skills = manifest.get('skills')
    if not isinstance(skills, dict):
        raise ValueError('Missing skill release inventory')
    for skill_id, item in skills.items():
        if not re.fullmatch(r'[a-z0-9-]+', skill_id) or not isinstance(item, dict):
            raise ValueError('Invalid skill release inventory')
        if not parse_version(item.get('version')) or not isinstance(item.get('requires'), list):
            raise ValueError('Invalid skill version or dependencies')
    defaults = manifest.get('defaultSkills')
    if not isinstance(defaults, list) or any(x not in skills for x in defaults):
        raise ValueError('Invalid default skill inventory')
    baselines = manifest.get('baselines', {})
    if not isinstance(baselines, dict):
        raise ValueError('Invalid release baselines')
    for version, hashes in baselines.items():
        if not parse_version(version) or not isinstance(hashes, dict):
            raise ValueError('Invalid release baseline')
        for path, sha in hashes.items():
            safe_relative(path)
            if not re.fullmatch(r'[0-9a-f]{64}', sha):
                raise ValueError('Invalid release baseline hash')


def release_payloads(manifest: dict, archive_bytes: bytes) -> dict[str, bytes]:
    validate_manifest(manifest)
    if digest(archive_bytes) != manifest.get('archiveSha256'):
        raise ValueError('Update archive checksum mismatch')
    result = {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        infos = archive.infolist()
        if len(infos) > 1200 or sum(x.file_size for x in infos) > MAX_BYTES:
            raise ValueError('Expanded update exceeds size limit')
        names = [x.filename for x in infos]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive paths')
        for info in infos:
            safe_relative(info.filename)
            if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Archive links are not supported')
        for entry in manifest['files']:
            try:
                data = archive.read(entry['archivePath'])
            except KeyError as error:
                raise ValueError('Update archive is missing ' + entry['archivePath']) from error
            if digest(data) != entry['sha256']:
                raise ValueError('Update file checksum mismatch: ' + entry['path'])
            result[entry['path']] = data
    return result


def read_receipt(root: Path) -> dict:
    path = root / '.merchjar-installation.json'
    if not path.exists():
        return {}
    if path.is_symlink():
        raise ValueError('Linked installation receipt is not supported')
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('files'), dict):
        raise ValueError('Invalid installation receipt; preserve and inspect it')
    return data


def detect_pack_version(root: Path, receipt: dict) -> str | None:
    if parse_version(receipt.get('version')):
        return receipt['version']
    for name in ('README.md', 'CLAUDE.md', 'AGENTS.md'):
        path = root / name
        if path.is_file():
            found = re.search(r'\*\*Pack Version:\*\*\s*(\d+\.\d+\.\d+)',
                              path.read_text(encoding='utf-8-sig'))
            if found:
                return found.group(1)
    return None


def dependency_closure(skills: dict, selected: set[str]) -> set[str]:
    pending = list(selected)
    while pending:
        skill = pending.pop()
        if skill not in skills:
            raise ValueError('Unknown skill in update request: ' + skill)
        for dependency in skills[skill]['requires']:
            if dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
    return selected


def select_owners(manifest: dict, requested: list[str], installed=None) -> tuple[set[str], set[str]]:
    if requested:
        selected = dependency_closure(manifest['skills'], set(requested))
        return {'skill:' + x for x in selected}, selected
    selected = set(manifest['defaultSkills'])
    selected.update(x for x in (installed or ()) if x in manifest['skills'])
    selected = dependency_closure(manifest['skills'], selected)
    return {'copilot', *('skill:' + x for x in selected)}, selected


def plan_update(root, manifest, payloads, requested=None):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not any((root / x).is_file() for x in ('AGENTS.md', 'CLAUDE.md')):
        raise ValueError('Choose an existing Copilot folder')
    receipt = read_receipt(root)
    installed_pack = detect_pack_version(root, receipt)
    baseline = manifest.get('baselines', {}).get(installed_pack, {})
    receipt_files = receipt.get('files', {})
    installed_versions = installed_skill_versions(root)
    owners, selected_skills = select_owners(
        manifest, requested or [], installed_versions if not requested else None)
    skipped_newer = set()
    for skill in selected_skills:
        current = parse_version(installed_versions.get(skill))
        available = parse_version(manifest['skills'][skill]['version'])
        if current and available and current > available:
            skipped_newer.add(skill)

    report = {
        'target_version': manifest['packVersion'], 'installed_version': installed_pack,
        'scope': sorted(selected_skills) if requested else 'default Copilot',
        'add': [], 'replace': [], 'unchanged': [], 'customized_preserved': [],
        'conflicts': [], 'newer_skills_preserved': sorted(skipped_newer),
        'applied': False,
    }
    snapshot = {}
    selected_entries = []
    for entry in manifest['files']:
        owner = entry['owner']
        if owner not in owners or (owner.startswith('skill:') and owner[6:] in skipped_newer):
            continue
        relative = entry['path']
        expected = payloads[relative]
        path = target_path(root, relative)
        current = path.read_bytes() if path.is_file() else None
        snapshot[relative] = digest(current) if current is not None else None
        selected_entries.append(entry)
        if current is None:
            report['add'].append(relative)
            continue
        current_hash = normalized_digest(current, relative)
        incoming_hash = normalized_digest(expected, relative)
        if current_hash == incoming_hash:
            report['unchanged'].append(relative)
            continue
        official_hash = receipt_files.get(relative) or baseline.get(relative)
        if official_hash and current_hash == official_hash:
            report['replace'].append(relative)
        elif official_hash and incoming_hash == official_hash:
            report['customized_preserved'].append(relative)
        else:
            report['conflicts'].append(relative)
    return root, report, snapshot, selected_entries


def skill_statuses(root, manifest, payloads):
    installed = installed_skill_versions(Path(root))
    receipt = read_receipt(Path(root))
    pack_version = detect_pack_version(Path(root), receipt)
    baseline = manifest.get('baselines', {}).get(pack_version, {})
    statuses = []
    installed_ids = set(installed)
    for skill_id, version in sorted(installed.items()):
        release = manifest['skills'].get(skill_id)
        if not release:
            statuses.append({'id': skill_id, 'installed': version, 'available': None,
                             'status': 'source_unknown'})
            continue
        incoming_version = release['version']
        missing = [x for x in release['requires'] if x not in installed_ids]
        current_tuple, incoming_tuple = parse_version(version), parse_version(incoming_version)
        paths = [e for e in manifest['files'] if e['owner'] == 'skill:' + skill_id]
        customized = False
        for entry in paths:
            path = target_path(Path(root), entry['path'])
            if not path.is_file():
                continue
            actual = normalized_digest(path.read_bytes(), entry['path'])
            official = receipt.get('files', {}).get(entry['path']) or baseline.get(entry['path'])
            incoming = normalized_digest(payloads[entry['path']], entry['path'])
            if actual != incoming and (not official or actual != official):
                customized = True
                break
        if missing:
            status = 'incompatible'
        elif customized:
            status = 'locally_customized'
        elif current_tuple and incoming_tuple and current_tuple > incoming_tuple:
            status = 'newer_installed'
        elif version == incoming_version and all(
                target_path(Path(root), e['path']).is_file() and
                normalized_digest(target_path(Path(root), e['path']).read_bytes(), e['path']) ==
                normalized_digest(payloads[e['path']], e['path']) for e in paths):
            status = 'current'
        elif current_tuple and incoming_tuple and current_tuple < incoming_tuple:
            status = 'update_available'
        else:
            status = 'source_or_version_unknown'
        statuses.append({'id': skill_id, 'installed': version, 'available': incoming_version,
                         'requires': release['requires'], 'missing_dependencies': missing,
                         'release_notes': release.get('releaseNotes', ''), 'status': status})
    return statuses


def atomic_json(path: Path, data: dict) -> None:
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def replace_from(source: Path, destination: Path) -> None:
    """Copy verified bytes beside the target, then atomically replace it."""
    swap = destination.with_name('.merchjar-swap-' + uuid.uuid4().hex + destination.suffix)
    try:
        with source.open('rb') as incoming, swap.open('xb') as output:
            shutil.copyfileobj(incoming, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(swap, destination)
    finally:
        if swap.exists():
            swap.unlink()


def apply_update(root, manifest, payloads, requested=None, fail_after=None):
    root, report, snapshot, entries = plan_update(root, manifest, payloads, requested)
    if report['conflicts']:
        return report
    update_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
    stage = root / ('.merchjar-update-' + update_id)
    backup = root / '.merchjar-backups' / update_id
    history = root / 'user' / 'library-updates'
    stage.mkdir(parents=True)
    backup.mkdir(parents=True)
    history.mkdir(parents=True, exist_ok=True)
    changed = set(report['add'] + report['replace'])
    applied = []
    installation_receipt = root / '.merchjar-installation.json'
    receipt_before = installation_receipt.read_bytes() if installation_receipt.is_file() else None
    update_receipt_path = history / (update_id + '.json')
    try:
        for entry in entries:
            if entry['path'] not in changed:
                continue
            staged = stage / safe_relative(entry['path'])
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(payloads[entry['path']])
            if digest(staged.read_bytes()) != entry['sha256']:
                raise ValueError('Staged update verification failed: ' + entry['path'])
        for relative, before in snapshot.items():
            path = target_path(root, relative)
            current = digest(path.read_bytes()) if path.is_file() else None
            if current != before:
                raise ValueError('Copilot files changed after inspection: ' + relative)
        for index, entry in enumerate(entries):
            relative = entry['path']
            if relative not in changed:
                continue
            destination = target_path(root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                saved = backup / safe_relative(relative)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, saved)
            replace_from(stage / safe_relative(relative), destination)
            applied.append(relative)
            if fail_after is not None and index >= fail_after:
                raise OSError('Simulated interrupted update')
        for entry in entries:
            relative = entry['path']
            if relative in report['customized_preserved']:
                continue
            path = target_path(root, relative)
            if not path.is_file() or normalized_digest(path.read_bytes(), relative) != normalized_digest(
                    payloads[relative], relative):
                raise ValueError('Applied update verification failed: ' + relative)

        inventory = root / 'skills/manage-library/scripts/installed_skills.py'
        if inventory.is_file():
            subprocess.run([sys.executable, str(inventory), '--root', str(root), '--write'],
                           cwd=root, stdout=subprocess.DEVNULL, check=True)

        prior = read_receipt(root)
        official = dict(prior.get('files', {}))
        for entry in entries:
            if entry['path'] not in report['customized_preserved']:
                official[entry['path']] = normalized_digest(payloads[entry['path']], entry['path'])
            elif entry['path'] not in official:
                installed = report['installed_version']
                old = manifest.get('baselines', {}).get(installed, {}).get(entry['path'])
                if old:
                    official[entry['path']] = old
        receipt = {'schema': 1, 'source': manifest.get('source'),
                   'version': manifest['packVersion'] if not requested else prior.get('version'),
                   'files': official, 'updatedAt': datetime.now(timezone.utc).isoformat(),
                   'lastUpdate': update_id}
        atomic_json(installation_receipt, receipt)
        update_receipt = dict(report)
        update_receipt.update({'applied': True, 'update_id': update_id,
                               'backup': backup.relative_to(root).as_posix()})
        atomic_json(update_receipt_path, update_receipt)
        report.update({'applied': True, 'update_id': update_id,
                       'backup': backup.relative_to(root).as_posix()})
    except Exception:
        for relative in reversed(applied):
            destination = target_path(root, relative)
            saved = backup / safe_relative(relative)
            if saved.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                replace_from(saved, destination)
            elif destination.exists():
                destination.unlink()
        if receipt_before is None:
            installation_receipt.unlink(missing_ok=True)
        else:
            installation_receipt.write_bytes(receipt_before)
        update_receipt_path.unlink(missing_ok=True)
        restored_inventory = root / 'skills/manage-library/scripts/installed_skills.py'
        if restored_inventory.is_file():
            subprocess.run([sys.executable, str(restored_inventory), '--root', str(root), '--write'],
                           cwd=root, stdout=subprocess.DEVNULL, check=False)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return report


def load_release(manifest_url: str):
    origin = urllib.parse.urlsplit(manifest_url).netloc
    manifest = json.loads(fetch(manifest_url, origin))
    # Record the manifest that was actually fetched. This keeps preview installs
    # on the supplied preview origin instead of claiming the production origin.
    manifest['source'] = manifest_url
    archive_url = urllib.parse.urljoin(manifest_url, manifest['archive'])
    archive = fetch(archive_url, origin)
    return manifest, release_payloads(manifest, archive)


def load_release_files(manifest_path: Path, archive_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    return manifest, release_payloads(manifest, archive_path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'update'))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--manifest')
    source.add_argument('--manifest-file', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--archive-file', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--skill', action='append', default=[])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.manifest_file:
            if not args.archive_file:
                raise ValueError('--manifest-file needs --archive-file')
            manifest, payloads = load_release_files(args.manifest_file, args.archive_file)
        else:
            manifest, payloads = load_release(args.manifest)
        if args.command == 'check':
            root, report, _, _ = plan_update(args.destination, manifest, payloads, args.skill)
            report['skills'] = skill_statuses(root, manifest, payloads)
        elif args.apply:
            report = apply_update(args.destination, manifest, payloads, args.skill)
        else:
            _, report, _, _ = plan_update(args.destination, manifest, payloads, args.skill)
        report['source'] = manifest.get('source')
        print(json.dumps(report, indent=2))
        return 2 if report['conflicts'] else 0
    except Exception as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
