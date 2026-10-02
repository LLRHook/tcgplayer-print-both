import assert from 'node:assert/strict';
let handler, changed, printCalls=0;
const session={}, local={};
const store=data=>({ get:async key=>({[key]:data[key]}),set:async values=>Object.assign(data,values),remove:async key=>delete data[key] });
const oid='TEST0001-ABCDEF-12345',token='d712e9fa-35c3-4f84-8812-a4b69f8918b7';
const sender={id:'pidblibebfmenlpcbnajfcdoikdldhgj',frameId:0,url:'https://sellerportal.tcgplayer.com/orders/'+oid,tab:{id:7,url:'https://sellerportal.tcgplayer.com/orders/'+oid}};
globalThis.chrome={
 runtime:{id:sender.id,onMessage:{addListener:fn=>handler=fn},sendNativeMessage:async(host,msg)=>{assert.equal(host,'com.victorivanov.tcgplayer_print');if(msg.command==='ping')return{ok:true,state:'ready'};printCalls++;assert.equal(msg.orderId,oid);assert.equal(msg.requestId,token);assert.equal(msg.pdfBase64,'JVBERi0=');return{ok:true,state:'completed',job:'mock-only',sheets:2};}},
 storage:{session:store(session),local:store(local)},tabs:{get:async()=>sender.tab,sendMessage:async()=>{}},downloads:{onChanged:{addListener:fn=>changed=fn},search:async()=>[]}
};
await import('../extension/background.js');
const send=(message,who=sender)=>new Promise(resolve=>handler(message,who,resolve));
assert.equal((await send({type:'TCGPRINT_ARM',clientBuild:'1.1.0',orderId:oid,token},{...sender,frameId:1})).ok,false);
assert.equal((await send({type:'TCGPRINT_ARM',clientBuild:'1.1.0',orderId:oid,token},{...sender,url:'https://evil.example/orders/'+oid})).ok,false);
assert.equal((await send({type:'TCGPRINT_ARM',clientBuild:'1.1.0',orderId:oid,token})).state,'armed');
const payload={type:'TCGPRINT_PDF',orderId:oid,token,pdfBase64:'JVBERi0='};
const results=await Promise.all([send(payload),send(payload)]);
assert.equal(results.filter(r=>r.ok).length,1);assert.equal(printCalls,1);assert.equal(session.pending,undefined);assert.equal(local.lastResult.state,'completed');
console.log('PASS: trusted current-order sender, iframe/site rejection and serialized one-handoff-only checks; native printing mocked.');
