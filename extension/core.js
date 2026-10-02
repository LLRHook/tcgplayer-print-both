export const HOST = 'com.victorivanov.tcgplayer_print';
export const ORDER_RE = /^[A-Z0-9]{8}-[A-Z0-9]{6}-[A-Z0-9]{5}$/;
export const FILE_RE = /^TCGplayer_PackingSlips_[A-Za-z0-9_ -]+(?:\s*\(\d+\))?\.pdf$/i;
export function orderFromUrl(url) {
  try {
    const u = new URL(url);
    if (u.origin !== 'https://sellerportal.tcgplayer.com') return null;
    const match = u.pathname.match(/^\/orders\/([^/]+)\/?$/);
    const id = match && decodeURIComponent(match[1]).toUpperCase();
    return id && ORDER_RE.test(id) ? id : null;
  } catch { return null; }
}
export function officialUrl(value) {
  try {
    const u = new URL(value.startsWith('blob:') ? value.slice(5) : value);
    return u.protocol === 'https:' && (u.hostname === 'tcgplayer.com' || u.hostname.endsWith('.tcgplayer.com'));
  } catch { return false; }
}
export function eligibleDownload(item, pending) {
  const file = (item.filename || '').split(/[\\/]/).pop();
  return pending && pending.phase === 'armed' && Date.now() < pending.expires &&
    item.state === 'complete' && FILE_RE.test(file) && item.exists !== false &&
    Date.parse(item.startTime) >= pending.created - 1000 &&
    (officialUrl(item.url || '') || officialUrl(item.finalUrl || '') || officialUrl(item.referrer || ''));
}
