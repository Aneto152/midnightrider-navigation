#!/usr/bin/env node

/**
 * MCP Server for Astronomical Data
 * 
 * Provides access to sun/moon/tide data from InfluxDB
 * 
 * Tools:
 * - get_sun_data: Sunrise/sunset times for a date
 * - get_moon_data: Moon phase, illumination, rise/set times
 * - get_tide_data: High/low tide times and levels
 * - get_next_event: Next sunrise/sunset/moonrise/moonset
 */

const http = require('http');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';

// MCP Protocol version
const MCP_VERSION = '2024-11-05';

// Server state
let requestId = 0;

/**
 * Query InfluxDB using Flux
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
          reject(new Error(`InfluxDB error: ${res.statusCode} ${data}`));
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
  let currentTable = null;
  const headers = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Skip empty lines
    if (!line.trim()) continue;

    // Table marker
    if (line.startsWith('#group')) {
      if (currentTable && headers.length > 0) {
        results.push(currentTable);
      }
      currentTable = {};
      continue;
    }

    // Header line
    if (line.startsWith('#datatype')) {
      headers.length = 0;
      continue;
    }

    if (line.startsWith(',')) {
      const parts = line.substring(1).split(',');
      headers.push(...parts);
      continue;
    }

    // Data line
    if (!line.startsWith('#') && headers.length > 0) {
      const values = line.split(',');
      const record = {};
      for (let j = 0; j < headers.length && j < values.length; j++) {
        record[headers[j]] = values[j];
      }
      if (currentTable && Object.keys(record).length > 0) {
        Object.assign(currentTable, record);
      }
    }
  }

  if (currentTable && Object.keys(currentTable).length > 0) {
    results.push(currentTable);
  }

  return results;
}

/**
 * Get sun data for a specific date
 */
async function getSunData(date) {
  const query = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start: ${date}T00:00:00Z, stop: ${date}T23:59:59Z)
    |> filter(fn: (r) => r._measurement =~ /environment\.sun/)`;

  const results = await queryInfluxDB(query);
  
  const data = {
    date,
    sunrise: null,
    sunset: null,
    source: 'astronomical'
  };

  for (const result of results) {
    if (result._measurement === 'environment.sun.sunriseTime') {
      data.sunrise = result._value;
    } else if (result._measurement === 'environment.sun.sunsetTime') {
      data.sunset = result._value;
    }
  }

  return data;
}

/**
 * Get moon data for a specific date
 */
async function getMoonData(date) {
  const query = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start: ${date}T00:00:00Z, stop: ${date}T23:59:59Z)
    |> filter(fn: (r) => r._measurement =~ /environment\.moon/)`;

  const results = await queryInfluxDB(query);
  
  const data = {
    date,
    moonrise: null,
    moonset: null,
    illumination: null,
    phase: null,
    source: 'astronomical'
  };

  for (const result of results) {
    if (result._measurement === 'environment.moon.moonriseTime') {
      data.moonrise = result._value;
    } else if (result._measurement === 'environment.moon.moonsetTime') {
      data.moonset = result._value;
    } else if (result._measurement === 'environment.moon.illumination') {
      data.illumination = parseFloat(result._value);
    } else if (result._measurement === 'environment.moon.phase') {
      data.phase = result._value;
    }
  }

  return data;
}

/**
 * Get tide data for a specific date
 */
async function getTideData(date) {
  const query = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start: ${date}T00:00:00Z, stop: ${date}T23:59:59Z)
    |> filter(fn: (r) => r._measurement =~ /environment\.tide/)`;

  const results = await queryInfluxDB(query);
  
  const data = {
    date,
    tideHighTime: null,
    tideHighLevel: null,
    tideLowTime: null,
    tideLowLevel: null,
    source: 'astronomical'
  };

  for (const result of results) {
    if (result._measurement === 'environment.tide.tideHighTime') {
      data.tideHighTime = result._value;
    } else if (result._measurement === 'environment.tide.tideHighLevel') {
      data.tideHighLevel = parseFloat(result._value);
    } else if (result._measurement === 'environment.tide.tideLowTime') {
      data.tideLowTime = result._value;
    } else if (result._measurement === 'environment.tide.tideLowLevel') {
      data.tideLowLevel = parseFloat(result._value);
    }
  }

  return data;
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_sun_data':
        return await getSunData(args.date || new Date().toISOString().split('T')[0]);

      case 'get_moon_data':
        return await getMoonData(args.date || new Date().toISOString().split('T')[0]);

      case 'get_tide_data':
        return await getTideData(args.date || new Date().toISOString().split('T')[0]);

      case 'get_next_event':
        const sunToday = await getSunData(new Date().toISOString().split('T')[0]);
        const moonToday = await getMoonData(new Date().toISOString().split('T')[0]);
        
        const events = [];
        if (sunToday.sunrise) events.push({ time: sunToday.sunrise, type: 'sunrise' });
        if (sunToday.sunset) events.push({ time: sunToday.sunset, type: 'sunset' });
        if (moonToday.moonrise) events.push({ time: moonToday.moonrise, type: 'moonrise' });
        if (moonToday.moonset) events.push({ time: moonToday.moonset, type: 'moonset' });
        
        const now = new Date();
        const nextEvent = events
          .filter(e => new Date(e.time) > now)
          .sort((a, b) => new Date(a.time) - new Date(b.time))[0];
        
        return nextEvent || { error: 'No events today' };

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Handle incoming MCP request
 */
async function handleRequest(request) {
  const { jsonrpc, id, method, params } = request;

  if (method === 'initialize') {
    return {
      jsonrpc,
      id,
      result: {
        protocolVersion: MCP_VERSION,
        capabilities: {
          tools: {
            listChanged: false
          }
        },
        serverInfo: {
          name: 'astronomical-mcp-server',
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
            name: 'get_sun_data',
            description: 'Get sunrise and sunset times for a specific date',
            inputSchema: {
              type: 'object',
              properties: {
                date: {
                  type: 'string',
                  description: 'Date in YYYY-MM-DD format (default: today)'
                }
              }
            }
          },
          {
            name: 'get_moon_data',
            description: 'Get moon phase, illumination, rise/set times for a date',
            inputSchema: {
              type: 'object',
              properties: {
                date: {
                  type: 'string',
                  description: 'Date in YYYY-MM-DD format (default: today)'
                }
              }
            }
          },
          {
            name: 'get_tide_data',
            description: 'Get high/low tide times and levels for a date',
            inputSchema: {
              type: 'object',
              properties: {
                date: {
                  type: 'string',
                  description: 'Date in YYYY-MM-DD format (default: today)'
                }
              }
            }
          },
          {
            name: 'get_next_event',
            description: 'Get the next upcoming astronomical event (sunrise/sunset/moonrise/moonset)',
            inputSchema: {
              type: 'object',
              properties: {}
            }
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
 * Main server loop (stdio transport)
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
