'use strict';

/**
 * @file signalk-heading-true-calculator.js
 * @version 1.0.1
 * @author MidnightRider J/30 — OpenClaw
 * @license MIT
 * @since 2026-06-13
 *
 * PURPOSE
 * Derives navigation.headingTrue from navigation.headingMagnetic +
 * navigation.magneticVariation. Activates ONLY when headingTrue is
 * not already provided by a live, non-stale sensor source.
 *
 * FORMULA
 * headingTrue (rad) = headingMagnetic (rad) + magneticVariation (rad)
 * Signal K convention: radians, 0=North, clockwise positive.
 * magneticVariation: East positive (SK specification).
 *
 * INPUTS (Signal K paths consumed)
 * navigation.headingMagnetic [rad] Required — from compass/NMEA
 * navigation.magneticVariation [rad] Optional — defaults to 0 with WARN log
 *
 * OUTPUT (Signal K path produced)
 * navigation.headingTrue [rad] Only when no live external source present
 *
 * GUARD CONDITIONS
 * G1: Skip if headingMagnetic is stale (older than maxHMAgeSecs)
 * G2: Skip if headingMagnetic is invalid (NaN, infinite, implausible)
 * G3: Use variation=0 with warning if magneticVariation unavailable
 * G4: Skip if another source provides fresh headingTrue (< staleSecs old)
 * Uses app.getSelfPath() public API for reliable cross-version detection
 *
 * CHANGELOG
 * v1.0.1 (2026-06-13) — Fix: subscriptionManager typo (was lowercase 'm')
 * Fix: removeAllListeners → removeListener with saved ref
 * Fix: guard condition now allows mv=null (defaults to 0)
 * Fix: G4 uses app.getSelfPath() instead of internal API
 * Add: data-flow.log boundary crossing entries
 * v1.0.0 (2026-06-13) — Initial release
 *
 * LOGGING
 * Service log : ~/midnightrider-navigation/logs/services/heading-true-calc.log
 * Data-flow : ~/midnightrider-navigation/logs/debug/data-flow.log
 * Rotation : 5 MB max, keeps .1 backup
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

  // ── Logging ──────────────────────────────────────────────────────────────

  function ensureDirs() {
    try {
      fs.mkdirSync(LOG_BASE + '/services', { recursive: true });
      fs.mkdirSync(LOG_BASE + '/debug', { recursive: true });
    } catch (_) {}
  }

  function rotateIfNeeded(file) {
    try {
      if (fs.existsSync(file) && fs.statSync(file).size > MAX_BYTES) {
        fs.renameSync(file, file + '.1');
      }
    } catch (_) {}
  }

  function svcLog(level, msg) {
    try {
      ensureDirs();
      rotateIfNeeded(LOG_SVC);
      fs.appendFileSync(LOG_SVC,
        '[' + new Date().toISOString() + '] [' + level + '] [heading-true-calc] ' + msg + '\n');
    } catch (_) {}
  }

  function flowLog(msg) {
    try {
      rotateIfNeeded(LOG_FLOW);
      fs.appendFileSync(LOG_FLOW,
        '[' + new Date().toISOString() + '] [FLOW] ' + msg + '\n');
    } catch (_) {}
  }

  // ── Runtime state ─────────────────────────────────────────────────────────

  let stats = { derived: 0, skipped: 0, errors: 0, heartbeats: 0 };
  let heartbeatTimer = null;
  let hm = null; // latest headingMagnetic (radians)
  let mv = null; // latest magneticVariation (radians), null if absent
  let hmTs = 0; // epoch-seconds of last headingMagnetic update
  let mvTs = 0; // epoch-seconds of last magneticVariation update

  // ── Plugin definition ─────────────────────────────────────────────────────

  const plugin = {
    id: PLUGIN_ID,
    name: 'True Heading Calculator (Magnetic + Variation)',
    description: 'Derives navigation.headingTrue from headingMagnetic + magneticVariation. ' +
      'Activates ONLY when headingTrue is not provided by another live source.',
    version: '1.0.1',
    schema: {
      type: 'object',
      title: 'True Heading Calculator — Configuration',
      properties: {
        debug: {
          type: 'boolean',
          title: 'Enable debug logging',
          description: 'Log every computation to SK debug stream and service log.',
          default: false
        },
        staleSecs: {
          type: 'number',
          title: 'External headingTrue stale threshold (seconds)',
          description: 'If another source provides headingTrue fresher than this, skip computation.',
          default: 10,
          minimum: 1,
          maximum: 300
        },
        maxHMAgeSecs: {
          type: 'number',
          title: 'Max acceptable headingMagnetic age (seconds)',
          description: 'Reject headingMagnetic values older than this.',
          default: 5,
          minimum: 1,
          maximum: 60
        }
      }
    }
  };

  // ── Plugin start ──────────────────────────────────────────────────────────

  plugin.start = function(options) {
    const config = Object.assign(
      { debug: false, staleSecs: 10, maxHMAgeSecs: 5 },
      options || {}
    );
    // Clamp config to safe ranges
    config.staleSecs = Math.max(1, Math.min(300, Number(config.staleSecs) || 10));
    config.maxHMAgeSecs = Math.max(1, Math.min(60, Number(config.maxHMAgeSecs) || 5));

    // Reset state
    hm = null; mv = null; hmTs = 0; mvTs = 0;
    stats = { derived: 0, skipped: 0, errors: 0, heartbeats: 0 };

    svcLog('INFO', 'STARTUP: ' + PLUGIN_ID + ' v1.0.1 starting');
    svcLog('INFO', 'CONFIG: debug=' + config.debug
      + ' staleSecs=' + config.staleSecs
      + ' maxHMAgeSecs=' + config.maxHMAgeSecs);

    // Subscribe to paths via subscriptionManager (FIX #1: capital M)
    app.subscriptionManager.subscribe(
      [
        { path: 'navigation.headingMagnetic', period: 500 },
        { path: 'navigation.magneticVariation', period: 5000 }
      ],
      (err, res) => {
        if (err) {
          svcLog('ERROR', 'Subscription error: ' + err.message);
          app.error('[' + PLUGIN_ID + '] ' + err.message);
        }
      }
    );

    svcLog('INFO', 'DEPENDENCY_CHECK: subscribed to navigation.headingMagnetic + navigation.magneticVariation');
    app.setPluginStatus('Waiting for navigation.headingMagnetic');

    // Heartbeat: log statistics every 5 minutes
    heartbeatTimer = setInterval(function() {
      stats.heartbeats++;
      svcLog('DEBUG', 'HEARTBEAT #' + stats.heartbeats
        + ': derived=' + stats.derived
        + ' skipped=' + stats.skipped
        + ' errors=' + stats.errors);
    }, 5 * 60 * 1000);

    // Listen to delta stream
    const deltaListener = (delta) => {
      try {
        const now = Date.now() / 1000;

        // Extract headingMagnetic and magneticVariation from delta
        if (delta.updates) {
          delta.updates.forEach(function(update) {
            if (!update.values) return;
            update.values.forEach(function(pv) {
              if (pv.path === 'navigation.headingMagnetic' && pv.value !== null) {
                hm = pv.value;
                hmTs = now;
              }
              if (pv.path === 'navigation.magneticVariation' && pv.value !== null) {
                mv = pv.value;
                mvTs = now;
              }
            });
          });
        }

        // FIX #3: Compute as long as hm is available (mv defaults to 0)
        if (hm === null) return;

        computeAndPublish(now, config);

      } catch (err) {
        stats.errors++;
        svcLog('ERROR', 'Delta processing exception: ' + err.message);
      }
    };

    app.on('delta:processed', deltaListener);

    plugin.stop = function() {
      svcLog('INFO', 'SHUTDOWN: stopping — stats=' + JSON.stringify(stats));
      if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
      app.removeListener('delta:processed', deltaListener); // FIX #2: use removeListener
      svcLog('INFO', 'SHUTDOWN: complete');
    };
  };

  // ── Core computation ──────────────────────────────────────────────────────

  /**
   * Runs all guard conditions and publishes headingTrue if guards pass.
   */
  function computeAndPublish(nowSec, config) {

    // Guard 1: headingMagnetic must be fresh
    const hmAge = nowSec - hmTs;
    if (hmAge > config.maxHMAgeSecs) {
      stats.skipped++;
      if (config.debug) {
        svcLog('DEBUG', 'SKIP G1: headingMagnetic stale ('
          + hmAge.toFixed(1) + 's > ' + config.maxHMAgeSecs + 's)');
      }
      return;
    }

    // Guard 2: headingMagnetic must be a valid finite number
    if (typeof hm !== 'number' || !isFinite(hm) || Math.abs(hm) > 4 * Math.PI) {
      stats.errors++;
      svcLog('ERROR', 'ERROR G2: headingMagnetic invalid (' + hm + ')');
      return;
    }

    // Guard 3: magneticVariation — use 0 if absent or stale
    let variation = 0;
    if (mv !== null) {
      const mvAge = nowSec - mvTs;
      if (!isFinite(mv)) {
        svcLog('WARN', 'WARN G3: magneticVariation not finite — using 0');
      } else if (mvAge > 60) {
        svcLog('WARN', 'WARN G3: magneticVariation stale (' + mvAge.toFixed(0) + 's) — using 0');
      } else {
        variation = Math.max(-Math.PI, Math.min(Math.PI, mv));
      }
    }

    // Guard 4: Skip if another LIVE source already provides fresh headingTrue
    // FIX #4: Use app.getSelfPath() (public API)
    const htObj = app.getSelfPath('navigation.headingTrue');
    if (htObj && htObj.value !== null && htObj.value !== undefined) {
      const srcLabel = (htObj.source && htObj.source.label) ? htObj.source.label : '';
      if (srcLabel !== PLUGIN_ID) {
        const htAge = htObj.timestamp
          ? (Date.now() - new Date(htObj.timestamp).getTime()) / 1000
          : Infinity;
        if (htAge < config.staleSecs) {
          stats.skipped++;
          if (config.debug) {
            svcLog('DEBUG', 'SKIP G4: headingTrue from \'' + srcLabel
              + '\' is ' + htAge.toFixed(1) + 's old');
          }
          return;
        }
      }
    }

    // Compute: headingTrue = headingMagnetic + variation
    // Normalize result to [0, 2π)
    let ht = (((hm + variation) % TWO_PI) + TWO_PI) % TWO_PI;

    // Sanity check result
    if (!isFinite(ht) || isNaN(ht)) {
      stats.errors++;
      svcLog('ERROR', 'ERROR: computed headingTrue is not finite (hm=' + hm + ' var=' + variation + ')');
      return;
    }

    // Publish to Signal K
    app.handleMessage(PLUGIN_ID, {
      updates: [{
        source: { label: PLUGIN_ID, type: 'derived' },
        timestamp: new Date().toISOString(),
        values: [{ path: 'navigation.headingTrue', value: ht }]
      }]
    });

    stats.derived++;

    // Logging
    const htDeg = (ht * 180 / Math.PI).toFixed(1);
    const hmDeg = (hm * 180 / Math.PI).toFixed(1);
    const varDeg = (variation * 180 / Math.PI).toFixed(2);

    if (config.debug) {
      app.debug('[' + PLUGIN_ID + '] HM=' + hmDeg + 'deg + Var=' + varDeg + 'deg → HT=' + htDeg + 'degT');
      svcLog('DEBUG', 'DATA_OUT: headingTrue=' + htDeg + 'degT'
        + ' (HM=' + hmDeg + 'deg + Var=' + varDeg + 'deg)');
    }

    // Data-flow log: boundary crossing event
    flowLog('Compass→SignalK: headingTrue=' + htDeg + 'degT'
      + ' [' + PLUGIN_ID + ']');

    app.setPluginStatus('HT=' + htDeg + 'degT'
      + ' | derived=' + stats.derived
      + ' skipped=' + stats.skipped);
  }

  return plugin;
};
