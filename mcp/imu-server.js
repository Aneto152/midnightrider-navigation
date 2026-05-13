#!/usr/bin/env node
/**
 * imu-server.js — Midnight Rider IMU & Sea State MCP Server
 * Exposes 4 tools:
 *   1. get_sea_state — wave height, period, Douglas scale
 *   2. get_motion_snapshot — roll, pitch, yaw, acceleration, rate of turn
 *   3. get_heel_trend — heel statistics over N minutes from InfluxDB
 *   4. get_acceleration_peaks — acceleration peaks and slam events
 */

const net = require('net');
const http = require('http');

const SIGNALK_URL = process.env.SIGNALK_HTTP || 'http://localhost:3000';
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';

// Utility: fetch from Signal K
async function skGet(path) {
  return new Promise((resolve) => {
    const url = `${SIGNALK_URL}/signalk/v1/api/${path}`;
    http.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(null);
        }
      });
    }).on('error', () => resolve(null));
  });
}

// Utility: query InfluxDB with Flux
async function influxQuery(query) {
  return new Promise((resolve) => {
    const url = `${INFLUX_URL}/api/v2/query?org=${INFLUX_ORG}`;
    const postData = `query=${encodeURIComponent(query)}`;
    
    const options = {
      hostname: new URL(INFLUX_URL).hostname,
      port: 8086,
      path: `/api/v2/query?org=${INFLUX_ORG}`,
      method: 'POST',
      headers: {
        'Authorization': `Token ${INFLUX_TOKEN}`,
        'Content-Type': 'application/vnd.flux',
        'Content-Length': Buffer.byteLength(query)
      }
    };
    
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const lines = data.split('\n').filter(l => l && !l.startsWith('#'));
          resolve(lines.map(l => {
            const parts = l.split(',');
            return {
              time: parts[0],
              value: parseFloat(parts[parts.length - 1]) || 0
            };
          }));
        } catch {
          resolve([]);
        }
      });
    }).on('error', () => resolve([]));
    
    req.write(query);
    req.end();
  });
}

// Convert radians to degrees
function radToDeg(rad) {
  return (rad * 180 / Math.PI);
}

// Tool 1: get_sea_state
async function getSeaState() {
  const nav = await skGet('environment/water/waves');
  if (!nav) return { error: 'No wave data available' };
  
  const height = nav.significantWaveHeight?.value || 0;
  const period = nav.period?.value || 0;
  const douglas = nav.seaState?.value || 0;
  
  const labels = [
    'Flat', 'Rippled', 'Smooth', 'Slight', 'Moderate', 'Rough', 'Very Rough', 'High', 'Very High'
  ];
  const impacts = [
    'Excellent — perfect sailing conditions',
    'Excellent — smooth water',
    'Very Good — minimal wave impact',
    'Good — manageable chop',
    'Fair — moderate conditions',
    'Challenging — active sea state',
    'Rough — significant impact on performance',
    'Very Rough — crew safety caution',
    'Extreme — dangerous conditions'
  ];
  
  return {
    wave_height_m: parseFloat(height.toFixed(2)),
    period_s: parseFloat(period.toFixed(1)),
    douglas_scale: Math.round(douglas),
    sea_state_label: labels[Math.min(Math.round(douglas), 8)],
    sailing_impact: impacts[Math.min(Math.round(douglas), 8)],
    source: 'WIT WT901BLECL Wave Analyzer'
  };
}

// Tool 2: get_motion_snapshot
async function getMotionSnapshot() {
  const nav = await skGet('navigation');
  if (!nav) return { error: 'No navigation data available' };
  
  const roll = nav.attitude?.roll?.value || 0;
  const pitch = nav.attitude?.pitch?.value || 0;
  const yaw = nav.attitude?.yaw?.value || 0;
  const ax = nav.acceleration?.x?.value || 0;
  const ay = nav.acceleration?.y?.value || 0;
  const az = nav.acceleration?.z?.value || 0;
  const rot = nav.rateOfTurn?.value || 0;
  
  const rollDeg = Math.abs(radToDeg(roll));
  const accelG = Math.sqrt(ax*ax + ay*ay + az*az) / 9.81;
  
  let motionState = 'upright';
  if (rollDeg > 25) motionState = 'slamming';
  else if (rollDeg > 15) motionState = 'heeled';
  else if (accelG > 1.5) motionState = 'surfing';
  
  let heelSide = 'neutral';
  if (roll > 0.1) heelSide = 'starboard';
  else if (roll < -0.1) heelSide = 'port';
  
  return {
    roll_deg: parseFloat(rollDeg.toFixed(1)),
    pitch_deg: parseFloat(Math.abs(radToDeg(pitch)).toFixed(1)),
    yaw_deg: parseFloat(radToDeg(yaw).toFixed(1)),
    accel_x: parseFloat(ax.toFixed(3)),
    accel_y: parseFloat(ay.toFixed(3)),
    accel_z: parseFloat(az.toFixed(3)),
    accel_total_g: parseFloat(accelG.toFixed(2)),
    rate_of_turn_deg_s: parseFloat(radToDeg(rot).toFixed(1)),
    motion_state: motionState,
    heel_side: heelSide
  };
}

