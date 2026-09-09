"""Offline monetary preflight for an agent-prepared plan, never an API writer."""
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def money(value, quantum):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0 or amount % quantum:
            raise ValueError('Amounts must be positive and use supported currency precision')
        return amount
    except InvalidOperation as error:
        raise ValueError('Invalid monetary amount') from error


def validate(plan):
    # Other marketplaces require a current verified limits object. No FX guessing.
    if (plan['marketplace'], plan['currency'], plan['ad_product']) == ('DE', 'EUR', 'SPONSORED_PRODUCTS'):
        limits = dict(quantum='0.01', min_budget='1.00', min_bid='0.02', max_bid='1000')
    else:
        limits = plan.get('verified_limits')
        if not limits or not limits.get('source') or not limits.get('checked_at'):
            raise ValueError('Current marketplace-specific limits are required')
    quantum = Decimal(limits['quantum'])
    if not quantum.is_finite() or quantum <= 0:
        raise ValueError('Invalid currency precision')
    minimum_budget = money(limits['min_budget'], quantum)
    minimum_bid = money(limits['min_bid'], quantum)
    maximum_bid = money(limits['max_bid'], quantum)
    if minimum_bid > maximum_bid:
        raise ValueError('Invalid bid limits')
    campaigns = plan['campaigns']
    if not campaigns:
        raise ValueError('No campaigns in plan')
    if plan.get('budget_basis') not in ('batch-total', 'per-campaign', 'per-product'):
        raise ValueError('Resolve budget scope before approval')
    total = Decimal('0')
    for campaign in campaigns:
        budget = money(campaign['daily_budget'], quantum)
        if budget < minimum_budget:
            raise ValueError(f'Campaign budget is below {minimum_budget}; minimum batch total is {minimum_budget * len(campaigns)}')
        total += budget
        for bid in [campaign['default_bid'], *campaign.get('target_bids', [])]:
            amount = money(bid, quantum)
            if not minimum_bid <= amount <= maximum_bid:
                raise ValueError(f'Bid is outside {minimum_bid}–{maximum_bid}')
    if total != money(plan['approved_configured_total'], quantum):
        raise ValueError('Campaign allocations do not match the approved configured total')
    return dict(campaign_count=len(campaigns), configured_total=str(total), currency=plan['currency'],
                monetary_preflight='passed', live_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(json.loads(args.plan.read_text(encoding='utf-8'))), indent=2))
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'Preflight failed: {error}\n')
