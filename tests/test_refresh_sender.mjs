// Red-capable regression: a valid top-level TCGplayer document navigates by
// history.pushState from the order list to the current order before clicking.
import assert from 'node:assert/strict';
let handler; const session={};let nativeCalls=0;
const oid='TEST0001-ABCDEF-12345';const origin='https://sellerportal.tcgplayer.com';
const liveTab={id:7,url:origin+'/orders/'+oid};
const sender={id:'pidblibebfmenlpcbnajfcdoikdldhgj',frameId:0,documentId:'document-A',origin,url:origin+'/orders',tab:liveTab};
if (process.env.TCGPRINT_REPRO_CURRENT_DOC) sender.url=liveTab.url;
const store=data=>({get:async key=>({[key]:data[key]}),set:async v=>Object.assign(data,v),remove:async key=>delete data[key]});
globalThis.chrome={runtime:{id:sender.id,onMessage:{addListener:fn=>handler=fn},sendNativeMessage:async()=>{nativeCalls++;return{ok:true,state:'ready'};}},storage:{session:store(session),local:store({})},tabs:{get:async()=>liveTab,sendMessage:async()=>{}},downloads:{onChanged:{addListener:()=>{}},search:async()=>[]}};
await import('../extension/background.js');
const response=await new Promise(resolve=>handler({type:'TCGPRINT_ARM',clientBuild:'1.0.0',orderId:oid,token:'d712e9fa-35c3-4f84-8812-a4b69f8918b7'},sender,resolve));
console.log(JSON.stringify({feedback:'trusted SPA/current-order ARM',actual:response,expected:'armed',nativeCalls}));
assert.equal(response.ok,true,`Exact user symptom reproduced: ${response.error}`);
assert.equal(response.state,'armed');
const send=(message,who=sender)=>new Promise(resolve=>handler(message,who,resolve));
const arm={type:'TCGPRINT_ARM',clientBuild:'1.0.0',orderId:oid,token:'d712e9fa-35c3-4f84-8812-a4b69f8918b7'};
const diagnostic=await send({type:'TCGPRINT_CONTEXT_CHECK',orderId:oid});
assert.equal(diagnostic.accepted,true);
const staleTabSnapshot={...sender,tab:{id:liveTab.id,url:origin+'/orders'}};
const staleSnapshotProbe=await send({type:'TCGPRINT_CONTEXT_CHECK',orderId:oid},staleTabSnapshot);
assert.equal(staleSnapshotProbe.accepted,true);
assert.equal(staleSnapshotProbe.evidence.liveTabUrl,origin+'/orders/'+oid);
assert.equal(staleSnapshotProbe.evidence.senderTabUrl,origin+'/orders');assert.equal(diagnostic.evidence.previousRuleWouldAccept,!!process.env.TCGPRINT_REPRO_CURRENT_DOC);
for(const altered of [{...sender,id:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},{...sender,frameId:1},{...sender,origin:'https://evil.example'},{...sender,url:'https://evil.example/orders/'+oid},{...sender,tab:undefined}]) {
 assert.equal((await send(arm,altered)).ok,false);
}
assert.equal((await send({...arm,orderId:'TEST0002-ABCDEF-12345'})).ok,false);
const changedDocument={...sender,documentId:'document-B'};
assert.equal((await send({...arm,type:'TCGPRINT_PDF',pdfBase64:'JVBERi0='},changedDocument)).ok,false);
liveTab.url=origin+'/orders/TEST0002-ABCDEF-12345';
assert.equal((await send({...arm,type:'TCGPRINT_PDF',pdfBase64:'JVBERi0='})).ok,false);
assert.equal(nativeCalls,1,'Only initial ping is permitted; rejected contexts never hand off PDF data.');
console.log('PASS: live-order navigation regression and extension/frame/origin/order/document-change rejection; no native print invoked.');
