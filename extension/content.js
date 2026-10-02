(() => {
  const CLIENT_BUILD = '1.0.0';
  const PACKING = '[data-testid="OrderDetails_CustomerDetails_btnPackingSlip"]';
  const DEFAULT = '[data-testid="OrderDetails_PackingSlipList_btnDownloadDefaultByRelease"]';
  const HEADER = '[data-testid="txtOrderHeader"]';
  let active = null;
  function orderId() {
    const path = location.pathname.match(/^\/orders\/([^/]+)\/?$/);
    const heading = document.querySelector(HEADER)?.textContent.trim().match(/^Order:\s*([A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+)/i);
    const id = path && decodeURIComponent(path[1]).toUpperCase();
    if (!id || !/^[A-Z0-9]{8}-[A-Z0-9]{6}-[A-Z0-9]{5}$/.test(id) || heading?.[1].toUpperCase() !== id) throw new Error('Order heading and page address do not match.');
    return id;
  }
  function show(text, isError = false) {
    const el = document.getElementById('tcgprint-status');
    if (el) {
      el.textContent = isError ? (/mismatch|do not match|changed/i.test(text) ? 'Order mismatch' : /helper|host|native|queue/i.test(text) ? 'Helper unavailable' : 'Print failed') : '';
      el.title = text; el.classList.toggle('tcgprint-error', isError);
    }
    const button = document.getElementById('tcgprint-button');
    if (button && active && !isError) { button.textContent = 'Printing…'; button.title = text; }
    if (button && isError) { button.textContent = 'Print both'; button.title = text; button.setAttribute('aria-label', 'Print the official packing slip and matching address label'); }
  }
  async function waitFor(selector, timeout = 5000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const found = [...document.querySelectorAll(selector)].filter(el => el.getClientRects().length && !el.disabled);
      if (found.length === 1) return found[0];
      if (found.length > 1) throw new Error('Packing-slip control is ambiguous.');
      await new Promise(resolve => setTimeout(resolve, 80));
    }
    throw new Error('Print Default control was not found.');
  }
  function finish(result) {
    if (!active) return;
    window.postMessage({ type: 'TCGPRINT_DISARM', token: active.token }, location.origin);
    clearTimeout(active.timeout); active = null;
    const button = document.getElementById('tcgprint-button'); if (button) { button.disabled = false; button.setAttribute('aria-busy', 'false'); }
    if (!result.ok) show(result.error || 'Printing failed. Check the helper.', true);
    else {
      if (button) { button.textContent = result.state === 'duplicate' ? 'Already printed' : result.state === 'submitted' ? 'Sent ✓' : 'Printed ✓'; button.setAttribute('aria-label', result.state === 'submitted' ? 'Packing slip and address label submitted' : 'Packing slip and address label printed'); button.title = result.state === 'duplicate' ? 'This click was already printed; duplicate skipped.' : (result.state === 'completed' ? 'Packing slip and address label completed.' : 'Both pages submitted to the printer.'); }
      show('');
      setTimeout(() => { if (button && !active) { button.textContent = 'Print both'; button.title = 'Print the official packing slip and matching address label'; button.setAttribute('aria-label', button.title); } }, 5000);
    }
  }
  async function printPair(button) {
    button.disabled = true; button.setAttribute('aria-busy', 'true'); button.setAttribute('aria-label', 'Printing packing slip and address label');
    try {
      const id = orderId(); const token = crypto.randomUUID();
      const response = await chrome.runtime.sendMessage({ type: 'TCGPRINT_ARM', orderId: id, token, clientBuild: CLIENT_BUILD });
      if (!response?.ok) throw new Error(response?.error || 'Local helper unavailable.');
      if (response.buildVersion !== CLIENT_BUILD) throw new Error('Reload the extension and refresh this page.');
      active = { orderId: id, token, timeout: setTimeout(() => {
        const old = active;
        if (old) chrome.runtime.sendMessage({ type: 'TCGPRINT_CANCEL', orderId: old.orderId, token: old.token }).catch(() => {});
        finish({ ok: false, error: 'No matched packing-slip PDF arrived. Nothing was retried automatically.' });
      }, 180000) };
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => { window.removeEventListener('message', ready); reject(new Error('PDF capture bridge did not initialize.')); }, 2000);
        function ready(event) {
          if (event.source === window && event.origin === location.origin && event.data?.type === 'TCGPRINT_BRIDGE_READY' && event.data.token === token) { clearTimeout(timer); window.removeEventListener('message', ready); resolve(); }
        }
        window.addEventListener('message', ready);
        window.postMessage({ type: 'TCGPRINT_ARM_BRIDGE', token, orderId: id }, location.origin);
      });
      show('Getting official packing slip...');
      if (!document.querySelector(DEFAULT)?.getClientRects().length) {
        const controls = document.querySelectorAll(PACKING);
        if (controls.length !== 1) throw new Error('Packing Slip control is missing or ambiguous.');
        controls[0].click();
      }
      const nativeDefault = await waitFor(DEFAULT);
      if (orderId() !== id) throw new Error('Order changed before downloading the slip.');
      nativeDefault.click();
      show('Printing packing slip + address label...');
    } catch (error) {
      if (active) {
        await chrome.runtime.sendMessage({ type: 'TCGPRINT_CANCEL', orderId: active.orderId, token: active.token }).catch(() => {});
        finish({ ok: false, error: error.message });
      } else { button.disabled = false; button.setAttribute('aria-busy', 'false'); show(error.message, true); }
    }
  }
  window.addEventListener('message', async event => {
    if (event.source !== window || event.origin !== location.origin || !active || event.data?.type !== 'TCGPRINT_PDF_BRIDGE' || event.data.token !== active.token || event.data.orderId !== active.orderId) return;
    const request = active;
    try {
      const response = await chrome.runtime.sendMessage({ type: 'TCGPRINT_PDF', orderId: request.orderId, token: request.token, pdfBase64: event.data.pdfBase64, filename: event.data.filename });
      if (active?.token === request.token) finish(response);
    } catch (error) { if (active?.token === request.token) finish({ ok: false, error: error.message }); }
  });
  chrome.runtime.onMessage.addListener((message, sender, reply) => {
    if (message?.type === 'TCGPRINT_CONTEXT_PROBE' && sender.id === chrome.runtime.id) {
      try {
        chrome.runtime.sendMessage({ type: 'TCGPRINT_CONTEXT_CHECK', orderId: orderId(), clientBuild: CLIENT_BUILD }).then(reply, error => reply({ ok: false, error: error.message }));
      } catch (error) { reply({ ok: false, error: error.message }); }
      return true;
    }
    if (message?.type === 'TCGPRINT_STATUS' && active?.token === message.token) finish(message);
  });
  function mount() {
    const controls = document.querySelectorAll(PACKING);
    const existing = document.getElementById('tcgprint-controls');
    if (controls.length !== 1) { if (existing) existing.remove(); return; }
    if (existing) return;
    try { orderId(); } catch { return; }
    const wrap = document.createElement('span'); wrap.id = 'tcgprint-controls';
    const button = document.createElement('button'); button.id = 'tcgprint-button'; button.type = 'button'; button.textContent = 'Print both'; button.title = 'Print the official packing slip and matching address label'; button.setAttribute('aria-label', button.title);
    button.disabled = !globalThis.TCGPRINT_READY;
    button.addEventListener('click', event => { if (event.isTrusted) return printPair(button); });
    const status = document.createElement('span'); status.id = 'tcgprint-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
    if (!globalThis.TCGPRINT_READY) button.title = 'Print helper setup is being completed.';
    wrap.append(button, status);
    const nativePopover = controls[0].closest('.tcg-popover');
    if (nativePopover?.parentElement?.classList.contains('customer-details__actions')) {
      // Add only our node beside the existing trigger; leave every React-owned
      // native element in its original parent to keep reconciliation intact.
      nativePopover.classList.add('tcgprint-group');
      nativePopover.append(wrap);
    }
  }
  new MutationObserver(mount).observe(document.documentElement, { childList: true, subtree: true });
  mount();
})();
