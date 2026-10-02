import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code = fs.readFileSync(new URL('../extension/content.js', import.meta.url), 'utf8');
const oid='TEST0001-ABCDEF-12345', token='d712e9fa-35c3-4f84-8812-a4b69f8918b7';
let tests=0;
function setup({ready=true,preflightError=null,wrongHeading=false}={}) {
 const ids=new Map(),messages=[],timers=new Map(),windowListeners=[];let statusListener,defaultClicks=0,packingClicks=0,nextTimer=0;
 const register=el=>{if(el.id)ids.set(el.id,el);for(const child of el.children)register(child);};
 class Element {
  constructor(tag){this.tag=tag;this.children=[];this.parentElement=null;this.textContent='';this.title='';this.disabled=false;this.visible=true;this.attributes={};this.events={};const values=new Set();this.classList={add:v=>values.add(v),contains:v=>values.has(v),toggle:(v,on)=>on?values.add(v):values.delete(v)};}
  append(...children){for(const child of children){child.parentElement=this;this.children.push(child);register(child);}}
  setAttribute(key,value){this.attributes[key]=value;}
  addEventListener(type,fn){this.events[type]=fn;}
  getClientRects(){return this.visible?[{}]:[];}
  closest(selector){let current=this;while(current){if(selector==='.tcg-popover'&&current.classList.contains('tcg-popover'))return current;current=current.parentElement;}return null;}
  click(trusted=true){if(this.disabled)return;return this.events.click?.({isTrusted:trusted});}
  remove(){ids.delete(this.id);}
 }
 const actions=new Element('div');actions.classList.add('customer-details__actions');
 const popover=new Element('div');popover.classList.add('tcg-popover');actions.append(popover);
 const trigger=new Element('div');popover.append(trigger);
 const packing=new Element('button');trigger.append(packing);
 const nativeDefault=new Element('button');nativeDefault.visible=false;
 packing.events.click=()=>{packingClicks++;nativeDefault.visible=true;};
 nativeDefault.events.click=()=>{defaultClicks++;};
 const heading={textContent:'Order: '+(wrongHeading?'TEST0002-ABCDEF-12345':oid)};
 const document={documentElement:{},querySelector:selector=>selector.includes('txtOrderHeader')?heading:selector.includes('btnDownloadDefaultByRelease')?nativeDefault:null,querySelectorAll:selector=>selector.includes('btnPackingSlip')?[packing]:selector.includes('btnDownloadDefaultByRelease')?[nativeDefault]:[],getElementById:id=>ids.get(id),createElement:tag=>new Element(tag)};
 const window={addEventListener:(type,fn)=>windowListeners.push(fn),removeEventListener:(type,fn)=>{const i=windowListeners.indexOf(fn);if(i>=0)windowListeners.splice(i,1);},postMessage:message=>{if(message.type==='TCGPRINT_ARM_BRIDGE')queueMicrotask(()=>{for(const fn of [...windowListeners])fn({source:window,origin:'https://sellerportal.tcgplayer.com',data:{type:'TCGPRINT_BRIDGE_READY',token}});});}};
 const context={document,window,location:{origin:'https://sellerportal.tcgplayer.com',pathname:'/orders/'+oid},crypto:{randomUUID:()=>token},MutationObserver:class{observe(){}},TCGPRINT_READY:ready,Date,Promise,setTimeout:(fn,ms)=>{timers.set(++nextTimer,{fn,ms});return nextTimer;},clearTimeout:id=>timers.delete(id),chrome:{runtime:{sendMessage:async msg=>{messages.push(msg);return msg.type==='TCGPRINT_ARM'&&preflightError?{ok:false,error:preflightError}:{ok:true,buildVersion:'1.1.0'};},onMessage:{addListener:fn=>statusListener=fn}}}};
 vm.runInNewContext(code,context);
 return {button:ids.get('tcgprint-button'),status:ids.get('tcgprint-status'),wrap:ids.get('tcgprint-controls'),popover,trigger,messages,timers,defaultClicks:()=>defaultClicks,packingClicks:()=>packingClicks,finish:r=>statusListener({type:'TCGPRINT_STATUS',token,...r})};
}
{
 const e=setup();assert.equal(e.button.disabled,false);assert.equal(e.button.textContent,'Print both');assert.equal(e.status.textContent,'');assert.equal(e.wrap.parentElement,e.popover);assert.equal(e.trigger.parentElement,e.popover);assert.equal(e.popover.classList.contains('tcgprint-group'),true);tests++;
}
{
 const e=setup({ready:false});assert.equal(e.button.disabled,true);assert.equal(e.status.textContent,'');e.button.click();assert.equal(e.messages.length,0);tests++;
}
{
 const e=setup();const first=e.button.click();e.button.click();await first;assert.equal(e.button.disabled,true);assert.equal(e.button.textContent,'Printing…');assert.equal(e.button.attributes['aria-busy'],'true');assert.equal(e.defaultClicks(),1);assert.equal(e.packingClicks(),1);assert.equal(e.messages.filter(m=>m.type==='TCGPRINT_ARM').length,1);tests++;
 e.finish({ok:true,state:'completed'});assert.equal(e.button.disabled,false);assert.equal(e.button.textContent,'Printed ✓');assert.equal(e.button.attributes['aria-busy'],'false');assert.equal(e.status.textContent,'');assert.match(e.button.title,/completed/);tests++;
 [...e.timers.values()].find(t=>t.ms===5000).fn();assert.equal(e.button.textContent,'Print both');assert.match(e.button.attributes['aria-label'],/^Print the official/);tests++;
}
{
 const e=setup();await e.button.click();e.finish({ok:true,state:'duplicate'});assert.equal(e.button.disabled,false);assert.equal(e.button.textContent,'Already printed');assert.match(e.button.title,/duplicate skipped/);tests++;
}
{
 const e=setup({preflightError:'Specified native messaging host not found.'});await e.button.click();assert.equal(e.button.disabled,false);assert.equal(e.button.attributes['aria-busy'],'false');assert.equal(e.status.textContent,'Helper unavailable');assert.equal(e.defaultClicks(),0);tests++;
}
{
 const e=setup();await e.button.click();e.finish({ok:false,error:'PDF_ORDER_MISMATCH'});assert.equal(e.button.disabled,false);assert.equal(e.status.textContent,'Order mismatch');assert.equal(e.button.attributes['aria-busy'],'false');tests++;
}
{
 const e=setup({wrongHeading:true});assert.equal(e.button,undefined);assert.equal(e.messages.length,0);tests++;
}
{ const e=setup();await e.button.click(false);assert.equal(e.messages.length,0);assert.equal(e.defaultClicks(),0);assert.equal(e.button.disabled,false);tests++; }
console.log(`PASS: ${tests} isolated content mount and ready/disabled/busy/success/duplicate/error/accessibility checks; no browser download or printer invoked.`);
