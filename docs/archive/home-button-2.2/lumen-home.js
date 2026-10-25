/*
 * Lumen's Home button and power-on helper. Runs as root on the TV's own node, started by
 * Lumen through the Homebrew Channel's exec service (no SSH). Prints one JSON line.
 *
 *   node lumen-home.js apply <home 0|1> <powerOn 0|1>   save the choice and put it in place
 *   node lumen-home.js ensure                           put the saved choice back (after a reboot,
 *                                                       a Lumen update or a GlassHouse update)
 *   node lumen-home.js ensure-key                       only the GlassHouse Home entry (used by the boot hook)
 *   node lumen-home.js remove                           give Home back, stop the boot hook, forget it
 *
 * The Home button goes through GlassHouse's remote-key filter, the same way Lightkeeper does:
 * GlassHouse's filter sits in the compositor's key-filter chain and reads which app each key
 * opens from the configd value glasshouse.remoteKeys (kept in /var/lib/tvweb/remotekeys.json).
 * Lumen only sets the "home" entry there and remembers what was there before, to put it back.
 *
 * Strict ES5: some TVs ship node 0.12.
 */
'use strict';
var fs = require('fs');
var path = require('path');
var execFile = require('child_process').execFile;
var spawn = require('child_process').spawn;

var APP_ID = 'org.webosbrew.lumen';
var ENV = process.env;
var DATA = ENV.LUMEN_HOME_DATA || '/var/lib/lumen';
var TVWEB = ENV.LUMEN_HOME_TVWEB || '/var/lib/tvweb';
var HOOK = ENV.LUMEN_HOME_HOOK || '/var/lib/webosbrew/init.d/61-lumen';
var LUNA_SEND = ENV.LUMEN_HOME_LUNA_SEND || '/usr/bin/luna-send';
var KEY_FILTERS = ENV.LUMEN_HOME_KEY_FILTERS || '/usr/lib/qt5/qml/KeyFilters';
var HERE = __dirname;
var CONFIG = path.join(DATA, 'config.json');
var REMOTE_KEYS = path.join(TVWEB, 'remotekeys.json');
var REMOTE_KEYS_VALUE = 'glasshouse.remoteKeys';
var FILTER_FILE = path.join(TVWEB, 'remotekeys-filter.js');
var CHAIN = 'com.webos.surfacemanager.keyFilters';

function out(o) { process.stdout.write(JSON.stringify(o) + '\n'); }
function readJSON(f) { try { var j = JSON.parse(fs.readFileSync(f, 'utf8')); return j && typeof j === 'object' ? j : null; } catch (e) { return null; } }
function writeAtomic(f, data, mode) { var t = f + '.tmp'; fs.writeFileSync(t, data, { mode: mode || 420 }); fs.renameSync(t, f); }
function exists(f) { try { fs.lstatSync(f); return true; } catch (e) { return false; } }

function luna(uri, params, cb) {
  execFile(LUNA_SEND, ['-n', '1', '-w', '8000', 'luna://' + uri, JSON.stringify(params || {})], { timeout: 15000 }, function (err, stdout) {
    var s = String(stdout || ''), j = null;
    try { j = JSON.parse(s.slice(s.indexOf('{'))); } catch (e) {}
    cb(j && j.returnValue !== false ? j : null);
  });
}

function loadConfig() { var c = readJSON(CONFIG) || {}; return { home: !!c.home, powerOn: !!c.powerOn, prevHome: typeof c.prevHome === 'string' ? c.prevHome : '' }; }
function saveConfig(c) {
  if (!exists(DATA)) fs.mkdirSync(DATA, 448);
  // pretty-printed: the boot hook reads "home": true and "powerOn": true with grep
  writeAtomic(CONFIG, JSON.stringify(c, null, 2) + '\n', 384);
}

/* ---------- the Home key, through GlassHouse ---------- */

// cb(state): 'off', 'active', 'pending' (GlassHouse restarting, about a minute), 'noglasshouse', 'unsupported' or 'failed'
function setHome(want, cfg, cb) {
  if (!exists(path.join(TVWEB, 'tvweb.js'))) return cb(want ? 'noglasshouse' : 'off');
  if (want && !exists(KEY_FILTERS)) return cb('unsupported');
  var j = readJSON(REMOTE_KEYS) || {};
  var keys = j.keys && typeof j.keys === 'object' ? j.keys : {};
  var cur = typeof j.home === 'string' ? j.home : '';
  var next;
  if (want) {
    if (cur !== APP_ID) cfg.prevHome = cur;          /* remember GlassHouse's own entry, if any, to give it back */
    next = APP_ID;
  } else {
    next = cur === APP_ID ? (cfg.prevHome || '') : cur;
    cfg.prevHome = '';
  }
  if (next === cur) return keyState(want, false, cb);
  var starting = typeof j.starting === 'string' ? j.starting : '';
  try {
    if (!Object.keys(keys).length && !next && !starting) { try { fs.unlinkSync(REMOTE_KEYS); } catch (e) {} }
    else {
      var file = { keys: keys, updated: new Date().toISOString() };
      if (next) file.home = next;
      if (starting) file.starting = starting;
      writeAtomic(REMOTE_KEYS, JSON.stringify(file, null, 2) + '\n', 420);
    }
  } catch (e) { return cb('failed'); }
  var value = { keys: keys };
  if (next) value.home = next;
  if (starting) value.starting = starting;
  var configs = {}; configs[REMOTE_KEYS_VALUE] = value;
  luna('com.webos.service.config/setConfigs', { configs: configs }, function (r) {
    if (!r) return cb('failed');
    keyState(want, true, cb);
  });
}

