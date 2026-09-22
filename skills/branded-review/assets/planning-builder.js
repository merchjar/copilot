(() => {
 const sessions=new Map();
 const allowed={brand_campaigns:['shared','category'],brand_ad_groups:['category','parent_family','single_asin','all_products'],brand_match:['phrase','exact_phrase'],defense_campaigns:['shared','category'],defense_pairing:['related','cross_sell','all_products']};
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const plural=(n,label)=>n+' '+label+(n===1?'':'s');
 const same=(a,b)=>Object.keys(allowed).every(k=>a?.[k]===b?.[k]);
 const valid=o=>o&&Object.keys(o).length===5&&Object.entries(allowed).every(([k,vs])=>vs.includes(o[k]))&&!(o.brand_ad_groups==='all_products'&&o.brand_campaigns!=='shared')&&!(o.defense_pairing==='all_products'&&o.defense_campaigns!=='shared');
 const draft=(d,o)=>({schema:'brand-planning-draft/1',scope:d.scope,baseline_sha256:d.baseline_sha256,simulation:d.simulation,options:o});
 const key=d=>'brand-plan:'+d.baseline_sha256;
 function restore(d){
  const candidates=[];
  try{const e=document.getElementById('planning-draft');if(e)candidates.push(JSON.parse(e.textContent));}catch{}
  try{const s=localStorage.getItem(key(d));if(s)candidates.push(JSON.parse(s));}catch{}
  return candidates.find(c=>c.schema==='brand-planning-draft/1'&&c.baseline_sha256===d.baseline_sha256&&JSON.stringify(c.scope)===JSON.stringify(d.scope)&&valid(c.options))?.options||d.options;
 }
 function products(d,asins,label){return `<details><summary>${esc(label)} · ${asins.length} ASINs</summary><ul class="plan-products">${asins.map(a=>`<li><code>${esc(a)}</code><span>${esc(d.products[a]?.title?.[0]||'Product name not supplied')}</span></li>`).join('')}</ul></details>`;}
 function render(r){
  const d=r._planData,o=sessions.get(key(d)),v=r._planView||'brand';
  r.querySelectorAll('[data-choice]').forEach(s=>s.value=o[s.dataset.choice]);r.querySelector('[data-plan-view]').value=v;
  r.querySelectorAll('[data-brand-control]').forEach(e=>e.hidden=v!=='brand');r.querySelectorAll('[data-defense-control]').forEach(e=>e.hidden=v!=='defense');
  const m=v==='brand'?d.brand_variants[o.brand_campaigns+':'+o.brand_ad_groups]:d.defense_variants[o.defense_campaigns+':'+o.defense_pairing];
  const separate=o[v==='brand'?'brand_campaigns':'defense_campaigns']==='category',cats=[...new Set(m.groups.map(g=>g.category))];
  if(!cats.includes(r._category))r._category=cats[0];
  const subset=m.groups.filter(g=>g.category===r._category);r._groupIndex=Math.min(r._groupIndex||0,Math.max(0,subset.length-1));const g=subset[r._groupIndex];
  r.querySelector('.planning-counts').innerHTML=`<div><strong>${m.pending?'To plan':m.campaigns||'To plan'}</strong><span>${v==='brand'?'Branded keyword campaigns':'Own-product defense campaigns'}</span></div><div><strong>${m.groups.length||'To plan'}</strong><span>Proposed ad groups</span></div><div><strong>${d.assigned}</strong><span>Products assigned · ${d.held.length} held</span></div>`;
  let note=v==='brand'?(separate?'Each category has its own campaign budget.':'Categories share one campaign budget.')+' All groups use the approved brand keywords. Category labels do not restrict search matching.':o.defense_pairing==='cross_sell'?'Choose compatible advertised products for each set of owned-ASIN targets. Copilot must review the actual pairings.':o.defense_pairing==='all_products'?'Every advertised product shares the full owned-ASIN target list. Review this wider set of combinations carefully.':'Start with products in the same category on both sides. Review relevance and compatibility before finalizing each group.';
  if(v==='brand'&&o.brand_ad_groups==='parent_family')note+=` ${d.parent_coverage.with_parent} products have valid parent data; ${d.parent_coverage.without_parent} do not. Missing parents stay separate.`;
  r.querySelector('.planning-guidance').textContent=note;
  const header=separate?`${m.campaigns} proposed campaigns, separate budgets`:`${d.brand} | ${v==='brand'?'Branded searches':'Own-product defense'}`;
  r.querySelector('.planning-diagram').innerHTML=m.pending?'<div class="grouping-needed"><b>Cross-sell pairings need review</b><p>Ask Copilot to propose compatible products and owned-ASIN targets. Campaign counts follow those groups.</p></div>':!g?'<p>Add or group your products to see their proposed campaigns.</p>':`<div class="plan-campaign-node"><span>NEW ${v==='brand'?'KEYWORD':'PRODUCT'} CAMPAIGN${m.campaigns===1?'':'S'}</span><b>${esc(header)}</b><small>${separate?'Select a campaign below':'One shared budget · '+m.groups.length+' ad groups'}</small></div><div class="plan-branches ${v==='defense'?'defense':''}">${cats.map(c=>`<button type="button" class="plan-category" data-category="${esc(c)}" aria-pressed="${c===r._category}"><small>${separate?'Campaign':'Product group'}</small><b>${esc(c)}</b><span>${plural(m.groups.filter(g=>g.category===c).length,'ad group')}</span></button>`).join('')}</div>`;
  const keywords=d.keywords.map(k=>`<span class="list-term">${esc(k.term)} <small>${o.brand_match==='phrase'?'Phrase':'Exact + Phrase'}</small></span>`).join('');r.querySelector('.planning-keywords').innerHTML=keywords;
  if(g){
   const picker=subset.length>1?`<label>Ad group to inspect<select data-ad-group>${subset.map((g,i)=>`<option value="${i}" ${i===r._groupIndex?'selected':''}>${esc(g.name)} · ${plural(g.advertised_asins.length,'product')}</option>`).join('')}</select></label>`:'';
   const targets=v==='brand'?`<div class="plan-targets brand"><span>KEYWORDS TARGETED</span><h3>Approved brand terms</h3><div class="list-terms">${keywords}</div><p>These keywords apply to the products in this ad group.</p></div>`:`<div class="plan-targets defense"><span>OWNED ASINs TARGETED</span><h3>${g.target_asins.length} proposed ASIN targets</h3>${products(d,g.target_asins,'Inspect target products')}<p>Specific owned-ASIN targets. Review with expanded targeting off.</p></div>`;
   r.querySelector('.planning-group-detail').innerHTML=`${picker}<h3>Ad group: ${esc(g.name)}</h3><div class="plan-pair">${targets}<div class="plan-ads"><span>PRODUCTS ADVERTISED</span><h3>${plural(g.advertised_asins.length,'product')} in the ads</h3>${products(d,g.advertised_asins,'Inspect advertised products')}<p>Targets and target bids are shared within this ad group.</p></div></div><p class="field-note">${v==='brand'?'Amazon decides which eligible products receive delivery. Grouping does not guarantee extra ad slots.':'Connections show proposed targeting. They do not guarantee delivery or product-page-only placements.'}</p>`;
  }else r.querySelector('.planning-group-detail').replaceChildren();
  r.querySelector('.planning-coverage').innerHTML=`<p>${d.known} known owned ASINs. ${d.assigned} assigned to product groups.</p>${d.held.length?products(d,d.held,'Products still needing review'):''}`;
  r.querySelector('.planning-status').textContent=(d.simulation?'Demo choices only. ':'')+(!same(o,d.options)?'Unsaved draft choices. Copy or save them for Copilot to update the plan.':'Saved proposal. Review settings before creating campaigns.');
  document.querySelectorAll('[data-plan-review-notice]').forEach(n=>n.hidden=same(o,d.options));
 }
 function refresh(d){document.querySelectorAll('.planning-builder').forEach(r=>{if(r._planData&&key(r._planData)===key(d))render(r);});}
 function init(r){
  if(r._planData)return;r._planData=JSON.parse(r.querySelector('.planning-data').textContent);const d=r._planData;
  if(!sessions.has(key(d)))sessions.set(key(d),{...restore(d)});
  r.addEventListener('change',e=>{
   if(e.target.matches('[data-plan-view]')){r._planView=e.target.value;r._category=null;r._groupIndex=0;render(r);return;}
   if(e.target.matches('[data-ad-group]')){r._groupIndex=Number(e.target.value);render(r);return;}
   const k=e.target.dataset.choice;if(!k)return;const o={...sessions.get(key(d)),[k]:e.target.value};
   if(k==='brand_ad_groups'&&o[k]==='all_products')o.brand_campaigns='shared';
   if(k==='brand_campaigns'&&o[k]==='category'&&o.brand_ad_groups==='all_products')o.brand_ad_groups='category';
   if(k==='defense_pairing'&&o[k]==='all_products')o.defense_campaigns='shared';
   if(k==='defense_campaigns'&&o[k]==='category'&&o.defense_pairing==='all_products')o.defense_pairing='related';
   if(!valid(o))return;sessions.set(key(d),o);r._groupIndex=0;try{localStorage.setItem(key(d),JSON.stringify(draft(d,o)));}catch{}refresh(d);
  });
  r.addEventListener('click',async e=>{
   const c=e.target.closest('[data-category]');if(c){r._category=c.dataset.category;r._groupIndex=0;render(r);return;}
   const o=sessions.get(key(d)),out=draft(d,o),status=r.querySelector('.planning-status');
   if(e.target.closest('[data-plan-reset]')){sessions.set(key(d),{...d.options});try{localStorage.removeItem(key(d));}catch{}refresh(d);return;}
   if(e.target.closest('[data-plan-copy]')){
    const text='Update my campaign plan with these choices. Keep existing campaigns running.\n\n'+JSON.stringify(out,null,2);
    try{await navigator.clipboard.writeText(text);status.textContent='Copied. Paste into the same Copilot conversation.';}catch{const pre=r.querySelector('.planning-copy-fallback');pre.hidden=false;pre.textContent=text;status.textContent='Copy the request below into Copilot.';}return;
   }
   if(e.target.closest('[data-plan-save]')){
    const clone=document.documentElement.cloneNode(true);clone.querySelectorAll('#planning-draft').forEach(n=>n.remove());
    const script=document.createElement('script');script.type='application/json';script.id='planning-draft';script.textContent=JSON.stringify(out).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');clone.querySelector('body').prepend(script);
    const url=URL.createObjectURL(new Blob(['<!doctype html>\n'+clone.outerHTML],{type:'text/html'})),a=document.createElement('a');a.href=url;a.download='brand-review-plan-draft.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status.textContent='Saved a draft copy. Give it to Copilot and ask: Update my campaign plan from this report.';
   }
  });render(r);
 }
 document.querySelectorAll('.planning-builder').forEach(init);
 new MutationObserver(rs=>rs.forEach(r=>r.addedNodes.forEach(n=>{if(n.nodeType!==1)return;if(n.matches('.planning-builder'))init(n);n.querySelectorAll('.planning-builder').forEach(init);}))).observe(document.body,{childList:true,subtree:true});
})();
