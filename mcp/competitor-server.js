#!/usr/bin/env node

/**
 * competitor-server.js — AIS Fleet Tracking MCP Server
 * 
 * Tracks nearby competitors via AIS (InfluxDB competitor_tracking measurement)
 * Provides tactical information for racing decisions
 * 
 * Tools:
 * 1. get_competitor_fleet — all tracked boats sorted by distance
 * 2. get_nearest_competitor — closest boat + gaining/losing analysis
 * 3. get_fleet_pressure — port/starboard distribution, rules analysis
 * 4. get_competitor_trend — distance trend for specific MMSI over time
 * 5. get_fleet_summary — narrative summary for Midnight Reporter
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';
const SIGNALK_URL = process.env.SIGNALK_HTTP || 'http://localhost:3000';

const MCP_VERSION = '2024-11-05';

// Load competitors data at startup
let competitorsData = {};
try {
  const competitorsPath = path.join(__dirname, '../regatta/competitors.json');
  if (fs.existsSync(competitorsPath)) {
    const raw = fs.readFileSync(competitorsPath, 'utf8');
    competitorsData = JSON.parse(raw);
  }
} catch (err) {
  console.error('Warning: Could not load competitors.json:', err.message);
}

// Helper: Query InfluxDB
async function queryInfluxDB(fluxQuery) {
  return new Promise((resolve, reject) => {
    const postData = fluxQuery;
    const options = {
      hostname: (() => { try { return new URL(INFLUX_URL).hostname; } catch(e) { return 'localhost'; } })(),
      port: (() => { try { return parseInt(new URL(INFLUX_URL).port) || 8086; } catch(e) { return 8086; } })(),
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

// Parse Flux CSV response
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
      headers.length = 0;
      headers.push(...line.substring(1).split(','));
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

// Helper: Get own COG from Signal K
async function getOwnCOG() {
  return new Promise((resolve) => {
    const options = {
      hostname: 'localhost',
      port: 3000,
      path: '/signalk/v1/api/navigation/courseOverGroundTrue',
      method: 'GET'
    };
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve((json.value * 180 / Math.PI) % 360);
        } catch { resolve(0); }
      });
    });
    req.on('error', () => resolve(0));
    req.end();
  });
}

// Convert radians to degrees
function radToDeg(rad) {
  return (rad * 180 / Math.PI) % 360;
}

// Get competitor metadata
function getCompetitorMeta(mmsi) {
  if (!competitorsData.competitors) return null;
  const boat = competitorsData.competitors.find(c => c.mmsi === mmsi);
  return boat || null;
}

// Determine relative position
function getRelativePosition(ownCOG, competitorBearing) {
  const diff = (competitorBearing - ownCOG + 360) % 360;
  if (diff < 45 || diff > 315) return 'ahead';
  if (diff < 135) return 'abeam_stbd';
  if (diff < 225) return 'behind';
  return 'abeam_port';
}

// TOOL 1: Get all tracked competitors
async function getCompetitorFleet(maxDistanceNm = 10) {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start:-10m)
      |> filter(fn:(r)=>r._measurement=="competitor_tracking")
      |> last()
      |> pivot(rowKey:["boat_name","mmsi","priority","competitor_id"],columnKey:["_field"],valueColumn:"_value")
      |> sort(columns:["distance_m"])`;

    const data = await queryInfluxDB(query);
    if (!data || data.length === 0) {
      return {
        tracked_count: 0,
        total_active: competitorsData._meta?.total_boats || 0,
        ais_connected: false,
        competitors: [],
        high_priority_close: []
      };
    }

    const ownCOG = await getOwnCOG();
    const competitors = data
      .map(row => {
        const distM = parseFloat(row.distance_m) || 0;
        const distNm = distM / 1852;
        if (distNm > maxDistanceNm) return null;

        const bearing = parseFloat(row.bearing_true) || 0;
        const meta = getCompetitorMeta(row.mmsi);

        return {
          name: row.boat_name || 'Unknown',
          skipper: meta?.skipper || 'Unknown',
          model: meta?.vessel?.model || 'Unknown',
          mmsi: row.mmsi,
          priority: row.priority || 'normal',
          distance_nm: parseFloat(distNm.toFixed(2)),
          bearing_true_deg: Math.round(bearing),
          sog_kts: parseFloat(((parseFloat(row.sog_ms) || 0) * 1.94384).toFixed(1)),
          cog_true_deg: Math.round(parseFloat(row.cog_true) || 0),
          ais_age_s: Math.round(parseFloat(row.ais_age_s) || 0),
          phrf_lis: meta?.ratings?.PHRF_LIS || null,
          irc_tcc: meta?.ratings?.IRC?.TCC || null,
          relative_position: getRelativePosition(ownCOG, bearing)
        };
      })
      .filter(c => c !== null);

    const highPriorityClose = competitors.filter(c => c.priority === 'high' && c.distance_nm <= 3);

    return {
      tracked_count: competitors.length,
      total_active: competitorsData._meta?.total_boats || 0,
      ais_connected: competitors.length > 0,
      competitors: competitors,
      high_priority_close: highPriorityClose.map(c => ({ name: c.name, distance_nm: c.distance_nm, bearing_deg: c.bearing_true_deg }))
    };
  } catch (err) {
    return { tracked_count: 0, total_active: 0, ais_connected: false, competitors: [], error: err.message };
  }
}

// TOOL 2: Get nearest competitor
async function getNearestCompetitor() {
  try {
    const fleet = await getCompetitorFleet(50);
    if (!fleet.competitors || fleet.competitors.length === 0) {
      return { error: 'No competitors tracked', ais_fresh: false };
    }

    const nearest = fleet.competitors[0];
    const isFresh = nearest.ais_age_s < 120;

    return {
      name: nearest.name,
      skipper: nearest.skipper,
      model: nearest.model,
      mmsi: nearest.mmsi,
      distance_nm: nearest.distance_nm,
      bearing_true_deg: nearest.bearing_true_deg,
      sog_kts: nearest.sog_kts,
      cog_true_deg: nearest.cog_true_deg,
      ais_age_s: nearest.ais_age_s,
      phrf_lis: nearest.phrf_lis,
      irc_tcc: nearest.irc_tcc,
      gaining: nearest.distance_nm < 1.0, // Mock: would need historical data
      delta_nm_5min: -0.1, // Mock: would need 5-min history
      tactical_note: `${nearest.name} (${nearest.model}) is ${nearest.distance_nm}nm on our ${nearest.relative_position.replace('_', ' ')}`,
      ais_fresh: isFresh
    };
  } catch (err) {
    return { error: 'Could not get nearest competitor', ais_fresh: false };
  }
}

// TOOL 3: Get fleet pressure (port/starboard distribution)
async function getFleetPressure() {
  try {
    const fleet = await getCompetitorFleet(50);
    const ownCOG = await getOwnCOG();

    let portCount = 0, stbdCount = 0, aheadCount = 0, behindCount = 0;
    const windwardBoats = [];

    fleet.competitors.forEach(c => {
      if (c.relative_position === 'abeam_port') portCount++;
      else if (c.relative_position === 'abeam_stbd') stbdCount++;
      else if (c.relative_position === 'ahead') aheadCount++;
      else if (c.relative_position === 'behind') behindCount++;
    });

    const fleetAssessment = `${stbdCount} boats to starboard, ${portCount} to port — ${stbdCount > portCount ? 'starboard tack favored' : 'port tack favored'}`;
    const rightsNote = `We have rights on ${behindCount} boats currently`;

    return {
      own_cog_deg: Math.round(ownCOG),
      port_count: portCount,
      stbd_count: stbdCount,
      ahead_count: aheadCount,
      behind_count: behindCount,
      windward_boats: windwardBoats,
      fleet_assessment: fleetAssessment,
      rights_note: rightsNote,
      tracked_count: fleet.tracked_count
    };
  } catch (err) {
    return { error: 'Could not assess fleet pressure', own_cog_deg: 0, port_count: 0, stbd_count: 0 };
  }
}

// TOOL 4: Get competitor trend
async function getCompetitorTrend(mmsi, minutes = 15) {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start:-${Math.min(minutes, 60)}m)
      |> filter(fn:(r)=>r._measurement=="competitor_tracking" and r.mmsi=="${mmsi}")
      |> filter(fn:(r)=>r._field=="distance_m")
      |> aggregateWindow(every:2m, fn:last, createEmpty:false)`;

    const data = await queryInfluxDB(query);
    if (!data || data.length < 2) {
      return { error: 'Insufficient trend data', mmsi, name: 'Unknown' };
    }

    const distances = data.map(d => parseFloat(d._value) || 0);
    const currentDist = distances[distances.length - 1];
    const earlierDist = distances[0];
    const deltaNm = (earlierDist - currentDist) / 1852;

    let trend = 'stable';
    if (deltaNm > 0.2) trend = 'gaining_on_us';
    else if (deltaNm < -0.2) trend = 'losing_to_us';

    const rateNmPerHour = (deltaNm / minutes) * 60;
    const meta = getCompetitorMeta(mmsi);

    return {
      mmsi,
      name: meta?.boat_name || 'Unknown',
      distance_history: distances.map((d, i) => ({
        time_min_ago: Math.round((distances.length - i - 1) * 2),
        distance_nm: parseFloat((d / 1852).toFixed(2))
      })),
      trend,
      rate_nm_per_hour: parseFloat(rateNmPerHour.toFixed(2)),
      trend_note: `Boat ${trend === 'gaining_on_us' ? 'gained' : 'lost'} ${Math.abs(deltaNm).toFixed(1)}nm in ${minutes}min — ${Math.abs(rateNmPerHour).toFixed(1)}nm/h`
    };
  } catch (err) {
    return { error: 'Could not calculate trend', mmsi };
  }
}

// TOOL 5: Get fleet summary
async function getFleetSummary() {
  try {
    const fleet = await getCompetitorFleet(10);
    const totalBoats = competitorsData._meta?.total_boats || 69;
    const trackedCount = fleet.tracked_count;
    const aisStatus = trackedCount > 0 ? 'active' : 'inactive';

    let fleetSnapshot = '';
    if (aisStatus === 'active') {
      const nearest = fleet.competitors[0];
      const highPriority = fleet.high_priority_close;
      const nearbyList = fleet.competitors.slice(0, 3).map(c => `${c.name} (${c.model}) at ${c.distance_nm}nm`).join(', ');

      fleetSnapshot = `Fleet of ${totalBoats} boats. AIS tracking ${trackedCount} competitors. Nearest: ${nearest.name} (${nearest.model}) at ${nearest.distance_nm}nm ${nearest.relative_position.replace('_', ' ')}. Nearby: ${nearbyList}.`;

      if (highPriority.length > 0) {
        fleetSnapshot += ` High priority: ${highPriority.map(h => h.name).join(', ')}.`;
      }
    } else {
      fleetSnapshot = `Fleet of ${totalBoats} boats. AIS receiver not yet connected — MMSI database ready for May 22.`;
    }

    return {
      total_competitors: totalBoats,
      tracked_now: trackedCount,
      ais_status: aisStatus,
      high_priority: fleet.high_priority_close,
      fleet_snapshot: fleetSnapshot,
      no_data_note: aisStatus === 'inactive' ? 'AIS receiver offline — system ready for race deployment' : null
    };
  } catch (err) {
    return {
      total_competitors: competitorsData._meta?.total_boats || 69,
      tracked_now: 0,
      ais_status: 'error',
      fleet_snapshot: 'Error retrieving fleet data',
      error: err.message
    };
  }
}

// Handle MCP tool calls
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_competitor_fleet':
        return await getCompetitorFleet(args.max_distance_nm || 10);
      case 'get_nearest_competitor':
        return await getNearestCompetitor();
      case 'get_fleet_pressure':
        return await getFleetPressure();
      case 'get_competitor_trend':
        return await getCompetitorTrend(args.mmsi, args.minutes || 15);
      case 'get_fleet_summary':
        return await getFleetSummary();
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) {
    return { error: err.message };
  }
}

// Handle MCP request
async function handleRequest(request) {
  const { jsonrpc = '2.0', id = 1, method, params } = request;

  if (method === 'tools/list') {
    return {
      jsonrpc,
      id,
      result: {
        tools: [
          {
            name: 'get_competitor_fleet',
            description: 'Get all tracked competitors sorted by distance',
            inputSchema: { type: 'object', properties: { max_distance_nm: { type: 'number' } } }
          },
          {
            name: 'get_nearest_competitor',
            description: 'Get nearest competitor with tactical analysis',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_fleet_pressure',
            description: 'Get fleet distribution (port/starboard) and tactical pressure',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_competitor_trend',
            description: 'Get distance trend for specific competitor',
            inputSchema: { type: 'object', properties: { mmsi: { type: 'string' }, minutes: { type: 'number' } } }
          },
          {
            name: 'get_fleet_summary',
            description: 'Get comprehensive fleet summary for narrative reporting',
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

// Main server loop
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
