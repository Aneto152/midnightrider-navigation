'use strict';
/**
 * @file signalk-truewind-calculator.js
 * @version 1.0.1
 * @license MIT
 *
 * PURPOSE
 * Computes True Wind Direction (TWD), True Wind Speed (TWS) and
 * True Wind Angle (TWA) from apparent wind + boat velocity vector.
 *
 * FORMULA (vector math in Earth frame)
 * AWD_abs = headingTrue + AWA (absolute apparent wind FROM direction)
 * v_aw_N = -AWS x cos(AWD_abs) (apparent wind velocity, North component)
 * v_aw_E = -AWS x sin(AWD_abs) (apparent wind velocity, East component)
 * v_boat_N = SOG x cos(COG) (boat velocity North)
 * v_boat_E = SOG x sin(COG) (boat velocity East)
 * v_tw = v_aw + v_boat (true wind velocity = sum)
 * TWS = sqrt(v_tw_N^2 + v_tw_E^2)
 * TWD = atan2(v_tw_E, v_tw_N) + pi (direction wind comes FROM, normalized)
 * TWA = TWD - headingTrue (angle from bow, normalized +/-pi)
 *
 * INPUTS
 * navigation.windAngleApparent [rad] AWA from Calypso
 * navigation.windSpeedApparent [m/s] AWS from Calypso
 * navigation.headingTrue [rad] HT from Plugin 1
 * navigation.speedOverGround [m/s] SOG from GPS
 * navigation.courseOverGroundTrue [rad] COG from GPS
 *
 * OUTPUTS
 * environment.wind.directionTrue [rad] TWD clockwise from N
 * environment.wind.speedTrue [m/s] TWS
 * environment.wind.angleTrueGround [rad] TWA from bow (+/-pi, + = stbd)
 *
 * SK 2.25.0 PATTERN — PLUGIN-DEVELOPMENT-GUIDE.md
 * streambundle.getSelfBus() primary subscription.
 * plugin.stop OUTSIDE plugin.start.
 */
const fs = require('fs');
const PLUGIN_ID = 'signalk-truewind-calculator';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/truewind-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const TWO_PI = 2 * Math.PI;
const MS_TO_KTS = 1 / 0.5144;
const RAD_TO_DEG = 180 / Math.PI;

