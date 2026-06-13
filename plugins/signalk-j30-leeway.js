'use strict';

/**
 * @file signalk-j30-leeway.js
 * @version 1.0.0
 * @author MidnightRider J/30 — OpenClaw
 * @license MIT
 * @since 2026-06-13
 *
 * PURPOSE
 * Computes performance.leewayAngle for the J/30 using the standard
 * empirical leeway formula derived from offshore racing polar methodology.
 *
 * FORMULA
 * Leeway(°) = LeewayFactor × |Heel(°)| / STW(kts)²
 *
 * Where:
 * LeewayFactor : empirical coefficient (J/30 typical: 10–14, default: 12)
 * Heel : roll angle in degrees (absolute value — sign applied separately)
 * STW : speed through water in knots (converted from m/s)
 *
 * J/30 characteristics that inform the default K=12:
 * - IOR design, moderate beam, fin keel
 * - Upwind typical heel: 15–25° at 6–7 kts
 * - Expected leeway at 20°/6kts: 12×20/36 ≈ 6.7° (realistic for IOR fins)
 *
 * SIGN CONVENTION
 * leewayAngle is defined so that: CTW = headingTrue + leewayAngle
 * Starboard heel (roll > 0) → leeward is PORT → leewayAngle NEGATIVE
 * Port heel (roll < 0) → leeward is STBD → leewayAngle POSITIVE
 * Applied as: leewayAngle = leewaySign × sign(roll) × magnitude_rad
 * where leewaySign defaults to -1 (standard convention).
 * If field observation shows reversed sign, set leewaySign = +1 in config.
 *
 * INPUTS (Signal K paths consumed)
 * navigation.attitude.roll [rad] Required — heel from UM982 or WIT
 * navigation.speedThroughWater [m/s] Required — paddlewheel or sonic log
 *
 * OUTPUT (Signal K path produced)
 * performance.leewayAngle [rad] Signed leeway angle (see convention above)
 *
 * GUARD CONDITIONS
 * G1: Skip if STW is below minSTW (too slow — divides by near-zero)
 * G2: Skip if STW or roll is invalid (NaN, infinite, implausible)
 * G3: Clamp computed leeway to maxLeeway cap
 * G4: Publish 0 if heel < minHeel (boat effectively upright)
 *
 * LOGGING
 * Service log : ~/midnightrider-navigation/logs/services/j30-leeway-calc.log
 * Data-flow : ~/midnightrider-navigation/logs/debug/data-flow.log
 * Rotation : 5 MB max, keeps .1 backup
 *
 * CONFIGURATION (SK Admin → Plugins → J/30 Leeway Calculator)
 * leewayFactor {number} Empirical K coefficient (default: 12, range: 5–25)
 * minSTW {number} Min STW in knots below which leeway = 0 (default: 0.5)
 * maxLeeway {number} Maximum leeway cap in degrees (default: 15)
 * minHeel {number} Min heel in degrees to compute leeway (default: 1.0)
 * leewaySign {number} Sign convention: -1 (default/standard) or +1 (reversed)
 * debug {boolean} Verbose logging (default: false)
 */

const fs = require('fs');
const path = require('path');

