// The guard's dedicated worker (plan I7): fetches the sentinel through every spelling, then says it is done.
const CFG = __CONFIG__;
Promise.all(CFG.sentinels.map(s => fetch(s + '/' + encodeURIComponent(CFG.ctx) + '/worker', {mode: 'no-cors'})
  .then(() => 'reached', () => 'failed')))
  .then(results => postMessage('done ' + results.join(',')));
