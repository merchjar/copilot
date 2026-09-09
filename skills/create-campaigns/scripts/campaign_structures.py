"""Offline ASIN intake and revision-checked private structure storage. No API calls."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile


def intake(text):
    valid, invalid, duplicates = [], [], []
    # CSV quoting and headerless newline files; pasted lists may use whitespace.
    for row in csv.reader(io.StringIO(text.lstrip('\ufeff'))):
        for cell in row:
            for value in cell.split():
                value = value.strip().upper()
                if value == 'ASIN' and not valid and not invalid and not duplicates:
                    continue
                if not re.fullmatch(r'[A-Z0-9]{10}', value):
                    invalid.append(value)
                elif value in valid:
                    duplicates.append(value)
                else:
                    valid.append(value)
    return dict(asins=valid, invalid=invalid, duplicates=duplicates)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value):
    from decimal import Decimal, InvalidOperation
    try:
        number = Decimal(str(value))
        return number.is_finite() and number > 0
    except InvalidOperation:
        return False


def validate(data):
    require(isinstance(data, dict) and type(data.get('schema_version')) is int
            and data['schema_version'] == 1, 'Unsupported or missing schema version')
    require(set(data) == {'schema_version', 'structures'}, 'Unexpected storage fields')
    require(isinstance(data['structures'], list), 'structures must be a list')
    ids, defaults = set(), set()
    fields = {'id', 'name', 'scope', 'purposes', 'default', 'grouping', 'roles',
              'naming', 'budget_policy', 'bid_defaults', 'keyword_policy', 'provenance'}
    for s in data['structures']:
        require(isinstance(s, dict) and set(s) == fields, 'Invalid structure fields')
        for key in ('id', 'name'):
            require(isinstance(s[key], str) and bool(s[key].strip()), 'Missing identity')
        require(s['id'] not in ids, 'Duplicate structure ID')
        ids.add(s['id'])
        require(s['scope'] == 'global' or (isinstance(s['scope'], str) and
                re.fullmatch(r'profile:[0-9]+', s['scope'])), 'Invalid scope')
        require(isinstance(s['purposes'], list) and bool(s['purposes']) and
                all(isinstance(p, str) and p.strip() for p in s['purposes']), 'Invalid purposes')
        require(type(s['default']) is bool, 'default must be boolean')
        if s['default']:
            for purpose in s['purposes']:
                pair = (s['scope'], purpose)
                require(pair not in defaults, 'Competing defaults for scope and purpose')
                defaults.add(pair)
        require(s['grouping'] in ('per-product', 'shared-purpose'), 'Invalid grouping')
        require(isinstance(s['roles'], list) and bool(s['roles']), 'Missing roles')
        role_ids = set()
        for role in s['roles']:
            require(isinstance(role, dict) and set(role) == {'id', 'mode', 'job'}, 'Invalid role')
            require(all(isinstance(v, str) and v.strip() for v in role.values()), 'Empty role field')
            require(role['id'] not in role_ids, 'Duplicate role ID')
            role_ids.add(role['id'])
            require(role['mode'] in ('auto-combined', 'keyword-broad', 'keyword-exact'),
                    'Target mode outside initial supported planning schema')
        require(isinstance(s['naming'], str) and bool(s['naming'].strip()), 'Missing naming pattern')
        policy = s['budget_policy']
        require(isinstance(policy, dict) and set(policy) == {'basis', 'weights'} and
                policy['basis'] == 'fresh-batch-total', 'A fresh batch amount is required')
        require(isinstance(policy['weights'], dict) and set(policy['weights']) == role_ids and
                all(positive(v) for v in policy['weights'].values()), 'Invalid allocation weights')
        require(isinstance(s['bid_defaults'], dict), 'Invalid bid defaults')
        for currency, bids in s['bid_defaults'].items():
            require(re.fullmatch(r'[A-Z]{3}', currency) and isinstance(bids, dict) and
                    set(bids) <= role_ids and all(positive(v) for v in bids.values()), 'Invalid currency bids')
        require(s['keyword_policy'] in ('ask', 'defer-manual', 'paused-placeholders'), 'Invalid keyword policy')
        provenance = s['provenance']
        require(isinstance(provenance, dict) and set(provenance) == {'confirmed_at', 'instruction'} and
                all(isinstance(v, str) and v.strip() for v in provenance.values()), 'Missing provenance')
        # No credentials or resolved entity/product inputs belong in this store.
        require('mj_live_' not in json.dumps(s), 'Credentials are forbidden')
    return data


def read_store(path):
    raw = path.read_bytes() if path.exists() else b''
    data = json.loads(raw) if raw else {'schema_version': 1, 'structures': []}
    if path.exists() and not raw:
        raise ValueError('Empty storage file; preserve and repair explicitly')
    return validate(data), hashlib.sha256(raw).hexdigest()


def mutate(path, expected, definition=None, remove=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + '.lock')
    # Cooperative writers serialize; the revision also detects edits since inspection.
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temp = None
    try:
        os.close(fd)
        data, revision = read_store(path)
        require(revision == expected, 'Storage changed; inspect again before editing')
        if remove is not None:
            require(any(s['id'] == remove for s in data['structures']), 'Unknown structure ID')
            data['structures'] = [s for s in data['structures'] if s['id'] != remove]
        else:
            validate({'schema_version': 1, 'structures': [definition]})
            data['structures'] = [definition if s['id'] == definition['id'] else s
                                  for s in data['structures']]
            if not any(s['id'] == definition['id'] for s in data['structures']):
                data['structures'].append(definition)
        validate(data)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.structures-', delete=False) as out:
            temp = Path(out.name)
            json.dump(data, out, indent=2, allow_nan=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        require(read_store(path)[1] == revision, 'Storage changed during edit')
        os.replace(temp, path)
        return read_store(path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
        lock.unlink()


def select(data, profile, purpose, named=None):
    applicable = [s for s in data['structures'] if s['scope'] in
                  ('global', 'profile:' + profile) and purpose in s['purposes']]
    if named:
        matches = [s for s in applicable if s['id'] == named]
        require(len(matches) == 1, 'Named structure is not applicable')
        return {'selected': matches[0], 'choices': []}
    for scope in ('profile:' + profile, 'global'):
        defaults = [s for s in applicable if s['scope'] == scope and s['default']]
        if defaults:
            return {'selected': defaults[0], 'choices': []}
    return {'selected': None, 'choices': applicable}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('intake')
    inputs = p.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--file', type=Path)
    inputs.add_argument('--text')
    for action in ('inspect', 'select', 'save', 'remove'):
        p = sub.add_parser(action)
        p.add_argument('--store', type=Path, required=True)
        if action == 'select':
            p.add_argument('--profile', required=True)
            p.add_argument('--purpose', required=True)
            p.add_argument('--id')
        if action in ('save', 'remove'):
            p.add_argument('--revision', required=True)
        if action == 'save':
            p.add_argument('--definition', type=Path, required=True)
        if action == 'remove':
            p.add_argument('--id', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'intake':
            result = intake(args.file.read_text(encoding='utf-8-sig') if args.file else args.text)
        else:
            data, revision = read_store(args.store)
            if args.command == 'save':
                data, revision = mutate(args.store, args.revision,
                                        json.loads(args.definition.read_text(encoding='utf-8-sig')))
            elif args.command == 'remove':
                data, revision = mutate(args.store, args.revision, remove=args.id)
            result = {'revision': revision, 'data': data}
            if args.command == 'select':
                result = select(data, args.profile, args.purpose, args.id)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError):
        # Never echo malformed private data or a credential-containing exception.
        print(json.dumps({'error': 'Input/storage rejected or unavailable. Existing data was preserved; inspect locally before retrying.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
