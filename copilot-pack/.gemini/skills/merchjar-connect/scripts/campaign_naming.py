"""Private, revision-checked naming preferences and offline name rendering. No API calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import string
import tempfile

TOKENS = {'asin', 'product', 'group', 'targeting', 'method', 'purpose', 'market',
          'ad_product', 'portfolio', 'brand', 'theme', 'variant'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def fields(pattern):
    require(isinstance(pattern, str) and pattern.strip(), 'Missing naming pattern')
    result = set()
    for _, token, spec, conversion in string.Formatter().parse(pattern):
        if token is not None:
            require(token in TOKENS and not spec and not conversion, 'Unsupported pattern token')
            result.add(token)
    require(bool(result), 'Pattern needs a supported token')
    return result


def validate(data):
    require(isinstance(data, dict) and set(data) == {'schema_version', 'conventions'}
            and type(data['schema_version']) is int and data['schema_version'] == 1,
            'Unsupported naming store schema')
    require(isinstance(data['conventions'], list), 'Invalid conventions')
    scopes = set()
    for item in data['conventions']:
        require(isinstance(item, dict) and set(item) - {'field_values'} == {
            'scope', 'name', 'single_asin', 'multi_asin', 'vocabulary', 'rules', 'provenance'},
            'Invalid convention fields')
        scope = item['scope']
        require(isinstance(scope, str) and (scope == 'global' or re.fullmatch(r'profile:[0-9]+', scope)),
                'Invalid convention scope')
        require(scope not in scopes, 'Competing conventions for one scope')
        scopes.add(scope)
        require(isinstance(item['name'], str) and item['name'].strip(), 'Missing convention name')
        fields(item['single_asin'])
        require('asin' not in fields(item['multi_asin']), 'Multi-ASIN pattern cannot imply a single ASIN')
        allowed = item.get('field_values', {})
        require(isinstance(allowed, dict) and all(
            key in TOKENS and isinstance(values, list) and values
            and all(isinstance(v, str) and v.strip() for v in values)
            and len(values) == len(set(values))
            for key, values in allowed.items()), 'Invalid field vocabulary')
        require(isinstance(item['vocabulary'], dict) and all(
            isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
            for k, v in item['vocabulary'].items()), 'Invalid vocabulary')
        require(isinstance(item['rules'], dict) and set(item['rules']) == {
            'product_labels', 'missing_product', 'mixed_targeting', 'collisions', 'dates'},
            'Incomplete exception rules')
        require(all(isinstance(v, str) and v.strip() for v in item['rules'].values()), 'Empty exception rule')
        require(isinstance(item['provenance'], dict) and set(item['provenance']) == {'confirmed_at', 'instruction'}
                and all(isinstance(v, str) and v.strip() for v in item['provenance'].values()),
                'Missing approval provenance')
    require('mj_live_' not in json.dumps(data), 'Credentials do not belong in naming preferences')
    return data


def read_store(path):
    raw = path.read_bytes() if path.exists() else b''
    require(not path.exists() or bool(raw), 'Empty naming store; preserve and repair explicitly')
    data = json.loads(raw) if raw else {'schema_version': 1, 'conventions': []}
    return validate(data), hashlib.sha256(raw).hexdigest()


def save(path, revision, definition):
    validate({'schema_version': 1, 'conventions': [definition]})
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temp = None
    try:
        os.close(fd)
        data, current = read_store(path)
        require(current == revision, 'Naming preferences changed; inspect and reconcile again')
        items = data['conventions']
        data['conventions'] = [definition if x['scope'] == definition['scope'] else x for x in items]
        if not any(x['scope'] == definition['scope'] for x in items):
            data['conventions'].append(definition)
        validate(data)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.naming-', delete=False) as output:
            temp = Path(output.name)
            json.dump(data, output, indent=2, allow_nan=False)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        require(read_store(path)[1] == current, 'Naming preferences changed during save')
        os.replace(temp, path)
        return read_store(path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
        lock.unlink()


def resolve(data, profile):
    require(isinstance(profile, str) and re.fullmatch(r'[0-9]+', profile), 'Profile ID must be a decimal string')
    validate(data)
    for scope in ('profile:' + profile, 'global'):
        for item in data['conventions']:
            if item['scope'] == scope:
                return item
    return None


def render(convention, facts):
    require(isinstance(facts, dict), 'Facts must be an object')
    asins = facts.get('asins')
    require(isinstance(asins, list) and asins and all(
        isinstance(a, str) and re.fullmatch(r'[A-Z0-9]{10}', a) for a in asins),
        'Verified advertised ASINs required; missing products need review')
    asins = sorted(set(asins))
    pattern = convention['single_asin' if len(asins) == 1 else 'multi_asin']
    values = {k: v for k, v in facts.items() if k in TOKENS}
    values.pop('asin', None)
    if len(asins) == 1:
        values['asin'] = asins[0]
    needed = fields(pattern)
    require(all(isinstance(values.get(k), str) and values[k].strip() for k in needed),
            'Missing naming facts; resolve before rendering')
    for key in needed:
        allowed = convention.get('field_values', {}).get(key)
        require(allowed is None or values[key] in allowed,
                'Naming value outside approved vocabulary: ' + key)
    result = pattern.format_map(values)
    require(1 <= len(result) <= 255 and not any(ord(c) < 32 for c in result), 'Invalid campaign name length/control character')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'resolve', 'save', 'render'])
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--profile')
    parser.add_argument('--revision')
    parser.add_argument('--definition', type=Path)
    parser.add_argument('--facts', type=Path)
    args = parser.parse_args()
    try:
        data, revision = read_store(args.store)
        if args.command == 'save':
            require(args.definition is not None and args.revision, 'Save needs definition and inspected revision')
            data, revision = save(args.store, args.revision,
                                  json.loads(args.definition.read_text(encoding='utf-8-sig')))
        result = {'data': data, 'revision': revision, 'path': str(args.store.resolve())}
        if args.command in ('resolve', 'render'):
            selected = resolve(data, args.profile)
            result = {'selected': selected, 'revision': revision}
            if args.command == 'render':
                require(selected is not None and args.facts is not None, 'Render needs a convention and facts')
                result['name'] = render(selected, json.loads(args.facts.read_text(encoding='utf-8-sig')))
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
