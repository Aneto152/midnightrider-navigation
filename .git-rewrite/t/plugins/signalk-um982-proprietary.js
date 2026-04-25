/**
 * Signal K Plugin for UM982 Proprietary Sentences
 * Parses #HEADINGA and #UNIHEADINGA sentences from Unicore UM982 GNSS receiver
 * 
 * UM982 sends proprietary attitude data (roll/pitch/yaw) via #HEADINGA sentences
 * Standard NMEA0183 parser ignores these non-standard sentences.
 * 
 * @author Aneto (MidnightRider J/30)
 * @version 1.0.0
 * @license MIT
 */

module.exports = function(app) {
  let plugin = {
    id: 'um982-proprietary',
    name: 'UM982 Proprietary Sentence Parser',
    description: 'Parses #HEADINGA sentences from Unicore UM982 for roll/pitch/yaw',
    version: '1.0.0',
    schema: {
      type: 'object',
      title: 'UM982 Proprietary Parser',
      description: 'Configuration for UM982 proprietary sentence parsing',
      required: [],
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
    
    app.debug('UM982 Proprietary Parser started');

    // Register custom NMEA0183 sentence parser
    // Listen for raw NMEA sentences
    if (app.registerNMEA0183Sentence) {
      // Standard way: register a sentence parser
      app.registerNMEA0183Sentence('HEA', parseHeadinga);
    }

    // Alternative: Hook into the serial data stream directly
    // This catches all data including proprietary sentences
    app.on('nmea0183out', (line) => {
      if (debug) {
        app.debug('NMEA line: ' + line);
      }

      // Parse #HEADINGA sentences
      if (line.startsWith('#HEADINGA') || line.startsWith('#UNIHEADINGA')) {
        try {
          const delta = parseProprietarySentence(line, app);
          if (delta && delta.updates && delta.updates.length > 0) {
            if (debug) {
              app.debug('Sending delta: ' + JSON.stringify(delta));
            }
            app.handleMessage(plugin.id, delta);
          }
        } catch (err) {
          app.error('Error parsing proprietary sentence: ' + err.message);
          if (debug) {
            app.error('Sentence: ' + line);
          }
        }
      }
    });

    plugin.stop = function() {
      app.debug('UM982 Proprietary Parser stopped');
    };

    return plugin;
  };

  /**
   * Parse #HEADINGA sentence
   * Format: #HEADINGA,COM1,13495,95.0,FINE,2415,73711.000,17020772,13,18;SOL_COMPUTED,L1_FLOAT,12.2446,260.1887,-35.0258,0.0000,292.7253,155.0128,"999",29,7,7,0,3,00,0,51*checksum
   * 
   * Key fields (post-semicolon):
   * [0] SOL_COMPUTED = Solution status
   * [1] L1_FLOAT = RTK mode
   * [2] 12.2446 = Roll (degrees)
   * [3] 260.1887 = Pitch (degrees)
   * [4] -35.0258 = Yaw/Heading (degrees)
   * [5] 0.0000 = Heading std dev
   * [6] 292.7253 = Baseline length (meters)
   * [7+] = Additional fields
   */
  function parseProprietarySentence(line, app) {
    try {
      // Remove checksum if present
      let sentence = line.split('*')[0];
      
      // Split on semicolon to get pre and post parts
      const parts = sentence.split(';');
      if (parts.length < 2) {
        return null;
      }

      const postParts = parts[1].split(',');
      
      // Verify we have enough fields
      if (postParts.length < 5) {
        return null;
      }

      const solStatus = postParts[0];      // SOL_COMPUTED
      const rtkMode = postParts[1];        // L1_FLOAT
      const roll = parseFloat(postParts[2]);       // 12.2446
      const pitch = parseFloat(postParts[3]);      // 260.1887
      const yaw = parseFloat(postParts[4]);        // -35.0258
      const headingStdDev = parseFloat(postParts[5]); // 0.0000
      const baseline = parseFloat(postParts[6]);   // 292.7253

      // Validate numbers
      if (isNaN(roll) || isNaN(pitch) || isNaN(yaw)) {
        return null;
      }

      // Skip if solution is insufficient
      if (solStatus === 'INSUFFICIENT_OBS' || solStatus === 'NONE') {
        // Return null or NaN values to indicate invalid solution
        return null;
      }

      // Convert degrees to radians for Signal K storage
      // Signal K uses radians internally
      const rollRad = (roll * Math.PI) / 180;
      const pitchRad = (pitch * Math.PI) / 180;
      const yawRad = (yaw * Math.PI) / 180;

      // Build Signal K delta
      // timestamp in ISO format
      const timestamp = new Date().toISOString();

      const delta = {
        timestamp: timestamp,
        updates: [
          {
            source: {
              label: 'um982-proprietary',
              type: 'NMEA0183'
            },
            timestamp: timestamp,
            values: [
              {
                path: 'navigation.attitude.roll',
                value: rollRad
              },
              {
                path: 'navigation.attitude.pitch',
                value: pitchRad
              },
              {
                path: 'navigation.attitude.yaw',
                value: yawRad
              },
              {
                path: 'navigation.attitude.yawReference',
                value: 'TRUE'  // Dual GNSS heading is true bearing
              },
              // Also store metadata
              {
                path: 'navigation.rtkMode',
                value: rtkMode
              },
              {
                path: 'navigation.gnssPositionStatus',
                value: solStatus
              },
              {
                path: 'navigation.baselineDistance',
                value: baseline
              }
            ]
          }
        ]
      };

      return delta;
    } catch (err) {
      app.error('Parse error in parseProprietarySentence: ' + err.message);
      return null;
    }
  }

  /**
   * Standard NMEA parser callback (for future use if Signal K supports it)
   */
  function parseHeadinga({ id, sentence, parts, tags }, session) {
    // Would be called by Signal K's standard parser
    // But proprietary sentences starting with # won't match standard patterns
    return null;
  }

  return plugin;
};