// Tool 3: get_heel_trend
async function getHeelTrend(minutes = 10) {
  const minClamped = Math.min(Math.max(minutes, 1), 60);
  const query = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start:-${minClamped}m)
    |> filter(fn:(r) => r._measurement == "navigation" and r._field == "roll")
    |> aggregateWindow(every:30s, fn:mean, createEmpty:false)`;
  
  const data = await influxQuery(query);
  if (!data.length) return { error: 'No heel data available' };
  
  const values = data.map(d => Math.abs(d.value * 180 / Math.PI));
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const over20 = values.filter(v => v > 20).length;
  
  let stability = 'stable';
  if (over20 > 5) stability = 'extreme';
  else if (max > 25) stability = 'variable';
  
  let trend = 'steady';
  if (values.length > 1) {
    const recent = values.slice(-3).reduce((a, b) => a + b) / 3;
    const earlier = values.slice(0, 3).reduce((a, b) => a + b) / 3;
    if (recent > earlier + 2) trend = 'increasing';
    else if (recent < earlier - 2) trend = 'decreasing';
  }
  
  return {
    duration_min: minClamped,
    samples_count: data.length,
    heel_mean_deg: parseFloat(mean.toFixed(1)),
    heel_max_deg: parseFloat(max.toFixed(1)),
    heel_min_deg: parseFloat(min.toFixed(1)),
    events_over_20deg: over20,
    stability: stability,
    trend: trend
  };
}

// Tool 4: get_acceleration_peaks
async function getAccelerationPeaks(minutes = 5) {
  const minClamped = Math.min(Math.max(minutes, 1), 60);
  const queryPos = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start:-${minClamped}m)
    |> filter(fn:(r) => r._measurement == "navigation" and r._field == "accel_z")
    |> aggregateWindow(every:1s, fn:max, createEmpty:false)`;
  
  const queryNeg = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start:-${minClamped}m)
    |> filter(fn:(r) => r._measurement == "navigation" and r._field == "accel_z")
    |> aggregateWindow(every:1s, fn:min, createEmpty:false)`;
  
  const dataPos = await influxQuery(queryPos);
  const dataNeg = await influxQuery(queryNeg);
  
  const peakPos = dataPos.length ? Math.max(...dataPos.map(d => d.value)) / 9.81 : 0;
  const peakNeg = dataNeg.length ? Math.abs(Math.min(...dataNeg.map(d => d.value))) / 9.81 : 0;
  
  const allAccel = [...dataPos, ...dataNeg].map(d => Math.abs(d.value) / 9.81);
  const slamCount = allAccel.filter(a => a > 2).length;
  
  let comfortIndex = 'smooth';
  if (peakPos > 2 || peakNeg > 2) comfortIndex = 'extreme';
  else if (peakPos > 1.3 || peakNeg > 1.3) comfortIndex = 'rough';
  else if (peakPos > 0.8 || peakNeg > 0.8) comfortIndex = 'comfortable';
  
  return {
    duration_min: minClamped,
    peak_positive_g: parseFloat(peakPos.toFixed(2)),
    peak_negative_g: parseFloat(peakNeg.toFixed(2)),
    slam_events: slamCount,
    comfort_index: comfortIndex,
    note: slamCount > 5 ? 'Heavy slamming detected — reduce sail or change course' : 'Conditions stable'
  };
}

// MCP Server
const tools = [
  {
    name: 'get_sea_state',
    description: 'Get current sea state: wave height, period, Douglas scale',
    inputSchema: { type: 'object', properties: {} }
  },
  {
    name: 'get_motion_snapshot',
    description: 'Get current motion: roll, pitch, yaw, acceleration, rate of turn',
    inputSchema: { type: 'object', properties: {} }
  },
  {
    name: 'get_heel_trend',
    description: 'Get heel statistics over N minutes from InfluxDB',
    inputSchema: {
      type: 'object',
      properties: {
        minutes: { type: 'number', description: 'Minutes of history (1-60, default 10)' }
      }
    }
  },
  {
    name: 'get_acceleration_peaks',
    description: 'Get acceleration peaks and slam events',
    inputSchema: {
      type: 'object',
      properties: {
        minutes: { type: 'number', description: 'Minutes of history (1-60, default 5)' }
      }
    }
  }
];

async function handleRequest(request) {
  const { method, params } = request;
  
  if (method === 'tools/list') {
    return { tools };
  }
  
  if (method === 'tools/call') {
    const { name, arguments: args } = params;
    
    switch (name) {
      case 'get_sea_state':
        return { content: [{ type: 'text', text: JSON.stringify(await getSeaState()) }] };
      case 'get_motion_snapshot':
        return { content: [{ type: 'text', text: JSON.stringify(await getMotionSnapshot()) }] };
      case 'get_heel_trend':
        return { content: [{ type: 'text', text: JSON.stringify(await getHeelTrend(args?.minutes || 10)) }] };
      case 'get_acceleration_peaks':
        return { content: [{ type: 'text', text: JSON.stringify(await getAccelerationPeaks(args?.minutes || 5)) }] };
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }
  
  return { error: `Unknown method: ${method}` };
}

// TCP Server (port 3005)
const server = net.createServer((socket) => {
  socket.on('data', async (data) => {
    try {
      const request = JSON.parse(data.toString());
      const response = await handleRequest(request);
      socket.write(JSON.stringify({ ...response, id: request.id || 1 }) + '\n');
    } catch (e) {
      socket.write(JSON.stringify({ error: e.message }) + '\n');
    }
  });
});

server.listen(3005, () => {
  console.log('🌊 IMU Server listening on port 3005');
});
