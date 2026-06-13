'use strict';

/**
 * signalk-heading-true-calculator v1.0.0
 * 
 * Derives navigation.headingTrue from headingMagnetic + magneticVariation.
 * 
 * GUARD CONDITION:
 *   Skips silently if another source provides fresh headingTrue (within staleSecs).
 *   This allows other instruments (GPS, UM982) to take priority without conflict.
 * 
 * INPUTS:
 *   - navigation.headingMagnetic (degrees or radians)
 *   - navigation.magneticVariation (radians, ±π)
 * 
 * OUTPUT:
 *   - navigation.headingTrue = headingMagnetic + magneticVariation (in radians)
 * 
 * CONFIGURATION:
 *   - debug (boolean): Enable debug-level logging
 *   - staleSecs (number): Consider headingTrue stale if older than this (default 10)
 *   - maxHMAgeSecs (number): Skip if headingMagnetic older than this (default 5)
 * 
 * LOGGING:
 *   - logs/services/heading-true-calc.log (RotatingFileHandler, 5MB/3 backups)
 *   - [STARTUP], [HEARTBEAT], [DATA_IN], [DATA_OUT], [WARN], [ERROR]
 */

const fs = require('fs');
const path = require('path');

module.exports = function(app) {
  let lastPublished = 0;
  let stats = { derived: 0, skipped: 0, errors: 0, heartbeats: 0 };
  let logFile = '/home/aneto/midnightrider-navigation/logs/services/heading-true-calc.log';
  const MAX_BYTES = 5 * 1024 * 1024;

  function ensureDir(d) {
    if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
  }

  function svcLog(level, msg) {
    try {
      ensureDir(path.dirname(logFile));
      try {
        if (fs.statSync(logFile).size > MAX_BYTES) {
          fs.renameSync(logFile, logFile + '.1');
        }
      } catch(e) {}
      fs.appendFileSync(logFile, `[${new Date().toISOString()}] [${level}] [heading-true-calc] ${msg}\n`);
    } catch(e) {}
  }

  const plugin = {
    id: 'signalk-heading-true-calculator',
    name: 'True Heading Calculator',
    description: 'Derives navigation.headingTrue from headingMagnetic + magneticVariation.',
    schema: {
      type: 'object',
      properties: {
        debug: { type: 'boolean', title: 'Debug logging', default: false },
        staleSecs: { type: 'number', title: 'Stale threshold (seconds)', default: 10 },
        maxHMAgeSecs: { type: 'number', title: 'Max headingMagnetic age (seconds)', default: 5 }
      }
    }
  };

  plugin.start = function(options) {
    const config = Object.assign({ debug: false, staleSecs: 10, maxHMAgeSecs: 5 }, options || {});

    svcLog('INFO', `STARTUP: signalk-heading-true-calculator v1.0.0 starting`);
    svcLog('INFO', `CONFIG: debug=${config.debug} staleSecs=${config.staleSecs} maxHMAgeSecs=${config.maxHMAgeSecs}`);
    svcLog('INFO', `DEPENDENCY_CHECK: subscribed to navigation.headingMagnetic + navigation.magneticVariation`);

    app.setPluginStatus('Initialized');

    // Subscribe to headingMagnetic and magneticVariation
    let hm = null, mv = null, hmTs = 0, mvTs = 0;

    app.subscriptionmanager.subscribe(
      [
        { path: 'navigation.headingMagnetic', period: 1000 },
        { path: 'navigation.magneticVariation', period: 1000 }
      ],
      (err, res) => {
        if (err) {
          svcLog('ERROR', `Subscription error: ${err.message}`);
          return;
        }
      }
    );

    // Listen to delta events
    app.on('delta:processed', (delta) => {
      try {
        const now = Date.now() / 1000;

        // Extract values from delta
        if (delta.updates) {
          delta.updates.forEach(update => {
            if (update.values) {
              update.values.forEach(val => {
                if (val.path === 'navigation.headingMagnetic') {
                  hm = val.value;
                  hmTs = now;
                }
                if (val.path === 'navigation.magneticVariation') {
                  mv = val.value;
                  mvTs = now;
                }
              });
            }
          });
        }

        // Check if we should derive headingTrue
        if (hm !== null && mv !== null) {
          const hmAge = now - hmTs;
          const mvAge = now - mvTs;

          // Guard 1: Check if headingMagnetic is fresh enough
          if (hmAge > config.maxHMAgeSecs) {
            stats.skipped++;
            if (config.debug) {
              svcLog('DEBUG', `SKIP: headingMagnetic stale (${hmAge.toFixed(1)}s > ${config.maxHMAgeSecs}s)`);
            }
            return;
          }

          // Guard 2: Check if magneticVariation is available and fresh
          if (mv === null || mvAge > 60) {
            svcLog('WARN', `SKIP: magneticVariation unavailable or stale — using variation=0`);
            mv = 0;
          }

          // Guard 3: Validate data
          if (typeof hm !== 'number' || typeof mv !== 'number' || !isFinite(hm) || !isFinite(mv)) {
            svcLog('WARN', `SKIP: invalid data — hm=${hm} mv=${mv}`);
            stats.skipped++;
            return;
          }

          // Guard 4: Check if another source already provides fresh headingTrue
          const skSelf = app.signalk.getSelf();
          if (skSelf && skSelf.navigation && skSelf.navigation.headingTrue) {
            const htVal = skSelf.navigation.headingTrue;
            const htTs = htVal._timestamp ? (Date.now() - new Date(htVal._timestamp).getTime()) / 1000 : 999;
            if (htTs < config.staleSecs) {
              stats.skipped++;
              if (config.debug) {
                svcLog('DEBUG', `SKIP: headingTrue already provided fresh (${htTs.toFixed(1)}s old)`);
              }
              return;
            }
          }

          // Derive headingTrue (in radians)
          let ht = hm + mv;
          while (ht > Math.PI) ht -= 2 * Math.PI;
          while (ht < -Math.PI) ht += 2 * Math.PI;

          // Publish delta
          app.handleMessage(plugin.id, {
            updates: [{
              source: { label: 'heading-true-calculator', type: 'computed' },
              timestamp: new Date().toISOString(),
              values: [{ path: 'navigation.headingTrue', value: ht }]
            }]
          });

          stats.derived++;
          lastPublished = now;

          if (config.debug) {
            svcLog('DEBUG', `DATA_OUT: headingTrue=${ht.toFixed(4)}rad (hm=${hm.toFixed(4)} + mv=${mv.toFixed(4)})`);
          }
        }

        // Heartbeat every 60 seconds
        if (now - lastPublished > 60) {
          stats.heartbeats++;
          svcLog('INFO', `HEARTBEAT: derived=${stats.derived} skipped=${stats.skipped} errors=${stats.errors}`);
          stats = { derived: 0, skipped: 0, errors: 0, heartbeats: stats.heartbeats };
          lastPublished = now;
        }

      } catch(e) {
        stats.errors++;
        svcLog('ERROR', `Exception: ${e.message}`);
      }
    });

    app.setPluginStatus('Running');
  };

  plugin.stop = function() {
    svcLog('INFO', 'SHUTDOWN: signalk-heading-true-calculator stopped');
  };

  return plugin;
};
