'use strict';
/**
 * @file signalk-heading-true-calculator.js
 * @version 1.0.6
 * @license MIT
 * CHANGELOG
 * v1.0.6 — Fix: own-output source check. SK 2.x uses $source (string).
 * v1.0.6 — Fix source check: handle $source (SK 2.x). Own output never treated as external.
 * v1.0.5 — Event-driven: fires on every headingMagnetic update.
 * Primary: app.streambundle.getSelfBus() (SK 2.x Bacon.js stream).
 * Fallback: app.registerDeltaInputHandler() (delta middleware).
 * checkTimer (10s): detects if external instrument provides headingTrue.
 * Computes at natural instrument cadence — no fixed poll rate.
 * v1.0.4 — Two-timer architecture (still polling-based)
 * v1.0.3 — Replace subscriptionManager with setInterval+getSelfPath
 */
const fs = require('fs');
const PLUGIN_ID = 'signalk-heading-true-calculator';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/heading-true-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const TWO_PI = 2 * Math.PI;

module.exports = function(app) {
  function ensureDirs(){try{fs.mkdirSync(LOG_BASE+'/services',{recursive:true});fs.mkdirSync(LOG_BASE+'/debug',{recursive:true});}catch(_){}}
  function rotateIfNeeded(f){try{if(fs.existsSync(f)&&fs.statSync(f).size>MAX_BYTES)fs.renameSync(f,f+'.1');}catch(_){}}
  function svcLog(level,msg){try{ensureDirs();rotateIfNeeded(LOG_SVC);fs.appendFileSync(LOG_SVC,'['+new Date().toISOString()+'] ['+level+'] [heading-true-calc] '+msg+'\n');}catch(_){}}
  function flowLog(msg){try{rotateIfNeeded(LOG_FLOW);fs.appendFileSync(LOG_FLOW,'['+new Date().toISOString()+'] [FLOW] '+msg+'\n');}catch(_){}}

  // Module-scope state
  let unsubscribes = [];
  let checkTimer = null;
  let heartbeatTimer = null;
  let stats = { derived:0, skipped:0, errors:0 };
  let externalHTActive = false;

  // ── Core compute function — called on every headingMagnetic event ─────────
  function computeAndPublish(hmValue, cfg) {
    try {
      if (externalHTActive) { stats.skipped++; return; }
      if (hmValue == null || !isFinite(hmValue) || isNaN(hmValue) || Math.abs(hmValue) > 4*Math.PI) {
        stats.errors++; return;
      }
      var variation = 0;
      var mvObj = app.getSelfPath('navigation.magneticVariation');
      if (mvObj && mvObj.value != null && isFinite(mvObj.value) && !isNaN(mvObj.value))
        variation = Math.max(-Math.PI, Math.min(Math.PI, mvObj.value));

      var ht = (((hmValue + variation) % TWO_PI) + TWO_PI) % TWO_PI;
      if (!isFinite(ht)) { stats.errors++; return; }

      app.handleMessage(PLUGIN_ID, { updates: [{ source: { label:PLUGIN_ID, type:'derived' },
        timestamp: new Date().toISOString(),
        values: [{ path:'navigation.headingTrue', value:ht }] }]
      });
      stats.derived++;
      var htD=(ht*180/Math.PI).toFixed(1), hmD=(hmValue*180/Math.PI).toFixed(1), vD=(variation*180/Math.PI).toFixed(2);
      if (cfg.debug) svcLog('DEBUG','HT='+htD+'deg HM='+hmD+'deg Var='+vD+'deg n='+stats.derived);
      flowLog('Compass→SK: headingTrue='+htD+'deg ['+PLUGIN_ID+']');
      if (app.setPluginStatus) app.setPluginStatus('HT='+htD+'deg | pub='+stats.derived+' ext='+externalHTActive);
    } catch(e) { stats.errors++; svcLog('ERROR','compute: '+e.message); }
  }

  const plugin = {
    id: PLUGIN_ID,
    name: 'True Heading Calculator (Magnetic + Variation)',
    description: 'Event-driven: fires on every headingMagnetic update. ' +
      'Defers to external instrument when active (checked every 10s).',
    version: '1.0.6',
    schema: { type:'object', title:'True Heading Calculator', properties: {
      debug: { type:'boolean', title:'Debug logging', default:false },
      checkIntervalS: { type:'number', title:'External HT check interval (s)', default:10, minimum:5, maximum:60 },
      maxHMAgeSecs: { type:'number', title:'Max headingMagnetic age (s)', default:5, minimum:1, maximum:30 },
      externalStaleS: { type:'number', title:'External HT stale threshold (s)', default:12, minimum:5, maximum:60 }
    }}
  };

  plugin.start = function(options) {
    var cfg = Object.assign(
      { debug:false, checkIntervalS:10, maxHMAgeSecs:5, externalStaleS:12 },
      options || {}
    );
    cfg.checkIntervalS = Math.max(5, Math.min(60, Number(cfg.checkIntervalS) || 10));
    cfg.maxHMAgeSecs = Math.max(1, Math.min(30, Number(cfg.maxHMAgeSecs) || 5));
    cfg.externalStaleS = Math.max(5, Math.min(60, Number(cfg.externalStaleS) || 12));
    unsubscribes = [];
    stats = { derived:0, skipped:0, errors:0 };
    externalHTActive = false;

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.6');
    svcLog('INFO','CONFIG: checkInterval='+cfg.checkIntervalS+'s externalStale='+cfg.externalStaleS+'s');
    if (app.setPluginStatus) app.setPluginStatus('Initialising...');

    // ── TIMER: every 10s — check if external instrument provides headingTrue ─
    function checkExternalHT() {
      try {
        var htObj = app.getSelfPath('navigation.headingTrue');
        if (htObj && htObj.value != null) {
          // Extract source — SK 2.x uses $source (string)
          var src = '';
          if (htObj.$source && typeof htObj.$source === 'string') {
            src = htObj.$source;
          } else if (htObj.source && htObj.source.label) {
            src = htObj.source.label;
          }
          // Check if this value is OUR OWN output
          var isOurOutput = (src.indexOf(PLUGIN_ID) >= 0);
          
          if (!isOurOutput && src !== '') {
            // Genuine external source
            var age = htObj.timestamp ? (Date.now()-new Date(htObj.timestamp).getTime())/1000 : Infinity;
            var prev = externalHTActive;
            externalHTActive = (age < cfg.externalStaleS);
            if (prev !== externalHTActive)
              svcLog('INFO','external HT: active='+externalHTActive+' src='+src+' age='+age.toFixed(1)+'s');
          } else {
            // Our own output or unknown source — never treat as external
            if (externalHTActive) svcLog('INFO','external HT cleared: src='+src+' (our output or unknown)');
            externalHTActive = false;
          }
        } else { externalHTActive = false; }
      } catch(e) { svcLog('ERROR','checkExternal: '+e.message); }
    }
    checkExternalHT();
    checkTimer = setInterval(checkExternalHT, cfg.checkIntervalS * 1000);

    // ── EVENT-DRIVEN: fire on every headingMagnetic update ───────────────────
    var subscribed = false;

    // Method 1: app.streambundle.getSelfBus() — fires on every SK value update
    try {
      if (app.streambundle && typeof app.streambundle.getSelfBus === 'function') {
        var bus = app.streambundle.getSelfBus('navigation.headingMagnetic');
        if (bus && typeof bus.onValue === 'function') {
          var unsub = bus.onValue(function(val) {
            // getSelfBus returns SKValue object {value, source, timestamp} or raw value
            var hmValue = (val !== null && typeof val === 'object' && 'value' in val)
              ? val.value : val;
            computeAndPublish(hmValue, cfg);
          });
          unsubscribes.push(unsub);
          subscribed = true;
          svcLog('INFO','SUBSCRIPTION: streambundle.getSelfBus — event-driven ✅');
        }
      }
    } catch(e) { svcLog('WARN','streambundle failed: '+e.message); }

    // Method 2: registerDeltaInputHandler — fallback if streambundle unavailable
    if (!subscribed) {
      try {
        if (typeof app.registerDeltaInputHandler === 'function') {
          app.registerDeltaInputHandler(function(delta, next) {
            try {
              if (delta && delta.updates) {
                delta.updates.forEach(function(u) {
                  if (u && u.values) {
                    u.values.forEach(function(pv) {
                      if (pv && pv.path === 'navigation.headingMagnetic' && pv.value != null) {
                        computeAndPublish(pv.value, cfg);
                      }
                    });
                  }
                });
              }
            } catch(e) { svcLog('ERROR','deltaHandler: '+e.message); }
            next(delta);
          });
          subscribed = true;
          svcLog('INFO','SUBSCRIPTION: registerDeltaInputHandler — event-driven ✅');
        }
      } catch(e) { svcLog('WARN','registerDeltaInputHandler failed: '+e.message); }
    }

    // Method 3: Final fallback — fast polling if both event methods unavailable
    if (!subscribed) {
      svcLog('WARN','Event-driven unavailable — polling fallback @ 200ms');
      var fallbackTimer = setInterval(function() {
        var hmObj = app.getSelfPath('navigation.headingMagnetic');
        if (!hmObj || hmObj.value == null) return;
        var age = hmObj.timestamp ? (Date.now()-new Date(hmObj.timestamp).getTime())/1000 : 0;
        if (age > cfg.maxHMAgeSecs) return;
        computeAndPublish(hmObj.value, cfg);
      }, 200);
      unsubscribes.push(function(){ clearInterval(fallbackTimer); });
      svcLog('INFO','SUBSCRIPTION: polling fallback 200ms');
    }

    heartbeatTimer = setInterval(function(){
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped
        +' err='+stats.errors+' extActive='+externalHTActive);
    }, 5*60*1000);

    svcLog('INFO','STARTUP: complete');
  };

  // plugin.stop OUTSIDE plugin.start — SK 2.25.0 requirement
  plugin.stop = function() {
    svcLog('INFO','SHUTDOWN: '+JSON.stringify(stats));
    if (checkTimer) { clearInterval(checkTimer); checkTimer=null; }
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer=null; }
    unsubscribes.forEach(function(u){ try{ if(typeof u==='function') u(); }catch(_){} });
    unsubscribes = [];
    svcLog('INFO','SHUTDOWN: complete');
  };

  return plugin;
};

// ── Pure math export for unit testing (do not call from plugin code) ──
function _computeHeadingTrue(hmRad, variationRad) {
  if (hmRad == null || !isFinite(hmRad) || isNaN(hmRad)) return null;
  var v = (variationRad != null && isFinite(variationRad) && !isNaN(variationRad)) ? variationRad : 0;
  v = Math.max(-Math.PI, Math.min(Math.PI, v));
  var ht = (((hmRad + v) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  return isFinite(ht) ? ht : null;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports._computeHeadingTrue = _computeHeadingTrue;
}
