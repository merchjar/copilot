"""Saved transition evidence and conservative progress labels. Never changes ads."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from decimal import Decimal

REVIEW_CHECKS = ('products_verified', 'negative_coverage_verified', 'replacement_coverage_reviewed',
                 'observation_window_reviewed', 'combined_results_reviewed', 'rollback_agreed')


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None: raise ValueError('Progress timestamps need a timezone')
    return parsed


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def sync_report(report, state=None, now=None):
    now = now or datetime.now(timezone.utc)
    identity = {k: report[k] for k in ('account_id', 'brand', 'currency')}
    if state and (state.get('schema') != 'brand-review-workspace/1' or state.get('identity') != identity):
        raise ValueError('Workspace belongs to a different account, brand or currency')
    state = deepcopy(state) if state else {'schema':'brand-review-workspace/1', 'identity':identity,
        'snapshots':[], 'waves':[], 'profile_id':None, 'plan_revision':None, 'plan_review_required':True,
        'evidence_history':[], 'read_only':True}
    rules_hash = fingerprint({'brand':report.get('brand_reference', {}),
        'owned':report.get('context', {}).get('products', {}).get('owned_asins', [])})
    if state.get('rules_hash') != rules_hash:
        state['plan_review_required'] = True
        if state.get('product_groups'):
            state['prior_product_groups'] = state.pop('product_groups')
    state['rules_hash'] = rules_hash
    snapshot = {'source_sha256':report['source_sha256'], 'analysis_hash':fingerprint(report),
        'start':report['observed_start'], 'end':report['observed_end'],
        'origin':'Merch Jar' if report.get('connection') else 'Upload', 'saved_at':now.isoformat()}
    if not state['snapshots'] or state['snapshots'][-1]['analysis_hash'] != snapshot['analysis_hash']:
        state['snapshots'].append(snapshot)
    state['updated_at'] = now.isoformat()
    return state


def add_evidence(state, bundle, folder, now=None):
    """Check locally normalized evidence against saved receipts; not API authentication."""
    now = now or datetime.now(timezone.utc)
    if bundle.get('identity') != state['identity'] or bundle.get('rules_hash') != state['rules_hash']:
        raise ValueError('Progress evidence has different identity or brand/catalog rules')
    profile = bundle.get('profile_id')
    if not isinstance(profile, str) or not profile or (state.get('profile_id') and profile != state['profile_id']):
        raise ValueError('Progress evidence needs the same verified profile')
    if bundle.get('account_mapping_verified') is not True:
        raise ValueError('Verify the uploaded account to Merch Jar profile mapping')
    if not bundle.get('plan_revision'): raise ValueError('Progress evidence needs a plan revision')
    checked = timestamp(bundle['checked_at'])
    if checked > now: raise ValueError('Progress evidence is from the future')
    if state.get('checked_at') and checked < timestamp(state['checked_at']):
        raise ValueError('Older evidence cannot replace a newer account check')
    root = Path(folder).resolve()
    receipts = bundle.get('receipts', [])
    if not receipts: raise ValueError('Saved read or execution receipts are required')
    for receipt in receipts:
        path = (root / receipt['file']).resolve()
        if not path.is_relative_to(root) or not path.is_file(): raise ValueError('Receipt must stay in the evidence folder')
        if hashlib.sha256(path.read_bytes()).hexdigest() != receipt['sha256']:
            raise ValueError('Progress receipt hash differs')
        if receipt.get('profile_id') != profile: raise ValueError('Receipt profile differs')
    waves = deepcopy(bundle.get('waves', []))
    if len({wave['id'] for wave in waves}) != len(waves): raise ValueError('Duplicate wave identity')
    if {w['id'] for w in state.get('waves', [])} - {w['id'] for w in waves}:
        raise ValueError('Keep all saved product groups in each progress update')
    for wave in waves:
        if not wave.get('source_campaign_ids'): raise ValueError('Wave needs exact source campaigns')
        for role_name in ('branded', 'defense'):
            role = wave.get(role_name, {})
            for ref in role.get('receipt_indexes', []):
                if type(ref) is not int or ref < 0 or ref >= len(receipts): raise ValueError('Invalid receipt reference')
            if role and not role.get('receipt_indexes'): raise ValueError('Each saved role needs linked evidence')
            if role.get('created') and not role.get('campaign_ids'): raise ValueError('Created campaigns need exact IDs')
            if role.get('negatives_verified'):
                negatives = role.get('negative_readback', {})
                if not negatives.get('ids') or not negatives.get('source_campaign_ids') or negatives.get('complete') is not True:
                    raise ValueError('Verified negatives need exact IDs, source campaigns and complete readback')
                if set(negatives['source_campaign_ids']) - set(wave['source_campaign_ids']):
                    raise ValueError('Negative readback differs from the selected existing campaigns')
                if timestamp(negatives['checked_at']) > checked:
                    raise ValueError('Negative readback is newer than its bundle')
            observation = role.get('observation')
            if observation:
                if not role.get('campaign_ids'): raise ValueError('Delivery observation needs campaign IDs')
                for key in ('impressions', 'spend', 'sales'):
                    value = Decimal(str(observation[key]))
                    if not value.is_finite() or value < 0: raise ValueError('Invalid delivery metric')
                if timestamp(observation['checked_at']) > checked: raise ValueError('Observation is newer than its bundle')
                start = datetime.fromisoformat(observation['period_start']).date()
                end = datetime.fromisoformat(observation['period_end']).date()
                through = datetime.fromisoformat(observation['data_through']).date()
                if start > end: raise ValueError('Reversed delivery period')
                if through > checked.date() or end > through: raise ValueError('Future or incomplete source period')
    campaigns=deepcopy(bundle.get('current_campaigns',[]))
    if not isinstance(campaigns,list):raise ValueError('Current campaigns must be a list')
    campaign_ids=set()
    for campaign in campaigns:
        if not isinstance(campaign.get('id'),str) or not campaign['id'] or campaign['id'] in campaign_ids:
            raise ValueError('Current campaigns need unique exact IDs')
        campaign_ids.add(campaign['id'])
        if not campaign.get('name') or campaign.get('state') not in ('ENABLED','PAUSED','ARCHIVED'):
            raise ValueError('Current campaign state must come from the account read')
        refs=campaign.get('receipt_indexes',[])
        if not refs or any(type(i) is not int or i<0 or i>=len(receipts) for i in refs):
            raise ValueError('Current campaign status needs linked read receipts')
    new = deepcopy(state)
    new.update({'profile_id':profile, 'plan_revision':bundle['plan_revision'],
        'plan_review_required':bundle.get('plan_reviewed') is not True, 'checked_at':bundle['checked_at'],
        'read_only':bundle.get('read_only', True), 'waves':waves,
        'current_plan':deepcopy(bundle.get('current_plan', [])), 'current_campaigns':campaigns})
    new['evidence_history'].append(deepcopy(bundle))
    return new


def role_status(role, plan_review_required=True, now=None):
    now = now or datetime.now(timezone.utc)
    if not role or not role.get('created'):
        return {'title':'Not created yet', 'tone':'pending', 'next':'Review the products, targets and settings before creating this campaign.'}
    if role.get('negatives_verified'):
        stamp = role.get('negative_readback', {}).get('checked_at', 'the saved check')
        return {'title':'Negatives verified on saved check', 'tone':'done', 'next':f'Verified at {stamp}. Refresh combined results and the actual traffic split before further changes.'}
    if not role.get('enabled_by_human'):
        return {'title':'Created; waiting to be enabled', 'tone':'pending', 'next':'Review the paused campaign, then enable it when ready.'}
    obs = role.get('observation')
    if not obs or not obs.get('complete') or not obs.get('after_launch'):
        return {'title':'Waiting for a delivery check', 'tone':'pending', 'next':'Read the complete period after launch for these campaign IDs.'}
    age = (now - timestamp(obs['checked_at'])).total_seconds()
    data_age = (now.date() - datetime.fromisoformat(obs['data_through']).date()).days
    if age < 0 or age > 86400 or data_age > 1:
        return {'title':'Needs fresh data', 'tone':'pending', 'next':'Refresh the account check. The saved observation is too old for a next-action recommendation.'}
    if Decimal(str(obs['impressions'])) <= 0:
        return {'title':'No impressions yet', 'tone':'pending', 'next':'Keep existing campaigns running. Check campaign status, products, bids and budget.'}
    missing = [key for key in REVIEW_CHECKS if role.get('checks', {}).get(key) is not True]
    if plan_review_required or missing:
        return {'title':'Getting impressions; review still needed', 'tone':'active',
                'next':'Delivery has started. Review coverage, the observation period and combined results before adding negatives.', 'missing':missing}
    return {'title':'Ready to review the negatives', 'tone':'ready',
            'next':'Review the exact source changes and apply only after approval. This status does not authorize a change.'}
