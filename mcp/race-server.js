#!/usr/bin/env node

/**
 * MCP Server for Race Management
 * 
 * Tools for managing race timing and tactical information:
 * - Current sails in use
 * - Start line information
 * - Start sequence timing
 * - Distance to start line
 * - Race marks
 * - Tactical situation
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
 * Get current sails
 */
async function getCurrentSails() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement =~ /sails\\./)
      |> last()`;

    const results = await queryInfluxDB(query);
    
    const sails = {
      mainsail: null,
      jib: null,
      spinnaker: null,
      jib_state: null,
      spinnaker_state: null
    };

    for (const result of results) {
      const measurement = result._measurement;
      const value = result._value;
      
      if (measurement === 'sails.mainsail') sails.mainsail = value;
      else if (measurement === 'sails.jib') sails.jib = value;
      else if (measurement === 'sails.spinnaker') sails.spinnaker = value;
      else if (measurement === 'sails.jib.state') sails.jib_state = value;
      else if (measurement === 'sails.spinnaker.state') sails.spinnaker_state = value;
    }

    return {
      mainsail: sails.mainsail || 'unknown',
      jib: sails.jib || 'none',
      jib_state: sails.jib_state || 'unknown',
      spinnaker: sails.spinnaker || 'none',
      spinnaker_state: sails.spinnaker_state || 'none',
      configuration: generateSailConfiguration(sails.mainsail, sails.jib, sails.spinnaker)
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Generate sail configuration description
 */
function generateSailConfiguration(main, jib, spinnaker) {
  const config = [];
  
  if (main) config.push(main);
  if (jib && jib !== 'none') config.push(jib);
  if (spinnaker && spinnaker !== 'none') config.push(spinnaker);
  
  return config.length > 0 ? config.join(' + ') : 'None set';
}

/**
 * Get race start timing
 */
async function getRaceStart() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -2h)
      |> filter(fn: (r) => r._measurement =~ /race\\.start\\./)
      |> last()`;

    const results = await queryInfluxDB(query);
    
    const raceData = {};
    for (const result of results) {
      const measurement = result._measurement;
      const value = result._value;
      raceData[measurement] = value;
    }

    const startTime = raceData['race.start.time'];
    const now = new Date();
    const startDate = startTime ? new Date(startTime) : null;
    
    let timeToStart = null;
    let status = 'unknown';

    if (startDate) {
      const diffMs = startDate - now;
      timeToStart = Math.floor(diffMs / 1000);

      if (timeToStart > 300) {
        status = 'Preparing';
      } else if (timeToStart > 0) {
        status = 'Countdown';
      } else if (timeToStart > -30) {
        status = 'Starting';
      } else {
        status = 'Started';
      }
    }

    return {
      race_name: raceData['race.start.name'] || 'Race 1',
      start_time: startTime,
      time_to_start_seconds: timeToStart,
      start_status: status,
      signal_sequence: getSignalSequence(timeToStart),
      class: raceData['race.start.class'] || 'J/30',
      start_line_length_meters: raceData['race.start.lineLength'] || 'unknown'
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get signal sequence description
 */
function getSignalSequence(secondsToStart) {
  if (secondsToStart === null) return 'No start time set';
  
  if (secondsToStart > 600) return '10+ minutes: Prepare';
  if (secondsToStart > 300) return '5-10 min: 1st Warning Signal (3 horn blasts)';
  if (secondsToStart > 240) return '4 min: Preparatory Signal (2 horn blasts)';
  if (secondsToStart > 0) return `${Math.floor(secondsToStart)}s to start (1 horn blast at 0)`;
  if (secondsToStart > -30) return 'START! (Continuing horn)';
  
  return 'Race started';
}

/**
 * Get distance to start line
 */
async function getDistanceToLine() {
  try {
    // Query boat position
    const latQuery = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "navigation.position.latitude")
      |> last()`;
    
    const lonQuery = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "navigation.position.longitude")
      |> last()`;

    const latRes = await queryInfluxDB(latQuery);
    const lonRes = await queryInfluxDB(lonQuery);

    const boatLat = latRes.length > 0 ? parseFloat(latRes[0]._value) : null;
    const boatLon = lonRes.length > 0 ? parseFloat(lonRes[0]._value) : null;

    // Query start line data
    const lineQuery = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -2h)
      |> filter(fn: (r) => r._measurement =~ /race\\.startLine\\./)
      |> last()`;

    const lineRes = await queryInfluxDB(lineQuery);

    const lineData = {};
    for (const result of lineRes) {
      const measurement = result._measurement;
      const value = result._value;
      lineData[measurement] = value;
    }

    if (!boatLat || !boatLon) {
      return { error: 'No position data available' };
    }

    // If no start line data, return estimated
    const startLineLat = lineData['race.startLine.latitude'] ? parseFloat(lineData['race.startLine.latitude']) : boatLat + 0.01;
    const startLineLon = lineData['race.startLine.longitude'] ? parseFloat(lineData['race.startLine.longitude']) : boatLon;

    const distance = haversineDistance(boatLat, boatLon, startLineLat, startLineLon);
    const distanceMeters = distance * 1000;

    return {
      boat_position: {
        latitude: boatLat.toFixed(6),
        longitude: boatLon.toFixed(6)
      },
      start_line_position: {
        latitude: startLineLat.toFixed(6),
        longitude: startLineLon.toFixed(6)
      },
      distance_meters: distanceMeters.toFixed(0),
      distance_nautical_miles: (distanceMeters / 1852).toFixed(3),
      distance_status: getDistanceStatus(distanceMeters),
      recommendation: getLineRecommendation(distanceMeters)
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Haversine distance calculation
 */
function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Get distance status
 */
function getDistanceStatus(distanceMeters) {
  if (distanceMeters < 500) return 'Very close to line';
  if (distanceMeters < 1000) return 'Close to line';
  if (distanceMeters < 2000) return 'Moderate distance';
  if (distanceMeters < 5000) return 'Far from line';
  return 'Very far from line';
}

/**
 * Get recommendation for line
 */
function getLineRecommendation(distanceMeters) {
  if (distanceMeters < 200) return '⚠️ DANGER: Too close! Risk of early start.';
  if (distanceMeters < 500) return 'Getting close. Prepare to come down to line.';
  if (distanceMeters < 1500) return 'Good position. Plan approach to line.';
  if (distanceMeters < 3000) return 'Adequate distance. Begin working toward line.';
  return 'Far from line. Start heading toward start line.';
}

/**
 * Get race marks
 */
async function getRaceMarks() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -2h)
      |> filter(fn: (r) => r._measurement =~ /race\\.mark\\./)`;

    const results = await queryInfluxDB(query);

    const marks = {};
    for (const result of results) {
      const measurement = result._measurement;
      const value = result._value;
      marks[measurement] = value;
    }

    return {
      windward_mark: marks['race.mark.windward'] || 'unknown',
      leeward_mark: marks['race.mark.leeward'] || 'unknown',
      gate_marks: [marks['race.mark.gate1'] || null, marks['race.mark.gate2'] || null],
      finish_line: marks['race.mark.finish'] || 'unknown',
      course_type: determineCourseType(marks)
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Determine course type
 */
function determineCourseType(marks) {
  const hasWind = marks['race.mark.windward'];
  const hasLee = marks['race.mark.leeward'];
  const hasGate = marks['race.mark.gate1'];

  if (hasWind && hasLee && hasGate) return 'Full Olympic (upwind/downwind/upwind)';
  if (hasWind && hasLee) return 'Simple windward/leeward';
  return 'Unknown/Custom course';
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_current_sails':
        return await getCurrentSails();

      case 'get_race_start':
        return await getRaceStart();

      case 'get_distance_to_line':
        return await getDistanceToLine();

      case 'get_race_marks':
        return await getRaceMarks();

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
          name: 'race-mcp-server',
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
            name: 'get_current_sails',
            description: 'Get current sails in use (main, jib, spinnaker)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_race_start',
            description: 'Get race start timing and countdown',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_distance_to_line',
            description: 'Get distance to start line with recommendations',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_race_marks',
            description: 'Get race course marks (windward, leeward, gates, finish)',
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