module.exports = function(app) {
  function ensureDirs(){try{fs.mkdirSync(LOG_BASE+'/services',{recursive:true});fs.mkdirSync(LOG_BASE+'/debug',{recursive:true});}catch(_){}}
  function rotateIfNeeded(f){try{if(fs.existsSync(f)&&fs.statSync(f).size>MAX_BYTES)fs.renameSync(f,f+'.1');}catch(_){}}
  function svcLog(level,msg){try{ensureDirs();rotateIfNeeded(LOG_SVC);fs.appendFileSync(LOG_SVC,'['+new Date().toISOString()+'] ['+level+'] [truewind-calc] '+msg+'\n');}catch(_){}}
  function flowLog(msg){try{rotateIfNeeded(LOG_FLOW);fs.appendFileSync(LOG_FLOW,'['+new Date().toISOString()+'] [FLOW] '+msg+'\n');}catch(_){}}

  let unsubscribes = [];
  let heartbeatTimer = null;
  let stats = { derived:0, skipped:0, errors:0 };

  function computeAndPublish(cfg) {
    try {
      var maxAgeMs = cfg.maxDataAgeSecs * 1000;
      var now = Date.now();
      function getVal(path) {
        var o = app.getSelfPath(path);
        if (!o || o.value == null) return null;
        if (o.timestamp && (now - new Date(o.timestamp).getTime()) > maxAgeMs) return null;
        return o.value;
      }
      var awa = getVal('navigation.windAngleApparent');
      var aws = getVal('navigation.windSpeedApparent');
      var ht = getVal('navigation.headingTrue');
      var sog = getVal('navigation.speedOverGround');
      var cog = getVal('navigation.courseOverGroundTrue');

      if (awa==null||aws==null||ht==null||sog==null||cog==null){stats.skipped++;return;}
      if (!isFinite(awa)||!isFinite(aws)||!isFinite(ht)||!isFinite(sog)||!isFinite(cog)){stats.errors++;return;}
      if (aws<0||aws>60||sog<0||sog>30){stats.errors++;return;}

      var awd_abs = ht + awa;
      var v_aw_N = -aws * Math.cos(awd_abs);
      var v_aw_E = -aws * Math.sin(awd_abs);
      var v_boat_N = sog * Math.cos(cog);
      var v_boat_E = sog * Math.sin(cog);
      var v_tw_N = v_aw_N + v_boat_N;
      var v_tw_E = v_aw_E + v_boat_E;

      var tws = Math.sqrt(v_tw_N*v_tw_N + v_tw_E*v_tw_E);
      if (!isFinite(tws)){stats.errors++;return;}
      if (tws * MS_TO_KTS > cfg.maxWindKts){stats.skipped++;return;}

      var twd = ((Math.atan2(v_tw_E, v_tw_N) + Math.PI) % TWO_PI + TWO_PI) % TWO_PI;

      var twa = twd - ht;
      while (twa > Math.PI) twa -= TWO_PI;
      while (twa < -Math.PI) twa += TWO_PI;

      if (!isFinite(twd)||!isFinite(twa)){stats.errors++;return;}

      app.handleMessage(PLUGIN_ID, { updates: [{ source:{ label:PLUGIN_ID, type:'derived' },
        timestamp: new Date().toISOString(),
        values: [
          { path:'environment.wind.directionTrue', value:twd },
          { path:'environment.wind.speedTrue', value:tws },
          { path:'environment.wind.angleTrueGround', value:twa }
        ]}]
      });
      stats.derived++;

      var twdD=(twd*RAD_TO_DEG).toFixed(1), twsK=(tws*MS_TO_KTS).toFixed(1), twaD=(twa*RAD_TO_DEG).toFixed(1);
      if (cfg.debug) svcLog('DEBUG','TWD='+twdD+'deg TWS='+twsK+'kts TWA='+twaD
        +' AWA='+(awa*RAD_TO_DEG).toFixed(1)+' AWS='+(aws*MS_TO_KTS).toFixed(1)+'kts');
      flowLog('Wind→SK: TWD='+twdD+'deg TWS='+twsK+'kts TWA='+twaD+'deg ['+PLUGIN_ID+']');
      if (app.setPluginStatus) app.setPluginStatus('TWD='+twdD+'degT TWS='+twsK+'kts TWA='+twaD+'deg | n='+stats.derived);
    } catch(e){ stats.errors++; svcLog('ERROR','compute: '+e.message); }
  }

  const plugin = {
    id: PLUGIN_ID,
    name: 'True Wind Calculator (TWD / TWS / TWA)',
    description: 'Event-driven on AWA. TWD/TWS/TWA from apparent wind + SOG/COG vector math.',
    version: '1.0.1',
    schema: { type:'object', title:'True Wind Calculator', properties: {
      maxDataAgeSecs:{ type:'number', title:'Max input age (s)', default:10, minimum:2, maximum:60 },
      maxWindKts: { type:'number', title:'Max TWS cap (kts)', default:70, minimum:5, maximum:120 },
      debug: { type:'boolean',title:'Debug logging', default:false }
    }}
  };

  plugin.start = function(options) {
    var cfg = Object.assign({ maxDataAgeSecs:10, maxWindKts:70, debug:false }, options||{});
    cfg.maxDataAgeSecs = Math.max(2, Math.min(60, Number(cfg.maxDataAgeSecs)||10));
    cfg.maxWindKts = Math.max(5, Math.min(120, Number(cfg.maxWindKts) ||70));
    unsubscribes = [];
    stats = { derived:0, skipped:0, errors:0 };

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.0');
    svcLog('INFO','CONFIG: maxAge='+cfg.maxDataAgeSecs+'s maxWind='+cfg.maxWindKts+'kts');
    if (app.setPluginStatus) app.setPluginStatus('Initialising...');

    var subscribed = false;

    try {
      if (app.streambundle && typeof app.streambundle.getSelfBus === 'function') {
        var bus = app.streambundle.getSelfBus('navigation.windAngleApparent');
        if (bus && typeof bus.onValue === 'function') {
          var unsub = bus.onValue(function() { computeAndPublish(cfg); });
          unsubscribes.push(unsub);
          subscribed = true;
          svcLog('INFO','SUBSCRIPTION: streambundle.getSelfBus(windAngleApparent) ✅');
        }
      }
    } catch(e){ svcLog('WARN','streambundle: '+e.message); }

    if (!subscribed) {
      try {
        if (typeof app.registerDeltaInputHandler === 'function') {
          app.registerDeltaInputHandler(function(delta, next) {
            try {
              if (delta && delta.updates) {
                var hasWind = false;
                delta.updates.forEach(function(u){
                  if (u && u.values) u.values.forEach(function(pv){
                    if (pv && (pv.path==='navigation.windAngleApparent'||
                      pv.path==='navigation.windSpeedApparent')) hasWind=true;
                  });
                });
                if (hasWind) computeAndPublish(cfg);
              }
            } catch(e){ svcLog('ERROR','deltaHandler: '+e.message); }
            next(delta);
          });
          subscribed = true;
          svcLog('INFO','SUBSCRIPTION: registerDeltaInputHandler ✅');
        }
      } catch(e){ svcLog('WARN','deltaHandler: '+e.message); }
    }

    if (!subscribed) {
      var fb = setInterval(function(){ computeAndPublish(cfg); }, 1000);
      unsubscribes.push(function(){ clearInterval(fb); });
      svcLog('WARN','SUBSCRIPTION: polling fallback 1000ms');
    }

    // Degraded mode: monitor Calypso anemometer absence
    var instrumentMonitor = setInterval(function() {
      var awa = app.getSelfPath('environment.wind.angleApparent');
      var ageMs = awa && awa.timestamp ? Date.now() - new Date(awa.timestamp).getTime() : Infinity;
      if (ageMs > 30000) {
        var ageSec = Math.round(ageMs / 1000);
        svcLog('WARN', 'DEGRADED: Calypso anemometer absent for ' + ageSec + 's — TWD/TWS stale');
        if (app.setPluginStatus) app.setPluginStatus('⚠️ Calypso absent (' + ageSec + 's)');
      }
    }, 30000);
    unsubscribes.push(function() { clearInterval(instrumentMonitor); });

    heartbeatTimer = setInterval(function(){
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped+' err='+stats.errors);
    }, 5*60*1000);
    svcLog('INFO','STARTUP: complete');
  };

  plugin.stop = function() {
    svcLog('INFO','SHUTDOWN: '+JSON.stringify(stats));
    if (heartbeatTimer){ clearInterval(heartbeatTimer); heartbeatTimer=null; }
    unsubscribes.forEach(function(u){ try{ if(typeof u==='function') u(); }catch(_){} });
    unsubscribes = [];
    svcLog('INFO','SHUTDOWN: complete');
  };

  return plugin;
};
