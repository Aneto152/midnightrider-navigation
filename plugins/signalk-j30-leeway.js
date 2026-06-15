'use strict';
/**
 * @file signalk-j30-leeway.js
 * @version 1.0.4
 * @license MIT
 * CHANGELOG
 * v1.0.3 — Event-driven: fires on every attitude.roll update (IMU cadence).
 * streambundle.getSelfBus() primary, delta handler fallback.
 * No source-check needed: leewayAngle is always our output.
 * v1.0.2 — setInterval+getSelfPath (cold-start fix)
 * v1.0.1 — plugin.stop outside plugin.start
 */
const fs = require('fs');
const PLUGIN_ID = 'signalk-j30-leeway';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/j30-leeway-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const MS_TO_KTS = 1 / 0.5144;
const DEG_TO_RAD = Math.PI / 180;

module.exports = function(app) {
  function ensureDirs(){try{fs.mkdirSync(LOG_BASE+'/services',{recursive:true});fs.mkdirSync(LOG_BASE+'/debug',{recursive:true});}catch(_){}}
  function rotateIfNeeded(f){try{if(fs.existsSync(f)&&fs.statSync(f).size>MAX_BYTES)fs.renameSync(f,f+'.1');}catch(_){}}
  function svcLog(level,msg){try{ensureDirs();rotateIfNeeded(LOG_SVC);fs.appendFileSync(LOG_SVC,'['+new Date().toISOString()+'] ['+level+'] [j30-leeway-calc] '+msg+'\n');}catch(_){}}
  function flowLog(msg){try{rotateIfNeeded(LOG_FLOW);fs.appendFileSync(LOG_FLOW,'['+new Date().toISOString()+'] [FLOW] '+msg+'\n');}catch(_){}}

  let unsubscribes = [];
  let heartbeatTimer = null;
  let stats = { derived:0, skipped:0, errors:0 };

  // ── Core compute — called on every attitude.roll event ───────────────────
  function computeAndPublish(rollValue, cfg) {
    try {
      if (rollValue == null || !isFinite(rollValue) || isNaN(rollValue) || Math.abs(rollValue) > Math.PI) {
        stats.errors++; return;
      }

      var speedKts = 0, speedSrc = 'none';
      var stwObj = app.getSelfPath('navigation.speedThroughWater');
      var sogObj = app.getSelfPath('navigation.speedOverGround');
      if (stwObj && stwObj.value != null && isFinite(stwObj.value) && stwObj.value >= 0) {
        speedKts = stwObj.value * MS_TO_KTS; speedSrc = 'STW';
      } else if (sogObj && sogObj.value != null && isFinite(sogObj.value) && sogObj.value >= 0) {
        speedKts = sogObj.value * MS_TO_KTS; speedSrc = 'SOG';
      }

      var heelDeg = rollValue * 180 / Math.PI;
      var lwyRad = 0;
      if (speedKts >= cfg.minSpeed && Math.abs(heelDeg) >= cfg.minHeel) {
        var lwyDeg = Math.min(cfg.leewayFactor * Math.abs(heelDeg) / (speedKts * speedKts), cfg.maxLeeway);
        lwyRad = cfg.leewaySign * (rollValue >= 0 ? 1 : -1) * lwyDeg * DEG_TO_RAD;
      }
      if (!isFinite(lwyRad)) { stats.errors++; return; }

      app.handleMessage(PLUGIN_ID, { updates: [{ source: { label:PLUGIN_ID, type:'derived' },
        timestamp: new Date().toISOString(),
        values: [{ path:'performance.leewayAngle', value:lwyRad }] }]
      });
      stats.derived++;
      var lD = (lwyRad * 180 / Math.PI).toFixed(1);
      if (cfg.debug) svcLog('DEBUG','leeway='+lD+'deg Heel='+heelDeg.toFixed(1)+' Spd='+speedKts.toFixed(2)+'kts('+speedSrc+')');
      flowLog('J30→SK: leeway='+lD+'deg ['+PLUGIN_ID+']');
      if (app.setPluginStatus) app.setPluginStatus('Leeway='+lD+'deg pub='+stats.derived);
    } catch(e) { stats.errors++; svcLog('ERROR','compute: '+e.message); }
  }

  const plugin = {
    id: PLUGIN_ID,
    name: 'J/30 Leeway Calculator',
    description: 'Event-driven on attitude.roll. Leeway(deg)=K×|Heel|/STW². SOG fallback.',
    version: '1.0.4',
    schema: { type:'object', title:'J/30 Leeway Calculator', properties: {
      leewayFactor: { type:'number', title:'K (J/30: 10-14)', default:12, minimum:5, maximum:25 },
      minSpeed: { type:'number', title:'Min speed kts', default:0.5, minimum:0.1, maximum:3.0 },
      maxLeeway: { type:'number', title:'Max leeway deg', default:15, minimum:5, maximum:30 },
      minHeel: { type:'number', title:'Min heel deg', default:1.0, minimum:0.5, maximum:5.0 },
      leewaySign: { type:'number', title:'Sign (-1 or +1)', default:-1, enum:[-1,1] },
      debug: { type:'boolean',title:'Debug logging', default:false }
    }}
  };

  plugin.start = function(options) {
    var cfg = Object.assign(
      { leewayFactor:12, minSpeed:0.5, maxLeeway:15, minHeel:1.0, leewaySign:-1, debug:false },
      options || {}
    );
    cfg.leewayFactor = Math.max(5, Math.min(25, Number(cfg.leewayFactor) || 12));
    cfg.minSpeed = Math.max(0.1, Math.min(3.0, Number(cfg.minSpeed) || 0.5));
    cfg.maxLeeway = Math.max(5, Math.min(30, Number(cfg.maxLeeway) || 15));
    cfg.minHeel = Math.max(0.5, Math.min(5.0, Number(cfg.minHeel) || 1.0));
    cfg.leewaySign = (cfg.leewaySign === 1) ? 1 : -1;
    unsubscribes = [];
    stats = { derived:0, skipped:0, errors:0 };

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.3');
    svcLog('INFO','CONFIG: K='+cfg.leewayFactor+' minSpeed='+cfg.minSpeed+'kts');
    if (app.setPluginStatus) app.setPluginStatus('Initialising...');

    var subscribed = false;

    // Method 1: streambundle — fires on every attitude.roll update
    try {
      if (app.streambundle && typeof app.streambundle.getSelfBus === 'function') {
        var bus = app.streambundle.getSelfBus('navigation.attitude.roll');
        if (bus && typeof bus.onValue === 'function') {
          var unsub = bus.onValue(function(val) {
            var rollValue = (val !== null && typeof val === 'object' && 'value' in val) ? val.value : val;
            computeAndPublish(rollValue, cfg);
          });
          unsubscribes.push(unsub);
          subscribed = true;
          svcLog('INFO','SUBSCRIPTION: streambundle.getSelfBus(attitude.roll) ✅');
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
                      if (pv && pv.path === 'navigation.attitude.roll' && pv.value != null)
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

    // Method 3: fast polling fallback
    if (!subscribed) {
      var fb = setInterval(function() {
        var r = app.getSelfPath('navigation.attitude.roll');
        if (r && r.value != null) computeAndPublish(r.value, cfg);
      }, 200);
      unsubscribes.push(function(){ clearInterval(fb); });
      svcLog('WARN','SUBSCRIPTION: polling fallback 200ms');
    }

    // Degraded mode: monitor WIT IMU absence
    var instrumentMonitor = setInterval(function() {
      var roll = app.getSelfPath('navigation.attitude.roll');
      var ageMs = roll && roll.timestamp ? Date.now() - new Date(roll.timestamp).getTime() : Infinity;
      if (ageMs > 30000) {
        var ageSec = Math.round(ageMs / 1000);
        svcLog('WARN', 'DEGRADED: WIT IMU absent for ' + ageSec + 's — leeway=0');
        if (app.setPluginStatus) app.setPluginStatus('⚠️ WIT IMU absent (' + ageSec + 's)');
      }
    }, 30000);
    unsubscribes.push(function() { clearInterval(instrumentMonitor); });

    heartbeatTimer = setInterval(function() {
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped+' err='+stats.errors);
    }, 5*60*1000);
    svcLog('INFO','STARTUP: complete');
  };

  plugin.stop = function() {
    svcLog('INFO','SHUTDOWN: '+JSON.stringify(stats));
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
    unsubscribes.forEach(function(u){ try{ if(typeof u==='function') u(); }catch(_){} });
    unsubscribes = [];
    svcLog('INFO','SHUTDOWN: complete');
  };

  return plugin;
};
