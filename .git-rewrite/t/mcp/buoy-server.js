#!/usr/bin/env node

/**
 * MCP Server for Buoy Data (NOAA)
 * 
 * Real-time wind observations from Long Island Sound buoys:
 * - NOAA 44065 (Stamford/Western LIS)
 * - NOAA 44025 (Central LIS)
 * - NOAA 44008 (Block Island/Eastern LIS)
 */

const http = require('http');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'signalk';

const MCP_VERSION = '2024-11-05';

// Buoy locations
const BUOYS = {
  '44065': { name: 'Stamford (Western LIS)', lat: 41.063, lon: -73.591, distance: '5 nm' },
  '44025': { name: 'Central LIS', lat: 40.876, lon: -73.100, distance: '20 nm' },
  '44008': { name: 'Block Island (Eastern LIS)', lat: 40.502, lon: -71.029, distance: '50 nm' }
};

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
 * Get current buoy data
 */
async function getBuoyData() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement =~ /^buoy\\./)
      |> group(columns: ["station"])
      |> last()`;

    const results = await queryInfluxDB(query);
    
    const buoyData = {};
    for (const result of results) {
      const station = result.station || 'unknown';
      const measurement = result._measurement;
      const value = result._value;
      const location = result.location || 'unknown';
      
      if (!buoyData[station]) {
        buoyData[station] = {
          location: location,
          station: station,
          buoy_info: BUOYS[station] || {},
          measurements: {}
        };
      }
      
      buoyData[station].measurements[measurement] = value;
    }

    // Format response
    const response = {
      timestamp: new Date().toISOString(),
      buoys: []
    };

    for (const [station, data] of Object.entries(buoyData)) {
      const info = BUOYS[station] || { name: 'Unknown', lat: 0, lon: 0, distance: '?' };
      
      response.buoys.push({
        station: station,
        name: info.name,
        location: `${info.lat}°N, ${info.lon}°W`,
        distance_from_stamford: info.distance,
        wind_speed_knots: data.measurements['buoy.wind_speed_knots'] ? parseFloat(data.measurements['buoy.wind_speed_knots']).toFixed(1) : null,
        wind_gust_knots: data.measurements['buoy.wind_gust_knots'] ? parseFloat(data.measurements['buoy.wind_gust_knots']).toFixed(1) : null,
        wind_direction_degrees: data.measurements['buoy.wind_direction'] ? parseFloat(data.measurements['buoy.wind_direction']).toFixed(0) : null,
        wave_height_meters: data.measurements['buoy.wave_height'] ? parseFloat(data.measurements['buoy.wave_height']).toFixed(2) : null,
        water_temperature_celsius: data.measurements['buoy.water_temperature'] ? parseFloat(data.measurements['buoy.water_temperature']).toFixed(1) : null
      });
    }

    return response;
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get wind comparison across all buoys
 */
async function getWindComparison() {
  try {
    const buoyData = await getBuoyData();
    
    if (buoyData.error) return buoyData;

    const comparison = {
      timestamp: buoyData.timestamp,
      summary: [],
      strongest: null,
      weakest: null,
      average_wind: 0
    };

    let totalWind = 0;
    let windCount = 0;

    for (const buoy of buoyData.buoys) {
      if (buoy.wind_speed_knots) {
        const wind = parseFloat(buoy.wind_speed_knots);
        totalWind += wind;
        windCount++;

        comparison.summary.push({
          station: buoy.station,
          name: buoy.name,
          wind_knots: wind,
          gust_knots: buoy.wind_gust_knots,
          distance: buoy.distance_from_stamford
        });

        if (!comparison.strongest || wind > parseFloat(comparison.strongest.wind_knots)) {
          comparison.strongest = {
            station: buoy.station,
            name: buoy.name,
            wind_knots: wind,
            location: buoy.location
          };
        }

        if (!comparison.weakest || wind < parseFloat(comparison.weakest.wind_knots)) {
          comparison.weakest = {
            station: buoy.station,
            name: buoy.name,
            wind_knots: wind,
            location: buoy.location
          };
        }
      }
    }

    if (windCount > 0) {
      comparison.average_wind = (totalWind / windCount).toFixed(1);
    }

    // Add assessment
    const avgWind = parseFloat(comparison.average_wind);
    if (avgWind < 5) comparison.assessment = 'Light wind across LIS';
    else if (avgWind < 10) comparison.assessment = 'Light to moderate wind';
    else if (avgWind < 15) comparison.assessment = 'Moderate to fresh wind';
    else if (avgWind < 20) comparison.assessment = 'Fresh to strong wind';
    else comparison.assessment = 'Strong wind conditions across LIS';

    return comparison;
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_buoy_data':
        return await getBuoyData();

      case 'get_wind_comparison':
        return await getWindComparison();

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
          name: 'buoy-mcp-server',
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
            name: 'get_buoy_data',
            description: 'Get current wind and wave data from all NOAA buoys in Long Island Sound',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_wind_comparison',
            description: 'Compare wind conditions across all LIS buoys (strongest, weakest, average)',
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
