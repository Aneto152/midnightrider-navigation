/**
 * Signal K Plugin - Sails Management System V2 (J/30 with J1/J2/J3)
 * 
 * Real-time sail configuration recommendations based on:
 * - Wind speed & direction (TWS, TWA)
 * - Boat attitude (heel angle)
 * - Performance metrics (efficiency vs polars)
 * - J1/J2/J3 jib classification (full detail)
 * - Safety limits (J/30: heel < 22°)
 * 
 * For: J/30 with J1 Genoa, J2 Working, J3 Heavy jibs
 * 
 * @author Aneto (MidnightRider J/30)
 * @version 2.0.0
 * @license MIT
 */

module.exports = function(app) {
  const debug = true;
  
  // Jib classification for J/30
  // Area in sq ft for reference
  const JIB_SPECS = {
    'J1': { name: 'J1 Genoa', area: 300, luff: 44, usage: 'Light air (<6kt)' },
    'J2': { name: 'J2 Working', area: 210, luff: 38, usage: 'Medium (6-12kt)' },
    'J3': { name: 'J3 Heavy', area: 180, luff: 36, usage: 'Strong (12-16kt)' },
    'STORM': { name: 'Storm Jib', area: 100, luff: 32, usage: 'Gale (>=16kt)' }
  };

  // Decision matrix: [tack][wind] = {main, jib, heel, recommendation}
  // Wind classes: LIGHT(<4), LIGHT_AIR(4-6), MEDIUM(7-12), FRESH(13-15), STRONG(16-18), GALE(>=19)
  // Jib options: J1, J2, J3, STORM, OUT (poled)
  
  const SAIL_MATRIX = {
    'BEATING': {
      'LIGHT': {
        main: 'FULL', jib: 'J1', area: 'FULL', heelTarget: 12,
        recommendation: 'Light air - J1 Genoa (max speed)'
      },
      'LIGHT_AIR': {
        main: 'FULL', jib: 'J1', area: 'FULL', heelTarget: 14,
        recommendation: 'Light air beating - J1 Genoa'
      },
      'MEDIUM': {
        main: 'FULL', jib: 'J2', area: 'FULL', heelTarget: 16,
        recommendation: 'Medium wind - J2 Working Jib'
      },
      'FRESH': {
        main: 'FULL', jib: 'J2', area: 'FULL', heelTarget: 18,
        recommendation: 'Fresh wind - J2 Working, monitor heel'
      },
      'STRONG': {
        main: '1REEF', jib: 'J3', area: 'FULL', heelTarget: 20,
        recommendation: 'Strong wind - Reef 1 + J3 Heavy'
      },
      'GALE': {
        main: '2REEF', jib: 'STORM', area: 'FULL', heelTarget: 22,
        recommendation: 'Gale - Reef 2 + Storm Jib (limit)'
      }
    },
    
    'CLOSE_REACH': {
      'LIGHT': {
        main: 'FULL', jib: 'J1', spinnaker: 'READY', heelTarget: 15,
        recommendation: 'Close reach light - J1 + spinnaker ready'
      },
      'LIGHT_AIR': {
        main: 'FULL', jib: 'J1', spinnaker: 'READY', heelTarget: 16,
        recommendation: 'Close reach light air - J1 Genoa'
      },
      'MEDIUM': {
        main: 'FULL', jib: 'J2', spinnaker: 'READY', heelTarget: 18,
        recommendation: 'Close reach medium - J2 + spi ready'
      },
      'FRESH': {
        main: 'FULL', jib: 'J2', spinnaker: 'DOWN', heelTarget: 20,
        recommendation: 'Close reach fresh - J2 + douse spinnaker'
      },
      'STRONG': {
        main: '1REEF', jib: 'J3', spinnaker: 'DOWN', heelTarget: 22,
        recommendation: 'Close reach strong - Reef 1 + J3'
      },
      'GALE': {
        main: '2REEF', jib: 'STORM', spinnaker: 'DOWN', heelTarget: 20,
        recommendation: 'Close reach gale - Reef 2 + Storm'
      }
    },
    
    'BEAM_REACH': {
      'LIGHT': {
        main: 'FULL', jib: 'J1', spinnaker: 'READY', heelTarget: 16,
        recommendation: 'Beam reach - J1 + power mode'
      },
      'LIGHT_AIR': {
        main: 'FULL', jib: 'J1', spinnaker: 'READY', heelTarget: 17,
        recommendation: 'Beam reach light - J1 Genoa up'
      },
      'MEDIUM': {
        main: 'FULL', jib: 'J2', spinnaker: 'READY', heelTarget: 18,
        recommendation: 'Beam reach medium - J2 optimal'
      },
      'FRESH': {
        main: 'FULL', jib: 'J2', spinnaker: 'DOWN', heelTarget: 20,
        recommendation: 'Beam reach fresh - J2 + spi down'
      },
      'STRONG': {
        main: '1REEF', jib: 'J3', spinnaker: 'DOWN', heelTarget: 22,
        recommendation: 'Beam reach strong - Reef + J3'
      },
      'GALE': {
        main: '2REEF', jib: 'STORM', spinnaker: 'DOWN', heelTarget: 20,
        recommendation: 'Beam reach gale - Reef 2 + Storm'
      }
    },
    
    'BROAD_REACH': {
      'LIGHT': {
        main: 'FULL', jib: 'OUT', spinnaker: 'UP', heelTarget: 14,
        recommendation: 'Broad reach - spinnaker up, jib poled'
      },
      'LIGHT_AIR': {
        main: 'FULL', jib: 'OUT', spinnaker: 'UP', heelTarget: 15,
        recommendation: 'Broad reach light - spi up'
      },
      'MEDIUM': {
        main: 'FULL', jib: 'OUT', spinnaker: 'READY', heelTarget: 17,
        recommendation: 'Broad reach medium - prepare spinnaker'
      },
      'FRESH': {
        main: 'FULL', jib: 'OUT', spinnaker: 'DOWN', heelTarget: 19,
        recommendation: 'Broad reach fresh - spi down'
      },
      'STRONG': {
        main: '1REEF', jib: 'OUT', spinnaker: 'DOWN', heelTarget: 20,
        recommendation: 'Broad reach strong - reef + jib poled'
      },
      'GALE': {
        main: '2REEF', jib: 'OUT', spinnaker: 'DOWN', heelTarget: 18,
        recommendation: 'Broad reach gale - minimal sail'
      }
    },
    
    'RUNNING': {
      'LIGHT': {
        main: 'FULL', jib: 'OUT', spinnaker: 'UP', heelTarget: 12,
        recommendation: 'Running light - spinnaker up, wing-on-wing'
      },
      'LIGHT_AIR': {
        main: 'FULL', jib: 'OUT', spinnaker: 'UP', heelTarget: 13,
        recommendation: 'Running light - spi up'
      },
      'MEDIUM': {
        main: 'FULL', jib: 'OUT', spinnaker: 'READY', heelTarget: 15,
        recommendation: 'Running medium - prepare spinnaker'
      },
      'FRESH': {
        main: 'FULL', jib: 'OUT', spinnaker: 'DOWN', heelTarget: 16,
        recommendation: 'Running fresh - spi down'
      },
      'STRONG': {
        main: '1REEF', jib: 'OUT', spinnaker: 'DOWN', heelTarget: 18,
        recommendation: 'Running strong - reef'
      },
      'GALE': {
        main: 'DOWN', jib: 'OUT', spinnaker: 'DOWN', heelTarget: 14,
        recommendation: 'Running gale - bare poles or minimal'
      }
    }
  };

  // Wind classifier
  function classifyWind(tws) {
    if (tws < 4) return 'LIGHT';
    if (tws < 6) return 'LIGHT_AIR';
    if (tws < 13) return 'MEDIUM';
    if (tws < 16) return 'FRESH';
    if (tws < 19) return 'STRONG';
    return 'GALE';
  }

  // Tack classifier (by True Wind Angle)
  function classifyTack(twa) {
    // Normalize to 0-360
    let angle = twa;
    if (angle < 0) angle += 360;
    if (angle >= 360) angle -= 360;

    if (angle < 50 || angle > 310) return 'BEATING';
    if (angle < 90) return 'CLOSE_REACH';
    if (angle < 150) return 'BEAM_REACH';
    if (angle < 210) return 'BROAD_REACH';
    return 'RUNNING';
  }

  // Jib decision logic (wind + heel based)
  function recommendJib(tws, heel) {
    const windClass = classifyWind(tws);

    // J1 logic: Light air only
    if (windClass === 'LIGHT' || windClass === 'LIGHT_AIR') {
      return { jib: 'J1', reason: 'Light air - max area' };
    }

    // J2 logic: Medium to Fresh (< 16kt)
    if (windClass === 'MEDIUM' || windClass === 'FRESH') {
      if (heel < 18) return { jib: 'J2', reason: `Medium wind, heel ${heel.toFixed(1)}°` };
      if (heel >= 18 && heel < 20) return { jib: 'J2', reason: `Fresh wind, heel rising to ${heel.toFixed(1)}°` };
    }

    // J3 logic: Strong wind or excessive heel
    if (windClass === 'STRONG') {
      if (heel >= 20) return { jib: 'J3', reason: `Strong wind + heel ${heel.toFixed(1)}° = reduce` };
      return { jib: 'J3', reason: `Strong wind (${tws.toFixed(1)} kt) = heavy jib` };
    }

    // Storm logic: Gale or extreme heel
    if (windClass === 'GALE' || heel >= 22) {
      return { jib: 'STORM', reason: `Gale conditions or heel ${heel.toFixed(1)}° critical` };
    }

    // Default
    return { jib: 'J2', reason: 'Default medium' };
  }

  // Plugin interface
  const plugin = {
    id: 'signalk-sails-management-v2',
    name: 'Sails Management V2 (J1/J2/J3)',
    description: 'Real-time sail recommendations for J/30 with J1/J2/J3 jibs',
    version: '2.0.0',
    
    schema: {
      type: 'object',
      title: 'Sails Management V2',
      properties: {
        enabled: { type: 'boolean', default: true },
        debug: { type: 'boolean', default: true },
        updateInterval: { type: 'number', default: 2000 }
      }
    },

    start: function(options, restartPlugin) {
      if (!options.enabled) return;

      const updateInterval = options.updateInterval || 2000;
      const doDebug = options.debug !== false;

      if (doDebug) {
        app.debug('[Sails V2] Plugin started (J1/J2/J3 support)');
        app.debug('[Sails V2] Jib specs: J1(' + JIB_SPECS.J1.area + 'sf), J2(' + JIB_SPECS.J2.area + 'sf), J3(' + JIB_SPECS.J3.area + 'sf), STORM(' + JIB_SPECS.STORM.area + 'sf)');
      }

      setInterval(function() {
        try {
          // Get required inputs
          const twsData = app.getSelfPath('environment.wind.speedTrue');
          const twaData = app.getSelfPath('environment.wind.angleTrue');
          const heelData = app.getSelfPath('navigation.attitude.roll');

          // Validate
          if (!twsData || !twaData || !heelData) return;
          if (twsData.value === undefined || twaData.value === undefined || heelData.value === undefined) return;

          const tws = twsData.value;
          const twa = twaData.value * 180 / Math.PI; // Convert radians to degrees
          const heel = Math.abs(heelData.value * 180 / Math.PI); // Convert to degrees, absolute

          // Classify
          const tack = classifyTack(twa);
          const windClass = classifyWind(tws);
          const jibRec = recommendJib(tws, heel);

          // Get matrix entry
          const matrix = SAIL_MATRIX[tack] && SAIL_MATRIX[tack][windClass];
          if (!matrix) return;

          // Build output
          const output = {
            current: {
              tack: tack,
              windClass: windClass,
              tws: tws.toFixed(2),
              twa: twa.toFixed(1),
              heel: heel.toFixed(1)
            },
            recommendation: {
              main: matrix.main,
              jib: jibRec.jib,
              jibs: {
                J1: { area: JIB_SPECS.J1.area, name: JIB_SPECS.J1.name },
                J2: { area: JIB_SPECS.J2.area, name: JIB_SPECS.J2.name },
                J3: { area: JIB_SPECS.J3.area, name: JIB_SPECS.J3.name },
                STORM: { area: JIB_SPECS.STORM.area, name: JIB_SPECS.STORM.name }
              },
              reason: jibRec.reason + ' (tack:' + tack + ')',
              heelTarget: matrix.heelTarget,
              fullRecommendation: matrix.recommendation
            }
          };

          // Inject into Signal K
          app.handleMessage({
            updates: [{
              source: { label: 'sails-v2', type: 'NMEA0183' },
              timestamp: new Date().toISOString(),
              values: [
                { path: 'navigation.sails.jib.recommended', value: jibRec.jib },
                { path: 'navigation.sails.jib.heelTarget', value: matrix.heelTarget },
                { path: 'navigation.sails.main.recommended', value: matrix.main },
                { path: 'navigation.sails.recommendation', value: matrix.recommendation }
              ]
            }]
          });

          if (doDebug) {
            app.debug('[Sails V2] Tack:' + tack + ' Wind:' + windClass + '(' + tws.toFixed(1) + 'kt) Heel:' + heel.toFixed(1) + '° → Recommend:' + matrix.main + ' + ' + jibRec.jib);
          }

        } catch (err) {
          app.error('[Sails V2] Error: ' + err.message);
        }
      }, updateInterval);

      app.debug('[Sails V2] Processing started (interval: ' + updateInterval + 'ms)');
    },

    stop: function() {
      app.debug('[Sails V2] Plugin stopped');
    }
  };

  return plugin;
};
