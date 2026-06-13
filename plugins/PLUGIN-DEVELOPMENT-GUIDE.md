# Signal K Plugin Development Guide — MidnightRider J/30

Version: 1.0 | SK Version tested: 2.25.0 | Last updated: 2026-06-13

This guide captures lessons learned from building Plugins 1–3 on SK 2.25.0.
Read this ENTIRELY before writing any new plugin.

---

## 1. MANDATORY JS STRUCTURE

SK 2.25.0 validates the plugin object at load time, BEFORE calling plugin.start().
Violating this causes silent rejection — the plugin never appears in the SK UI.

### ✅ CORRECT PATTERN (matches signalk-um982-gnss reference)

```javascript
'use strict';
const fs = require('fs');

const PLUGIN_ID = 'signalk-my-plugin';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/my-plugin.log';

module.exports = function(app) {

  // ── LOGGING helpers ─────────────────────────────────────────────────────
  function svcLog(level, msg) {
    try {
      fs.mkdirSync(LOG_BASE + '/services', { recursive: true });
      fs.appendFileSync(LOG_SVC,
        '[' + new Date().toISOString() + '] [' + level + '] [my-plugin] ' + msg + '\n');
    } catch (_) {}
  }

  // ── MODULE-SCOPE STATE (mandatory — plugin.stop must access these) ──────
  let unsubscribes = []; // ← MUST be here, NOT inside plugin.start
  let heartbeatTimer = null; // ← MUST be here, NOT inside plugin.start
  let myData = null; // other state variables here

  // ── PLUGIN DEFINITION ───────────────────────────────────────────────────
  const plugin = {
    id: PLUGIN_ID,
    name: 'My Plugin Name',
    description: 'What it does.',
    version: '1.0.0',
    schema: { type: 'object', properties: { debug: { type: 'boolean', default: false } } }
  };

  // ── plugin.start ─────────────────────────────────────────────────────────
  plugin.start = function(options) {
    const cfg = Object.assign({ debug: false }, options || {});

    // ALWAYS reset module-scope state at start
    unsubscribes = [];
    myData = null;

    svcLog('INFO', 'STARTUP: ' + PLUGIN_ID + ' v1.0.0');

    // Subscribe via subscriptionManager (capital M)
    app.subscriptionManager.subscribe(
      { context: 'vessels.self', subscribe: [
        { path: 'navigation.headingTrue', period: 500, policy: 'ideal', minPeriod: 200 }
      ]},
      unsubscribes, // ← pass module-scope array
      function(err) { svcLog('ERROR', 'subscribe: ' + err); },
      function(delta) { /* process delta */ }
    );

    heartbeatTimer = setInterval(function() {
      svcLog('DEBUG', 'HEARTBEAT: alive');
    }, 5 * 60 * 1000);

    if (app.setPluginStatus) app.setPluginStatus('Running');
    svcLog('INFO', 'STARTUP: complete');

    // ❌ DO NOT define plugin.stop here
  };

  // ── plugin.stop — OUTSIDE plugin.start ───────────────────────────────────
  // SK 2.25.0 checks typeof plugin.stop === 'function' at load time.
  // If plugin.stop is inside plugin.start, it is undefined at load → SK rejects plugin silently.
  plugin.stop = function() {
    svcLog('INFO', 'SHUTDOWN: stopping');
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
    unsubscribes.forEach(function(u) { try { u(); } catch (_) {} });
    unsubscribes = [];
    svcLog('INFO', 'SHUTDOWN: complete');
  };

  return plugin;
};
```

### ❌ WRONG PATTERN (causes silent rejection)

```javascript
plugin.start = function(options) {
  const unsubscribes = []; // ← WRONG: local scope

  // ... setup ...

  plugin.stop = function() { // ← WRONG: defined inside start
    unsubscribes.forEach(...);
  };
};
return plugin; // plugin.stop is undefined here → SK rejects
```

---

## 2. MANDATORY package.json

```json
{
  "name": "signalk-my-plugin",
  "version": "1.0.0",
  "main": "signalk-my-plugin.js",
  "license": "MIT",
  "keywords": ["signalk", "signalk-node-server-plugin"]
}
```

**Critical field:** `"signalk-node-server-plugin"` in `keywords`.
SK's plugin scanner (`src/modules.ts → findModulesInDir`) checks this keyword.
Missing it = plugin never discovered = never loaded.

---

## 3. DEPLOYMENT PROCEDURE (SK 2.25.0)

### Why NOT ~/.signalk/node_modules/

SK scans two directories (from `src/modules.ts → getModulePaths()`):
1. `~/.signalk/node_modules/` — **unreliable**: SK service may run as a different user
   than the config directory owner → `fs.readdirSync()` fails silently
2. `/usr/lib/node_modules/signalk-server/node_modules/` — **always works**: world-readable,
   same directory SK runs from

**Always deploy to the appPath location.**

### Deploy commands (for every new plugin)

```bash
SK_NM=/usr/lib/node_modules/signalk-server/node_modules
REPO=/home/aneto/midnightrider-navigation

# Deploy
sudo mkdir -p $SK_NM/<plugin-name>
sudo cp $REPO/plugins/<plugin-name>.js $SK_NM/<plugin-name>/<plugin-name>.js
sudo cp $REPO/plugins/<plugin-name>-package.json $SK_NM/<plugin-name>/package.json

# Activate (add to settings.json via python3, then restart)
sudo systemctl restart signalk

# Verify appears in UI (should see plugin in SK Plugin Configuration)
curl -s http://localhost:3000/plugins/list | python3 -c "
import json,sys
data=json.load(sys.stdin)
plugins=data if isinstance(data,list) else list(data.values())
for p in plugins:
  if '<plugin-name>' in p.get('id',''):
    print('FOUND:', p.get('id'), '| enabled=', p.get('enabled'))
"
```

