// netguard.cjs - per-program network guard for HyperFrames and other Node runs.
// Load with NODE_OPTIONS="--require <this file>". Blocks every non-loopback
// net/tls connect and every DNS lookup of a non-loopback name in this Node
// process, its worker threads, and child Node processes (they inherit
// NODE_OPTIONS), failing them with ENETUNREACH. Each attempt is appended as one
// JSON line to $NETGUARD_LOG. NETGUARD_ALLOW=1 = observe-only (log, let through).
// ponytail: covers Node only; Chrome/ffmpeg children are guarded separately.
'use strict';
const net = require('net');
const dns = require('dns');
const fs = require('fs');

const LOG = process.env.NETGUARD_LOG || '';
const ALLOW = process.env.NETGUARD_ALLOW === '1';
const LOOP_NAMES = new Set(['localhost', '127.0.0.1', '::1', '[::1]', '']);
const isLoop = (h) => h == null || LOOP_NAMES.has(String(h).toLowerCase()) || /^127\./.test(String(h)) || /^::ffff:127\./i.test(String(h));

function record(kind, host, port) {
  const stack = (new Error().stack || '').split('\n').slice(1)
    .filter((l) => !l.includes('netguard.cjs')).slice(0, 4).map((s) => s.trim());
  const line = JSON.stringify({ t: new Date().toISOString(), pid: process.pid, kind, host, port, stack }) + '\n';
  if (LOG) { try { fs.appendFileSync(LOG, line); } catch (_) { /* never break the host on a log error */ } }
}
const blocked = (kind, host, port) => {
  record(ALLOW ? 'observed:' + kind : kind, host, port);
  const e = new Error(`netguard: blocked ${kind} to ${host}:${port ?? ''}`);
  e.code = 'ENETUNREACH';
  return e;
};

// net.Socket#connect is the funnel for net.connect, tls.connect, http(s), undici/fetch.
const origConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  let o = args[0];
  if (Array.isArray(o)) o = o[0];
  if (o && typeof o === 'object') {
    if (!o.path && !isLoop(o.host)) {
      if (ALLOW) { blocked('connect', o.host, o.port); return origConnect.apply(this, args); }
      const err = blocked('connect', o.host, o.port);
      process.nextTick(() => this.destroy(err));
      return this;
    }
  } else if (typeof o === 'number' || (typeof o === 'string' && /^\d+$/.test(o))) {
    const host = typeof args[1] === 'string' ? args[1] : 'localhost';
    if (!isLoop(host)) {
      if (ALLOW) { blocked('connect', host, o); return origConnect.apply(this, args); }
      const err = blocked('connect', host, o);
      process.nextTick(() => this.destroy(err));
      return this;
    }
  }
  return origConnect.apply(this, args);
};

// DNS: refuse to resolve anything but loopback names.
const origLookup = dns.lookup;
dns.lookup = function (host, opts, cb) {
  if (typeof opts === 'function') { cb = opts; opts = {}; }
  if (!isLoop(host)) {
    if (ALLOW) { blocked('dns.lookup', host); return origLookup.call(this, host, opts, cb); }
    const err = blocked('dns.lookup', host);
    process.nextTick(() => cb(err));
    return {};
  }
  return origLookup.call(this, host, opts, cb);
};
const origPLookup = dns.promises.lookup;
dns.promises.lookup = function (host, opts) {
  if (!isLoop(host)) {
    if (ALLOW) { blocked('dns.promises.lookup', host); return origPLookup.call(this, host, opts); }
    return Promise.reject(blocked('dns.promises.lookup', host));
  }
  return origPLookup.call(this, host, opts);
};
for (const fn of ['resolve', 'resolve4', 'resolve6', 'resolveAny', 'resolveCname', 'resolveTxt', 'resolveSrv']) {
  if (typeof dns[fn] === 'function') {
    const orig = dns[fn];
    dns[fn] = function (host, ...rest) {
      if (ALLOW) { blocked('dns.' + fn, host); return orig.call(this, host, ...rest); }
      const cb = rest[rest.length - 1];
      const err = blocked('dns.' + fn, host);
      if (typeof cb === 'function') process.nextTick(() => cb(err));
      return {};
    };
  }
  if (typeof dns.promises[fn] === 'function') {
    const orig = dns.promises[fn];
    dns.promises[fn] = (host, ...rest) => (ALLOW ? (blocked('dns.promises.' + fn, host), orig.call(dns.promises, host, ...rest))
      : Promise.reject(blocked('dns.promises.' + fn, host)));
  }
}
