const BUILD_VERSION='1.1.0';
async function lastResult(){
 const el=document.getElementById('last-result');
 try{
  const {lastResult:r}=await chrome.storage.local.get('lastResult');
  if(!r){el.textContent='No print result yet.';return;}
  const fields=['ok','state','orderId','job','requestId','reusedRequest','pages','error','time'];
  el.textContent=JSON.stringify(Object.fromEntries(fields.filter(key=>r[key]!==undefined).map(key=>[key,r[key]])),null,2);
 }catch(error){el.textContent=error.message||'Last result unavailable.';}
}
async function check(){
 const el=document.getElementById('status');
 try{const r=await chrome.runtime.sendMessage({type:'TCGPRINT_PING'});el.textContent=r?.ok?(r.buildVersion===BUILD_VERSION?'Ready · ' + r.printer:'Reload extension'):(r?.error||'Helper unavailable');}
 catch(e){el.textContent=e.message;}
 await lastResult();
}
document.getElementById('check').addEventListener('click',check);check();
document.getElementById('context').addEventListener('click',async()=>{
 const el=document.getElementById('context-result');el.textContent='Checking page…';
 let timer;
 try{
  const probe=(async()=>{const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true});if(!tab)throw new Error('No active order tab.');return chrome.tabs.sendMessage(tab.id,{type:'TCGPRINT_CONTEXT_PROBE'});})();
  const result=await Promise.race([probe,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Page did not respond. Reload extension and refresh page.')),3500);})]);
  el.textContent=result?JSON.stringify(result,null,2):'Page did not respond. Reload extension and refresh page.';
 }catch(error){el.textContent=error.message||'Reload extension and refresh page.';}
 finally{clearTimeout(timer);}
});

document.getElementById('job').addEventListener('click', async () => {
 const el = document.getElementById('status');
 try { const r = await chrome.runtime.sendMessage({ type: 'TCGPRINT_CHECK_JOB' }); el.textContent = r?.ok ? (r.state === 'completed' ? 'Printed ✓' : r.state === 'resolved' ? 'Ready to reprint' : r.state === 'submitted' ? 'Queued' : 'Printer needs attention') : (r?.error || 'Status unavailable'); } catch (e) { el.textContent = e.message; }
 await lastResult();
});
