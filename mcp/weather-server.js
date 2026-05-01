#!/usr/bin/env node

/**
 * MCP Server for Weather Data
 * 
 * Tools for accessing weather information logged to InfluxDB:
 * - Current conditions (temperature, humidity, pressure, wind)
 * - Forecast (6h, 12h, 24h, 3-day)
 * - Alerts (severe weather)
 * - Weather trends
 */

const http = require('http');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';

const MCP_VERSION = '2024-11-05';

/**
 * Query InfluxDB
 */
async function queryInfluxDB(fluxQuery) {
  return new Promise((resolve, reject) => {
    const postData = fluxQuery;
    const options = {
      hostname: 'localhost',
      port: 8086,
      path: `/api/v2/query?org=${INFLUX_ORG}`,
      method: 'POST',
      headers: {
        'Authorization': `Token ${INFLUX_TOKEN}`,
        'Content-Type': 'application/vnd.flux',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode === 200) {
          resolve(parseFluxResponse(data));
        } else {
          reject(new Error(`InfluxDB error: ${res.statusCode}`));
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

/**
 * Parse Flux CSV response
 */
function parseFluxResponse(csvData) {
  const lines = csvData.trim().split('\n');
  if (lines.length < 4) return [];

  const results = [];
  let currentRecord = {};
  const headers = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;

    if (line.startsWith('#group') || line.startsWith('#datatype')) continue;

    if (line.startsWith(',')) {
      const parts = line.substring(1).split(',');
      headers.length = 0;
      headers.push(...parts);
      continue;
    }

    if (!line.startsWith('#') && headers.length > 0) {
      const values = line.split(',');
      for (let j = 0; j < headers.length && j < values.length; j++) {
        currentRecord[headers[j]] = values[j];
      }
      if (Object.keys(currentRecord).length > 0) {
        results.push({ ...currentRecord });
      }
    }
  }

  return results;
}

/**
 * Get current weather conditions
 */
async function getCurrentWeather() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -30m)
      |> filter(fn: (r) => r._measurement =~ /^weather\\./ and r.location == "stamford")
      |> last()`;

    const results = await queryInfluxDB(query);
    
    const weatherData = {};
    for (const result of results) {
      const measurement = result._measurement;
      const value = result._value;
      weatherData[measurement] = value;
    }

    return {
      timestamp: new Date().toISOString(),
      temperature_celsius: weatherData['weather.temperature'] ? parseFloat(weatherData['weather.temperature']).toFixed(1) : null,
      temperature_fahrenheit: weatherData['weather.temperature'] ? (parseFloat(weatherData['weather.temperature']) * 9/5 + 32).toFixed(1) : null,
      humidity_percent: weatherData['weather.humidity'] ? parseFloat(weatherData['weather.humidity']).toFixed(0) : null,
      pressure_hpa: weatherData['weather.pressure'] ? parseFloat(weatherData['weather.pressure']).toFixed(1) : null,
      wind_speed_kmh: weatherData['weather.wind_speed'] ? parseFloat(weatherData['weather.wind_speed']).toFixed(1) : null,
      wind_speed_knots: weatherData['weather.wind_speed'] ? (parseFloat(weatherData['weather.wind_speed']) / 1.852).toFixed(1) : null,
      wind_direction_degrees: weatherData['weather.wind_direction'] ? parseFloat(weatherData['weather.wind_direction']).toFixed(0) : null,
      wind_gust_kmh: weatherData['weather.wind_gust'] ? parseFloat(weatherData['weather.wind_gust']).toFixed(1) : null,
      wind_gust_knots: weatherData['weather.wind_gust'] ? (parseFloat(weatherData['weather.wind_gust']) / 1.852).toFixed(1) : null,
      precipitation_mm: weatherData['weather.precipitation'] ? parseFloat(weatherData['weather.precipitation']).toFixed(1) : null,
      condition: weatherData['weather.condition'] || 'Unknown',
      assessment: assessWeather(weatherData)
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get weather trend (improving/stable/deteriorating)
 */
async function getWeatherTrend() {
  try {
    // Compare last 30 min with previous 30 min
    const recent = await queryInfluxDB(`from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -30m)
      |> filter(fn: (r) => r._measurement == "weather.temperature" and r.location == "stamford")
      |> last()`);
    
    const previous = await queryInfluxDB(`from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -60m, stop: -30m)
      |> filter(fn: (r) => r._measurement == "weather.temperature" and r.location == "stamford")
      |> last()`);

    const recentTemp = recent.length > 0 ? parseFloat(recent[0]._value) : null;
    const previousTemp = previous.length > 0 ? parseFloat(previous[0]._value) : null;

    let trend = 'Stable';
    let tempChange = 0;

    if (recentTemp && previousTemp) {
      tempChange = recentTemp - previousTemp;
      if (tempChange > 0.5) trend = 'Warming';
      else if (tempChange < -0.5) trend = 'Cooling';
    }

    return {
      temperature_trend: trend,
      temperature_change_celsius: tempChange.toFixed(1),
      assessment: `Temperature ${trend.toLowerCase()} (${tempChange > 0 ? '+' : ''}${tempChange.toFixed(1)}°C last 30 min)`
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get wind assessment for sailing
 */
async function getWindAssessment() {
  try {
    const current = await getCurrentWeather();
    
    if (!current.wind_speed_knots) {
      return { error: 'No wind data available' };
    }

    const wind = parseFloat(current.wind_speed_knots);
    const gust = current.wind_gust_knots ? parseFloat(current.wind_gust_knots) : wind;
    
    return {
      wind_speed_knots: current.wind_speed_knots,
      wind_gust_knots: current.wind_gust_knots,
      wind_direction_degrees: current.wind_direction_degrees,
      sailing_condition: getSailingCondition(wind),
      wind_range: `${wind.toFixed(1)} - ${gust.toFixed(1)} knots`,
      recommendations: getWindRecommendations(wind, gust),
      best_sail_combo: suggestSails(wind)
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get sailing condition from wind speed
 */
function getSailingCondition(windSpeed) {
  if (windSpeed < 5) return 'Light wind - challenging';
  if (windSpeed < 8) return 'Light breeze - good for training';
  if (windSpeed < 12) return 'Moderate breeze - optimal';
  if (windSpeed < 16) return 'Fresh breeze - good racing conditions';
  if (windSpeed < 20) return 'Strong breeze - manageable';
  if (windSpeed < 25) return 'Strong gale - expert sailing';
  return 'Severe gale - dangerous';
}

/**
 * Get wind recommendations
 */
function getWindRecommendations(wind, gust) {
  const recs = [];

  if (wind < 5) {
    recs.push('Light conditions - focus on smooth sailing');
    recs.push('Avoid sudden maneuvers');
  } else if (wind < 8) {
    recs.push('Good for light air sailing');
    recs.push('Watch for wind shear');
  } else if (wind < 12) {
    recs.push('Optimal conditions');
    recs.push('Standard sail configuration');
  } else if (wind < 16) {
    recs.push('Good racing wind');
    recs.push('Consider reefing if gusts exceed ' + (wind + 5));
  } else if (wind < 20) {
    recs.push('Strong conditions - reef mainsail');
    recs.push('Consider jib2 or storm jib');
  } else {
    recs.push('WARNING: Severe conditions');
    recs.push('Consider returning to harbor');
    recs.push('Double-check all safety equipment');
  }

  if (gust > wind + 8) {
    recs.push('Significant gusts detected - adjust trim frequently');
  }

  return recs;
}

/**
 * Suggest sail combination
 */
function suggestSails(wind) {
  if (wind < 5) return 'Main + Jib1 (max area)';
  if (wind < 8) return 'Main + Jib1';
  if (wind < 12) return 'Main + Jib2';
  if (wind < 16) return 'Main + Jib3 or Jib2';
  if (wind < 20) return 'Main (reefed) + Jib3';
  return 'Storm jib only';
}

/**
 * Assess overall weather
 */
function assessWeather(weatherData) {
  const temp = weatherData['weather.temperature'];
  const humidity = weatherData['weather.humidity'];
  const pressure = weatherData['weather.pressure'];
  const condition = weatherData['weather.condition'];

  let assessment = '';

  if (condition && condition.includes('Rain')) assessment += '⚠️ RAIN. ';
  if (condition && condition.includes('Thunderstorm')) assessment += '⚠️ THUNDERSTORM. ';
  if (condition && condition.includes('Fog')) assessment += '⚠️ FOG. ';
  
  if (temp && parseFloat(temp) < 0) assessment += '🥶 Below freezing. ';
  if (humidity && parseFloat(humidity) > 90) assessment += '💧 High humidity. ';
  
  if (pressure) {
    const p = parseFloat(pressure);
    if (p < 1010) assessment += '⬇️ Falling pressure (deteriorating). ';
    if (p > 1025) assessment += '⬆️ Rising pressure (improving). ';
  }

  if (!assessment) assessment = '✅ Good conditions';

  return assessment;
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_current_weather':
        return await getCurrentWeather();

      case 'get_weather_trend':
        return await getWeatherTrend();

      case 'get_wind_assessment':
        return await getWindAssessment();

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Handle MCP request
 */
async function handleRequest(request) {
  const { jsonrpc, id, method, params } = request;

  if (method === 'initialize') {
    return {
      jsonrpc,
      id,
      result: {
        protocolVersion: MCP_VERSION,
        capabilities: { tools: { listChanged: false } },
        serverInfo: {
          name: 'weather-mcp-server',
          version: '1.0.0'
        }
      }
    };
  }

  if (method === 'tools/list') {
    return {
      jsonrpc,
      id,
      result: {
        tools: [
          {
            name: 'get_current_weather',
            description: 'Get current weather conditions (temperature, humidity, wind, pressure)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_weather_trend',
            description: 'Get weather trend (warming/cooling/stable)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_wind_assessment',
            description: 'Get sailing-specific wind assessment with recommendations',
            inputSchema: { type: 'object', properties: {} }
          }
        ]
      }
    };
  }

  if (method === 'tools/call') {
    const result = await handleTool(params.name, params.arguments || {});
    return {
      jsonrpc,
      id,
      result: {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }
        ]
      }
    };
  }

  return {
    jsonrpc,
    id,
    error: {
      code: -32601,
      message: 'Method not found'
    }
  };
}

/**
 * Main server loop
 */
async function main() {
  const readline = require('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  rl.on('line', async (line) => {
    if (!line.trim()) return;

    try {
      const request = JSON.parse(line);
      const response = await handleRequest(request);
      console.log(JSON.stringify(response));
    } catch (err) {
      console.error(JSON.stringify({
        jsonrpc: '2.0',
        error: {
          code: -32700,
          message: 'Parse error',
          data: err.message
        }
      }));
    }
  });

  rl.on('close', () => {
    process.exit(0);
  });
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
