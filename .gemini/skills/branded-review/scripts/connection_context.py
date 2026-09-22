"""Inspect connection setup only inside an explicitly accessible workspace. No API calls."""
import argparse
import json
from pathlib import Path
import re


def inspect_connection(workspace):
    root = Path(workspace).expanduser().resolve(strict=True)
    connect = any((root / folder / 'merchjar-connect/SKILL.md').is_file()
                  for folder in ('skills', '.agents/skills', '.claude/skills'))
    config = root / 'user/MJ_COPILOT_CONFIG.md'
    if not connect:
        return {'state': 'unavailable', 'next_action': 'offer_connection', 'live_reads_verified': False}
    if config.is_file():
        text = re.sub(r'<!--.*?-->', '', config.read_text(encoding='utf-8-sig'), flags=re.S)
        section = re.search(r'^## API Key\s*(.*?)(?=\n## |\Z)', text, re.M | re.S)
        if section and re.search(r'\bmj_live_[A-Za-z0-9_]+\b', section[1]):
            return {'state': 'configured_unverified', 'next_action': 'verify_existing_connection', 'live_reads_verified': False}
    return {'state': 'setup_required', 'next_action': 'configure_existing_copilot', 'live_reads_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, help='Authorized session/project root, not a changed shell working directory')
    args = parser.parse_args()
    print(json.dumps(inspect_connection(args.workspace)))
