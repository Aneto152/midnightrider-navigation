'use strict';
/**
 * @file signalk-current-calculator.js
 * @version 1.0.3
 * @license MIT
 * CHANGELOG
 * v1.0.2 — Event-driven: fires on every SOG update (GPS cadence).
 * streambundle.getSelfBus() primary, delta handler fallback.
 * Reads headingTrue (P1), leewayAngle (P2) via getSelfPath.
 * v1.0.1 — setInterval+getSelfPath (cold-start fix)
 * v1.0.0 — Initial release
 */
const fs = require('fs');
const PLUGIN_ID = 'signalk-current-calculator';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/current-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const MS_TO_KTS = 1 / 0.5144;
const RAD_TO_DEG = 180 / Math.PI;
const TWO_PI = 2 * Math.PI;

module.exports = function(app) {
  function ensureDirs(){try{fs.mkdirSync(LOG_BASE+'/services',{recursive:true});fs.mkdirSync(LOG_BASE+'/debug',{recursive:true});}catch(_){}}
  function rotateIfNeeded(f){try{if(fs.existsSync(f)&&fs.statSync(f).size>MAX_BYTES)fs.renameSync(f,f+'.1');}catch(_){}}
  function svcLog(level,msg){try{ensureDirs();rotateIfNeeded(LOG_SVC);fs.appendFileSync(LOG_SVC,'['+new Date().toISOString()+'] ['+level+'] [current-calc] '+msg+'\n');}catch(_){}}
  function flowLog(msg){try{rotateIfNeeded(LOG_FLOW);fs.appendFileSync(LOG_FLOW,'['+new Date().toISOString()+'] [FLOW] '+msg+'\n');}catch(_){}}

  let unsubscribes = [];
  let heartbeatTimer = null;
  let smoothN = null, smoothE = null;
  let stats = { derived:0, skipped:0, errors:0 };

  // ── Core compute — called on every SOG update ─────────────────────────────
  function computeAndPublish(sogValue, cfg) {
    try {
      var maxAgeMs = cfg.maxDataAgeSecs * 1000;
      var now = Date.now();
      function getVal(path) {
        var o = app.getSelfPath(path);
        if (!o || o.value == null) return null;
        // staleness filter removed — use any available value
        return o.value;
      }
      var sog = sogValue;
      var ht = getVal('navigation.headingTrue');
      var stw = getVal('navigation.speedThroughWater');
      var cog = getVal('navigation.courseOverGroundTrue');
      var lwy = getVal('performance.leewayAngle');

      if (ht==null||stw==null||cog==null||sog==null) { stats.skipped++; return; }
      if (!isFinite(ht)||!isFinite(stw)||!isFinite(cog)||!isFinite(sog)) { stats.errors++; return; }
      // minSOG/minSTW guards removed — publish if data present

      var leeway = (lwy != null && isFinite(lwy) && Math.abs(lwy) < Math.PI/4) ? lwy : 0;
      var ctw = ht + leeway;
      var rawN = sog * Math.cos(cog) - stw * Math.cos(ctw);
      var rawE = sog * Math.sin(cog) - stw * Math.sin(ctw);

      if (smoothN == null) { smoothN = rawN; smoothE = rawE; }
      else { var a = cfg.smoothingAlpha; smoothN = a*smoothN + (1-a)*rawN; smoothE = a*smoothE + (1-a)*rawE; }

      var drift = Math.sqrt(smoothN*smoothN + smoothE*smoothE);
      var setRad = ((Math.atan2(smoothE, smoothN) % TWO_PI) + TWO_PI) % TWO_PI;

      if (drift * MS_TO_KTS > cfg.maxCurrentKts) { stats.skipped++; return; }
      if (!isFinite(drift) || !isFinite(setRad)) { stats.errors++; return; }

      app.handleMessage(PLUGIN_ID, { updates: [{ source: { label:PLUGIN_ID, type:'derived' },
        timestamp: new Date().toISOString(),
        values: [{ path:'environment.current.setTrue', value:setRad },
          { path:'environment.current.drift', value:drift }] }]
      });
      stats.derived++;
      var sD=(setRad*RAD_TO_DEG).toFixed(1), dK=(drift*MS_TO_KTS).toFixed(2);
      if (cfg.debug) svcLog('DEBUG','set='+sD+'deg drift='+dK+'kts n='+stats.derived);
      flowLog('NavCalc→SK: set='+sD+'degT drift='+dK+'kts ['+PLUGIN_ID+']');
      if (app.setPluginStatus) app.setPluginStatus('Set='+sD+'degT Drift='+dK+'kts | n='+stats.derived);
    } catch(e) { stats.errors++; svcLog('ERROR','compute: '+e.message); }
  }

  const plugin = {
    id: PLUGIN_ID,
    name: 'Water Current Calculator (Set & Drift)',
    description: 'Event-driven on SOG updates. CTW=HT+leeway. EMA smoothed.',
    version: '1.0.3',
    schema: { type:'object', title:'Water Current Calculator', properties: {
      minSOG: { type:'number', title:'Min SOG m/s', default:0.3, minimum:0, maximum:2.0 },
      minSTW: { type:'number', title:'Min STW m/s', default:0.3, minimum:0, maximum:2.0 },
      maxDataAgeSecs:{ type:'number', title:'Max input age s', default:10, minimum:2, maximum:60 },
      smoothingAlpha:{ type:'number', title:'EMA alpha', default:0.7, minimum:0, maximum:0.95 },
      maxCurrentKts: { type:'number', title:'Max current kts', default:5, minimum:1, maximum:10 },
      debug: { type:'boolean',title:'Debug logging', default:false }
    }}
  };

  plugin.start = function(options) {
    var cfg = Object.assign(
      { minSOG:0.3, minSTW:0.3, maxDataAgeSecs:10, smoothingAlpha:0.7, maxCurrentKts:5, debug:false },
      options || {}
    );
    cfg.minSOG = Math.max(0, Math.min(2.0, Number(cfg.minSOG) || 0.3));
    cfg.minSTW = Math.max(0, Math.min(2.0, Number(cfg.minSTW) || 0.3));
    cfg.maxDataAgeSecs = Math.max(2, Math.min(60, Number(cfg.maxDataAgeSecs)|| 10));
    cfg.smoothingAlpha = Math.max(0, Math.min(0.95,Number(cfg.smoothingAlpha)|| 0.7));
    cfg.maxCurrentKts = Math.max(1, Math.min(10, Number(cfg.maxCurrentKts) || 5));
    smoothN = null; smoothE = null;
    unsubscribes = [];
    stats = { derived:0, skipped:0, errors:0 };

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.2');
    svcLog('INFO','CONFIG: alpha='+cfg.smoothingAlpha+' maxCurrent='+cfg.maxCurrentKts+'kts');
    if (app.setPluginStatus) app.setPluginStatus('Initialising...');

    var subscribed = false;

    // Method 1: streambundle on SOG (GPS cadence trigger)
    try {
      if (app.streambundle && typeof app.streambundle.getSelfBus === 'function') {
        var bus = app.streambundle.getSelfBus('navigation.speedOverGround');
        if (bus && typeof bus.onValue === 'function') {
          var unsub = bus.onValue(function(val) {
            var sogValue = (val !== null && typeof val === 'object' && 'value' in val) ? val.value : val;
            computeAndPublish(sogValue, cfg);
          });
          unsubscribes.push(unsub);
          subscribed = true;
          svcLog('INFO','SUBSCRIPTION: streambundle.getSelfBus(speedOverGround) ✅');
        }
      }
    } catch(e) { svcLog('WARN','streambundle: '+e.message); }

    // Method 2: delta handler fallback
    if (!subscribed) {
      try {
        if (typeof app.registerDeltaInputHandler === 'function') {
          app.registerDeltaInputHandler(function(delta, next) {
            try {
              if (delta && delta.updates) {
                delta.updates.forEach(function(u) {
                  if (u && u.values) {
                    u.values.forEach(function(pv) {
                      if (pv && pv.path === 'navigation.speedOverGround' && pv.value != null)
                        computeAndPublish(pv.value, cfg);
                    });
                  }
                });
              }
            } catch(e) { svcLog('ERROR','deltaHandler: '+e.message); }
            next(delta);
          });
          subscribed = true;
          svcLog('INFO','SUBSCRIPTION: registerDeltaInputHandler ✅');
        }
      } catch(e) { svcLog('WARN','deltaHandler: '+e.message); }
    }

    // Method 3: polling fallback
    if (!subscribed) {
      var fb = setInterval(function() {
        var s = app.getSelfPath('navigation.speedOverGround');
        if (s && s.value != null) computeAndPublish(s.value, cfg);
      }, 1000);
      unsubscribes.push(function(){ clearInterval(fb); });
      svcLog('WARN','SUBSCRIPTION: polling fallback 1000ms');
    }

    heartbeatTimer = setInterval(function() {
      var dk = smoothN!=null ?(Math.sqrt(smoothN*smoothN+smoothE*smoothE)*MS_TO_KTS).toFixed(2)+'kts' : 'N/A';
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped+' drift='+dk);
    }, 5*60*1000);
    svcLog('INFO','STARTUP: complete');
  };

  plugin.stop = function() {
    svcLog('INFO','SHUTDOWN: '+JSON.stringify(stats));
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
    unsubscribes.forEach(function(u){ try{ if(typeof u==='function') u(); }catch(_){} });
    unsubscribes = [];
    smoothN = null; smoothE = null;
    svcLog('INFO','SHUTDOWN: complete');
  };

  return plugin;
};
