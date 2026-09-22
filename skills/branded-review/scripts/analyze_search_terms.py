"""Initial adapter for Amazon Ads' English default Search term CSV.

Read-only source handling. No API calls, uploads, or account mutations.
Produces a reconciled JSON analysis and a standalone HTML review.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import hashlib
from html import escape
import json
from pathlib import Path
import re
import unicodedata
from report_context import product_context, targeting_context

METRICS = {"spend": "Total cost", "sales": "Sales", "clicks": "Clicks",
           "purchases": "Purchases", "impressions": "Impressions"}
LABELS = {"brand_query": "Explicit brand queries", "other_query": "Other text queries (provisional non-brand)",
          "brand_review": "Possible brand variants", "asin_unknown": "ASIN rows (ownership unknown)",
          "missing_query": "Unreported search term", "owned_asin": "ASINs matching the advertised brand catalog"}
REQUIRED = ["Budget currency", "Date range", "Advertiser account ID", "Advertiser account name",
            "Campaign ID", "Campaign name", "Ad group ID", "Ad group name", "Search term", *METRICS.values()]


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def identifier(value):
    # Amazon uses literal ="..." wrappers to preserve IDs in spreadsheet programs.
    match = re.fullmatch(r'="([^"]*)"', value.strip())
    return match.group(1) if match else value.strip()


def number(value, column, line):
    if not value.strip():
        raise ValueError(f"Missing {column} at source line {line}; missing is not zero")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {column} at source line {line}") from exc
    if not result.is_finite():
        raise ValueError(f"Nonfinite {column} at source line {line}")
    return result


def dates(value):
    start, end = value.split(" - ")
    start, end = (datetime.strptime(v, "%b %d, %Y").date() for v in (start, end))
    if start > end:
        raise ValueError("Reversed date range")
    return start, end


def rule_matches(value, rule):
    term = normalize(rule['term'])
    if rule.get('match') == 'contains_compact':
        return re.sub(r'[\s-]', '', term) in re.sub(r'[\s-]', '', value)
    if rule.get('match') == 'exact':
        return value == term
    return bool(re.search(r'(?<!\w)' + r'[\s-]*'.join(re.escape(x) for x in term.split()) + r'(?!\w)', value))


def classify(query, aliases, reference=None):
    value = normalize(query)
    if not value:
        return "missing_query", "Source query is blank; no traffic identity inferred"
    if re.fullmatch(r"(?:b[a-z0-9]{9}|[0-9]{10})", value) and any(c.isdigit() for c in value):
        return "asin_unknown", "Reported ASIN; owned-product list not supplied"
    if reference:
        for rule in reference.get('exceptions', []):
            if rule.get('status') == 'approved' and rule_matches(value, rule):
                return rule['category'], f"Approved exception: {rule['term']}"
        for rule in reference.get('rules', []):
            if rule.get('status') == 'rejected' and rule_matches(value, rule):
                return 'other_query', f"Reviewed and excluded brand candidate: {rule['term']}"
        for rule in reference.get('rules', []):
            if rule.get('status') == 'approved' and rule_matches(value, rule):
                return 'brand_query', f"Approved brand rule: {rule['term']}"
    for alias in aliases:
        pattern = r"(?<!\w)" + r"[\s-]+".join(re.escape(x) for x in normalize(alias).split()) + r"(?!\w)"
        if re.search(pattern, value):
            return "brand_query", f"Contains brand identifier: {alias}"
        # Only spacing and hyphens change, never letters. Whole-name boundaries
        # prevent a brand being inferred from a substring of an unrelated word.
        compact = re.sub(r'[\s\-\u2010-\u2015]', '', normalize(alias))
        pattern = r'(?<!\w)' + r'[\s\-\u2010-\u2015]*'.join(re.escape(c) for c in compact) + r'(?!\w)'
        if compact and re.search(pattern, value):
            return 'brand_query', f'Formatting equivalent of confirmed brand: {alias}'
    if reference:
        for rule in reference.get('rules', []):
            if rule.get('status') == 'proposed' and rule_matches(value, rule):
                return 'brand_review', f"Proposed brand rule requires confirmation: {rule['term']}"
    # Suggest, never approve, near spellings and brand names joined to model names.
    tokens = re.findall(r"[a-z0-9]+", value)
    for alias in aliases:
        compact = re.sub(r"[^a-z0-9]", "", normalize(alias))
        if len(compact) < 6:
            continue
        if compact in re.sub(r"[\s-]", "", value):
            return "brand_review", "Possible brand identifier joined to another word/model"
        if any(len(t) >= 6 and SequenceMatcher(None, t, compact).ratio() >= .84 for t in tokens):
            return "brand_review", "Possible spelling variant; confirmation needed"
    return "other_query", "No supplied brand identifier matched; alias coverage not yet approved"


def empty_metrics():
    return {name: Decimal(0) for name in METRICS}


def add(destination, metrics):
    for name in METRICS:
        destination[name] += metrics[name]


def ratio(numerator, denominator):
    return float(numerator / denominator) if denominator > 0 else None


def present(metrics):
    return {**{k: str(v) for k, v in metrics.items()},
            "acos": ratio(metrics["spend"], metrics["sales"]),
            "cpc": ratio(metrics["spend"], metrics["clicks"]),
            "purchase_rate": ratio(metrics["purchases"], metrics["clicks"])}


def brand_decisions(rows):
    buckets = {}
    for row in rows:
        if row['category'] == 'brand_review':
            label = row['reason']
        elif row['reason'].startswith('Formatting equivalent'):
            label = 'Spacing/hyphen variants included automatically'
        else:
            continue
        bucket = buckets.setdefault(label, {'rows': 0, 'metrics': empty_metrics(), 'queries': {}})
        metrics = {key: Decimal(row[key]) for key in METRICS}
        bucket['rows'] += 1; add(bucket['metrics'], metrics)
        bucket['queries'][row['query']] = bucket['queries'].get(row['query'], Decimal(0)) + metrics['spend']
    return [{'reason': reason, 'automatic': reason.startswith('Spacing/'), 'rows': b['rows'],
             'distinct_queries': len(b['queries']), **present(b['metrics']),
             'examples': sorted(b['queries'], key=lambda q: (-b['queries'][q], q))[:6],
             'recommendation': 'Include equivalent spacing and hyphens; retain explicit exceptions.' if reason.startswith('Spacing/')
                 else 'Review these examples together. Confirm brand spelling intent separately from model-only names; performance is not identity evidence.'}
            for reason, b in buckets.items()]


def analyze(source, advertiser, currency, brand, aliases, reference=None, advertised_products=None, targeting=None, marketplace=None, catalog=None):
    source = Path(source)
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(REQUIRED) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Unsupported export; missing columns: {', '.join(sorted(missing))}")
        original = [(line, r) for line, r in enumerate(reader, 2)]
    selected = [(line, r) for line, r in original
                if r["Advertiser account name"] == advertiser and r["Budget currency"] == currency]
    if not selected:
        raise ValueError("No rows match the exact advertiser and currency selection")
    accounts = {identifier(r["Advertiser account ID"]) for _, r in selected}
    if len(accounts) != 1:
        raise ValueError("Advertiser name is ambiguous across account IDs; select by ID before proceeding")
    account_id = next(iter(accounts))
    if reference:
        if reference.get('account_id') != account_id or reference.get('currency') != currency or reference.get('brand') != brand:
            raise ValueError('Saved brand reference does not match the selected account, currency and brand')
        if marketplace and reference.get('marketplace') != marketplace:
            raise ValueError('Saved brand reference has a different marketplace')
        for rule in reference.get('rules', []) + reference.get('exceptions', []):
            if not rule.get('term', '').strip() or rule.get('status') not in ('approved','proposed','rejected'):
                raise ValueError('Brand reference contains an invalid rule')
            if rule.get('match','phrase') not in ('phrase','exact','contains_compact'):
                raise ValueError('Brand reference contains an unsupported matching method')
        if any(r.get('category') not in ('brand_query','other_query','brand_review') for r in reference.get('exceptions', [])):
            raise ValueError('Brand reference exception has an unsupported class')
    context, products_by_group, owned = {}, {}, set()
    if advertised_products:
        if not marketplace:
            raise ValueError('Select marketplace before using product ownership evidence')
        context['products'], products_by_group = product_context(advertised_products, account_id, currency, brand, marketplace)
        owned = set(context['products']['owned_asins'])
    if catalog is not None:
        expected = {'account_id':account_id, 'brand':brand, 'marketplace':marketplace}
        if not marketplace or catalog.get('scope') != expected:
            raise ValueError('Catalog account, brand and marketplace must match the selected report')
        if not catalog.get('source') or catalog.get('ownership_verified') is not True:
            raise ValueError('Catalog needs source evidence and verified brand ownership')
        supplied = set(catalog.get('owned_asins', []))
        if any(not re.fullmatch(r'(?:B[A-Z0-9]{9}|[0-9]{10})', str(a)) for a in supplied):
            raise ValueError('Invalid ASIN in catalog')
        if supplied & set(context.get('products', {}).get('conflicted_asins', [])):
            raise ValueError('Resolve conflicting product ownership before using the catalog')
        excluded = set(catalog.get('excluded_asins', []))
        if any(not re.fullmatch(r'(?:B[A-Z0-9]{9}|[0-9]{10})', str(a)) for a in excluded) or supplied & excluded:
            raise ValueError('Invalid or conflicting explicit catalog exclusions')
        owned = (owned | supplied) - excluded
        context['products'] = {**context.get('products', {}), 'kind':'saved_catalog',
            'owned_asins':sorted(owned), 'product_count':len(owned), 'marketplace':marketplace,
            'catalog_complete':catalog.get('complete') is True, 'catalog_source':catalog['source'],
            'observed_start':catalog.get('observed_start'), 'observed_end':catalog.get('observed_end')}
    aliases = list(dict.fromkeys([brand, *(reference or {}).get('aliases', []), *aliases]))
    groups = {key: {"metrics": empty_metrics(), "rows": 0} for key in LABELS}
    campaigns, terms, windows, classified = {}, {}, defaultdict(list), []
    total, seen, starts, ends = empty_metrics(), set(), [], []
    # Independent source-column sums are checked against the classified result below.
    source_total = {k: sum((number(r[v], v, line) for line, r in selected), Decimal(0)) for k, v in METRICS.items()}
    for line, row in selected:
        signature = tuple(row.items())
        if signature in seen:
            raise ValueError(f"Duplicate source row at line {line}; resolve overlapping exports")
        seen.add(signature)
        cid, aid = identifier(row["Campaign ID"]), identifier(row["Ad group ID"])
        start, end = dates(row["Date range"])
        grain = cid, aid, row["Search term"]
        if any(start <= old_end and end >= old_start for old_start, old_end in windows[grain]):
            raise ValueError(f"Overlapping campaign/ad-group/query periods at source line {line}")
        windows[grain].append((start, end)); starts.append(start); ends.append(end)
        metrics = {k: number(row[v], v, line) for k, v in METRICS.items()}
        category, reason = classify(row["Search term"], aliases, reference)
        if category == 'asin_unknown' and row['Search term'].strip().upper() in owned:
            category, reason = 'owned_asin', 'ASIN matches verified product evidence for the selected brand and marketplace'
        add(total, metrics); add(groups[category]["metrics"], metrics); groups[category]["rows"] += 1
        campaign = campaigns.setdefault(cid, {"id": cid, "name": row["Campaign name"], "metrics": empty_metrics(),
                                                "groups": {k: empty_metrics() for k in LABELS}})
        if campaign["name"] != row["Campaign name"]:
            raise ValueError(f"Conflicting campaign names for one ID at line {line}; resolve export grain")
        add(campaign["metrics"], metrics); add(campaign["groups"][category], metrics)
        term = terms.setdefault((category, row["Search term"]), empty_metrics()); add(term, metrics)
        classified.append({"source_line": line, "campaign_id": cid, "campaign_name": row["Campaign name"],
                           "ad_group_id": aid, "ad_group_name": row["Ad group name"], "query": row["Search term"],
                           "start": start.isoformat(), "end": end.isoformat(), "category": category,
                           "reason": reason, **{k: str(v) for k, v in metrics.items()}})
    grouped_total = {k: sum((g["metrics"][k] for g in groups.values()), Decimal(0)) for k in METRICS}
    if total != source_total or grouped_total != source_total:
        raise ValueError("Classification does not reconcile to the selected source population")
    campaign_rows = []
    for c in campaigns.values():
        campaign_rows.append({"id": c["id"], "name": c["name"], **present(c["metrics"]),
                              "brand_spend": str(c["groups"]["brand_query"]["spend"]),
                              "other_spend": str(c["groups"]["other_query"]["spend"]),
                              "mixed": c["groups"]["brand_query"]["clicks"] > 0 and c["groups"]["other_query"]["clicks"] > 0})
    term_rows = [{"query": q, "category": c, **present(m)} for (c, q), m in terms.items()]
    if targeting:
        context['targeting'] = targeting_context(targeting, account_id, currency, classify, aliases, reference, products_by_group)
    for receipt in context.values():
        receipt['same_date_envelope_as_search'] = (receipt['observed_start'],receipt['observed_end']) == (min(starts).isoformat(),max(ends).isoformat())
        receipt['use'] = 'Identity/configuration context only; metrics not added or compared to search-term totals'
    return {"schema": "brand-traffic-review/default-templates", "brand": brand, "advertiser": advertiser,
            "currency": currency, "source_path": str(source.resolve()), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_rows": len(original), "selected_rows": len(selected), "excluded_other_scope_rows": len(original)-len(selected),
            "account_id": next(iter(accounts)), "campaign_count": len(campaigns),
            "ad_group_count": len({r['ad_group_id'] for r in classified if r['ad_group_id']}),
            "observed_start": min(starts).isoformat(), "observed_end": max(ends).isoformat(),
            "brand_reference": {"aliases": aliases, "status": "core rules applied; proposed additions held for review",
                                "rules": (reference or {}).get('rules', []), "exceptions":(reference or {}).get('exceptions', []),
                                "marketplace":marketplace or (reference or {}).get('marketplace'), "website": (reference or {}).get('website'),
                                "owned_asin_count":len(owned)}, "context":context,
            "totals": present(total), "brand_decisions": brand_decisions(classified),
            "groups": [{"category": k, "label": LABELS[k], "rows": v["rows"], **present(v["metrics"])} for k,v in groups.items()],
            "mixed_campaign_count": sum(c["mixed"] for c in campaign_rows),
            "campaigns": sorted(campaign_rows, key=lambda c: Decimal(c['brand_spend']), reverse=True),
            "terms": sorted(term_rows, key=lambda t: Decimal(t['spend']), reverse=True), "rows": classified,
            "limitations": ["Proposed brand names and spellings remain outside the branded/non-branded comparison.",
                            "Ad product, marketplace and attribution window are not explicit in this export.",
                            "Reported row periods span the displayed dates; this is not a daily trend report.",
                            "No matching campaign report has verified account-wide coverage; recent sales may still change.",
                            "Current bids, goals, negatives and eligible advertised products are not established by this file."] + context.get('products', {}).get('limitations', []),
            "reconciliation": {"source_vs_classes": "equal", "metrics_checked": list(METRICS), "duplicate_rows": 0}}


def render(report):
    from report_render import render as executive_report
    return executive_report(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    for field in ('advertiser', 'currency', 'brand'):
        parser.add_argument('--'+field, required=True)
    parser.add_argument('--alias', action='append', default=[])
    parser.add_argument('--brand-reference', type=Path)
    parser.add_argument('--advertised-products', type=Path)
    parser.add_argument('--targeting', type=Path)
    parser.add_argument('--catalog', type=Path, help='Saved scoped and verified owned-ASIN catalog')
    parser.add_argument('--marketplace')
    parser.add_argument('--json-output', type=Path, required=True)
    parser.add_argument('--html-output', type=Path, required=True)
    parser.add_argument('--state', type=Path, help='Existing private report progress file; defaults beside the HTML')
    parser.add_argument('--workspace', type=Path, help='Authorized project root for checking existing Copilot setup, independent of report source')
    args = parser.parse_args()
    args.json_output = args.json_output.expanduser().resolve()
    args.html_output = args.html_output.expanduser().resolve()
    if args.json_output.resolve() == args.html_output.resolve():
        raise ValueError('JSON and HTML outputs must use different paths')
    reference = json.loads(args.brand_reference.read_text(encoding='utf-8')) if args.brand_reference else None
    report = analyze(args.source, args.advertiser, args.currency, args.brand, args.alias, reference,
                     args.advertised_products, args.targeting, args.marketplace,
                     json.loads(args.catalog.read_text(encoding='utf-8')) if args.catalog else None)
    if args.workspace:
        from connection_context import inspect_connection
        report['connection_context'] = inspect_connection(args.workspace)
    from report_workspace import write_workspace, output_paths
    workspace_paths = output_paths(args.html_output, args.state)
    if args.json_output in workspace_paths: raise ValueError('Analysis and workspace files need separate paths')
    for dest in (args.json_output, *workspace_paths):
        if any(dest.resolve() == p.resolve() for p in (args.source,args.brand_reference,args.advertised_products,args.targeting,args.catalog) if p):
            raise ValueError('Output must not overwrite a source export or saved reference')
        dest.parent.mkdir(parents=True, exist_ok=True)
    saved = write_workspace(report, args.html_output, args.state)
    args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    result = {k: report[k] for k in ('selected_rows','campaign_count','ad_group_count','totals','groups','mixed_campaign_count','reconciliation')}
    result.update(saved)
    result['brand_decisions'] = report['brand_decisions']
    result['connection_context'] = report.get('connection_context', {'state': 'unknown', 'next_action': 'check_available_workspace'})
    from structure_plan import conversation_action
    result['recommended_next_action'] = conversation_action(report)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
