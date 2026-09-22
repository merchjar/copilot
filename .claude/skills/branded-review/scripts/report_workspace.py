"""One maintained performance, proposal and progress report. No API calls or writes."""
import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
from campaign_map import render as campaign_map
from transition_progress import sync_report, add_evidence, role_status
from structure_plan import needs_asins, structure_html, lists_html, build_structure


def scope_css(css, scope):
    """Scope the bundled simple stylesheet while preserving media and font rules."""
    out = []; pos = 0
    while pos < len(css):
        opening = css.find('{', pos)
        if opening < 0: break
        heading = css[pos:opening].strip(); depth = 1; closing = opening + 1
        while depth:
            if css[closing] == '{': depth += 1
            if css[closing] == '}': depth -= 1
            closing += 1
        body = css[opening+1:closing-1]
        if heading.startswith('@media'):
            out.append(heading+'{'+scope_css(body,scope)+'}')
        elif heading.startswith('@'):
            out.append(heading+'{'+body+'}')
        else:
            selectors = [scope if x.strip() in ('body', ':root') else scope+' '+x.strip() for x in heading.split(',')]
            out.append(','.join(selectors)+'{'+body+'}')
        pos = closing
    return ''.join(out)


def next_step(report, state):
    """Pick a display action from saved evidence; never advances or authorizes work."""
    available = bool(state.get('profile_id') or report.get('connection')) or report.get('connection_context',{}).get('state') in ('verified','configured_unverified')
    if needs_asins(report) and not state.get('waves') and not available:
        return (0, 'Add your product list', 'Upload your brand ASIN list or Amazon Ads’ Advertised product report to separate your own products from other ASIN traffic and size the campaign plan.', 'Help me add my ASIN list to this report.', '')
    if not state.get('profile_id'):
        connection = report.get('connection_context', {}).get('state', 'unknown')
        if report.get('connection') or connection in ('configured_unverified', 'verified'):
            return (0, 'Review your current campaigns', 'Use the available Merch Jar connection to check products, targets and existing negatives.', 'Review my current campaign setup.', '')
        if connection == 'unavailable':
            return (0, 'Connect Merch Jar', 'Connect Merch Jar so Copilot can review your current products, targets and negatives.', 'Help me connect Merch Jar and review my campaign setup.', 'https://merchjar.com/copilot/')
        if connection == 'setup_required':
            return (0, 'Finish your Merch Jar connection', 'Copilot is already available. Set up its connection to review the current account.', 'Help me finish my Merch Jar connection.', 'https://merchjar.com/copilot/')
        return (0, 'Check your available connection', 'Have Copilot check whether a Merch Jar connection is already available, then review your current campaigns.', 'Review my current campaign setup.', '')
    if state.get('plan_review_required') or not state.get('waves'):
        return (1, 'Review the detailed plan', 'Confirm which campaigns and products to use before preparing account changes.', 'Review the campaign plan with me.', '')
    roles = [wave[k] for wave in state['waves'] for k in ('branded', 'defense') if wave.get(k)]
    if not roles:
        return (1, 'Review the detailed plan', 'Choose the next product group and its campaign changes.', 'Review the campaign plan with me.', '')
    if any(role_status(r,False)['tone']=='ready' and not r.get('negatives_verified') for r in roles):
        return (3, 'Review ready exclusions', 'Review negatives only for coverage that has passed its delivery checks. Other traffic keeps running.', 'Review which negatives are ready to add.', '')
    if any(not r.get('created') for r in roles):
        return (2, 'Review the next campaign setup', 'Check the proposed products, bids and budgets. New campaigns are created paused after review.', 'Review the next campaign setup with me.', '')
    if any(not r.get('enabled_by_human') for r in roles):
        return (2, 'Review the paused campaigns', 'Review the created campaigns before enabling them. Keep the existing campaigns running.', 'Check the paused campaigns before I enable them.', '')
    if any(role_status(r,False)['tone'] not in ('ready','done') for r in roles):
        return (2, 'Check campaign delivery', 'Review fresh delivery and combined results before changing existing campaigns.', 'Check how the new campaigns are doing.', '')
    if any(not r.get('negatives_verified') for r in roles):
        return (3, 'Review the proposed negatives', 'Check the exact changes against current coverage before applying them.', 'Review which negatives are ready to add.', '')
    return (3, 'Check results after separation', 'Refresh combined results and confirm which traffic the campaigns now receive.', 'Check the results since the campaign changes.', '')


