document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-plan-request]');if(!button)return;
 const request=button.dataset.planRequest,status=button.closest('.grouping-options').querySelector('.plan-option-status');
 try{await navigator.clipboard.writeText(request);status.textContent='Copied: '+request+' Paste it into Copilot to update the plan.'}
 catch{status.textContent=request;const range=document.createRange();range.selectNodeContents(status);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range)}
});
