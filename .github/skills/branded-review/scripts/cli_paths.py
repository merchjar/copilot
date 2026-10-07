"""Command-line path handling shared by the report helpers.

Git Bash with MSYS_NO_PATHCONV=1 passes POSIX drive paths such as /c/projects/... unchanged, and Windows
Python would resolve them to a C:\\c\\projects folder, writing reports to an unintended folder. Convert drive-style
paths to Windows drive paths and reject other root-relative POSIX paths on Windows.
"""
import argparse
import os
from pathlib import Path
import re

_DRIVE = re.compile(r'^/(?:cygdrive/)?([A-Za-z])(?=/|$)(.*)$')


def cli_path(value, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    text = str(value)
    if windows and text.startswith('/') and not text.startswith('//'):
        match = _DRIVE.match(text)
        if not match:
            raise argparse.ArgumentTypeError(
                f'{text} is a POSIX path that Windows Python cannot resolve reliably; use a drive path such as D:/reports/report.html')
        text = f'{match.group(1).upper()}:{match.group(2) or "/"}'
    return Path(text).expanduser()
