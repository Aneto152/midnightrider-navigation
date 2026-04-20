/**
 * Signal K Plugin for Astronomical Data
 * Phase 1A: Sunrise/Sunset, Moonrise/Moonset, Moon Illumination & Phase
 * 
 * Updates: Once per day (check every hour)
 * Source: suncalc (npm) - no external API required
 * 
 * @author Aneto (MidnightRider J/30)
 * @version 1.0.0
 * @license MIT
 */

module.exports = function(app) {
  let plugin = {
    id: 'signalk-astronomical',
    name: 'Astronomical Data Plugin',
    description: 'Calculates and provides sunrise/sunset, moonrise/moonset, and moon phase data',
    version: '1.0.0',
    schema: {
      type: 'object',
      title: 'Astronomical Data Configuration',
      required: [],
      properties: {
        enabled: {
          type: 'boolean',
          title: 'Enable Plugin',
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
    let lastUpdateDate = null;

    app.debug('[Astro] Plugin started');

    // Check every hour if date has changed
    const checkInterval = setInterval(() => {
      checkAndUpdateAstronomical();
    }, 3600000); // 1 hour

    // Also check on startup
    checkAndUpdateAstronomical();

    function checkAndUpdateAstronomical() {
      try {
        const today = new Date().toLocaleDateString();

        if (lastUpdateDate === today) {
          if (debug) {
            app.debug('[Astro] Already updated today, skipping');
          }
          return;
        }

        if (debug) {
          app.debug('[Astro] Date changed, calculating new values');
        }

        // Get boat position from Signal K
        const position = app.signalk.self.navigation && app.signalk.self.navigation.position;

        if (!position || !position.value || !position.value.latitude || !position.value.longitude) {
          app.error('[Astro] No GPS position available yet');
          return;
        }

        const lat = position.value.latitude;
        const lon = position.value.longitude;

        if (debug) {
          app.debug(`[Astro] Using position: lat=${lat}, lon=${lon}`);
        }

        // Calculate astronomical data
        const astroData = calculateAstronomicalData(lat, lon);

        // Send to Signal K
        sendToSignalK(astroData);

        lastUpdateDate = today;
        app.debug(`[Astro] Updated astronomical data for ${today}`);

      } catch (err) {
        app.error(`[Astro] Error in checkAndUpdateAstronomical: ${err.message}`);
        if (debug) {
          app.error(`[Astro] Stack: ${err.stack}`);
        }
      }
    }

    function calculateAstronomicalData(lat, lon) {
      try {
        // Dynamically require suncalc
        let SunCalc;
        try {
          SunCalc = require('suncalc');
        } catch (e) {
          app.error('[Astro] suncalc module not found. Install with: npm install suncalc');
          return null;
        }

        const now = new Date();

        // Sun times
        const sunTimes = SunCalc.getTimes(now, lat, lon);
        
        // Moon times
        const moonTimes = SunCalc.getMoonTimes(now, lat, lon);
        
        // Moon illumination
        const moonIll = SunCalc.getMoonIllumination(now);

        const data = {
          timestamp: now.toISOString(),
          sun: {
            sunriseTime: sunTimes.sunrise ? sunTimes.sunrise.toISOString() : null,
            sunsetTime: sunTimes.sunset ? sunTimes.sunset.toISOString() : null
          },
          moon: {
            moonriseTime: moonTimes.rise ? moonTimes.rise.toISOString() : null,
            moonsetTime: moonTimes.set ? moonTimes.set.toISOString() : null,
            illumination: moonIll.fraction, // 0.0 to 1.0
            phase: getMoonPhase(moonIll.phase) // Convert to phase name
          }
        };

        if (debug) {
          app.debug(`[Astro] Calculated: ${JSON.stringify(data, null, 2)}`);
        }

        return data;

      } catch (err) {
        app.error(`[Astro] Error calculating data: ${err.message}`);
        return null;
      }
    }

    function getMoonPhase(phase) {
      // phase is angle in radians: 0 = new moon, π = full moon
      const phasePercent = (phase / (2 * Math.PI)) * 100;

      if (phasePercent < 6.25) return 'new_moon';
      if (phasePercent < 18.75) return 'waxing_crescent';
      if (phasePercent < 31.25) return 'first_quarter';
      if (phasePercent < 43.75) return 'waxing_gibbous';
      if (phasePercent < 56.25) return 'full_moon';
      if (phasePercent < 68.75) return 'waning_gibbous';
      if (phasePercent < 81.25) return 'last_quarter';
      if (phasePercent < 93.75) return 'waning_crescent';
      return 'new_moon';
    }

    function sendToSignalK(astroData) {
      if (!astroData) {
        app.error('[Astro] No data to send');
        return;
      }

      const delta = {
        timestamp: astroData.timestamp,
        updates: [
          {
            source: {
              label: 'signalk-astronomical',
              type: 'plugin'
            },
            timestamp: astroData.timestamp,
            values: [
              {
                path: 'navigation.sun.sunriseTime',
                value: astroData.sun.sunriseTime
              },
              {
                path: 'navigation.sun.sunsetTime',
                value: astroData.sun.sunsetTime
              },
              {
                path: 'navigation.moon.moonriseTime',
                value: astroData.moon.moonriseTime
              },
              {
                path: 'navigation.moon.moonsetTime',
                value: astroData.moon.moonsetTime
              },
              {
                path: 'navigation.moon.illumination',
                value: astroData.moon.illumination
              },
              {
                path: 'navigation.moon.phase',
                value: astroData.moon.phase
              }
            ]
          }
        ]
      };

      if (debug) {
        app.debug(`[Astro] Sending delta: ${JSON.stringify(delta, null, 2)}`);
      }

      app.handleMessage(plugin.id, delta);
    }

    // Cleanup on stop
    plugin.stop = function() {
      clearInterval(checkInterval);
      app.debug('[Astro] Plugin stopped');
    };

    return plugin;
  };

  return plugin;
};