def progress_html(report, workspace):
    private = bool(report.get('privacy'))
    state = {} if private else (workspace or {})
    waves = state.get('waves', [])
    connected = bool(state.get('profile_id'))
    stamp = escape(state.get('checked_at') or 'No connected progress check saved')
    read_only = '<p class="progress-note">This connection is read-only. Planning and account checks are available; applying changes is unavailable here.</p>' if connected and state.get('read_only') else ''
    intro = '<h1>Setup &amp; progress</h1>'
    handoff = ''
    roadmap = ''
    if private:
        intro = '<h1>Setup and progress</h1><p class="lead">Account-specific progress is hidden in this privacy presentation.</p>'
    else:
        stage, title, body, prompt, link = next_step(report, state)
        setup_link = f'<a class="setup-link" href="{link}">Set up Merch Jar ↗</a>' if link else ''
        handoff = f'''<section class="next-action"><div class="next-action-summary"><p class="eyebrow">Your next step</p><h2>{title}</h2><p>{body}</p>{setup_link}</div><div class="request-box"><div><span>Ask Copilot</span><p id="copilot-request">{prompt}</p></div><button class="button" type="button" data-copy-request>Copy request</button></div><p class="copy-result" id="copy-result" role="status"></p></section>'''
        stages = ['Review account','Review plan','Create & check delivery','Negatives & results']
        steps = []
        for i, label in enumerate(stages):
            cls = 'current' if i == stage else 'later' if i > stage else 'previous'
            current = ' aria-current="step"' if i == stage else ''
            status = 'Current step' if i == stage else 'Later' if i > stage else 'Earlier step'
            steps.append(f'<li class="{cls}"{current}><span>{i+1}</span><div>{escape(label)}<small>{status}</small></div></li>')
        roadmap = '<ol class="setup-roadmap" aria-label="Setup sequence">'+''.join(steps)+'</ol>'
    cards = []
    for wave in waves:
        roles = []
        for kind, title in [('branded','Branded campaigns'), ('defense','Own-product defense')]:
            role = wave.get(kind, {})
            status = role_status(role, state.get('plan_review_required', True))
            obs = role.get('observation', {})
            metrics = ''
            if obs:
                metrics = f'<p class="check-data">{escape(str(obs["impressions"]))} impressions · {escape(obs["period_start"])} to {escape(obs["period_end"])}</p><p class="check-data">Source data through {escape(obs["data_through"])}</p>'
            roles.append(f'<article class="progress-card {kind}"><h3>{title}</h3><strong class="status {status["tone"]}">{escape(status["title"])}</strong>{metrics}<p>{escape(status["next"])}</p></article>')
        cards.append(f'<section class="wave"><h2>{escape(wave["name"])}</h2><div class="progress-grid">{"".join(roles)}</div></section>')
    rows = state.get('current_plan', [])
    detailed = ''
    if rows:
        body = ''.join(f'<tr><td>{escape(str(r.get("existing_campaign", "New campaign")))}</td><td>{escape(str(r.get("products", "To review")))}</td><td>{escape(str(r.get("change", "To review")))}</td><td>{escape(str(r.get("next_action", "To review")))}</td></tr>' for r in rows)
        detailed = '<section class="section"><h2>Saved rollout details</h2><p class="progress-note">These rows describe the saved rollout scope. They do not establish that the whole catalog is planned or covered. Review the product structure above before choosing the next group.</p><div class="table-scroll"><table><thead><tr><th>Campaign</th><th>Products</th><th>Proposed change</th><th>Next action</th></tr></thead><tbody>'+body+'</tbody></table></div></section>'
    baseline = ''
    snapshots = state.get('snapshots', [])
    if len(snapshots) > 1:
        first, latest = snapshots[0], snapshots[-1]
        baseline = f'<p class="progress-note">Original report: {escape(first["start"])} to {escape(first["end"])} ({escape(first["origin"])}). Current performance view: {escape(latest["start"])} to {escape(latest["end"])} ({escape(latest["origin"])}). Different periods are not a like-for-like performance comparison.</p>'
    from review_flow import render as review_flow
    board=review_flow(report,state)
    structure = '' if private else '<details class="review-structure"><summary>Review or change the proposed structure</summary>'+structure_html(report, state.get('product_groups'))+'</details>' + lists_html(report)
    return f'''<div class="intro"><div>{intro}</div></div>{read_only}{handoff}{roadmap}{board}{structure}{detailed}{''.join(cards)}
<div class="progress-note"><b>Last account check:</b> {stamp}. This report updates when Copilot runs a new check.</div>
<details class="progress-details"><summary>How progress checks work</summary><p>Impressions show that delivery has started. Review coverage and combined results before adding negatives.</p><p>Opening this report does not contact Amazon or refresh its data. Ask Copilot to check progress and update the same report.</p>{baseline}</details>'''


