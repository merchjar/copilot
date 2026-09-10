"""Inventory canonical local skills without reading config or loading skill instructions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import uuid


def inspect(root):
    root = Path(root).resolve()
    folder = root / 'skills'
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError('Expected a canonical skills directory in the selected Copilot')
    items = []
    for child in sorted(folder.iterdir()):
        entry = child / 'SKILL.md'
        if child.is_symlink() or not child.is_dir() or not entry.is_file():
            continue
        if entry.is_symlink():
            continue
        text = entry.read_text(encoding='utf-8-sig')
        front = re.match(r'^---\s*\n(.*?)\n---', text, re.S)
        metadata = front.group(1) if front else ''

        def field(key):
            found = re.search(r'^\s*' + re.escape(key) + r':\s*(.*?)\s*$', metadata, re.M)
            return found.group(1).strip('"\'') if found else None

        hashes = {}
        skipped = []
        for parent, dirs, files in os.walk(child, followlinks=False):
            parent = Path(parent)
            links = [d for d in dirs if (parent / d).is_symlink()]
            skipped.extend((parent / d).relative_to(root).as_posix() for d in links)
            dirs[:] = sorted(d for d in dirs if d != '__pycache__' and d not in links)
            for name in sorted(files):
                path = parent / name
                if path.suffix == '.pyc':
                    continue
                if path.is_symlink():
                    skipped.append(path.relative_to(root).as_posix())
                    continue
                hashes[path.relative_to(child).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        requires = [x.strip() for x in (field('requires-skills') or '').split(',') if x.strip()]
        items.append({'id': child.name, 'declared_name': field('name'),
                      'version': field('version'), 'description': field('description'),
                      'entry': entry.relative_to(root).as_posix(), 'requires': requires,
                      'files_sha256': hashes, 'skipped_links': skipped,
                      'update_status': 'not_checked'})
    ids = {item['id'] for item in items}
    for item in items:
        item['missing_dependencies'] = [dep for dep in item['requires'] if dep not in ids]
    return {'schema_version': 1, 'source': 'local canonical skills', 'skills': items}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument('--write', action='store_true', help='Refresh generated installed-skills.json')
    args = ap.parse_args()
    try:
        result = inspect(args.root)
        if args.write:
            target = args.root.resolve() / 'installed-skills.json'
            if target.is_symlink():
                raise ValueError('Refusing a symlink inventory destination')
            temp = target.with_name('.installed-skills-' + uuid.uuid4().hex + '.tmp')
            try:
                with temp.open('x', encoding='utf-8') as stream:
                    json.dump(result, stream, indent=2)
                    stream.write('\n')
                os.replace(temp, target)
            finally:
                if temp.exists():
                    temp.unlink()
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