// Is GlassHouse's filter in the compositor's chain? If not, a GlassHouse restart puts it there.
function keyState(want, changed, cb) {
  if (!want) return cb('off');
  luna('com.webos.service.config/getConfigs', { configNames: [CHAIN] }, function (r) {
    var list = (r && r.configs && r.configs[CHAIN]) || [];
    var inChain = list.some ? list.some(function (e) { return e && e.file === FILTER_FILE; }) : false;
    if (inChain) return cb('active');
    if (!r) return cb('failed');
    if (changed) execFile(path.join(TVWEB, 'tvwebctl'), ['restart'], { timeout: 30000 }, function () {});
    cb('pending');
  });
}

/* ---------- the boot hook ---------- */

function startHook() {
  // detached and with no output left open: the exec service waits for its output to close
  var child = spawn('/bin/sh', [HOOK], { detached: true, stdio: 'ignore', cwd: '/' });
  child.unref();
}
function installHook() {
  var init = path.join(HERE, 'lumen-init');
  // the package stores this folder writable by all (drwxrwxrwx); these files run as root, so lock
  // them down before anything runs: folder and hook 755, helper 644, app folder not writable by others
  fs.chmodSync(HERE, 493);
  fs.readdirSync(HERE).forEach(function (f) { fs.chmodSync(path.join(HERE, f), f === 'lumen-init' ? 493 : 420); });
  try { fs.chmodSync(path.dirname(HERE), fs.statSync(path.dirname(HERE)).mode & 493); } catch (e) {}
  if (!exists(path.dirname(HOOK))) throw new Error('the Homebrew Channel start-up folder is missing');
  // a link into the app rather than a copy: once Lumen is gone, nothing of it runs at boot
  try { fs.unlinkSync(HOOK); } catch (e) {}
  fs.symlinkSync(init, HOOK);
  // a copy of this helper, so the hook can still give Home back if Lumen is deleted
  if (!exists(DATA)) fs.mkdirSync(DATA, 448);
  fs.writeFileSync(path.join(DATA, 'lumen-home.js'), fs.readFileSync(__filename), { mode: 448 });
  startHook();
}
// The hook's two listeners, matched from the start of their command line (see lumen-init).
function stopListeners() {
  var heads = [LUNA_SEND + '\0-i\0luna://com.webos.service.tvpower/power/getPowerState\0',
               LUNA_SEND + '\0-i\0luna://com.webos.applicationManager/getAppLifeEvents\0'];
  var pids = [];
  try { pids = fs.readdirSync('/proc').filter(function (d) { return /^\d+$/.test(d); }); } catch (e) {}
  pids.forEach(function (pid) {
    var cmd = '';
    try { cmd = fs.readFileSync('/proc/' + pid + '/cmdline', 'utf8'); } catch (e) { return; }
    if (heads.some(function (h) { return cmd.indexOf(h) === 0; })) { try { process.kill(+pid); } catch (e) {} }
  });
}
function removeHook() {
  try { fs.unlinkSync(HOOK); } catch (e) {}
  try { fs.writeFileSync('/tmp/lumen-home.gen', 'stopped\n'); } catch (e) {}   /* the hook's loops end... */
  stopListeners();                                                              /* ...once their listeners stop */
}

/* ---------- commands ---------- */

function apply(cfg, cb) {
  setHome(cfg.home, cfg, function (state) {
    try {
      if (cfg.home || cfg.powerOn) { saveConfig(cfg); installHook(); }
      else { removeHook(); try { fs.unlinkSync(CONFIG); fs.unlinkSync(path.join(DATA, 'lumen-home.js')); fs.rmdirSync(DATA); } catch (e) {} }
    } catch (e) { return cb({ ok: false, home: state, powerOn: cfg.powerOn, error: e.message }); }
    cb({ ok: state !== 'failed', home: state, powerOn: cfg.powerOn });
  });
}

var cmd = process.argv[2];
if (!exists(LUNA_SEND)) { out({ ok: false, error: 'no luna-send on this system' }); }
else if (cmd === 'apply') {
  var c = loadConfig();
  c.home = process.argv[3] === '1'; c.powerOn = process.argv[4] === '1';
  apply(c, out);
} else if (cmd === 'ensure') {
  var c2 = loadConfig();
  if (!c2.home && !c2.powerOn) out({ ok: true, home: 'off', powerOn: false });
  else apply(c2, out);
} else if (cmd === 'ensure-key') {
  // from the boot hook: only the Home entry, never the hook itself (which would restart the caller)
  var c4 = loadConfig();
  if (!c4.home) out({ ok: true, home: 'off' });
  else setHome(true, c4, function (state) { try { saveConfig(c4); } catch (e) {} out({ ok: state !== 'failed', home: state }); });
} else if (cmd === 'remove') {
  var c3 = loadConfig(); c3.home = false; c3.powerOn = false;
  apply(c3, out);
} else {
  out({ ok: false, error: 'usage: apply <0|1> <0|1> | ensure | remove' });
}
