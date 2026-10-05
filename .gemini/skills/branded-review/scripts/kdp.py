"""Book (KDP) account support: KENP column detection, account signals and KENP-inclusive ACoS.

Standard ACoS stays spend / attributed sales. When KENP data is present the report adds
ACoS incl. KENP = spend / (attributed sales + estimated KENP royalties). No API calls or writes.
"""
from __future__ import annotations

from decimal import Decimal
import re

ISBN10 = re.compile(r'[0-9]{9}[0-9X]')
FORMULA = 'Ad spend / (attributed sales + estimated KENP royalties)'
RULE_KINDS = {'brand', 'author', 'pen_name', 'series', 'title', 'product_line'}
KIND_LABELS = {'author': 'author name', 'pen_name': 'author name', 'series': 'series', 'title': 'title',
               'product_line': 'product line'}


def _compact(header):
    return re.sub(r'[^a-z0-9]+', '', header.casefold())


def is_kenp_header(header):
    """Amazon labels vary: 'Estimated KENP royalties (14 days)', 'KENP Read',
    'Kindle Edition Normalized Pages (KENP) Read', or API-style 'kindleEditionNormalizedPagesRead14d'."""
    words = re.sub(r'[^a-z0-9]+', ' ', header.casefold()).split()
    return 'kenp' in words or 'kindleeditionnormalizedpage' in _compact(header)


def kenp_columns(fieldnames, royalties=None, pages=None):
    """Return (royalties column, pages-read column). Several candidates need an explicit choice."""
    fields = list(fieldnames or [])
    kenp = [h for h in fields if is_kenp_header(h)]
    found_royalties = [h for h in kenp if 'royalt' in _compact(h)]
    found_pages = [h for h in kenp if h not in found_royalties and 'read' in _compact(h)]

    def pick(explicit, found, label):
        if explicit:
            if explicit not in fields:
                raise ValueError(f'KENP {label} column not found: {explicit}')
            return explicit
        if len(found) > 1:
            raise ValueError(f'Several KENP {label} columns found ({", ".join(found)}); choose one with the matching attribution window')
        return found[0] if found else None
    return pick(royalties, found_royalties, 'royalties'), pick(pages, found_pages, 'pages read')


def present(spend, royalties, pages_read, sales_basis):
    base = sales_basis + royalties
    return {'royalties': str(royalties), 'pages_read': str(pages_read), 'sales_basis': str(sales_basis),
            'acos_incl_kenp': float(spend / base) if base > 0 else None}


def empty():
    return {'royalties': Decimal(0), 'pages_read': Decimal(0), 'sales_basis': Decimal(0)}


def book_ids(ids):
    return sorted({str(i).strip().upper() for i in ids if ISBN10.fullmatch(str(i).strip().upper())})


def account_status(kenp_activity=None, confirmed=False, isbn_ids=(), kenp_included=False, kenp_columns_present=False):
    """Classify the account. Only KENP activity or a user statement turns on KDP reporting.
    Book-style product IDs alone are a prompt to ask, never a classification."""
    signals = []
    if kenp_activity:
        signals.append({'signal': kenp_activity, 'strength': 'strong'})
    if confirmed:
        signals.append({'signal': 'User confirmed the account advertises books', 'strength': 'strong'})
    if isbn_ids:
        signals.append({'signal': f'{len(isbn_ids)} advertised ISBN-10 product IDs', 'strength': 'weak',
                        'examples': list(isbn_ids)[:3]})
    if not signals:
        return None
    status = 'detected' if kenp_activity else 'confirmed' if confirmed else 'possible'
    result = {'status': status, 'signals': signals, 'kenp_included': kenp_included}
    if not kenp_included:
        result['next_step'] = ('Ask whether this account advertises books. If it does, request a Search term export that includes '
                               'the KENP royalties column so Kindle Unlimited reads can be counted.' if status == 'possible' else
                               'This data has no KENP royalties. Request a Search term export that includes the KENP royalties column, '
                               'or use the Merch Jar connection, so Kindle Unlimited reads can be counted.')
        if kenp_columns_present:
            result['next_step'] = 'The KENP columns are present but report no page reads for this period.'
    return result


def rule_label(rule, default='brand rule'):
    label = KIND_LABELS.get(rule.get('kind'))
    return f'{label} rule' if label and label != 'author name' else (label or default)