def compose(performance, report, workspace=None):
    map_html = campaign_map(None if report.get('privacy') else report, embedded=True, product_groups=(workspace or {}).get('product_groups'))
    css = re.search(r'<style>(.*?)</style>',map_html,re.S).group(1)
    plan = re.search(r'<main class="wrap">(.*?)</main>',map_html,re.S).group(1)
    plan_script = re.search(r'<script>(.*?)</script>',map_html,re.S).group(1)
    # Keep one main landmark and one global footer. The plan has its own scoped typography.
    plan = re.sub(r'<footer>.*?</footer>', '', plan, flags=re.S)
    products = report.get('context', {}).get('products', {})
    own = products.get('product_count', 0)
    coverage_note = 'Complete catalog as supplied.' if products.get('catalog_complete') else 'Full-catalog coverage still needs checking.'
    product_note = f'{own} owned ASINs identified. {coverage_note}' if own else 'Add your ASIN list to identify own-product traffic and refine the defense proposal.'
    plan = '<div class="proposal-status"><b>Included with your report</b><span>'+escape(product_note)+'</span></div>'+plan
    progress = progress_html(report,workspace)
    nav = '''<nav class="report-tabs" role="tablist" aria-label="Brand review steps"><button id="tab-performance" role="tab" aria-selected="true" aria-controls="performance-panel" data-report-tab="performance">1. Performance</button><button id="tab-plan" role="tab" aria-selected="false" aria-controls="plan-panel" data-report-tab="plan" tabindex="-1">2. Campaign plan</button><button id="tab-progress" role="tab" aria-selected="false" aria-controls="progress-panel" data-report-tab="progress" tabindex="-1">3. Setup &amp; progress</button></nav>'''
    outer_css = (Path(__file__).resolve().parents[1]/'assets/workspace.css').read_text(encoding='utf-8')
    outer_css += (Path(__file__).resolve().parents[1]/'assets/planning.css').read_text(encoding='utf-8')
    performance = performance.replace('</style>', scope_css(css,'#plan-panel')+outer_css+(Path(__file__).resolve().parents[1]/'assets/report-theme.css').read_text(encoding='utf-8')+'</style>', 1)
    performance = performance.replace('<main class="wrap">','<main class="wrap">'+nav+'<section id="performance-panel" role="tabpanel" aria-labelledby="tab-performance">',1)
    performance = performance.replace('</main>', f'</section><section id="plan-panel" role="tabpanel" aria-labelledby="tab-plan" hidden>{plan}</section><section id="progress-panel" role="tabpanel" aria-labelledby="tab-progress" hidden>{progress}</section></main>',1)
    script = '''const reportTabs=[...document.querySelectorAll('[data-report-tab]')];function showReportTab(name,focus=false){if(!reportTabs.some(t=>t.dataset.reportTab===name))name='performance';reportTabs.forEach(tab=>{const active=tab.dataset.reportTab===name;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;document.getElementById(tab.getAttribute('aria-controls')).hidden=!active;if(active&&focus)tab.focus()});history.replaceState(null,'','#'+name)}reportTabs.forEach((tab,index)=>{tab.addEventListener('click',()=>showReportTab(tab.dataset.reportTab));tab.addEventListener('keydown',event=>{let next=index;if(event.key==='ArrowRight')next=(index+1)%3;else if(event.key==='ArrowLeft')next=(index+2)%3;else if(event.key==='Home')next=0;else if(event.key==='End')next=2;else return;event.preventDefault();showReportTab(reportTabs[next].dataset.reportTab,true)})});document.querySelectorAll('[data-report-go]').forEach(button=>button.addEventListener('click',()=>showReportTab(button.dataset.reportGo,true)));showReportTab(location.hash.slice(1));'''
    copy_script = '''document.querySelectorAll('[data-copy-request]').forEach(button=>button.addEventListener('click',async()=>{const request=document.getElementById('copilot-request'),status=document.getElementById('copy-result');try{if(!navigator.clipboard)throw new Error('Clipboard unavailable');await navigator.clipboard.writeText(request.textContent);status.textContent='Copied. Paste this into your Copilot conversation.'}catch(error){const range=document.createRange();range.selectNodeContents(request);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent='Request selected. Copy it into your Copilot conversation.'}}));'''
    script += '''document.addEventListener('click',event=>{if(!event.target.closest('[data-edit-brand-lists]'))return;showReportTab('performance');const lists=document.getElementById('brand-lists');if(lists){lists.open=true;lists.scrollIntoView({behavior:'smooth',block:'start'});lists.querySelector('summary').focus()}});'''
    from report_interactions import enhance
    script += (Path(__file__).resolve().parents[1]/'assets/planning-builder.js').read_text(encoding='utf-8')
    return enhance(performance.replace('</body>', '<script>'+script+plan_script+copy_script+'</script></body>'), report)