const PLUGIN_ID = 'signalk-j30-leeway';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/j30-leeway-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const TWO_PI = 2 * Math.PI;
const MS_TO_KTS = 1 / 0.5144; // metres/sec → knots conversion factor
const DEG_TO_RAD = Math.PI / 180;

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
        '[' + new Date().toISOString() + '] [' + level + '] [j30-leeway-calc] ' + msg + '\n');
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
  let roll = null; // latest heel angle (radians), null if absent
  let stw = null; // latest speed through water (m/s), null if absent
  let rollTs = 0; // epoch-seconds of last roll update
  let stwTs = 0; // epoch-seconds of last STW update

  // ── Plugin definition ─────────────────────────────────────────────────────

  const plugin = {
    id: PLUGIN_ID,
    name: 'J/30 Leeway Calculator',
    description: 'Computes performance.leewayAngle using J/30 empirical formula: ' +
      'Leeway(°) = K × |Heel(°)| / STW(kts)². ' +
      'K=12 default for J/30 IOR fin keel.',
    version: '1.0.0',
    schema: {
      type: 'object',
      title: 'J/30 Leeway Calculator — Configuration',
      properties: {
        leewayFactor: {
          type: 'number',
          title: 'Leeway Factor K (J/30 typical: 10–14)',
          description: 'Empirical coefficient. Higher = more leeway for same heel and speed. ' +
            'J/30 IOR fin keel: start at 12, adjust from heel/COG/heading comparison.',
          default: 12,
          minimum: 5,
          maximum: 25
        },
        minSTW: {
          type: 'number',
          title: 'Minimum STW (knots) — below this, publish leewayAngle = 0',
          description: 'Prevents divide-by-near-zero at low speeds. Also avoids noise at anchor.',
          default: 0.5,
          minimum: 0.1,
          maximum: 2.0
        },
        maxLeeway: {
          type: 'number',
          title: 'Maximum leeway cap (degrees)',
          description: 'Clamps output to this value. Prevents unrealistic values at low speed/high heel.',
          default: 15,
          minimum: 5,
          maximum: 30
        },
        minHeel: {
          type: 'number',
          title: 'Minimum heel (degrees) to compute leeway',
          description: 'Below this threshold, publish leewayAngle = 0 (boat effectively upright).',
          default: 1.0,
          minimum: 0.5,
          maximum: 5.0
        },
        leewaySign: {
          type: 'number',
          title: 'Leeway sign convention: -1 (standard) or +1 (reversed)',
          description: 'Standard (-1): stbd heel → negative leewayAngle → CTW rotates to port. ' +
            'Set to +1 only if field validation shows opposite behavior.',
          default: -1,
          enum: [-1, 1]
        },
        maxRollAgeSecs: {
          type: 'number',
          title: 'Max acceptable roll data age (seconds)',
          description: 'Discard heel values older than this.',
          default: 5,
          minimum: 1,
          maximum: 30
        },
        maxSTWAgeSecs: {
          type: 'number',
          title: 'Max acceptable STW data age (seconds)',
          description: 'Discard STW values older than this.',
          default: 5,
          minimum: 1,
          maximum: 30
        },
        debug: {
          type: 'boolean',
          title: 'Enable debug logging',
          default: false
        }
      }
    }
  };

  // ── Plugin start ──────────────────────────────────────────────────────────

  plugin.start = function(options) {
    const config = Object.assign(
      { leewayFactor: 12, minSTW: 0.5, maxLeeway: 15, minHeel: 1.0,
        leewaySign: -1, maxRollAgeSecs: 5, maxSTWAgeSecs: 5, debug: false },
      options || {}
    );

    // Clamp and validate
    config.leewayFactor = Math.max(5, Math.min(25, Number(config.leewayFactor) || 12));
    config.minSTW = Math.max(0.1, Math.min(2.0, Number(config.minSTW) || 0.5));
    config.maxLeeway = Math.max(5, Math.min(30, Number(config.maxLeeway) || 15));
    config.minHeel = Math.max(0.5, Math.min(5.0, Number(config.minHeel) || 1.0));
    config.maxRollAgeSecs = Math.max(1, Math.min(30, Number(config.maxRollAgeSecs) || 5));
    config.maxSTWAgeSecs = Math.max(1, Math.min(30, Number(config.maxSTWAgeSecs) || 5));
    config.leewaySign = (config.leewaySign === 1) ? 1 : -1;

    // Reset state on start
    roll = null; stw = null; rollTs = 0; stwTs = 0;
    stats = { derived: 0, skipped: 0, errors: 0, heartbeats: 0 };

    svcLog('INFO', 'STARTUP: ' + PLUGIN_ID + ' v1.0.0 starting');
    svcLog('INFO', 'CONFIG: K=' + config.leewayFactor
      + ' minSTW=' + config.minSTW + 'kts'
      + ' maxLwy=' + config.maxLeeway + 'deg'
      + ' minHeel=' + config.minHeel + 'deg'
      + ' sign=' + config.leewaySign
      + ' debug=' + config.debug);

    // Subscribe via subscriptionManager (capital M)
    const unsubscribes = [];
    app.subscriptionManager.subscribe(
      {
        context: 'vessels.self',
        subscribe: [
          { path: 'navigation.attitude.roll', period: 500, policy: 'ideal', minPeriod: 200 },
          { path: 'navigation.speedThroughWater', period: 1000, policy: 'ideal', minPeriod: 500 }
        ]
      },
      unsubscribes,
      function(err) {
        svcLog('ERROR', 'ERROR: subscriptionManager failed — ' + err);
        app.error('[' + PLUGIN_ID + '] Subscription error: ' + err);
      },
      function(delta) {
        processDelta(delta, config);
      }
    );

    svcLog('INFO', 'DEPENDENCY_CHECK: subscribed to navigation.attitude.roll (500ms) '
      + '+ navigation.speedThroughWater (1000ms)');
    app.setPluginStatus('Waiting for attitude.roll + speedThroughWater');

    // Heartbeat: 5 minutes
    heartbeatTimer = setInterval(function() {
      stats.heartbeats++;
      const rollDeg = roll !== null ? (roll * 180 / Math.PI).toFixed(1) + 'deg' : 'null';
      const stwKts = stw !== null ? (stw * MS_TO_KTS).toFixed(2) + 'kts' : 'null';
      svcLog('DEBUG', 'HEARTBEAT #' + stats.heartbeats
        + ': derived=' + stats.derived
        + ' skipped=' + stats.skipped
        + ' errors=' + stats.errors
        + ' roll=' + rollDeg
        + ' STW=' + stwKts);
    }, 5 * 60 * 1000);

    // Safe cleanup: save reference for removeListener
    plugin.stop = function() {
      svcLog('INFO', 'SHUTDOWN: stopping — stats=' + JSON.stringify(stats));
      if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
      unsubscribes.forEach(function(u) { try { u(); } catch (_) {} });
      svcLog('INFO', 'SHUTDOWN: complete');
    };
  };

  // ── Delta processor ───────────────────────────────────────────────────────

  function processDelta(delta, config) {
    try {
      const now = Date.now() / 1000;
      if (!delta.updates) return;

      delta.updates.forEach(function(update) {
        if (!update.values) return;
        update.values.forEach(function(pv) {
          if (pv.path === 'navigation.attitude.roll' && pv.value !== null) {
            roll = pv.value;
            rollTs = now;
          }
          if (pv.path === 'navigation.speedThroughWater' && pv.value !== null) {
            stw = pv.value;
            stwTs = now;
          }
        });
      });

      // Need both inputs
      if (roll === null || stw === null) return;

      computeAndPublish(now, config);

    } catch (err) {
      stats.errors++;
      svcLog('ERROR', 'ERROR: delta processing exception — ' + err.message);
    }
  }

  // ── Core computation ──────────────────────────────────────────────────────

  /**
   * Applies all guard conditions and publishes performance.leewayAngle.
   *
   * Guard conditions:
   * G1: Both roll and STW must be fresh (within maxRollAgeSecs/maxSTWAgeSecs)
   * G2: Both values must be finite numbers in plausible ranges
   * G3: STW must be >= minSTW to avoid divide-by-near-zero
   * G4: Heel below minHeel → publish 0 (boat upright, no leeway)
   *
   * @param {number} nowSec - Current time in epoch-seconds
   * @param {object} config - Active plugin configuration
   */
  function computeAndPublish(nowSec, config) {

    // Guard 1: Freshness check
    const rollAge = nowSec - rollTs;
    const stwAge = nowSec - stwTs;
    if (rollAge > config.maxRollAgeSecs) {
      stats.skipped++;
      if (config.debug) svcLog('DEBUG', 'SKIP G1: roll stale (' + rollAge.toFixed(1) + 's)');
      return;
    }
    if (stwAge > config.maxSTWAgeSecs) {
      stats.skipped++;
      if (config.debug) svcLog('DEBUG', 'SKIP G1: STW stale (' + stwAge.toFixed(1) + 's)');
      return;
    }

    // Guard 2: Validity check
    if (!isFinite(roll) || isNaN(roll) || Math.abs(roll) > Math.PI) {
      // roll > 180° is physically impossible for a sailing vessel
      stats.errors++;
      svcLog('ERROR', 'ERROR G2: roll invalid (' + roll + ' rad) — expected |roll| < π');
      return;
    }
    if (!isFinite(stw) || isNaN(stw) || stw < 0 || stw > 30) {
      // STW > 30 m/s (~58 kts) is physically impossible
      stats.errors++;
      svcLog('ERROR', 'ERROR G2: STW invalid (' + stw + ' m/s) — expected 0–30');
      return;
    }

    // Convert units
    const heelDeg = roll * 180 / Math.PI; // radians → degrees
    const stwKts = stw * MS_TO_KTS; // m/s → knots

    // Guard 3: Minimum STW (prevents divide-by-near-zero)
    if (stwKts < config.minSTW) {
      // Publish 0 leeway at anchor or near-stopped
      publishLeeway(0, config);
      if (config.debug) {
        svcLog('DEBUG', 'G3: STW=' + stwKts.toFixed(2) + 'kts < minSTW=' + config.minSTW + 'kts → leeway=0');
      }
      return;
    }

    // Guard 4: Minimum heel (upright boat has no significant leeway)
    if (Math.abs(heelDeg) < config.minHeel) {
      publishLeeway(0, config);
      if (config.debug) {
        svcLog('DEBUG', 'G4: heel=' + heelDeg.toFixed(2) + 'deg < minHeel=' + config.minHeel + 'deg → leeway=0');
      }
      return;
    }

    // ── Compute leeway magnitude ───────────────────────────────────────────
    // Formula: Leeway(°) = K × |Heel(°)| / STW(kts)²
    let leewayMagDeg = config.leewayFactor * Math.abs(heelDeg) / (stwKts * stwKts);

    // Guard 3 continued: clamp to maxLeeway cap
    leewayMagDeg = Math.min(leewayMagDeg, config.maxLeeway);

    // Apply sign convention: leewaySign × sign(roll) × magnitude
    // Default (sign=-1): stbd heel → negative leewayAngle → CTW rotates to port (leeward)
    const leewaySign = (roll >= 0) ? 1 : -1;
    const leewayRad = config.leewaySign * leewaySign * leewayMagDeg * DEG_TO_RAD;

    // Sanity check result
    if (!isFinite(leewayRad) || isNaN(leewayRad)) {
      stats.errors++;
      svcLog('ERROR', 'ERROR: computed leewayRad is not finite'
        + ' (K=' + config.leewayFactor
        + ' heel=' + heelDeg.toFixed(1)
        + ' STW=' + stwKts.toFixed(2) + ')');
      return;
    }

    publishLeeway(leewayRad, config);

    // Logging (always log magnitude in degrees for readability)
    const signedDeg = (leewayRad * 180 / Math.PI).toFixed(2);
    if (config.debug) {
      app.debug('[' + PLUGIN_ID + '] '
        + 'Heel=' + heelDeg.toFixed(1) + 'deg '
        + 'STW=' + stwKts.toFixed(2) + 'kts '
        + '→ Leeway=' + signedDeg + 'deg');
    }
    svcLog('DEBUG', 'DATA_OUT: leeway=' + signedDeg + 'deg'
      + ' (K=' + config.leewayFactor
      + ' Heel=' + heelDeg.toFixed(1) + 'deg'
      + ' STW=' + stwKts.toFixed(2) + 'kts'
      + ' total=' + stats.derived + ')');
    flowLog('J30Polar→SignalK: leewayAngle=' + signedDeg + 'deg'
      + ' from Heel=' + heelDeg.toFixed(1) + 'deg'
      + ' STW=' + stwKts.toFixed(2) + 'kts'
      + ' K=' + config.leewayFactor
      + ' [' + PLUGIN_ID + ']');
  }

  /**
   * Publishes a leeway angle value to Signal K and updates UI status.
   * @param {number} leewayRad - Leeway angle in radians
   * @param {object} config - Active plugin configuration
   */
  function publishLeeway(leewayRad, config) {
    app.handleMessage(PLUGIN_ID, {
      updates: [{
        source: { label: PLUGIN_ID, type: 'derived' },
        timestamp: new Date().toISOString(),
        values: [{ path: 'performance.leewayAngle', value: leewayRad }]
      }]
    });

    stats.derived++;

    const lwyDeg = (leewayRad * 180 / Math.PI).toFixed(1);
    app.setPluginStatus('Leeway=' + lwyDeg + 'deg'
      + ' | K=' + config.leewayFactor
      + ' derived=' + stats.derived
      + ' skip=' + stats.skipped);
  }

  return plugin;
};
