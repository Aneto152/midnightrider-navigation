'use strict';

/**
 * @file signalk-heading-true-calculator.js
 * @version 1.0.2
 * @author MidnightRider J/30 — OpenClaw
 * @license MIT
 *
 * CHANGELOG
 * v1.0.2 — CRITICAL FIX: plugin.stop moved OUTSIDE plugin.start.
 * SK 2.25.0 checks typeof plugin.stop === 'function' at load time.
 * unsubscribes[] moved to module scope so plugin.stop can access it.
 * v1.0.1 — subscriptionManager fix, removeAllListeners fix, guard fixes
 * v1.0.0 — Initial release
 *
 * PURPOSE: Derives navigation.headingTrue = headingMagnetic + magneticVariation.
 * Activates ONLY when headingTrue not already provided by a live source.
 */

const fs = require('fs');
const path = require('path');

const PLUGIN_ID = 'signalk-heading-true-calculator';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/heading-true-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const TWO_PI = 2 * Math.PI;

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
        '['+new Date().toISOString()+'] ['+level+'] [heading-true-calc] '+msg+'\n');
    } catch (_) {}
  }
  function flowLog(msg) {
    try {
      rotateIfNeeded(LOG_FLOW);
      fs.appendFileSync(LOG_FLOW, '['+new Date().toISOString()+'] [FLOW] '+msg+'\n');
    } catch (_) {}
  }

  // ── Module-scope state (accessible by plugin.stop defined outside start) ──
  let unsubscribes = [];
  let heartbeatTimer = null;
  let stats = { derived: 0, skipped: 0, errors: 0 };
  let hm = null, mv = null, hmTs = 0, mvTs = 0;

  const plugin = {
    id: PLUGIN_ID,
    name: 'True Heading Calculator (Magnetic + Variation)',
    description: 'Derives navigation.headingTrue from headingMagnetic + magneticVariation. ' +
      'Activates only when no live source provides headingTrue.',
    version: '1.0.2',
    schema: {
      type: 'object',
      title: 'True Heading Calculator',
      properties: {
        debug: { type: 'boolean', title: 'Debug logging', default: false },
        staleSecs: { type: 'number', title: 'External headingTrue stale (s)', default: 10, minimum: 1, maximum: 300 },
        maxHMAgeSecs: { type: 'number', title: 'Max headingMagnetic age(s)', default: 5, minimum: 1, maximum: 60 }
      }
    }
  };

  plugin.start = function(options) {
    const cfg = Object.assign({ debug: false, staleSecs: 10, maxHMAgeSecs: 5 }, options || {});
    cfg.staleSecs = Math.max(1, Math.min(300, Number(cfg.staleSecs) || 10));
    cfg.maxHMAgeSecs = Math.max(1, Math.min(60, Number(cfg.maxHMAgeSecs) || 5));

    // Reset module-scope state on every start
    unsubscribes = [];
    hm = null; mv = null; hmTs = 0; mvTs = 0;
    stats = { derived: 0, skipped: 0, errors: 0 };

    svcLog('INFO', 'STARTUP: '+PLUGIN_ID+' v1.0.2');
    svcLog('INFO', 'CONFIG: staleSecs='+cfg.staleSecs+' maxHMAgeSecs='+cfg.maxHMAgeSecs+' debug='+cfg.debug);

    app.subscriptionManager.subscribe(
      { context: 'vessels.self', subscribe: [
        { path: 'navigation.headingMagnetic', period: 500, policy: 'ideal', minPeriod: 200 },
        { path: 'navigation.magneticVariation', period: 5000, policy: 'ideal', minPeriod: 1000 }
      ]},
      unsubscribes,
      function(err) { stats.errors++; svcLog('ERROR', 'subscriptionManager: '+err); },
      function(delta) {
        try {
          var now = Date.now() / 1000;
          if (!delta.updates) return;
          delta.updates.forEach(function(u) {
            if (!u.values) return;
            u.values.forEach(function(pv) {
              if (pv.value == null) return;
              if (pv.path === 'navigation.headingMagnetic') { hm = pv.value; hmTs = now; }
              if (pv.path === 'navigation.magneticVariation') { mv = pv.value; mvTs = now; }
            });
          });
          if (hm !== null) compute(now, cfg);
        } catch(e) { stats.errors++; svcLog('ERROR','delta: '+e.message); }
      }
    );

    svcLog('INFO', 'DEPENDENCY_CHECK: subscribed headingMagnetic(500ms) + magneticVariation(5s)');
    if (app.setPluginStatus) app.setPluginStatus('Waiting for navigation.headingMagnetic');

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
    if ((nowSec - hmTs) > cfg.maxHMAgeSecs) { stats.skipped++; return; }
    if (!isFinite(hm) || isNaN(hm) || Math.abs(hm) > 4*Math.PI) {
      stats.errors++; svcLog('ERROR','invalid headingMagnetic: '+hm); return;
    }
    var variation = 0;
    if (mv !== null && isFinite(mv) && !isNaN(mv))
      variation = Math.max(-Math.PI, Math.min(Math.PI, mv));

    var htObj = app.getSelfPath('navigation.headingTrue');
    if (htObj && htObj.value != null) {
      var src = (htObj.source && htObj.source.label) ? htObj.source.label : '';
      if (src !== PLUGIN_ID) {
        var age = htObj.timestamp
          ? (Date.now() - new Date(htObj.timestamp).getTime()) / 1000 : Infinity;
        if (age < cfg.staleSecs) { stats.skipped++; return; }
      }
    }

    var ht = (((hm + variation) % TWO_PI) + TWO_PI) % TWO_PI;
    if (!isFinite(ht)) { stats.errors++; return; }

    app.handleMessage(PLUGIN_ID, {
      updates: [{ source: { label: PLUGIN_ID, type: 'derived' },
        timestamp: new Date().toISOString(),
        values: [{ path: 'navigation.headingTrue', value: ht }] }]
    });
    stats.derived++;
    var htD = (ht*180/Math.PI).toFixed(1), hmD = (hm*180/Math.PI).toFixed(1),
        vD = (variation*180/Math.PI).toFixed(2);
    if (cfg.debug) svcLog('DEBUG','DATA_OUT: HT='+htD+'deg (HM='+hmD+' Var='+vD+' n='+stats.derived+')');
    flowLog('Compass→SK: headingTrue='+htD+'deg HM='+hmD+'deg Var='+vD+'deg ['+PLUGIN_ID+']');
    if (app.setPluginStatus) app.setPluginStatus('HT='+htD+'deg pub='+stats.derived+' skip='+stats.skipped);
  }

  return plugin;
};
