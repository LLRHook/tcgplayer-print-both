import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { orderFromUrl, eligibleDownload } from '../extension/core.js';
const pdf = fs.readFileSync(new URL('./generated/native-default.pdf', import.meta.url));
const source = fs.readFileSync(new URL('../extension/pdf-bridge.js', import.meta.url), 'utf8');
const oid = 'TEST0001-ABCDEF-12345', token = 'd712e9fa-35c3-4f84-8812-a4b69f8918b7';
let tests = 0;
function environment() {
  const listeners = new Map(), messages = []; let clicks = 0, dispatches = 0;
  class Target { dispatchEvent() { dispatches++; return true; } }
  class Anchor extends Target { constructor() { super(); this.download = 'TCGplayer_PackingSlips_test.pdf'; } click() { clicks++; } }
  class XHR extends Target { addEventListener(event, callback) { this.callback = callback; } send() { this.callback?.(); } }
  const window = { addEventListener(type, callback) { const a = listeners.get(type) || []; a.push(callback); listeners.set(type, a); }, postMessage(data) { messages.push(data); } };
  const url = { createObjectURL: () => 'blob:https://sellerportal.tcgplayer.com/native' };
  const document = { addEventListener() {} };
  const response = { headers: { get: () => 'application/pdf' }, clone: () => ({ blob: async () => new Blob([pdf], { type: 'application/pdf' }) }) };
  window.fetch = async () => response;
  const context = { window, location: { origin: 'https://sellerportal.tcgplayer.com' }, URL: url, document, EventTarget: Target, HTMLAnchorElement: Anchor, XMLHttpRequest: XHR, Blob, ArrayBuffer, Uint8Array, Date, btoa, String, Map };
  vm.runInNewContext(source, context);
  function arm() { for (const fn of listeners.get('message')) fn({ source: window, origin: context.location.origin, data: { type: 'TCGPRINT_ARM_BRIDGE', token, orderId: oid } }); }
  return { arm, Anchor, XHR, window, url, messages, response, clicks: () => clicks, dispatches: () => dispatches };
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };
{
 const e = environment(); const a = new e.Anchor(); a.href = e.url.createObjectURL(new Blob([pdf], { type: 'application/pdf' })); a.click(); await settle();
 assert.equal(e.clicks(), 1); assert.equal(e.messages.length, 0); tests++;
}
{
 const e = environment(); e.arm(); const a = new e.Anchor(); a.href = e.url.createObjectURL(new Blob([pdf], { type: 'application/pdf' })); a.click(); await settle();
 const messages = e.messages.filter(x => x.type === 'TCGPRINT_PDF_BRIDGE'); assert.equal(messages.length, 1); assert.deepEqual(Buffer.from(messages[0].pdfBase64, 'base64'), pdf); assert.equal(e.clicks(), 0); assert.equal(messages[0].orderId, oid); tests++;
}
{
 const e = environment(); e.arm(); const a = new e.Anchor(); a.href = e.url.createObjectURL(new Blob([pdf], { type: 'application/pdf' })); a.dispatchEvent({ type: 'click' }); await settle();
 assert.equal(e.dispatches(), 0); assert.equal(e.messages.filter(x => x.type === 'TCGPRINT_PDF_BRIDGE').length, 1); tests++;
}
{
 const e = environment(); e.arm(); assert.equal(await e.window.fetch('/native/export'), e.response); await settle();
 assert.deepEqual(Buffer.from(e.messages.find(x => x.type === 'TCGPRINT_PDF_BRIDGE').pdfBase64, 'base64'), pdf); tests++;
}
{
 const e = environment(); e.arm(); const xhr = new e.XHR(); xhr.response = new Blob([pdf], { type: 'application/pdf' }); xhr.send(); await settle();
 assert.equal(e.messages.filter(x => x.type === 'TCGPRINT_PDF_BRIDGE').length, 1); tests++;
}
{
 const e = environment(); e.arm(); const a = new e.Anchor(); a.download = 'unrelated.pdf'; a.href = e.url.createObjectURL(new Blob([pdf], { type: 'application/pdf' })); a.click(); await settle();
 assert.equal(e.clicks(), 1); tests++;
}
{
 const e = environment(); e.arm(); await e.window.fetch('/native/export'); const a = new e.Anchor(); a.href = e.url.createObjectURL(new Blob([pdf], { type: 'application/pdf' })); a.click(); await settle();
 assert.equal(e.messages.filter(x => x.type === 'TCGPRINT_PDF_BRIDGE').length, 1); tests++;
}
{
 const e = environment(); e.arm(); e.url.createObjectURL(new Blob(['not a pdf'], { type: 'application/pdf' })); await settle();
 assert.equal(e.messages.filter(x => x.type === 'TCGPRINT_PDF_BRIDGE').length, 0); tests++;
}
assert.equal(orderFromUrl('https://sellerportal.tcgplayer.com/orders/'+oid), oid);
assert.equal(orderFromUrl('https://evil.example/orders/'+oid), null);
const pending = { phase: 'armed', created: Date.now(), expires: Date.now()+1000 };
const download = { filename:'/tmp/example/TCGplayer_PackingSlips_20260101_120000.pdf',state:'complete',exists:true,startTime:new Date().toISOString(),url:'blob:https://sellerportal.tcgplayer.com/abc' };
assert.equal(eligibleDownload(download,pending),true);assert.equal(eligibleDownload({...download,startTime:'2026-01-01'},pending),false);assert.equal(eligibleDownload({...download,url:'https://evil.example/file'},pending),false);tests+=2;
console.log(`PASS: ${tests} PDF capture, suppression, exact-byte and origin/download checks; no printer invoked.`);
