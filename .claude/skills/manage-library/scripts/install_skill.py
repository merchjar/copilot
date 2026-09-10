"""Install one verified Library skill into an existing Copilot. No account/API actions.

Default is a dry run. Existing differing files block the entire operation; they
are never overwritten. Requires Python 3.9+. Standard library only.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
import urllib.parse
import urllib.request
import zipfile

MAX_BYTES = 25 * 1024 * 1024
RUNTIMES = ('.agents', '.claude', '.gemini', '.github')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def same_content(existing, expected, relative):
    if existing == expected:
        return True
    # Git/ZIP installs can differ only in Windows line endings. Preserve those
    # bytes in place; downloaded archives and inventory still require exact hashes.
    if Path(relative).suffix.lower() in ('.md', '.py', '.json', '.txt', '.sh') and b'\0' not in existing + expected:
        return existing.replace(b'\r\n', b'\n') == expected.replace(b'\r\n', b'\n')
    return False


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Invalid package path')
    parts = value.split('/')
    if any(part in ('', '.', '..') for part in parts) or PurePosixPath(value).is_absolute():
        raise ValueError('Invalid package path')
    return Path(*parts)


def target_path(root, relative):
    path = root / safe_relative(relative)
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError('Linked install paths are not supported')
    resolved = path.resolve()
    if root not in resolved.parents:
        raise ValueError('Install path leaves the selected Copilot')
    return path


def fetch(url, origin):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != origin or parsed.username or parsed.password:
        raise ValueError('Package URLs must use the same HTTPS origin as the manifest')
    request = urllib.request.Request(url, headers={'User-Agent': 'MerchJar-Library-Installer/0.1', 'Accept': '*/*'})
    with urllib.request.urlopen(request, timeout=30) as response:
        final = urllib.parse.urlsplit(response.url)
        if final.scheme != 'https' or final.netloc != origin:
            raise ValueError('Cross-origin package redirect rejected')
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Package exceeds size limit')
    return data


def payloads(manifest, archive_bytes):
    if manifest.get('schema') != 1 or manifest.get('kind') != 'skill':
        raise ValueError('Unsupported install manifest')
    skill = manifest.get('id', '')
    if not skill or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in skill):
        raise ValueError('Invalid skill ID')
    if digest(archive_bytes) != manifest['archiveSha256']:
        raise ValueError('Archive checksum mismatch')
    filelist = manifest.get('files', [])
    if not filelist or len(filelist) > 500:
        raise ValueError('Invalid file inventory')
    allowed_skills = {skill, 'merchjar-connect'}
    result = {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        infos = archive.infolist()
        if len(infos) > 700 or sum(i.file_size for i in infos) > MAX_BYTES:
            raise ValueError('Expanded package exceeds size limit')
        names = [i.filename for i in infos]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate archive paths')
        for info in infos:
            safe_relative(info.filename)
            if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Archive links are not supported')
        for entry in filelist:
            relative = entry['path']
            parts = safe_relative(relative).parts
            if parts[0] == 'skills':
                if len(parts) < 3 or parts[1] not in allowed_skills:
                    raise ValueError('Unexpected skill in package')
            elif parts[0] not in ('tools', 'reference', 'docs') or len(parts) < 2:
                raise ValueError('Package may only install skills and shared support files')
            if relative in result:
                raise ValueError('Duplicate install path')
            data = archive.read(entry['archivePath'])
            if digest(data) != entry['sha256']:
                raise ValueError('File checksum mismatch: ' + relative)
            result[relative] = data
        for required in ('skills/' + skill + '/SKILL.md', 'skills/merchjar-connect/SKILL.md', 'tools/merchjar_client.py'):
            if required not in result:
                raise ValueError('Required dependency missing: ' + required)
    # Keep all standard pack runtime discovery folders consistent.
    for relative, data in list(result.items()):
        if relative.startswith('skills/'):
            for runtime in RUNTIMES:
                result[runtime + '/' + relative] = data
    return result


def plan(root, files):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not any((root / name).is_file() for name in ('AGENTS.md', 'CLAUDE.md')):
        raise ValueError('Choose your existing Copilot folder, containing AGENTS.md or CLAUDE.md')
    if not ((root / 'tools/merchjar_client.py').is_file() or (root / 'skills/merchjar-connect/SKILL.md').is_file()):
        raise ValueError('The selected directory is not an existing Merch Jar Copilot')
    report = {'add': [], 'unchanged': [], 'conflicts': []}
    for relative, data in files.items():
        path = target_path(root, relative)
        if path.exists():
            key = 'unchanged' if path.is_file() and same_content(path.read_bytes(), data, relative) else 'conflicts'
            report[key].append(relative)
        else:
            report['add'].append(relative)
    return root, report


def install(root, files, apply=False):
    root, report = plan(root, files)
    report['applied'] = False
    if not apply or report['conflicts']:
        return report
    created = []
    try:
        # Recheck the entire plan before writing. Exclusive create prevents overwrites.
        _, fresh = plan(root, files)
        if fresh != {k: report[k] for k in ('add', 'unchanged', 'conflicts')}:
            raise ValueError('Copilot files changed after inspection; run the check again')
        for relative in report['add']:
            destination = target_path(root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as output:
                created.append(destination)
                output.write(files[relative])
        for relative, data in files.items():
            if not same_content(target_path(root, relative).read_bytes(), data, relative):
                raise ValueError('Installed file verification failed: ' + relative)
        report['applied'] = True
    except Exception:
        # Remove only new files created by this attempt, never pre-existing files.
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    origin = urllib.parse.urlsplit(args.manifest).netloc
    manifest = json.loads(fetch(args.manifest, origin))
    url = urllib.parse.urljoin(args.manifest, manifest['archive'])
    files = payloads(manifest, fetch(url, origin))
    report = install(args.destination, files, args.apply)
    report['skill'] = manifest['id']
    report['source'] = manifest['source']
    print(json.dumps(report, indent=2))
    return 2 if report['conflicts'] else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
