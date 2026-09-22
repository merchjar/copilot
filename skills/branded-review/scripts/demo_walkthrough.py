"""Fictional scenes rendered by the real progress rules, never saved as account evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import report_workspace
from transition_progress import REVIEW_CHECKS, role_status

ASSETS = Path(__file__).resolve().parents[1]/'assets'


def scenes(report):
    now = datetime.now(timezone.utc)
    pilot=report.get('demo_pilot', {'source_campaign':'Backpack discovery','products':'Daypacks',
                                  'branded_campaign':'New branded campaign','defense_campaign':'New own-product defense'})
    day = (now-timedelta(days=1)).date().isoformat()
    observation = {'impressions':0,'spend':'0','sales':'0','period_start':day,'period_end':day,
                   'data_through':day,'checked_at':now.isoformat(),'complete':True,'after_launch':True}
    empty = {'waves':[], 'plan_review_required':True, 'read_only':False,
             'product_groups':report.get('demo_product_groups')}
    items = [('Report ready', 'Start with an uploaded report. The visual proposal is already available.', deepcopy(empty))]
    empty.update({'profile_id':'fictional-demo-profile', 'checked_at':now.isoformat(),
                  'current_campaigns':[{'id':'fictional-source','name':pilot['source_campaign'],'state':'ENABLED'}]})
    items.append(('Account reviewed', 'Copilot has reviewed the fictional account. The detailed changes still need review.',deepcopy(empty)))
    empty.update({'plan_review_required':False,'current_plan':[
        {'existing_campaign':pilot['source_campaign'],'products':pilot['products'],'change':'Keep running; retain for non-brand searches','next_action':'Wait for replacement coverage before adding negatives'},
        {'existing_campaign':pilot['branded_campaign'],'products':pilot['products'],'change':'Create a separate branded campaign','next_action':'Review products, bids and budget'},
        {'existing_campaign':pilot['defense_campaign'],'products':'Owned product ASINs','change':'Create a separate defense campaign','next_action':'Review products, bids and budget'}],
        'waves':[{'id':'fictional-product-group','name':pilot['products'],'branded':{'created':False},'defense':{'created':False}}]})
    items.append(('Plan reviewed','The plan keeps discovery running and proposes separate branded and defense campaigns.',deepcopy(empty)))
    for kind in ('branded','defense'):
        empty['waves'][0][kind]={'created':True,'campaign_ids':['fictional-'+kind], 'enabled_by_human':False}
    for row in empty['current_plan'][1:]:
        row['change']='Created paused'
        row['next_action']='Human reviews and enables when ready'
    items.append(('Created paused','Campaigns are paused for review. Creation does not mean they are enabled.',deepcopy(empty)))
    for kind in ('branded','defense'):
        empty['waves'][0][kind].update({'enabled_by_human':True,'observation':deepcopy(observation)})
    for row in empty['current_plan'][1:]:
        row['change']='Enabled by the human'
        row['next_action']='Check delivery and replacement coverage'
    items.append(('No impressions','In this scene the human has enabled the campaigns, but delivery has not started. Existing campaigns keep running.',deepcopy(empty)))
    empty['waves'][0]['branded']['observation'].update({'impressions':1200,'spend':'18','sales':'160'})
    items.append(('First impressions','Branded delivery has started. Impressions alone do not clear the negatives; defense is still waiting.',deepcopy(empty)))
    empty['waves'][0]['branded']['checks']={k:True for k in REVIEW_CHECKS}
    items.append(('Defense still waiting','Branded coverage has been reviewed. Its status does not clear the own-product exclusions. Defense needs its own evidence.',deepcopy(empty)))
    empty['waves'][0]['defense']['observation'].update({'impressions':850,'spend':'12','sales':'90'})
    empty['waves'][0]['defense']['checks']={k:True for k in REVIEW_CHECKS}
    empty['current_plan'][0]['next_action']='Review the exact proposed negatives before approval'
    for row in empty['current_plan'][1:]:
        row['next_action']='Coverage reviewed; continue monitoring delivery'
    items.append(('Review negatives','Both destinations have reviewed coverage, an appropriate observation period, combined results and a rollback plan. The exact negatives still need approval.',deepcopy(empty)))
    for kind in ('branded','defense'):
        empty['waves'][0][kind].update({'negatives_verified':True,'negative_readback':{'checked_at':now.isoformat()}})
    empty['current_plan'][0]['change']='Retained for non-brand traffic; approved exclusions verified'
    empty['current_plan'][0]['next_action']='Refresh combined results and check the traffic split'
    items.append(('Changes verified','This fictional scene represents approved changes followed by readback. Existing campaigns remain in use for non-brand traffic; results still need follow-up.',deepcopy(empty)))
    stale=deepcopy(items[7][2])
    for kind in ('branded','defense'):
        stale['waves'][0][kind]['observation']['checked_at']=(now-timedelta(days=3)).isoformat()
        stale['waves'][0][kind]['observation']['data_through']=(now-timedelta(days=3)).date().isoformat()
    for row in stale['current_plan']:
        row['next_action']='Refresh account data before making a change'
    items.append(('Data is stale','Old results cannot clear a new change. Copilot needs a fresh account check.',stale))
    # Exercise production status logic at a fixed clock so the walkthrough stays reproducible.
    original = report_workspace.role_status
    try:
        report_workspace.role_status = lambda role, required: role_status(role, required, now)
        result=[]
        for label, explanation, state in items:
            html=report_workspace.progress_html(report,state)
            html=html.replace('<b>Last account check:</b>', '<b>Simulated account check:</b>')
            result.append((label, explanation, html))
        return result
    finally:
        report_workspace.role_status = original


def build(html, report):
    items=scenes(report)
    controls=''.join(f'<button type="button" data-demo-scene="{i}" aria-pressed="{str(i==0).lower()}">{i+1}. {escape(label)}</button>' for i,(label,_,_) in enumerate(items))
    templates=''.join(f'<template id="demo-scene-{i}"><p class="demo-explanation">{escape(explanation)}</p>{body}</template>' for i,(_,explanation,body) in enumerate(items))
    panel=f'''<section id="progress-panel" role="tabpanel" aria-labelledby="tab-progress" hidden><div class="demo-controls"><h2>Walk through the setup</h2><p>Real performance data with fictional names. Jump to a scene or use Next scene to explore simulated setup progress.</p><div class="demo-scenes">{controls}</div><div class="demo-navigation"><button type="button" class="quiet-button" id="demo-back">Previous</button><button type="button" class="quiet-button" id="demo-next">Next scene →</button><span id="demo-position" role="status"></span></div></div><div id="demo-content"></div>{templates}</section>'''
    start=html.index('<section id="progress-panel"')
    end=html.index('</main>',start)
    html=html[:start]+panel+html[end:]
    html=html.replace('<body>','<body><aside class="simulation-banner"><strong>DEMO</strong>Anonymized performance data. Fictional identities; setup progress simulated.</aside>',1)
    return html.replace('</body>','<script>'+(ASSETS/'simulation.js').read_text(encoding='utf-8')+'</script></body>')


def main():
    import argparse
    import json
    from anonymized_demo import make_demo, verify_html
    from report_render import render
    from report_delivery import report_artifact
    p=argparse.ArgumentParser(description='Create a separate anonymized walkthrough with simulated progress. No account calls.')
    p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--html-output',type=Path,required=True)
    p.add_argument('--product-groups',type=Path,help='Optional private proposed grouping; identities will be replaced')
    a=p.parse_args();source=a.analysis.resolve();dest=a.html_output.resolve()
    if source==dest or dest.exists():raise ValueError('Choose a new, separate demo output; existing files are preserved')
    report=json.loads(source.read_text(encoding='utf-8-sig'))
    grouping=json.loads(a.product_groups.read_text(encoding='utf-8')) if a.product_groups else None
    demo=make_demo(report,grouping)
    html=build(render(demo,{'product_groups':demo.get('demo_product_groups')}),demo)
    checked=verify_html(report,html)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8') as out:out.write(html)
    print(json.dumps({'report_artifact':report_artifact(dest),'validation':checked,'account_changes':False}))


if __name__=='__main__':main()
