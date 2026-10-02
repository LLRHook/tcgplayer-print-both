import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code=fs.readFileSync(new URL('../extension/popup.js',import.meta.url),'utf8');
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function setup({response,oldWorker=false,hung=false,result,storageError,jobResponse}={}){
 const timers=new Map();const nodes=Object.fromEntries(['status','check','context','context-result','last-result','job'].map(id=>[id,{textContent:'',addEventListener(type,fn){this.click=fn;}}]));let next=0;
 vm.runInNewContext(code,{document:{getElementById:id=>nodes[id]},chrome:{storage:{local:{get:async()=>{if(storageError)throw new Error(storageError);return {lastResult:result};}}},runtime:{sendMessage:async message=>message.type==='TCGPRINT_CHECK_JOB'?jobResponse:({ok:true,printer:'Example_Queue',buildVersion:oldWorker?'old':'1.0.0'})},tabs:{query:async()=>[{id:7}],sendMessage:async()=>hung?new Promise(()=>{}):response}},Promise,JSON,setTimeout:(fn,ms)=>{timers.set(++next,{fn,ms});return next;},clearTimeout:id=>timers.delete(id)});
 return{nodes,timers};
}
{
 const e=setup();await settle();assert.equal(e.nodes.status.textContent,'Ready · Example_Queue');await e.nodes.context.click();assert.match(e.nodes['context-result'].textContent,/Page did not respond.*Reload/);
}
{
 const e=setup({hung:true});const pending=e.nodes.context.click();await settle();assert.equal(e.nodes['context-result'].textContent,'Checking page…');[...e.timers.values()].find(t=>t.ms===3500).fn();await pending;assert.match(e.nodes['context-result'].textContent,/Page did not respond.*Reload/);
}
{
 const e=setup({oldWorker:true});await settle();assert.equal(e.nodes.status.textContent,'Reload extension');
}
{
 const expected={ok:true,accepted:true,evidence:{frameId:0,workerBuild:'1.0.0'}};const e=setup({response:expected});await e.nodes.context.click();assert.deepEqual(JSON.parse(e.nodes['context-result'].textContent),expected);
}
{
 const result={ok:true,state:'completed',orderId:'TEST0001-ABCDEF-12345',job:'RW403B-51',requestId:'d70e56e0-example',pages:2,time:123};const e=setup({result});await settle();assert.deepEqual(JSON.parse(e.nodes['last-result'].textContent),result);assert.equal(e.nodes.status.textContent,'Ready · Example_Queue');
}
{
 const e=setup();await settle();assert.equal(e.nodes['last-result'].textContent,'No print result yet.');
}
{
 const e=setup({result:{ok:false,error:'<b>QUEUE_CHECK</b>',state:'uncertain',buyerAddress:'private'}});await settle();const actual=JSON.parse(e.nodes['last-result'].textContent);assert.equal(actual.error,'<b>QUEUE_CHECK</b>');assert.equal(actual.state,'uncertain');assert.equal(actual.buyerAddress,undefined);
}
{
 const e=setup({storageError:'Storage unavailable'});await settle();assert.equal(e.nodes['last-result'].textContent,'Storage unavailable');assert.equal(e.nodes.status.textContent,'Ready · Example_Queue');
}
for (const [response, expected] of [[{ok:true,state:'completed'},'Printed ✓'],[{ok:true,state:'submitted'},'Queued'],[{ok:true,state:'uncertain'},'Printer needs attention'],[{ok:true,state:'resolved'},'Ready to reprint'],[{ok:false,error:'No print job to check.'},'No print job to check.']]) {
 const e=setup({jobResponse:response});await settle();await e.nodes.job.click();assert.equal(e.nodes.status.textContent,expected);
}
console.log('PASS: 13 popup no-response/timeout/cached-build/diagnostic/last-result checks; no browser or printing invoked.');
