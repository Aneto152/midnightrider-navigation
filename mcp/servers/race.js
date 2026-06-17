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
      hostname: (() => { try { return new URL(INFLUX_URL).hostname; } catch(e) { return 'localhost'; } })(), port: (() => { try { return parseInt(new URL(INFLUX_URL).port) || 8086; } catch(e) { return 8086; } })(),
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
 * Get Cross-Track Error (XTE) from Signal K qtVLM
 */
async function getXTE() {
  try {
    // Read from Signal K courseRhumbline
    const xteUrl = `${SIGNALK_URL}/signalk/v1/api/navigation/courseRhumbline/crossTrackError`;
    const nextUrl = `${SIGNALK_URL}/signalk/v1/api/navigation/courseRhumbline/nextPoint`;
    
    const xteData = await fetch(xteUrl).then(r => r.json()).catch(() => null);
    const nextData = await fetch(nextUrl).then(r => r.json()).catch(() => null);
    
    const xte_m = xteData?.value || 0;
    const xte_nm = Math.abs(xte_m) / 1852;
    const side = xte_m > 0 ? 'starboard' : (xte_m < 0 ? 'port' : 'on_track');
    const next = nextData?.value || {};
    const dist_m = next.distance || null;
    
    return {
      xte_m: parseFloat(xte_m.toFixed(1)),
      xte_nm: parseFloat(xte_nm.toFixed(3)),
      xte_side: side,
      qtVLM_active: xteData?.value !== undefined,
      next_waypoint_name: next.name || 'Unknown',
      distance_to_waypoint_nm: dist_m ? parseFloat((dist_m / 1852).toFixed(2)) : null,
      note: Math.abs(xte_m) > 100 ? `${Math.abs(xte_m).toFixed(0)}m to ${side} of rhumb line` : 'On track'
    };
  } catch (err) {
    return { error: err.message, qtVLM_active: false };
  }
}

/**
 * Get Race Events log from regatta server
 */
async function getRaceEvents(lastN = 10) {
  try {
    const url = 'http://localhost:5000/api/event';
    const response = await fetch(url).then(r => r.json()).catch(() => []);
    const events = (Array.isArray(response) ? response : (response?.events || [])).slice(-Math.min(lastN, 50));
    const maneuvers = events.filter(e => ['tack', 'gybe', 'mark_rounding'].includes(e?.type));
    
    return {
      events: events,
      total_events: events.length,
      last_event: events[events.length - 1] || null,
      last_maneuver: maneuvers[maneuvers.length - 1] || null,
      event_types: [...new Set(events.map(e => e?.type).filter(Boolean))]
    };
  } catch (err) {
    return { error: err.message, events: [] };
  }
}

/**
 * Get ETA to next waypoint/mark
 */
async function getMarkETA() {
  try {
    const posUrl = `${SIGNALK_URL}/signalk/v1/api/navigation/position`;
    const sogUrl = `${SIGNALK_URL}/signalk/v1/api/navigation/speedOverGround`;
    const nextUrl = `${SIGNALK_URL}/signalk/v1/api/navigation/courseRhumbline/nextPoint`;
    
    const [posData, sogData, nextData] = await Promise.all([
      fetch(posUrl).then(r => r.json()).catch(() => null),
      fetch(sogUrl).then(r => r.json()).catch(() => null),
      fetch(nextUrl).then(r => r.json()).catch(() => null)
    ]);
    
    const sogMs = sogData?.value || 0;
    const sogKts = sogMs * 1.94384;
    const distM = nextData?.value?.distance || null;
    const distNm = distM ? distM / 1852 : null;
    const etaH = (distNm && sogKts > 0.5) ? (distNm / sogKts) : null;
    
    const now = new Date();
    let etaTime = null;
    if (etaH) {
      const eta = new Date(now.getTime() + etaH * 3600000);
      etaTime = eta.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'America/New_York' }) + ' EDT';
    }
    
    return {
      mark_name: nextData?.value?.name || 'Next mark',
      distance_nm: distNm ? parseFloat(distNm.toFixed(2)) : null,
      sog_kts: parseFloat(sogKts.toFixed(1)),
      eta_hours: etaH ? parseFloat(etaH.toFixed(2)) : null,
      eta_minutes: etaH ? Math.round(etaH * 60) : null,
      eta_local_time: etaTime,
      note: etaTime ? `${nextData?.value?.name || 'Mark'} in ${Math.floor(etaH)}h ${Math.round((etaH % 1) * 60)}min at ${sogKts.toFixed(1)}kts` : 'Speed too low for ETA estimate'
    };
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
      case 'get_current_sails':
        return await getCurrentSails();

      case 'get_race_start':
        return await getRaceStart();

      case 'get_distance_to_line':
        return await getDistanceToLine();

      case 'get_race_marks':
        return await getRaceMarks();

      case 'get_xte':
        return await getXTE();

      case 'get_race_events':
        return await getRaceEvents(args.last_n || 10);

      case 'get_mark_eta':
        return await getMarkETA();

      case 'get_xte':
        return await getXTE();

      case 'get_race_events':
        return await getRaceEvents(args.last_n || 10);

      case 'get_mark_eta':
        return await getMarkETA();

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
            name: 'get_xte',
            description: 'Get cross-track error (XTE) from qtVLM rhumb line',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_race_events',
            description: 'Get race events log (tacks, gybes, mark roundings)',
            inputSchema: { type: 'object', properties: { last_n: { type: 'number' } } }
          },
          {
            name: 'get_mark_eta',
            description: 'Get ETA to next mark in hours/minutes EDT',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_race_marks',
            description: 'Get race course marks (windward, leeward, gates, finish)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_xte',
            description: 'Get cross-track error (XTE) from qtVLM rhumb line',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_race_events',
            description: 'Get recent race events (tacks, gybes, mark roundings)',
            inputSchema: { type: 'object', properties: { last_n: { type: 'number' } } }
          },
          {
            name: 'get_mark_eta',
            description: 'Get estimated time of arrival to next mark',
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
 * Get Cross-Track Error (XTE) from qtVLM
 */
async function getXTE() {
  try {
    const response = await new Promise((resolve, reject) => {
      const options = {
        hostname: 'localhost',
        port: 3000,
        path: '/signalk/v1/api/navigation/courseRhumbline',
        method: 'GET'
      };
      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch { resolve(null); }
        });
      });
      req.on('error', () => reject(null));
      req.end();
    });

    if (!response || !response.crossTrackError) {
      return { xte_m: 0, xte_nm: 0, xte_side: 'on_track', qtVLM_active: false, note: 'qtVLM not active' };
    }

    const xteM = response.crossTrackError?.value || 0;
    const xteNm = xteM / 1852;
    const xteSide = xteM > 0 ? 'starboard' : (xteM < 0 ? 'port' : 'on_track');
    const nextPoint = response.nextPoint?.value || {};
    const distNm = (nextPoint.position?.distance || 0) / 1852;

    return {
      xte_m: Math.round(xteM),
      xte_nm: parseFloat(xteNm.toFixed(2)),
      xte_side: xteSide,
      next_waypoint_name: nextPoint.position?.name || 'Unknown',
      next_waypoint_lat: nextPoint.position?.latitude || 0,
      next_waypoint_lon: nextPoint.position?.longitude || 0,
      distance_to_waypoint_nm: parseFloat(distNm.toFixed(2)),
      qtVLM_active: true,
      note: `${Math.abs(Math.round(xteM))}m to ${xteSide} of rhumb line — steer ${xteSide === 'starboard' ? 'port' : 'starboard'} to correct`
    };
  } catch (err) {
    return { error: 'XTE unavailable', qtVLM_active: false };
  }
}

