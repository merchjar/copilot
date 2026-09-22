(()=>{
 const search=document.querySelector('#campaign-search');if(!search)return;
 const buttons=[...document.querySelectorAll('[data-campaign-filter]')];let mode='all',limit=10;
 const rows=[...document.querySelectorAll('[data-campaign]')],more=document.getElementById('more-campaigns'),sort=document.getElementById('campaign-sort');
 function updateInventory(){
  const q=search.value.trim().toLowerCase();let visible=0,total=0;
  rows.sort((a,b)=>Number(b.dataset[sort.value])-Number(a.dataset[sort.value])||a.dataset.campaign.localeCompare(b.dataset.campaign));
  rows.forEach(row=>{
   row.parentNode.append(row);
   const match=row.dataset.campaign.includes(q)&&(mode==='all'||row.dataset.mixed==='true');
   if(match)total++;
   const show=match&&visible<limit;row.hidden=!show;if(show)visible++;
  });
  buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.campaignFilter===mode)));
  document.querySelector('#visible-count').textContent=visible+' of '+total+' matching campaigns shown';
  more.hidden=visible>=total;more.textContent='Show next '+Math.min(10,total-visible)+' campaigns';
  const table=document.querySelector('#inventory .table-scroll');if(table)table.scrollTop=0;
  let empty=document.getElementById('inventory-empty');
  if(!empty){empty=document.createElement('p');empty.id='inventory-empty';empty.className='note';table.after(empty)}
  empty.textContent=visible?'':'No campaigns match. Clear the search or show all campaigns.';empty.hidden=!!visible;
 }
 search.addEventListener('input',()=>{limit=10;updateInventory()});
 sort.addEventListener('change',()=>{limit=10;updateInventory()});
 more.addEventListener('click',()=>{limit+=10;updateInventory()});
 buttons.forEach(button=>button.addEventListener('click',()=>{mode=button.dataset.campaignFilter;limit=10;updateInventory()}));
 updateInventory();
})();
