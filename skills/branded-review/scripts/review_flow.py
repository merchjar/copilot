"""Existing evidence, proposed destinations and next actions without invented live status."""
from collections import defaultdict
from decimal import Decimal
from html import escape
from transition_progress import role_status


def render(report,state):
    if report.get('privacy'):return ''
    hist=defaultdict(lambda:{'spend':Decimal(0),'brand':Decimal(0),'name':''})
    for r in report.get('rows',[]):
        item=hist[str(r['campaign_id'])];item['name']=r.get('campaign_name') or str(r['campaign_id'])
        item['spend']+=Decimal(str(r.get('spend',0)))
        if r.get('category')=='brand_query':item['brand']+=Decimal(str(r.get('spend',0)))
    def card(name,badge,note,css=''):
        return f'<li class="{css}"><span class="evidence-label">{escape(badge)}</span><b>{escape(name)}</b><span>{escape(note)}</span></li>'
    current=state.get('current_campaigns',[])
    existing=[]
    if current:
        for c in current[:5]:
            label={'ENABLED':'Enabled at last check','PAUSED':'Paused at last check','ARCHIVED':'Archived at last check'}.get(c.get('state'),'Status not established')
            existing.append(card(c['name'],label,'Retain useful coverage; review before applying exclusions.'))
        intro=f'{len(current)} campaigns in the saved account check. Status reflects that check, not a live refresh.'
    else:
        for _,c in sorted(hist.items(),key=lambda pair:-pair[1]['brand'])[:3]:
            existing.append(card(c['name'],'Report history · current status unknown',
                f"{report.get('currency','')} {c['spend']:,.0f} spend · {c['brand']:,.0f} from branded searches"))
        intro=f'{len(hist)} campaigns appear in the search-term report. Showing the {min(3,len(hist))} with the most branded spend. A current account check is needed to confirm which are enabled.'
    proposed=[];actions=[]
    for wave in state.get('waves',[]):
        for kind,label in [('branded','Branded searches'),('defense','Own-product defense')]:
            role=wave.get(kind)
            if role is None:continue
            status=role_status(role,state.get('plan_review_required',True))
            title=wave['name']+' · '+label
            ids=role.get('campaign_ids',[])
            proposed.append(card(title,status['title'],('Campaign IDs: '+', '.join(ids)) if ids else 'Proposed destination; no created campaign recorded.'))
            actions.append(card(title,'Next action',status['next'],'next-step-card'))
    if not proposed:
        proposed=[card('Branded searches','Proposed · not created','Approved brand Phrase keywords in the grouping you choose.'),
                  card('Own-product defense','Proposed · not created','Relevant advertised products paired with selected owned ASINs.')]
        actions=[card('Review the structure and product lists','Next action','Save your choices, then have Copilot check current campaigns, products, targets and negatives.','next-step-card')]
    summary='<details><summary>Show remaining campaigns from the saved check</summary><ul>'+''.join(card(c['name'],c.get('state','Unknown'),'Saved account state') for c in current[5:])+'</ul></details>' if len(current)>5 else ''
    source='Simulated account evidence' if report.get('simulation') else 'Saved evidence'
    return f'''<section class="transition-board"><h2>Your campaign transition</h2><p>{escape(intro)}</p><p class="planning-status" data-plan-review-notice hidden>Your structure choices have changed. Review the revised plan before using these saved next actions.</p><div class="transition-columns"><div class="transition-lane"><h3>Existing campaigns</h3><ul>{''.join(existing)}</ul>{summary}<p class="field-note">Keep useful non-brand, discovery and other-ASIN coverage.</p></div><div class="transition-lane"><h3>New campaign coverage</h3><ul>{''.join(proposed)}</ul></div><div class="transition-lane"><h3>Next proposed actions</h3><ul>{''.join(actions)}</ul></div></div><p class="field-note">{source}. Brand keyword exclusions and owned-ASIN exclusions have separate delivery reviews. Impressions alone do not authorize either change.</p></section>'''
