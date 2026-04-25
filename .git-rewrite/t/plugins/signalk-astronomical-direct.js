/**
 * Signal K Astronomical Data Plugin - DIRECT to InfluxDB
 * Bypasses Signal K schema issues by sending directly to InfluxDB
 * 
 * Sends sun/moon/tide data directly as line protocol to InfluxDB
 * No Signal K schema registration needed!
 */

module.exports = function(app) {
  let plugin = {
    id: 'signalk-astronomical-direct',
    name: 'Astronomical Data Plugin (Direct InfluxDB)',
    description: 'Calculates and sends sun/moon/tide data directly to InfluxDB',
    version: '3.0.0-direct',
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
        },
        influxUrl: {
          type: 'string',
          description: 'InfluxDB URL',
          default: 'http://localhost:8086'
        },
        influxToken: {
          type: 'string',
          description: 'InfluxDB API token'
        },
        influxOrg: {
          type: 'string',
          default: 'MidnightRider'
        },
        influxBucket: {
          type: 'string',
          default: 'signalk'
        },
        noaaStation: {
          type: 'string',
          description: 'NOAA station ID for tides',
          default: '8467150'
        }
      }
    }
  };

  plugin.start = function(options, restartPlugin) {
    const debug = options.debug || false;
    let lastUpdateDate = null;
    
    const DEFAULT_LAT = options.defaultLat || 41.0534;
    const DEFAULT_LON = options.defaultLon || -73.5387;
    
    // InfluxDB config
    const INFLUX_URL = options.influxUrl || 'http://localhost:8086';
    const INFLUX_TOKEN = options.influxToken;
    const INFLUX_ORG = options.influxOrg || 'MidnightRider';
    const INFLUX_BUCKET = options.influxBucket || 'signalk';
    
    // NOAA config
    const NOAA_STATION = options.noaaStation || '8467150';
    const NOAA_API = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter';
    
    let axios;
    try {
      axios = require('axios');
    } catch (e) {
      app.warn('[AstroDirect] axios not found');
      axios = null;
    }

    if (!INFLUX_TOKEN) {
      app.error('[AstroDirect] ❌ InfluxDB token not configured!');
      return plugin;
    }

    console.log('[AstroDirect] 🌍 Plugin started (DIRECT InfluxDB mode)');
    console.log(`[AstroDirect] Config: ${JSON.stringify({ INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET, NOAA_STATION, DEBUG: debug })}`);
    
    if (!INFLUX_TOKEN) {
      console.error('[AstroDirect] ❌❌❌ NO TOKEN CONFIGURED!');
      return plugin;
    }
    console.log('[AstroDirect] ✅ Token found');
    
    // Send immediately on startup
    console.log('[AstroDirect] Calling sendAstroDataDirect()...');
    sendAstroDataDirect().catch(err => {
      console.error('[AstroDirect] Startup error:', err.message);
    });
    
    // Check every hour
    setInterval(sendAstroDataDirect, 3600000);
    
    async function sendAstroDataDirect() {
      console.log('[AstroDirect] --> sendAstroDataDirect called');
      try {
        const today = new Date().toLocaleDateString();
        
        // Skip if already updated today
        if (lastUpdateDate === today) {
          console.log('[AstroDirect] ⏭️  Already updated today, skipping');
          return;
        }
        
        console.log('[AstroDirect] ⏰ Calculating and sending data...');
        
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
        
        console.log(`[AstroDirect] 📍 Position: ${lat.toFixed(4)}, ${lon.toFixed(4)}`);
        
        // Calculate astronomical data
        const SunCalc = require('suncalc');
        const now = new Date();
        
        const sunTimes = SunCalc.getTimes(now, lat, lon);
        const moonTimes = SunCalc.getMoonTimes(now, lat, lon);
        const moonIll = SunCalc.getMoonIllumination(now);
        
        // Get tides from NOAA
        let tideData = null;
        if (axios) {
          try {
            tideData = await fetchTides(now);
          } catch (err) {
            app.warn(`[AstroDirect] NOAA failed: ${err.message}`);
          }
        }
        
        // Build line protocol for InfluxDB
        const lines = buildLineProtocol(sunTimes, moonTimes, moonIll, tideData, now);
        
        console.log(`[AstroDirect] 📝 Built ${lines.length} line(s) for InfluxDB`);
        lines.slice(0, 3).forEach(line => console.log(`[AstroDirect]   ${line.substring(0, 60)}...`));
        
        // Send to InfluxDB
        console.log('[AstroDirect] Sending to InfluxDB...');
        await sendToInfluxDB(lines);
        
        console.log('[AstroDirect] ✅ Sent to InfluxDB successfully!');
        
        lastUpdateDate = today;
        
      } catch (err) {
        console.error(`[AstroDirect] ❌ Error: ${err.message}`);
        console.error('[AstroDirect] Stack:', err.stack);
      }
    }
    
    async function fetchTides(date) {
      const tomorrow = new Date(date.getTime() + 86400000);
      const beginDate = formatDate(date);
      const endDate = formatDate(tomorrow);
      
      if (debug) app.debug(`[AstroDirect] 🌊 Fetching NOAA tides ${beginDate}-${endDate}`);
      
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
      
      if (response.data && response.data.predictions) {
        const highs = response.data.predictions.filter(p => p.type === 'H');
        const lows = response.data.predictions.filter(p => p.type === 'L');
        
        return {
          tideHighTime: highs.length > 0 ? highs[0].t : null,
          tideHighLevel: highs.length > 0 ? parseFloat(highs[0].v) : null,
          tideLowTime: lows.length > 0 ? lows[0].t : null,
          tideLowLevel: lows.length > 0 ? parseFloat(lows[0].v) : null
        };
      }
      
      return null;
    }
    
    function formatDate(date) {
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      return `${yyyy}${mm}${dd}`;
    }
    
    function buildLineProtocol(sunTimes, moonTimes, moonIll, tideData, timestamp) {
      const lines = [];
      const tags = `source=astronomical-plugin`;
      const ts = timestamp.getTime() * 1000000; // nanoseconds
      
      // Sun data
      lines.push(`environment.sun.sunriseTime,${tags} value="${sunTimes.sunrise.toISOString()}" ${ts}`);
      lines.push(`environment.sun.sunsetTime,${tags} value="${sunTimes.sunset.toISOString()}" ${ts}`);
      
      // Moon data
      lines.push(`environment.moon.moonriseTime,${tags} value="${moonTimes.rise ? moonTimes.rise.toISOString() : ''}" ${ts}`);
      lines.push(`environment.moon.moonsetTime,${tags} value="${moonTimes.set ? moonTimes.set.toISOString() : ''}" ${ts}`);
      lines.push(`environment.moon.illumination,${tags} value=${moonIll.fraction} ${ts}`);
      lines.push(`environment.moon.phase,${tags} value="${getPhase(moonIll.phase)}" ${ts}`);
      
      // Tide data (if available)
      if (tideData) {
        if (tideData.tideHighTime) lines.push(`environment.tide.tideHighTime,${tags} value="${tideData.tideHighTime}" ${ts}`);
        if (tideData.tideHighLevel !== null) lines.push(`environment.tide.tideHighLevel,${tags} value=${tideData.tideHighLevel} ${ts}`);
        if (tideData.tideLowTime) lines.push(`environment.tide.tideLowTime,${tags} value="${tideData.tideLowTime}" ${ts}`);
        if (tideData.tideLowLevel !== null) lines.push(`environment.tide.tideLowLevel,${tags} value=${tideData.tideLowLevel} ${ts}`);
      }
      
      return lines;
    }
    
    async function sendToInfluxDB(lines) {
      if (!lines || lines.length === 0) {
        console.warn('[AstroDirect] No lines to send');
        return;
      }
      
      console.log(`[AstroDirect] SendToInfluxDB: ${lines.length} lines, token length=${INFLUX_TOKEN.length}`);
      
      const data = lines.join('\n');
      
      const response = await axios.post(
        `${INFLUX_URL}/api/v2/write?org=${INFLUX_ORG}&bucket=${INFLUX_BUCKET}&precision=ns`,
        data,
        {
          headers: {
            'Authorization': `Token ${INFLUX_TOKEN}`,
            'Content-Type': 'text/plain'
          },
          timeout: 5000
        }
      );
      
      console.log(`[AstroDirect] InfluxDB response: ${response.status}`);
      
      if (response.status !== 204 && response.status !== 200) {
        throw new Error(`InfluxDB returned ${response.status}`);
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
      app.debug('[AstroDirect] Plugin stopped');
    };
    
    return plugin;
  };

  return plugin;
};
