import { HOST, ORDER_RE, orderFromUrl, eligibleDownload } from './core.js';

const BUILD_VERSION = '1.0.0';
const SELLER_ORIGIN = 'https://sellerportal.tcgplayer.com';
function urlOrigin(value) { try { return new URL(value).origin; } catch { return null; } }
function safeUrl(value) { try { const u = new URL(value); return u.origin + u.pathname; } catch { return null; } }
async function inspectOrderSender(message, sender) {
  const checks = {
    extension: sender.id === chrome.runtime.id,
    topFrame: sender.frameId === 0,
    tab: Number.isInteger(sender.tab?.id),
    documentOrigin: urlOrigin(sender.url) === SELLER_ORIGIN,
    senderOrigin: sender.origin === undefined || sender.origin === SELLER_ORIGIN,
    requestedOrder: typeof message.orderId === 'string' && ORDER_RE.test(message.orderId)
  };
  let liveTab = null;
  if (checks.extension && checks.topFrame && checks.tab && checks.documentOrigin && checks.senderOrigin) {
    try { liveTab = await chrome.tabs.get(sender.tab.id); } catch {}
  }
  const liveOrder = orderFromUrl(liveTab?.url || '');
  checks.currentTabOrder = !!liveOrder && liveOrder === message.orderId;
  const documentOrder = orderFromUrl(sender.url || sender.tab?.url || '');
  return {
    accepted: Object.values(checks).every(Boolean),
    orderId: liveOrder,
    checks,
    evidence: {
      extensionId: sender.id || null, frameId: sender.frameId ?? null,
      documentId: sender.documentId || null,
      documentUrl: safeUrl(sender.url), senderTabUrl: safeUrl(sender.tab?.url),
      liveTabUrl: safeUrl(liveTab?.url), origin: sender.origin || null,
      requestedOrder: checks.requestedOrder ? message.orderId : null,
      clientBuild: message.clientBuild || null, workerBuild: BUILD_VERSION,
      documentOrder,
      previousRuleWouldAccept: sender.id === chrome.runtime.id && sender.frameId === 0 && !!sender.tab && !!documentOrder && documentOrder === message.orderId
    }
  };
}

let serial = Promise.resolve();
function exclusively(fn) {
  const result = serial.then(fn, fn);
  serial = result.catch(() => {});
  return result;
}
async function native(message) {
  const result = await chrome.runtime.sendNativeMessage(HOST, message);
  if (!result || !result.ok) throw new Error(result?.error || 'Local print helper did not respond.');
  return result;
}
async function pending() { return (await chrome.storage.session.get('pending')).pending; }
async function status(p, result) {
  await chrome.storage.local.set({ lastResult: { ...result, orderId: p.orderId, time: Date.now() } });
  try { await chrome.tabs.sendMessage(p.tabId, { type: 'TCGPRINT_STATUS', token: p.token, ...result }); } catch {}
}
async function handoff(p, payload) {
  p.phase = 'processing';
  await chrome.storage.session.set({ pending: p });
  try {
    const tab = await chrome.tabs.get(p.tabId);
    if (orderFromUrl(tab.url) !== p.orderId) throw new Error('Order changed before PDF handoff.');
    const result = await native({ command: 'print', orderId: p.orderId, requestId: p.token, ...payload });
    await status(p, result);
    await chrome.storage.session.remove('pending');
    return result;
  } catch (error) {
    const result = { ok: false, state: 'error', requestId: p.token, error: error.message };
    await status(p, result);
    await chrome.storage.session.remove('pending');
    return result;
  }
}
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  exclusively(async () => {
    if (message?.type === 'TCGPRINT_PING' && sender.id === chrome.runtime.id && !sender.tab) return { ...await native({ command: 'ping' }), buildVersion: BUILD_VERSION };
    if (message?.type === 'TCGPRINT_CHECK_JOB' && sender.id === chrome.runtime.id && !sender.tab) {
      const { lastResult } = await chrome.storage.local.get('lastResult');
      if (!lastResult?.requestId || !lastResult?.orderId) return { ok: false, error: 'No print job to check.' };
      const result = await native({ command: 'status', orderId: lastResult.orderId, requestId: lastResult.requestId });
      await chrome.storage.local.set({ lastResult: { ...lastResult, ...result, time: Date.now() } });
      return result;
    }
    const inspection = await inspectOrderSender(message, sender);
    if (message.type === 'TCGPRINT_CONTEXT_CHECK' && sender.id === chrome.runtime.id) return { ok: inspection.accepted, state: 'context', ...inspection };
    if (!inspection.accepted) throw new Error('Untrusted order-page message.');
    const orderId = inspection.orderId;
    if (message.type === 'TCGPRINT_ARM') {
      if (message.clientBuild !== BUILD_VERSION) throw new Error('Reload the extension and refresh this page.');
      if (typeof message.token !== 'string' || !/^[a-f0-9-]{36}$/i.test(message.token)) throw new Error('Invalid print request token.');
      const current = await pending();
      if (current && Date.now() < current.expires) throw new Error('A print request is already in progress.');
      await native({ command: 'ping' });
      const p = { orderId, tabId: sender.tab.id, token: message.token, created: Date.now(), expires: Date.now() + 90000, phase: 'armed', documentId: sender.documentId || null };
      await chrome.storage.session.set({ pending: p });
      return { ok: true, state: 'armed', buildVersion: BUILD_VERSION };
    }
    const p = await pending();
    if (!p || p.token !== message.token || p.tabId !== sender.tab.id || p.orderId !== orderId || (p.documentId && p.documentId !== sender.documentId)) throw new Error('No matching print request.');
    if (message.type === 'TCGPRINT_CANCEL') {
      if (p.phase === 'armed') await chrome.storage.session.remove('pending');
      return { ok: true };
    }
    if (message.type === 'TCGPRINT_PDF' && p.phase === 'armed' && Date.now() < p.expires) {
      if (typeof message.pdfBase64 !== 'string' || message.pdfBase64.length > 24 * 1024 * 1024) throw new Error('PDF exceeds transfer limit.');
      return handoff(p, { pdfBase64: message.pdfBase64, filename: message.filename });
    }
    throw new Error('Unsupported extension message.');
  }).then(reply, error => reply({ ok: false, state: 'error', error: error.message }));
  return true;
});
chrome.downloads.onChanged.addListener(delta => {
  if (delta.state?.current !== 'complete') return;
  exclusively(async () => {
    const p = await pending();
    const [item] = await chrome.downloads.search({ id: delta.id });
    if (!item || !eligibleDownload(item, p)) return;
    // The one-click contract requires captured bytes, without Save As or a
    // filesystem permission prompt. A completed download alone is not enough.
    await status(p, { ok: false, state: 'error', error: 'The official PDF was downloaded but its bytes were not captured. Nothing was printed. Reload the extension and order page.' });
    await chrome.storage.session.remove('pending');
  }).catch(error => console.warn('TCGplayer print handoff failed:', error.message));
});
