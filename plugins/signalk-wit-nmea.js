/**
 * Signal K Plugin - WIT IMU NMEA0183 Parser
 * 
 * Parses standard NMEA sentences from WIT WT901BLECL IMU:
 * - $HEHDT (Heading True)
 * - $HEATT (Attitude: roll, pitch, yaw)
 * 
 * Injects data into Signal K tree
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
            { path: 'navigation.attitude.roll', value: rollRad },
            { path: 'navigation.attitude.pitch', value: pitchRad },
            { path: 'navigation.attitude.yaw', value: yawRad }
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
