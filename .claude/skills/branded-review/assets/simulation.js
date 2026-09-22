(()=>{
 const root=document.getElementById('demo-content');if(!root)return;
 const buttons=[...document.querySelectorAll('[data-demo-scene]')];let current=0;
 function show(index){
  current=Math.max(0,Math.min(buttons.length-1,index));root.replaceChildren(document.getElementById('demo-scene-'+current).content.cloneNode(true));
  buttons.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===current)));
  document.getElementById('demo-back').disabled=current===0;document.getElementById('demo-next').disabled=current===buttons.length-1;
  document.getElementById('demo-position').textContent='Scene '+(current+1)+' of '+buttons.length+' · '+buttons[current].textContent.replace(/^\d+\. /,'');
 }
 buttons.forEach((b,i)=>b.addEventListener('click',()=>show(i)));
 document.getElementById('demo-back').addEventListener('click',()=>show(current-1));document.getElementById('demo-next').addEventListener('click',()=>show(current+1));
 root.addEventListener('click',async event=>{
  if(!event.target.closest('[data-copy-request]'))return;
  const request=root.querySelector('#copilot-request'),status=root.querySelector('#copy-result');
  const text='In this fictional simulation, '+request.textContent[0].toLowerCase()+request.textContent.slice(1);
  try{await navigator.clipboard.writeText(text);status.textContent='Copied a simulation request. This does not perform an account action.'}
  catch{const range=document.createRange();range.selectNodeContents(request);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent='Request selected. This is a fictional walkthrough.'}
 });
 show(0);
})();
