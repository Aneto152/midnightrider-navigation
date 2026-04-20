#!/usr/bin/env node

/**
 * MCP Server for Crew Management
 * 
 * Tools for managing crew on board:
 * - Current helmsman
 * - Time at helm
 * - Crew rotation tracking
 * - Workload management
 * - Crew positions
 */

const http = require('http');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'signalk';

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
 * Get latest crew data
 */
async function getCrewStatus() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement =~ /crew\\./)
      |> last()`;

    const results = await queryInfluxDB(query);
    
    const crewData = {};
    for (const result of results) {
      const measurement = result._measurement;
      const value = result._value;
      crewData[measurement] = value;
    }

    return {
      current_helmsman: crewData['crew.helmsman.name'] || null,
      helmsman_watch_start: crewData['crew.helmsman.watchStart'] || null,
      helmsman_time_at_helm: crewData['crew.helmsman.timeAtHelm'] || null,
      tactician: crewData['crew.tactician.name'] || null,
      main_trimmer: crewData['crew.mainTrimmer.name'] || null,
      jib_trimmer: crewData['crew.jibTrimmer.name'] || null,
      bowman: crewData['crew.bowman.name'] || null,
      pit_crew: crewData['crew.pit.name'] || null,
      crew_count: Object.keys(crewData).filter(k => k.includes('.name')).length
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get helmsman watch history
 */
async function getHelmsmanHistory() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -8h)
      |> filter(fn: (r) => r._measurement == "crew.helmsman.change")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 10)`;

    const results = await queryInfluxDB(query);
    
    const history = results.map((r, idx) => ({
      helmsman: r._value,
      time: r._time,
      order: idx + 1
    }));

    return {
      helmsman_changes: history,
      total_changes: history.length,
      race_duration_hours: 8
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get crew workload assessment
 */
async function getCrewWorkload() {
  try {
    const windSpeed = (await queryInfluxDB(`from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "environment.wind.speedTrue")
      |> mean()`))[0]?._value;

    const sog = (await queryInfluxDB(`from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
      |> mean()`))[0]?._value;

    const workload = assessWorkload(windSpeed, sog);

    return {
      current_wind_speed: windSpeed ? windSpeed.toFixed(1) : null,
      current_speed: sog ? sog.toFixed(1) : null,
      workload_level: workload.level,
      workload_percentage: workload.percentage,
      recommended_watches: workload.recommendedWatches,
      crew_rotation_minutes: workload.rotationMinutes,
      priority_positions: workload.priorityPositions,
      assessment: workload.assessment
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Assess crew workload based on conditions
 */
function assessWorkload(windSpeed, boatSpeed) {
  const wind = windSpeed ? parseFloat(windSpeed) : 10;
  const speed = boatSpeed ? parseFloat(boatSpeed) : 6;

  let level = 'light';
  let percentage = 20;
  let rotationMinutes = 60;
  let recommendedWatches = 3;
  let priorityPositions = [];
  let assessment = '';

  if (wind < 8) {
    level = 'light';
    percentage = 20;
    rotationMinutes = 90;
    recommendedWatches = 2;
    assessment = 'Light conditions. Crew can focus on trim and tactics.';
  } else if (wind < 12) {
    level = 'moderate';
    percentage = 50;
    rotationMinutes = 60;
    recommendedWatches = 3;
    priorityPositions = ['Helmsman', 'Main Trimmer'];
    assessment = 'Moderate conditions. Regular rotation recommended.';
  } else if (wind < 16) {
    level = 'high';
    percentage = 75;
    rotationMinutes = 45;
    recommendedWatches = 4;
    priorityPositions = ['Helmsman', 'Main Trimmer', 'Jib Trimmer'];
    assessment = 'High workload. Frequent helm rotations advised.';
  } else {
    level = 'intense';
    percentage = 100;
    rotationMinutes = 30;
    recommendedWatches = 5;
    priorityPositions = ['Helmsman', 'Main Trimmer', 'Jib Trimmer', 'Bowman'];
    assessment = 'Intense conditions. Maximum alertness required.';
  }

  return {
    level,
    percentage,
    rotationMinutes,
    recommendedWatches,
    priorityPositions,
    assessment
  };
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_crew_status':
        return await getCrewStatus();

      case 'get_helmsman_history':
        return await getHelmsmanHistory();

      case 'get_crew_workload':
        return await getCrewWorkload();

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
          name: 'crew-mcp-server',
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
            name: 'get_crew_status',
            description: 'Get current crew on board (helmsman, tactician, trimmers, etc.)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_helmsman_history',
            description: 'Get helmsman rotation history',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_crew_workload',
            description: 'Get crew workload assessment and rotation recommendations',
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