/**
 * Get Race Events from regatta server
 */
async function getRaceEvents(lastN = 10) {
  try {
    const response = await new Promise((resolve, reject) => {
      const options = {
        hostname: 'localhost',
        port: 5000,
        path: '/api/event',
        method: 'GET'
      };
      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch { resolve([]); }
        });
      });
      req.on('error', () => reject([]));
      req.end();
    });

    const allEvents = Array.isArray(response) ? response : (response.events || []);
    const recentEvents = allEvents.slice(-Math.min(lastN, 50));
    const lastEvent = recentEvents[recentEvents.length - 1] || {};
    const maneuvers = recentEvents.filter(e => ['tack', 'gybe', 'mark_rounding'].includes(e.type));
    const lastManeuver = maneuvers[maneuvers.length - 1];

    return {
      events: recentEvents.map(e => ({ time: e.time, type: e.type, description: e.description })),
      event_types: ['tack', 'gybe', 'mark_rounding', 'start', 'finish', 'penalty'],
      total_events_today: allEvents.length,
      last_event: { time: lastEvent.time, description: lastEvent.description },
      last_maneuver: lastManeuver ? { time: lastManeuver.time, type: lastManeuver.type, description: lastManeuver.description } : null
    };
  } catch (err) {
    return { error: 'Events unavailable', events: [], total_events_today: 0 };
  }
}

/**
 * Calculate ETA to next mark
 */
async function getMarkETA() {
  try {
    const posResponse = await new Promise((resolve, reject) => {
      const options = {
        hostname: 'localhost',
        port: 3000,
        path: '/signalk/v1/api/navigation',
        method: 'GET'
      };
      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch { resolve(null); }
        });
      });
      req.on('error', () => reject(null));
      req.end();
    });

    if (!posResponse || !posResponse.position) {
      return { error: 'Position unavailable' };
    }

    const ownLat = posResponse.position?.value?.latitude || 0;
    const ownLon = posResponse.position?.value?.longitude || 0;
    const sog = (posResponse.speedOverGround?.value || 0) / 0.51444;
    const vmg = (posResponse.speedMadeGood?.value || 0) / 0.51444;
    const markLat = posResponse.courseRhumbline?.nextPoint?.value?.position?.latitude || ownLat;
    const markLon = posResponse.courseRhumbline?.nextPoint?.value?.position?.longitude || ownLon;
    const markName = posResponse.courseRhumbline?.nextPoint?.value?.position?.name || 'Next Mark';

    const R = 3440.065;
    const dLat = (markLat - ownLat) * Math.PI / 180;
    const dLon = (markLon - ownLon) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(ownLat * Math.PI / 180) * Math.cos(markLat * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    const c = 2 * Math.asin(Math.sqrt(a));
    const distanceNm = R * c;

    const etaHours = sog > 0 ? distanceNm / sog : 0;
    const etaMinutes = Math.round((etaHours % 1) * 60);
    const etaHoursInt = Math.floor(etaHours);

    const now = new Date();
    const eta = new Date(now.getTime() + etaHours * 3600000);
    const etaLocalTime = eta.toLocaleString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'America/New_York' });

    return {
      mark_name: markName,
      distance_nm: parseFloat(distanceNm.toFixed(2)),
      sog_kts: parseFloat(sog.toFixed(1)),
      vmg_kts: parseFloat(vmg.toFixed(1)),
      eta_hours: etaHoursInt,
      eta_minutes: etaMinutes,
      eta_local_time: etaLocalTime,
      note: `${markName} in ${etaHoursInt}h ${etaMinutes}min at current SOG of ${sog.toFixed(1)} kts`
    };
  } catch (err) {
    return { error: 'ETA calculation failed' };
  }
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
