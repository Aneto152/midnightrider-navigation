/**
 * Signal K Astronomical Data Plugin - SIMPLIFIED
 * Ultra-simple version for debugging
 * Just sends sun/moon data, no NOAA tides complexity
 */

module.exports = function(app) {
  let plugin = {
    id: 'signalk-astronomical-simple',
    name: 'Astronomical Data Plugin (Simple)',
    description: 'Simplified sun/moon calculator',
    version: '2.0.0-simple',
    schema: {
      type: 'object',
      properties: {
        enabled: {
          type: 'boolean',
          default: true
        },
        debug: {
          type: 'boolean',
          default: true
        },
        defaultLat: {
          type: 'number',
          default: 41.0534
        },
        defaultLon: {
          type: 'number',
          default: -73.5387
        }
      }
    }
  };

  plugin.start = function(options, restartPlugin) {
    const debug = options.debug || false;
    let lastUpdateDate = null;
    
    const DEFAULT_LAT = options.defaultLat || 41.0534;
    const DEFAULT_LON = options.defaultLon || -73.5387;

    app.debug('[Astro] 🌍 SIMPLE Plugin started');
    
    // Send immediately on startup
    console.log('[Astro] 🌍 Executing on startup...');
    sendAstroData();
    
    // Check every hour
    setInterval(sendAstroData, 3600000);
    
    function sendAstroData() {
      try {
        const today = new Date().toLocaleDateString();
        
        // Skip if already updated today
        if (lastUpdateDate === today) {
          if (debug) app.debug('[Astro] Already updated today');
          return;
        }
        
        if (debug) app.debug('[Astro] ⏰ Sending data...');
        
        // Get position or use default
        let lat = DEFAULT_LAT;
        let lon = DEFAULT_LON;
        
        const position = app.signalk.self && 
                        app.signalk.self.navigation && 
                        app.signalk.self.navigation.position;
        if (position && position.value) {
          lat = position.value.latitude || DEFAULT_LAT;
          lon = position.value.longitude || DEFAULT_LON;
        }
        
        if (debug) app.debug(`[Astro] Position: ${lat}, ${lon}`);
        
        // Calculate
        const SunCalc = require('suncalc');
        const now = new Date();
        
        const sunTimes = SunCalc.getTimes(now, lat, lon);
        const moonTimes = SunCalc.getMoonTimes(now, lat, lon);
        const moonIll = SunCalc.getMoonIllumination(now);
        
        if (debug) {
          console.log('[Astro] ☀️  Sunrise:', sunTimes.sunrise.toISOString());
          console.log('[Astro] 🌅 Sunset:', sunTimes.sunset.toISOString());
          console.log('[Astro] 🌙 Moon illumination:', (moonIll.fraction * 100).toFixed(1) + '%');
        }
        
        // Create delta
        const delta = {
          timestamp: now.toISOString(),
          updates: [{
            source: {
              label: 'signalk-astronomical-simple',
              type: 'plugin'
            },
            timestamp: now.toISOString(),
            values: [
              { path: 'environment.sun.sunriseTime', value: sunTimes.sunrise.toISOString() },
              { path: 'environment.sun.sunsetTime', value: sunTimes.sunset.toISOString() },
              { path: 'environment.moon.moonriseTime', value: moonTimes.rise ? moonTimes.rise.toISOString() : null },
              { path: 'environment.moon.moonsetTime', value: moonTimes.set ? moonTimes.set.toISOString() : null },
              { path: 'environment.moon.illumination', value: moonIll.fraction },
              { path: 'environment.moon.phase', value: getPhase(moonIll.phase) }
            ]
          }]
        };
        
        if (debug) {
          console.log('[Astro] 📤 Sending to Signal K:');
          console.log(JSON.stringify(delta, null, 2));
        }
        
        // Send it!
        app.handleMessage(plugin.id, delta);
        
        if (debug) app.debug('[Astro] ✅ Sent!');
        
        lastUpdateDate = today;
        
      } catch (err) {
        app.error('[Astro] ❌ Error:', err.message);
        if (debug) console.error(err);
      }
    }
    
    function getPhase(phase) {
      const p = (phase / (2 * Math.PI)) * 100;
      if (p < 6.25) return 'new_moon';
      if (p < 18.75) return 'waxing_crescent';
      if (p < 31.25) return 'first_quarter';
      if (p < 43.75) return 'waxing_gibbous';
      if (p < 56.25) return 'full_moon';
      if (p < 68.75) return 'waning_gibbous';
      if (p < 81.25) return 'last_quarter';
      if (p < 93.75) return 'waning_crescent';
      return 'new_moon';
    }
    
    plugin.stop = function() {
      app.debug('[Astro] Plugin stopped');
    };
    
    return plugin;
  };

  return plugin;
};
