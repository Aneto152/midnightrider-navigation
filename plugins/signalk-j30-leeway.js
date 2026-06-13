'use strict';

/**
 * @file signalk-j30-leeway.js
 * @version 1.0.1
 * @author MidnightRider J/30 — OpenClaw
 * @license MIT
 *
 * CHANGELOG
 * v1.0.1 — CRITICAL FIX: plugin.stop moved OUTSIDE plugin.start (SK 2.25.0)
 * unsubscribes[] at module scope. STW optional (defaults to SOG fallback).
 * v1.0.0 — Initial release
 *
 * PURPOSE: Leeway(deg) = K × |Heel(deg)| / STW(kts)² K=12 default for J/30.
 * Sign: CTW = headingTrue + leewayAngle (stbd heel → negative leewayAngle)
 */

const fs = require('fs');
const path = require('path');

const PLUGIN_ID = 'signalk-j30-leeway';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/j30-leeway-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const MS_TO_KTS = 1 / 0.5144;
const DEG_TO_RAD = Math.PI / 180;

module.exports = function(app) {

  function ensureDirs() {
    try {
      fs.mkdirSync(LOG_BASE + '/services', { recursive: true });
      fs.mkdirSync(LOG_BASE + '/debug', { recursive: true });
    } catch (_) {}
  }
  function rotateIfNeeded(f) {
    try { if (fs.existsSync(f) && fs.statSync(f).size > MAX_BYTES) fs.renameSync(f, f+'.1'); }
    catch (_) {}
  }
  function svcLog(level, msg) {
    try {
      ensureDirs(); rotateIfNeeded(LOG_SVC);
      fs.appendFileSync(LOG_SVC,
        '['+new Date().toISOString()+'] ['+level+'] [j30-leeway-calc] '+msg+'\n');
    } catch (_) {}
  }
  function flowLog(msg) {
    try {
      rotateIfNeeded(LOG_FLOW);
      fs.appendFileSync(LOG_FLOW, '['+new Date().toISOString()+'] [FLOW] '+msg+'\n');
    } catch (_) {}
  }

  // ── Module-scope state ────────────────────────────────────────────────────
  let unsubscribes = [];
  let heartbeatTimer = null;
  let stats = { derived: 0, skipped: 0, errors: 0 };
  let roll = null, stw = null, sog = null;
  let rollTs = 0, stwTs = 0, sogTs = 0;

  const plugin = {
    id: PLUGIN_ID,
    name: 'J/30 Leeway Calculator',
    description: 'Leeway(deg)=K×|Heel(deg)|/STW(kts)². K=12 for J/30 IOR fin keel. ' +
      'Uses SOG as STW fallback when no log sensor present.',
    version: '1.0.1',
    schema: {
      type: 'object',
      title: 'J/30 Leeway Calculator',
      properties: {
        leewayFactor: { type: 'number', title: 'Leeway Factor K (J/30: 10-14)', default: 12, minimum: 5, maximum: 25 },
        minSpeed: { type: 'number', title: 'Min speed (kts) to compute leeway', default: 0.5, minimum: 0.1, maximum: 3.0 },
        maxLeeway: { type: 'number', title: 'Max leeway cap (deg)', default: 15, minimum: 5, maximum: 30 },
        minHeel: { type: 'number', title: 'Min heel (deg)', default: 1.0, minimum: 0.5, maximum: 5.0 },
        leewaySign: { type: 'number', title: 'Sign convention (-1 or +1)', default: -1, enum: [-1, 1] },
        maxRollAgeSecs: { type: 'number', title: 'Max roll age (s)', default: 5, minimum: 1, maximum: 30 },
        debug: { type: 'boolean', title: 'Debug logging', default: false }
      }
    }
  };

  plugin.start = function(options) {
    const cfg = Object.assign(
      { leewayFactor: 12, minSpeed: 0.5, maxLeeway: 15, minHeel: 1.0,
        leewaySign: -1, maxRollAgeSecs: 5, debug: false },
      options || {}
    );
    cfg.leewayFactor = Math.max(5, Math.min(25, Number(cfg.leewayFactor) || 12));
    cfg.minSpeed = Math.max(0.1, Math.min(3.0, Number(cfg.minSpeed) || 0.5));
    cfg.maxLeeway = Math.max(5, Math.min(30, Number(cfg.maxLeeway) || 15));
    cfg.minHeel = Math.max(0.5, Math.min(5.0, Number(cfg.minHeel) || 1.0));
    cfg.maxRollAgeSecs = Math.max(1, Math.min(30, Number(cfg.maxRollAgeSecs) || 5));
    cfg.leewaySign = (cfg.leewaySign === 1) ? 1 : -1;

    unsubscribes = [];
    roll = null; stw = null; sog = null;
    rollTs = 0; stwTs = 0; sogTs = 0;
    stats = { derived: 0, skipped: 0, errors: 0 };

    svcLog('INFO', 'STARTUP: '+PLUGIN_ID+' v1.0.1');
    svcLog('INFO', 'CONFIG: K='+cfg.leewayFactor+' minSpeed='+cfg.minSpeed
      +'kts maxLeeway='+cfg.maxLeeway+'deg sign='+cfg.leewaySign);

    app.subscriptionManager.subscribe(
      { context: 'vessels.self', subscribe: [
        { path: 'navigation.attitude.roll', period: 500, policy: 'ideal', minPeriod: 200 },
        { path: 'navigation.speedThroughWater', period: 1000, policy: 'ideal', minPeriod: 500 },
        { path: 'navigation.speedOverGround', period: 1000, policy: 'ideal', minPeriod: 500 }
      ]},
      unsubscribes,
      function(err) { stats.errors++; svcLog('ERROR','subscriptionManager: '+err); },
      function(delta) {
        try {
          var now = Date.now() / 1000;
          if (!delta.updates) return;
          delta.updates.forEach(function(u) {
            if (!u.values) return;
            u.values.forEach(function(pv) {
              if (pv.value == null) return;
              if (pv.path === 'navigation.attitude.roll') { roll = pv.value; rollTs = now; }
              if (pv.path === 'navigation.speedThroughWater') { stw = pv.value; stwTs = now; }
              if (pv.path === 'navigation.speedOverGround') { sog = pv.value; sogTs = now; }
            });
          });
          if (roll !== null) compute(now, cfg);
        } catch(e) { stats.errors++; svcLog('ERROR','delta: '+e.message); }
      }
    );

    svcLog('INFO', 'DEPENDENCY_CHECK: roll(500ms) + STW(1s) + SOG(1s, fallback)');
    if (app.setPluginStatus) app.setPluginStatus('Waiting for attitude.roll');

    heartbeatTimer = setInterval(function() {
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped+' err='+stats.errors);
    }, 5*60*1000);

    svcLog('INFO', 'STARTUP: complete');
  };

  // ─── plugin.stop OUTSIDE plugin.start — required by SK 2.25.0 ───────────
  plugin.stop = function() {
    svcLog('INFO', 'SHUTDOWN: stats='+JSON.stringify(stats));
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
    unsubscribes.forEach(function(u) { try { u(); } catch(_) {} });
    unsubscribes = [];
    svcLog('INFO', 'SHUTDOWN: complete');
  };

  function compute(nowSec, cfg) {
    if ((nowSec - rollTs) > cfg.maxRollAgeSecs) { stats.skipped++; return; }
    if (!isFinite(roll) || isNaN(roll) || Math.abs(roll) > Math.PI) {
      stats.errors++; svcLog('ERROR','invalid roll: '+roll); return;
    }

    // Speed: prefer STW, fall back to SOG (no log sensor)
    var speedMs = null;
    var speedSrc = '';
    if (stw !== null && (nowSec - stwTs) <= 10 && isFinite(stw) && stw >= 0) {
      speedMs = stw; speedSrc = 'STW';
    } else if (sog !== null && (nowSec - sogTs) <= 10 && isFinite(sog) && sog >= 0) {
      speedMs = sog; speedSrc = 'SOG';
    }

    if (speedMs === null) { stats.skipped++; return; }

    var speedKts = speedMs * MS_TO_KTS;
    var heelDeg = roll * 180 / Math.PI;

    if (speedKts < cfg.minSpeed) { publish(0, cfg); return; }
    if (Math.abs(heelDeg) < cfg.minHeel) { publish(0, cfg); return; }

    var lwyDeg = cfg.leewayFactor * Math.abs(heelDeg) / (speedKts * speedKts);
    lwyDeg = Math.min(lwyDeg, cfg.maxLeeway);
    var lwyRad = cfg.leewaySign * (roll >= 0 ? 1 : -1) * lwyDeg * DEG_TO_RAD;
    if (!isFinite(lwyRad)) { stats.errors++; return; }

    publish(lwyRad, cfg);

    if (cfg.debug) {
      svcLog('DEBUG','DATA_OUT: leeway='+(lwyRad*180/Math.PI).toFixed(2)+'deg'
        +' Heel='+heelDeg.toFixed(1)+'deg Spd='+speedKts.toFixed(2)+'kts('+speedSrc+')');
      flowLog('J30→SK:leeway='+(lwyRad*180/Math.PI).toFixed(2)+'deg ['+PLUGIN_ID+']');
    }
  }

  function publish(lwyRad, cfg) {
    app.handleMessage(PLUGIN_ID, {
      updates: [{ source: { label: PLUGIN_ID, type: 'derived' },
        timestamp: new Date().toISOString(),
        values: [{ path: 'performance.leewayAngle', value: lwyRad }] }]
    });
    stats.derived++;
    if (app.setPluginStatus)
      app.setPluginStatus('Leeway='+(lwyRad*180/Math.PI).toFixed(1)+'deg pub='+stats.derived);
  }

  return plugin;
};
