(()=>{
 const source=document.getElementById('brand-list-data');if(!source)return;
 const context=JSON.parse(source.textContent),base=context.baseline;
 const clone=value=>JSON.parse(JSON.stringify(value));
 const key='merchjar-brand-list-draft:'+context.baseline_sha256+':'+context.scope.account_id;
 const byId=id=>document.getElementById(id),status=byId('list-status');
 const aliases=byId('brand-aliases'),asins=byId('owned-asins'),complete=byId('catalog-complete');
 let draft=clone(base),storage=true;
 try{const saved=JSON.parse(localStorage.getItem(key)||'null');if(saved&&saved.brand_reference&&Array.isArray(saved.owned_asins)){draft=saved;status.textContent='Your draft is restored. The report still uses the last applied lists.'}}catch{storage=false}
 const embedded=document.getElementById('brand-list-draft');
 if(embedded){try{
  const saved=JSON.parse(embedded.textContent);
  if(saved.schema!=='brand-review-preferences-draft/2'||saved.baseline_sha256!==context.baseline_sha256||JSON.stringify(saved.scope)!==JSON.stringify(context.scope))throw Error('Draft does not match');
  draft=clone(base);
  for(const [field,container,property] of [['names',draft.brand_reference,'aliases'],['asins',draft,'owned_asins'],['rules',draft.brand_reference,'rules']]){
   const removed=saved.changes['remove_'+field]||[],added=saved.changes['add_'+field]||[];
   container[property]=(container[property]||[]).filter(value=>!removed.some(x=>JSON.stringify(x)===JSON.stringify(value))).concat(added);
  }
  if('catalog_complete' in saved.changes)draft.catalog_complete=saved.changes.catalog_complete;
  status.textContent='This saved report contains your draft changes. Its figures still use the original lists.';
 }catch{status.textContent='The saved draft could not be loaded. Ask Copilot to check this file before applying changes.'}}
 const lines=value=>[...new Set(value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean))];
 const asinLines=value=>[...new Set(value.toUpperCase().split(/[\s,;]+/).filter(Boolean))].sort();
 function option(value,label){const o=document.createElement('option');o.value=value;o.textContent=label;return o}
 function renderRules(){
  const root=byId('brand-rules');root.replaceChildren();
  for(const [index,rule] of (draft.brand_reference.rules||[]).entries()){
   const row=document.createElement('div');row.className='editable-rule';
   const term=document.createElement('input');term.value=rule.term;term.setAttribute('aria-label','Rule term '+(index+1));
   const match=document.createElement('select');match.setAttribute('aria-label','Match for rule '+(index+1));
   [['phrase','Contains whole phrase'],['exact','Exact search only'],['contains_compact','Joined spelling']].forEach(([v,t])=>match.append(option(v,t)));match.value=rule.match||'phrase';
   const state=document.createElement('select');state.setAttribute('aria-label','Classification for rule '+(index+1));
   [['approved','Include as branded'],['proposed','Hold for review'],['rejected','Exclude from branded']].forEach(([v,t])=>state.append(option(v,t)));state.value=rule.status;
   const remove=document.createElement('button');remove.type='button';remove.className='remove-rule';remove.textContent='Remove';remove.setAttribute('aria-label','Remove rule '+(index+1));
   term.addEventListener('input',()=>{rule.term=term.value;changed()});match.addEventListener('change',()=>{rule.match=match.value;changed()});state.addEventListener('change',()=>{rule.status=state.value;changed()});
   remove.addEventListener('click',()=>{draft.brand_reference.rules.splice(index,1);renderRules();changed()});
   row.append(term,match,state,remove);root.append(row);
  }
  if(!root.children.length){const p=document.createElement('p');p.className='field-note';p.textContent='No additional spelling rules.';root.append(p)}
 }
 function fill(){aliases.value=(draft.brand_reference.aliases||[]).join('\n');asins.value=draft.owned_asins.join('\n');complete.checked=draft.catalog_complete;renderRules();validate()}
 function read(){draft.brand_reference.aliases=lines(aliases.value);draft.owned_asins=asinLines(asins.value);draft.catalog_complete=complete.checked;return clone(draft)}
 function validate(){
  const current=read(),errors=[];
  if(!current.brand_reference.aliases.some(a=>a.toLowerCase()===context.scope.brand.toLowerCase()))errors.push('Keep the primary brand name in the list. Ask Copilot to change the brand itself.');
  const invalid=current.owned_asins.filter(a=>!/^(?:B[A-Z0-9]{9}|[0-9]{10})$/.test(a));
  if(invalid.length)errors.push('Check these ASINs: '+invalid.slice(0,5).join(', ')+'. Use the full Amazon product identifier.');
  if(current.catalog_complete&&!current.owned_asins.length)errors.push('Add your ASINs before marking this as the full list.');
  if((current.brand_reference.rules||[]).some(r=>!r.term.trim()))errors.push('Enter a term for each rule, or remove the blank row.');
  byId('asin-list-count').textContent='('+current.owned_asins.length+')';byId('list-errors').textContent=errors.join(' ');
  for(const id of ['copy-list-changes','download-list-changes','save-report-changes'])byId(id).disabled=!!errors.length;
  return !errors.length;
 }
 function changed(){
  validate();byId('list-copy-fallback').hidden=true;
  try{localStorage.setItem(key,JSON.stringify(draft))}catch{storage=false}
  status.textContent=storage?'Draft saved in this browser. Report figures have not changed.':'Draft kept for this visit. Download changes to keep a copy.';
 }
 for(const input of [aliases,asins,complete])input.addEventListener('input',changed);
 byId('add-brand-rule').addEventListener('click',()=>{(draft.brand_reference.rules??=[]).push({term:'',match:'phrase',status:'proposed',source:'Report editor draft'});renderRules();changed();byId('brand-rules').lastElementChild.querySelector('input').focus()});
 const exceptions=base.brand_reference.exceptions||[];
 if(exceptions.length){const p=document.createElement('p');p.className='field-note';p.textContent='Saved search exceptions are preserved: '+exceptions.map(r=>r.term+' ('+r.category+')').join(', ')+'. Ask Copilot to change these exceptions.';byId('saved-exceptions').append(p)}
 function payload(){
  const proposed=read(),minus=(a,b)=>a.filter(x=>!b.some(y=>JSON.stringify(x)===JSON.stringify(y))),changes={};
  for(const [field,after,before] of [['names',proposed.brand_reference.aliases,base.brand_reference.aliases||[]],['asins',proposed.owned_asins,base.owned_asins],['rules',proposed.brand_reference.rules||[],base.brand_reference.rules||[]]]){
   const added=minus(after,before),removed=minus(before,after);
   if(added.length)changes['add_'+field]=added;if(removed.length)changes['remove_'+field]=removed;
  }
  if(proposed.catalog_complete!==base.catalog_complete)changes.catalog_complete=proposed.catalog_complete;
  return {schema:'brand-review-preferences-draft/2',simulation:context.simulation,status:'draft_not_applied',scope:context.scope,marketplace:context.marketplace,
   baseline_sha256:context.baseline_sha256,report_source_sha256:context.report_source_sha256,
   changes};
 }
 byId('copy-list-changes').addEventListener('click',async()=>{
  if(!validate())return;
  const data=payload();
  const text=(context.simulation?'This is a fictional simulation. Do not apply it to a real account.\n\n':'')+
   'Update my report and saved brand lists with these changes.\n\n'+JSON.stringify(data,null,2);
  try{await navigator.clipboard.writeText(text);status.textContent='Copied. Paste into Copilot to apply the changes and refresh your report.'}
  catch{const fallback=byId('list-copy-fallback');fallback.value=text;fallback.hidden=false;fallback.focus();fallback.select();status.textContent='Changes selected below. Copy them into your Copilot conversation.'}
 });
 byId('save-report-changes').addEventListener('click',()=>{
  if(!validate())return;
  const root=document.documentElement.cloneNode(true);
  root.querySelectorAll('#brand-list-draft,.saved-draft-notice').forEach(node=>node.remove());
  const data=document.createElement('script');data.id='brand-list-draft';data.type='application/json';
  data.textContent=JSON.stringify(payload()).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
  root.querySelector('#brand-list-data').after(data);
  const note=document.createElement('div');note.className='saved-draft-notice';note.setAttribute('role','status');
  note.textContent='Draft changes included. Figures have not been recalculated. Give this file to Copilot and say: “Apply the brand-list changes saved in this report.”';
  root.querySelector('body').prepend(note);
  const blob=new Blob(['<!DOCTYPE html>\n'+root.outerHTML],{type:'text/html'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=context.simulation?'fictional-report-with-changes.html':'brand-report-with-changes.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  status.textContent='Saved a report copy with your changes. Give it to Copilot and say: “Apply the brand-list changes saved in this report.”';
 });
 byId('download-list-changes').addEventListener('click',()=>{
  if(!validate())return;
  const blob=new Blob([JSON.stringify(payload(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=context.simulation?'fictional-brand-list-changes.json':'brand-list-changes.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  status.textContent='Changes downloaded. Attach that file to Copilot and ask it to update your brand lists.';
 });
 byId('reset-list-draft').addEventListener('click',()=>{draft=clone(base);try{localStorage.removeItem(key)}catch{}fill();byId('list-copy-fallback').hidden=true;status.textContent='Draft reset. Showing the lists used in this report.'});
 fill();
})();
