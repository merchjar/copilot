"""Verify an existing report and return its absolute delivery path. Never rewrites it."""
import argparse
import hashlib
import json
from pathlib import Path


def report_artifact(path):
    path = Path(path).expanduser()
    if not path.is_absolute():
        raise ValueError('Use the absolute report path captured when it was written, not a path relative to the current folder')
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError('Report path must identify a file')
    content = path.read_bytes()
    if not content:
        raise ValueError('Report file is empty; do not present a download')
    # Angle-bracket Markdown destinations handle spaces and parentheses. Encode
    # delimiters that could otherwise escape that destination on POSIX filesystems.
    target = path.as_posix().replace('%', '%25').replace('<', '%3C').replace('>', '%3E').replace('\n', '%0A').replace('\r', '%0D')
    return {'absolute_path': path.as_posix(), 'bytes': len(content),
            'sha256': hashlib.sha256(content).hexdigest(),
            'markdown_link': '[Open report](<' + target + '>)',
            'file_verified': True, 'client_preview_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path, help='Existing report, absolute filesystem path')
    args = parser.parse_args()
    print(json.dumps({'report_artifact': report_artifact(args.report)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
