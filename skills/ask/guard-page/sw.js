// The guard's Service Worker (plan I7, probe P7: a Service Worker's requests escape the URL allowlist alone).
// On activation it requests the sentinel through every spelling, the external stand-in and an external host, and
// reports each outcome to its own origin.
const CFG = __CONFIG__;
function report(k, v) {
  return fetch(CFG.base + '/r?ctx=' + encodeURIComponent(CFG.ctx) + '&k=' + encodeURIComponent(k) +
    '&v=' + encodeURIComponent(String(v)), {cache: 'no-store'}).catch(() => {});
}
function probe(url) { return fetch(url, {mode: 'no-cors', cache: 'no-store'}).then(() => 'reached', () => 'failed'); }
async function probes() {
  const sentinel = await Promise.all(CFG.sentinels.map(s => probe(s + '/' + encodeURIComponent(CFG.ctx) + '/sw')));
  await report('sw-sentinel', sentinel.join(','));
  await report('sw-lan', await probe(CFG.lan + '/' + encodeURIComponent(CFG.ctx) + '/sw'));
  await report('sw-external', await probe(CFG.external));
  await report('sw-done', 'yes');
}
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(probes()));
