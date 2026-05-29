/**
 * Signal K Plugin - WIT IMU NMEA0183 Parser
 *
 * Parses NMEA sentences from WIT WT901BLECL IMU (BLE accelerometer/gyroscope).
 *
 * Sentences handled:
 * - $HEATT — Attitude (roll, pitch, yaw in degrees)
 * - $HEHDT — Heading True (NOT handled here — already parsed by kflex NMEA0183 provider)
 *
 * AXIS REMAPPING (verified physically by Denis, 2026-05-17):
 * WIT Pitch (field[1]) → SK navigation.attitude.roll (gîte bâbord/tribord)
 * WIT Roll (field[0]) → SK navigation.attitude.pitch (assiette étrave haut/bas)
 * WIT Yaw (field[2]) → SK navigation.attitude.yaw (cap magnétique, post-calibration)
 *
 * MULTI-SOURCE NOTE (2026-05-29):
 * signalk-um982-proprietary also writes to navigation.attitude.* from the UM982 GNSS.
 * This is intentional — Signal K tags each delta with its source label (wit-nmea vs
 * um982-proprietary). Both sources coexist; Grafana can filter by source if needed.
 * WIT: faster IMU updates (dynamic heel/trim), magnetic yaw
 * UM982: GPS-based True heading, RTK quality metadata
 *
 * Signal K paths produced:
 * navigation.attitude.roll (radians, positive = starboard heel)
 * navigation.attitude.pitch (radians, positive = bow up)
 * navigation.attitude.yaw (radians, magnetic heading)
 * navigation.attitude (composite object for PGN 127257 → Vulcan 7 display)
 *
 * @author Aneto (MidnightRider J/30)
 * @version 1.0.0
 * @license MIT
 */

module.exports = function(app) {
  let plugin = {
    id: 'signalk-wit-nmea',
    name: 'WIT IMU NMEA Parser',
    description: 'Parse WIT WT901BLECL IMU attitude and heading sentences',
    version: '1.0.0',
    schema: {
      type: 'object',
      title: 'WIT IMU NMEA Parser',
      properties: {
        enabled: {
          type: 'boolean',
          title: 'Enable Parser',
          default: true
        },
        debug: {
          type: 'boolean',
          title: 'Debug Logging',
          default: false
        }
      }
    }
  };

  plugin.start = function(options, restartPlugin) {
    const debug = options.debug || false;
    
    app.debug('[WIT NMEA] Parser started');

    // Listen for all NMEA0183 sentences
    app.on('nmea0183out', (line) => {
      try {
        // Parse $HEATT sentences (WIT attitude)
        if (line.startsWith('$HEATT')) {
          const delta = parseHeatt(line);
          if (delta) {
            if (debug) {
              app.debug(`[WIT NMEA] HEATT: ${line}`);
            }
            app.handleMessage(plugin.id, delta);
          }
        }
        // Note: $HEHDT is already handled by kflex NMEA0183 provider
        // This plugin adds the attitude (roll/pitch/yaw) that kflex can't map
      } catch (err) {
        if (debug) {
          app.error(`[WIT NMEA] Error: ${err.message} on ${line}`);
        }
      }
    });

    plugin.stop = function() {
      app.debug('[WIT NMEA] Parser stopped');
    };

    return plugin;
  };

  /**
   * Parse $HEATT sentence
   * Format: $HEATT,roll,pitch,yaw*checksum
   * Values in degrees, convert to radians for Signal K
   */
  function parseHeatt(sentence) {
    try {
      // Remove checksum
      const data = sentence.split('*')[0];
      const fields = data.substring(7).split(',');
      
      if (fields.length < 3) {
        return null;
      }

      const rollDeg = parseFloat(fields[0]);
      const pitchDeg = parseFloat(fields[1]);
      const yawDeg = parseFloat(fields[2]);

      // Validate values
      if (isNaN(rollDeg) || isNaN(pitchDeg) || isNaN(yawDeg)) {
        return null;
      }

      // Convert to radians
      const rollRad = (rollDeg * Math.PI) / 180;
      const pitchRad = (pitchDeg * Math.PI) / 180;
      const yawRad = (yawDeg * Math.PI) / 180;

      // Build Signal K delta
      // NOTE: WIT axes remapped per physical verification (Denis 2026-05-17):
      // WIT Pitch (field[1]) → SK roll (gîte: bâbord/tribord)
      // WIT Roll (field[0]) → SK pitch (assiette: étrave haut/bas)
      // WIT Yaw (field[2]) → SK yaw (cap magnétique, calibration en mer)
      const delta = {
        context: 'vessels.self',
        source: {
          label: 'wit-nmea',
          type: 'NMEA0183'
        },
        timestamp: new Date().toISOString(),
        updates: [{
          source: { label: 'wit-nmea' },
          timestamp: new Date().toISOString(),
          values: [
            { path: 'navigation.attitude.roll', value: pitchRad },      // WIT Pitch = gîte
            { path: 'navigation.attitude.pitch', value: rollRad },      // WIT Roll = assiette
            { path: 'navigation.attitude.yaw', value: yawRad },         // WIT Yaw = cap (post-magneto)
            { path: 'navigation.attitude', value: { roll: pitchRad, pitch: rollRad, yaw: yawRad } }  // Composite for PGN 127257 → Vulcan 7
          ]
        }]
      };

      return delta;
    } catch (err) {
      return null;
    }
  }

  return plugin;
};