def output_paths(html_output, state_path=None):
    html = Path(html_output).expanduser().resolve()
    path = Path(state_path).expanduser().resolve() if state_path else html.with_suffix('.workspace.json')
    baseline = path.with_name(path.stem+'.baseline.json')
    if len({html, path, baseline}) != 3: raise ValueError('Report, state and baseline need separate paths')
    return html, path, baseline


def write_workspace(report, html_output, state_path=None, evidence_path=None, workspace_root=None, product_groups=None):
    """Preserve the first analysis and update one HTML/state pair on each requested refresh."""
    from report_render import render
    from report_delivery import report_artifact
    presentation_report = report
    if workspace_root is not None:
        from connection_context import inspect_connection
        presentation_report = {**report, 'connection_context':inspect_connection(workspace_root)}
    html, path, baseline = output_paths(html_output, state_path)
    protected = {Path(report['source_path']).resolve()} if report.get('source_path') else set()
    if {html,path,baseline} & protected: raise ValueError('Output must not replace source data')
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    state = sync_report(report, state)
    if product_groups is not None:
        build_structure(report, product_groups)
        if state.get('product_groups') != product_groups: state['plan_review_required'] = True
        state['product_groups'] = product_groups
    if evidence_path:
        evidence_path = Path(evidence_path).resolve()
        if evidence_path in {html,path,baseline}: raise ValueError('Output must not replace evidence')
        state = add_evidence(state,json.loads(evidence_path.read_text(encoding='utf-8')),evidence_path.parent)
    baseline_text = json.dumps(report,ensure_ascii=False)
    if state.get('baseline_sha256'):
        if not baseline.exists() or hashlib.sha256(baseline.read_bytes()).hexdigest() != state['baseline_sha256']:
            raise ValueError('Saved baseline is missing or changed; preserve it before refreshing')
    elif baseline.exists():
        raise ValueError('Untracked baseline already exists; do not replace it')
    output = render(presentation_report,workspace=state)
    html.parent.mkdir(parents=True,exist_ok=True);path.parent.mkdir(parents=True,exist_ok=True)
    if not baseline.exists():
        baseline.write_text(baseline_text,encoding='utf-8')
        state['baseline_sha256'] = hashlib.sha256(baseline.read_bytes()).hexdigest()
    html.write_text(output,encoding='utf-8')
    path.write_text(json.dumps(state,indent=2),encoding='utf-8')
    from structure_plan import conversation_action
    action=conversation_action(presentation_report)
    if state.get('product_groups'):
        action={'action':'review_product_groups','say':'Show the proposed full product coverage and pending items, then use current configuration to choose the first rollout group. No automatic pilot selection.'}
    return {'report_artifact':report_artifact(html), 'state_path':str(path), 'snapshots':len(state['snapshots']),
            'recommended_next_action':action, 'account_changes':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis',required=True,type=Path)
    parser.add_argument('--html-output',required=True,type=Path)
    parser.add_argument('--state',type=Path)
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--workspace',type=Path,help='Currently authorized session root; refreshes setup guidance without new performance data or API calls')
    parser.add_argument('--product-groups',type=Path,help='Proposed full product grouping; no account changes or eligibility approval')
    args=parser.parse_args()
    if args.analysis.resolve() in set(output_paths(args.html_output,args.state)):
        raise ValueError('Do not overwrite the analysis input')
    grouping=json.loads(args.product_groups.read_text(encoding='utf-8')) if args.product_groups else None
    print(json.dumps(write_workspace(json.loads(args.analysis.read_text(encoding='utf-8')),args.html_output,args.state,args.evidence,args.workspace,grouping)))