### Verify discovery before troubleshooting

```bash
# 1. Keyword present?
python3 -c "
import json
d=json.load(open('/usr/lib/node_modules/signalk-server/node_modules/<plugin>/package.json'))
print('keywords:', d.get('keywords'))
print('OK:', 'signalk-node-server-plugin' in d.get('keywords',[]))
"

# 2. plugin.stop defined at factory return time?
grep -n "plugin\.stop" plugins/<plugin-name>.js
# Must show at least 2 lines, NEITHER inside plugin.start block

# 3. Syntax check
node --check plugins/<plugin-name>.js
```

---

## 4. SETTINGS.JSON ACTIVATION

SK uses settings.json for plugin configuration, not for plugin discovery.
Still needed to enable the plugin:

```python
import json
path = '/home/aneto/.signalk/settings.json'
with open(path) as f:
  d = json.load(f)
if 'plugins' not in d:
  d['plugins'] = {}
d['plugins']['signalk-my-plugin'] = {
  'enabled': True,
  'configuration': { 'debug': False }
}
with open(path,'w') as f:
  json.dump(d, f, indent=2)
```

---

## 5. LOGGING CONVENTIONS

```javascript
// Log file location
const LOG_SVC = '/home/aneto/midnightrider-navigation/logs/services/<plugin>.log';
const LOG_FLOW = '/home/aneto/midnightrider-navigation/logs/debug/data-flow.log';

// Log permissions: SK service user may differ from repo owner
// Fix if logs are empty after deployment:
// sudo chmod -R 777 /home/aneto/midnightrider-navigation/logs/

// Mandatory probe points in plugin.start():
svcLog('INFO', 'STARTUP: ' + PLUGIN_ID + ' vX.Y.Z');
svcLog('INFO', 'CONFIG: key=value key2=value2');
svcLog('INFO', 'DEPENDENCY_CHECK: subscribed to path1 + path2');
svcLog('INFO', 'STARTUP: complete');

// Mandatory probe in plugin.stop():
svcLog('INFO', 'SHUTDOWN: stopping — stats=' + JSON.stringify(stats));
svcLog('INFO', 'SHUTDOWN: complete');

// Periodic heartbeat (every 5 min):
heartbeatTimer = setInterval(function() {
  svcLog('DEBUG', 'HEARTBEAT: derived=N skip=N err=N');
}, 5 * 60 * 1000);

// NEVER log: tokens, passwords, API keys, secrets
```

---

## 6. SK API COMPATIBILITY (SK 2.25.0)

```javascript
// ✅ These APIs exist in SK 2.25.0:
app.subscriptionManager.subscribe(...) // capital M — use this for subscriptions
app.handleMessage(pluginId, delta) // publish data to SK
app.getSelfPath('navigation.headingTrue') // read current SK value
app.debug('message') // SK debug output
app.error('message') // SK error output
if (app.setPluginStatus) app.setPluginStatus('text') // guard: older versions lack this

// ❌ These do NOT exist or are unreliable:
app.subscriptionmanager // lowercase m — typo, undefined
app.removeAllListeners() // DANGEROUS: removes ALL SK event listeners globally
app.signalk.self.path // internal API — unstable across versions
```

---

## 7. QUICK CHECKLIST BEFORE DEPLOYING ANY PLUGIN

```
□ plugin.stop defined OUTSIDE plugin.start
□ unsubscribes = [] at module scope (not inside start)
□ heartbeatTimer at module scope
□ All data state variables at module scope
□ app.subscriptionManager (capital M)
□ if (app.setPluginStatus) guard on setPluginStatus calls
□ package.json has "signalk-node-server-plugin" in keywords
□ package.json "main" points to correct JS filename
□ node --check passes
□ Deployed to /usr/lib/node_modules/signalk-server/node_modules/
□ settings.json updated with enabled: true
□ SK restarted via systemctl (never docker)
□ Plugin appears in SK UI Plugin Configuration page
□ sudo chmod -R 777 /home/aneto/midnightrider-navigation/logs/ if logs empty
```

---

## 8. REFERENCE IMPLEMENTATION

See plugins/signalk-um982-gnss.js — a working plugin on this vessel that follows
the correct structure. Its pattern (plugin.stop outside start, module-scope state)
is the reference for all new plugins.

Working plugins on this vessel (SK 2.25.0):
- signalk-heading-true-calculator v1.0.2 — navigation.headingTrue
- signalk-j30-leeway v1.0.1 — performance.leewayAngle
- signalk-current-calculator v1.0.0 — environment.current.setTrue + drift

---

## 9. COLD-START / subscriptionManager ISSUE

### Problem
`app.subscriptionManager` is undefined in SK 2.25.0 when plugin.start() is called.
Error: *Cannot read properties of undefined (reading 'subscribe')*

### Fix — use setInterval + getSelfPath

```javascript
// ❌ BROKEN in SK 2.25.0:
app.subscriptionManager.subscribe({ context: 'vessels.self', subscribe: [...] }, ...);

// ✅ CORRECT:
pollTimer = setInterval(function() {
  var obj = app.getSelfPath('navigation.headingMagnetic');
  if (!obj || obj.value == null) return;
  if (obj.timestamp && Date.now()-new Date(obj.timestamp).getTime() > maxAgeMs) return;
  // use obj.value
}, 500);
```
