"""Compatibility entry point; shared naming support lives in Merch Jar Connect."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    shared = Path(__file__).resolve().parents[2] / 'merchjar-connect/scripts/campaign_naming.py'
    if not shared.is_file():
        raise SystemExit('Shared naming helper missing. Install compatible Merch Jar Connect (1.4+).')
    runpy.run_path(str(shared), run_name='__main__')
