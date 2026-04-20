/**
 * Signal K Plugin for Astronomical Data + Tides
 * Phase 1: Sunrise/Sunset, Moonrise/Moonset, Moon Illumination, Tides (NOAA)
 * 
 * Updates: Once per day (check every hour)
 * Sources: 
 *   - suncalc (npm) for sun/moon calculations
 *   - NOAA API for tide predictions (NY Harbor: station 8518750)
 * 
 * @author Aneto (MidnightRider J/30)
 * @version 1.1.0
 * @license MIT
 */

module.exports = function(app) {
  let plugin = {
    id: 'signalk-astronomical',
    name: 'Astronomical Data + Tides Plugin',
    description: 'Calculates sunrise/sunset, moonrise/moonset, moon phase, and fetches tide predictions from NOAA',
    version: '1.1.0',
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
        },
        noaaStation: {
          type: 'string',
          title: 'NOAA Tides Station ID',
          description: 'Station ID for NOAA tides API (default: 8518750 for NY Harbor)',
          default: '8518750'
        }
      }
    }
  };

  plugin.start = function(options, restartPlugin) {
    const debug = options.debug || false;
    let lastUpdateDate = null;

    // NOAA API configuration
    const NOAA_STATION = options.noaaStation || '8518750';
    const NOAA_API = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter';

    // Try to require axios, warn if not available
    let axios;
    try {
      axios = require('axios');
    } catch (e) {
      app.warn('[Astro] axios not found for NOAA API. Install with: npm install axios');
      axios = null;
    }

    app.debug('[Astro] Plugin started');
    app.debug(`[Astro] NOAA Station: ${NOAA_STATION}`);

    // Check every hour if date has changed
    const checkInterval = setInterval(() => {
      checkAndUpdateAstronomical();
    }, 3600000); // 1 hour

    // Also check on startup
    checkAndUpdateAstronomical();

    function checkAndUpdateAstronomical() {
      try {
        const today = new Date().toLocaleDateString();
        
        // Check if environment data already exists
        const hasEnvironmentData = app.signalk.self.environment && 
                                   app.signalk.self.environment.sun &&
                                   app.signalk.self.environment.sun.sunriseTime;
        
        // Send if: date changed OR no environment data yet
        if (lastUpdateDate === today && hasEnvironmentData) {
          if (debug) {
            app.debug('[Astro] Already updated today, skipping');
          }
          return;
        }

        if (debug) {
          if (lastUpdateDate !== today) {
            app.debug('[Astro] Date changed, calculating new values');
          } else {
            app.debug('[Astro] No environment data yet, sending first values');
          }
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

        // Fetch tides from NOAA and send combined data
        if (axios) {
          fetchTidesAndSend(astroData);
        } else {
          // Send astro data only if axios not available
          sendToSignalK(astroData);
        }

        lastUpdateDate = today;
        app.debug(`[Astro] Updated data for ${today}`);

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
          app.debug(`[Astro] Calculated astro data: ${JSON.stringify(data, null, 2)}`);
        }

        return data;

      } catch (err) {
        app.error(`[Astro] Error calculating astro data: ${err.message}`);
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

    async function fetchTidesAndSend(astroData) {
      try {
        const tomorrow = new Date(new Date().getTime() + 86400000);
        const beginDate = formatDate(new Date());
        const endDate = formatDate(tomorrow);

        if (debug) {
          app.debug(`[Astro] Fetching NOAA tides for ${beginDate} to ${endDate}`);
        }

        const response = await axios.get(NOAA_API, {
          params: {
            station: NOAA_STATION,
            begin_date: beginDate,
            end_date: endDate,
            product: 'predictions',
            datum: 'MLLW',
            time_zone: 'lst_ldt',
            units: 'metric',
            format: 'json'
          },
          timeout: 10000
        });

        if (response.data && response.data.predictions && response.data.predictions.length > 0) {
          const tideData = parseTideData(response.data.predictions);
          if (tideData) {
            astroData.tide = tideData;
            if (debug) {
              app.debug(`[Astro] Parsed tide data: ${JSON.stringify(tideData)}`);
            }
          }
        } else {
          app.warn('[Astro] No tide predictions in NOAA response');
        }

        // Send combined data to Signal K
        sendToSignalK(astroData);

      } catch (err) {
        app.warn(`[Astro] NOAA API error (will send astro data only): ${err.message}`);
        // Send astro data even if tides fail
        sendToSignalK(astroData);
      }
    }

    function formatDate(date) {
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      return `${yyyy}${mm}${dd}`;
    }

    function parseTideData(predictions) {
      try {
        // Find high and low tides
        const highs = predictions.filter(p => p.type === 'H');
        const lows = predictions.filter(p => p.type === 'L');

        if (highs.length === 0 || lows.length === 0) {
          app.warn('[Astro] No tide extrema found in predictions');
          return null;
        }

        // Get first high and low
        const highTide = highs[0];
        const lowTide = lows[0];

        return {
          tideHighTime: highTide.t,  // ISO format from NOAA
          tideHighLevel: parseFloat(highTide.v),
          tideLowTime: lowTide.t,
          tideLowLevel: parseFloat(lowTide.v)
        };
      } catch (err) {
        app.error(`[Astro] Error parsing tide data: ${err.message}`);
        return null;
      }
    }

    function sendToSignalK(astroData) {
      if (!astroData) {
        app.error('[Astro] No data to send');
        return;
      }

      const values = [
        {
          path: 'environment.sun.sunriseTime',
          value: astroData.sun.sunriseTime
        },
        {
          path: 'environment.sun.sunsetTime',
          value: astroData.sun.sunsetTime
        },
        {
          path: 'environment.moon.moonriseTime',
          value: astroData.moon.moonriseTime
        },
        {
          path: 'environment.moon.moonsetTime',
          value: astroData.moon.moonsetTime
        },
        {
          path: 'environment.moon.illumination',
          value: astroData.moon.illumination
        },
        {
          path: 'environment.moon.phase',
          value: astroData.moon.phase
        }
      ];

      // Add tide data if available
      if (astroData.tide) {
        values.push(
          {
            path: 'environment.tide.tideHighTime',
            value: astroData.tide.tideHighTime
          },
          {
            path: 'environment.tide.tideHighLevel',
            value: astroData.tide.tideHighLevel
          },
          {
            path: 'environment.tide.tideLowTime',
            value: astroData.tide.tideLowTime
          },
          {
            path: 'environment.tide.tideLowLevel',
            value: astroData.tide.tideLowLevel
          }
        );
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
            values: values
          }
        ]
      };

      if (debug) {
        app.debug(`[Astro] Sending delta with ${values.length} values`);
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
