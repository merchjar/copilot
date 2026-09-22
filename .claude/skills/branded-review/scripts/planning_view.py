"""Interactive proposed structures using the same data as the saved plan."""
from html import escape
import json
from planning_options import architecture, baseline, scope


def render(report, grouping, structure):
    s=structure;grouping=grouping or {'groups':[]}
    variants={}
    for campaigns in ('shared','category'):
        for mode in ('category','parent_family','single_asin','all_products'):
            if mode=='all_products' and campaigns=='category':continue
            opt={**s['options'],'brand_campaigns':campaigns,'brand_ad_groups':mode}
            a=architecture(s,opt,grouping)
            variants[campaigns+':'+mode]={'campaigns':a['proposed_branded_campaigns'],'groups':a['branded_ad_groups']}
    defense={}
    for campaigns in ('shared','category'):
        for pairing in ('related','cross_sell','all_products'):
            if pairing=='all_products' and campaigns=='category':continue
            a=architecture(s,{**s['options'],'defense_campaigns':campaigns,'defense_pairing':pairing},grouping)
            defense[campaigns+':'+pairing]={'campaigns':a['proposed_defense_campaigns'],'groups':a['defense_ad_groups'],
                                          'pending':a['defense_pairing_pending']}
    payload={'schema':'brand-planning-view/1','scope':scope(report),'baseline_sha256':baseline(report,grouping),
             'simulation':bool(report.get('simulation')),'options':s['options'],'brand_variants':variants,'defense_variants':defense,
             'keywords':s['shared_brand_keywords'],'products':s['product_details'],
             'held':s['held_products'],'known':s['known_products'],'assigned':s['assigned_products'],
             'parent_coverage':s['parent_coverage'],'brand':report['brand']}
    encoded=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    if not s['known_products']:
        from structure_plan import asin_help
        missing='<div class="grouping-needed"><b>Add your ASIN list to fill in this plan.</b>'+asin_help()+'</div>'
    elif not s['groups']:
        missing='<div class="grouping-needed"><b>Your products need grouping.</b><p>Ask Copilot to group your products from their names, then compare the structures here.</p></div>'
    else:missing=''
    return f'''<section class="structure-plan planning-builder"><h2>Choose your proposed campaign structure</h2>
<p>Create new branded coverage and separate own-product defense. Keep existing campaigns running while replacements get established.</p>
<script type="application/json" class="planning-data">{encoded}</script>
<div class="planning-controls"><label>Traffic<select data-plan-view><option value="brand">Brand searches</option><option value="defense">Own-product defense</option></select></label>
<label data-brand-control>Campaign budgets<select data-choice="brand_campaigns"><option value="shared">One campaign, shared budget</option><option value="category">Separate campaign per category</option></select></label>
<label data-brand-control>Products in each ad group<select data-choice="brand_ad_groups"><option value="category">Related product category</option><option value="parent_family">Related variations</option><option value="single_asin">One advertised ASIN</option><option value="all_products">All products together</option></select></label>
<label data-defense-control hidden>Campaign budgets<select data-choice="defense_campaigns"><option value="shared">One defense campaign</option><option value="category">Separate campaign per group</option></select></label>
<label data-defense-control hidden>Ads and ASIN targets<select data-choice="defense_pairing"><option value="related">Related products in the same category</option><option value="cross_sell">Selected cross-sell groups</option><option value="all_products">Whole catalog on both sides</option></select></label></div>
<div class="planning-guidance"></div><div class="planning-counts" aria-live="polite"></div>
<div class="planning-diagram"></div><div class="planning-group-detail"></div>
<details class="planning-advanced"><summary>Brand keywords and match types</summary><p>Use approved brand names and spellings. Category labels organize products; they do not narrow which searches match. Distinctive product-line terms need their own relevant product selection.</p><label>Match types<select data-choice="brand_match"><option value="phrase">Phrase</option><option value="exact_phrase">Exact and Phrase</option></select></label><div class="planning-keywords"></div><p>Phrase can match searches with words before or after the brand. Exact adds a separate bidding choice. Reporting spelling rules do not automatically create Amazon keywords.</p></details>
<div class="planning-coverage"></div>{missing}
<div class="planning-handoff"><p class="planning-status" role="status">Saved proposal. Review settings before creating campaigns.</p><div class="planning-actions"><button type="button" class="button" data-plan-copy>Copy choices for Copilot</button><button type="button" class="quiet-button" data-plan-save>Save report with choices</button><button type="button" class="quiet-button" data-plan-reset>Reset choices</button></div><pre class="planning-copy-fallback" hidden></pre><p>Changes here are a draft. Copilot saves the plan and reviews current products, targets, negatives, bids and budgets before account changes.</p></div>
</section>'''
