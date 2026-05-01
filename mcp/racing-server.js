#!/usr/bin/env node

/**
 * MCP Server for Racing Data
 * 
 * Comprehensive racing tools based on Signal K specification
 * 
 * Coverage:
 * - Navigation (heading, position, course, speed)
 * - Performance (VMG, polar, tactics)
 * - Wind (apparent, true, gusts)
 * - Water (depth, temperature, current)
 * - Sailing (heel, pitch, trim)
 * - Race (time to start, marks, scoring)
 * - Crew (position, workload)
 */

const http = require('http');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';

const MCP_VERSION = '2024-11-05';
let requestId = 0;

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
 * Get latest value from InfluxDB
 */
async function getLatestValue(measurement) {
  const query = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "${measurement}")
    |> last()`;

  const results = await queryInfluxDB(query);
  return results.length > 0 ? parseFloat(results[0]._value) : null;
}

/**
 * Get average over time period
 */
async function getAverage(measurement, minutes = 5) {
  const query = `from(bucket:"${INFLUX_BUCKET}")
    |> range(start: -${minutes}m)
    |> filter(fn: (r) => r._measurement == "${measurement}")
    |> mean()`;

  const results = await queryInfluxDB(query);
  return results.length > 0 ? parseFloat(results[0]._value) : null;
}

/**
 * Convert radians to degrees
 */
function radToDeg(rad) {
  return (rad * 180 / Math.PI) % 360;
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      // NAVIGATION
      case 'get_heading':
        const heading = await getLatestValue('navigation.headingTrue');
        return {
          heading_degrees: heading ? radToDeg(heading) : null,
          heading_radians: heading,
          unit: 'degrees (0-360)'
        };

      case 'get_position':
        const latQuery = `from(bucket:"${INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "navigation.position.latitude") |> last()`;
        const lonQuery = `from(bucket:"${INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "navigation.position.longitude") |> last()`;
        
        const latRes = await queryInfluxDB(latQuery);
        const lonRes = await queryInfluxDB(lonQuery);
        
        return {
          latitude: latRes.length > 0 ? parseFloat(latRes[0]._value) : null,
          longitude: lonRes.length > 0 ? parseFloat(lonRes[0]._value) : null,
          unit: 'decimal degrees'
        };

      case 'get_sog':
        const sog = await getLatestValue('navigation.speedOverGround');
        return {
          speed_over_ground_knots: sog ? sog / 0.51444 : null,
          speed_over_ground_ms: sog,
          unit: 'knots'
        };

      case 'get_cog':
        const cog = await getLatestValue('navigation.courseOverGround');
        return {
          course_over_ground_degrees: cog ? radToDeg(cog) : null,
          course_over_ground_radians: cog,
          unit: 'degrees (0-360)'
        };

      // PERFORMANCE
      case 'get_stw':
        const stw = await getLatestValue('navigation.speedThroughWater');
        return {
          speed_through_water_knots: stw ? stw / 0.51444 : null,
          speed_through_water_ms: stw,
          unit: 'knots'
        };

      case 'get_vmg':
        const vmg = await getLatestValue('performance.velocityMadeGood');
        return {
          vmg_knots: vmg ? vmg / 0.51444 : null,
          vmg_percent: vmg ? (vmg / (await getLatestValue('performance.targetVMG') || 1)) * 100 : null,
          unit: 'knots'
        };

      case 'get_performance':
        return {
          vmg: await getLatestValue('performance.velocityMadeGood'),
          target_vmg: await getLatestValue('performance.targetVMG'),
          target_speed: await getLatestValue('performance.targetSpeed'),
          vmg_ratio: await getLatestValue('performance.velocityMadeGoodRatio'),
          beat_angle: await getLatestValue('performance.beatAngle'),
          unit: 'mixed'
        };

      // WIND
      case 'get_wind_apparent':
        const appSpeed = await getLatestValue('environment.wind.speedApparent');
        const appAngle = await getLatestValue('environment.wind.angleApparent');
        return {
          speed_knots: appSpeed ? appSpeed / 0.51444 : null,
          angle_degrees: appAngle ? radToDeg(appAngle) : null,
          angle_radians: appAngle,
          direction: appAngle ? (appAngle < Math.PI ? 'starboard' : 'port') : null
        };

      case 'get_wind_true':
        const trueSpeed = await getLatestValue('environment.wind.speedTrue');
        const trueAngle = await getLatestValue('environment.wind.angleTrue');
        return {
          speed_knots: trueSpeed ? trueSpeed / 0.51444 : null,
          angle_degrees: trueAngle ? radToDeg(trueAngle) : null,
          angle_radians: trueAngle,
          direction: trueAngle ? (trueAngle < Math.PI ? 'starboard' : 'port') : null
        };

      case 'get_wind_direction':
        const windDir = await getLatestValue('environment.wind.directionTrue');
        return {
          direction_degrees: windDir ? radToDeg(windDir) : null,
          direction_compass: getCompassDir(windDir ? radToDeg(windDir) : 0),
          unit: 'degrees (0=N, 90=E, 180=S, 270=W)'
        };

      // WATER
      case 'get_depth':
        const depth = await getLatestValue('environment.water.depth');
        return {
          depth_meters: depth,
          depth_feet: depth ? depth * 3.28084 : null,
          unit: 'meters'
        };

      case 'get_water_temp':
        const temp = await getLatestValue('environment.water.temperature');
        return {
          temperature_celsius: temp,
          temperature_fahrenheit: temp ? (temp * 9/5) + 32 : null,
          unit: 'celsius'
        };

      case 'get_current':
        const currentSpeed = await getLatestValue('environment.current.speedOverGround');
        const currentDir = await getLatestValue('environment.current.directionTrue');
        return {
          speed_knots: currentSpeed,
          direction_degrees: currentDir ? radToDeg(currentDir) : null,
          direction_compass: getCompassDir(currentDir ? radToDeg(currentDir) : 0),
          unit: 'mixed'
        };

      // SAILING
      case 'get_heel':
        const heel = await getLatestValue('navigation.attitude.roll');
        return {
          heel_degrees: heel ? radToDeg(heel) : null,
          heel_radians: heel,
          side: heel ? (heel > 0 ? 'starboard' : 'port') : null,
          unit: 'degrees'
        };

      case 'get_pitch':
        const pitch = await getLatestValue('navigation.attitude.pitch');
        return {
          pitch_degrees: pitch ? radToDeg(pitch) : null,
          pitch_radians: pitch,
          trim: pitch ? (pitch > 0 ? 'bow_up' : 'bow_down') : null,
          unit: 'degrees'
        };

      case 'get_attitude':
        return {
          roll: await getLatestValue('navigation.attitude.roll'),
          pitch: await getLatestValue('navigation.attitude.pitch'),
          yaw: await getLatestValue('navigation.attitude.yaw'),
          unit: 'radians'
        };

      // COMBINED
      case 'get_race_data':
        return {
          position: {
            latitude: (await queryInfluxDB(`from(bucket:"${INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "navigation.position.latitude") |> last()`))[0]?._value,
            longitude: (await queryInfluxDB(`from(bucket:"${INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "navigation.position.longitude") |> last()`))[0]?._value
          },
          heading: await getLatestValue('navigation.headingTrue'),
          speed: {
            through_water: await getLatestValue('navigation.speedThroughWater'),
            over_ground: await getLatestValue('navigation.speedOverGround')
          },
          wind: {
            apparent_speed: await getLatestValue('environment.wind.speedApparent'),
            apparent_angle: await getLatestValue('environment.wind.angleApparent'),
            true_speed: await getLatestValue('environment.wind.speedTrue'),
            true_direction: await getLatestValue('environment.wind.directionTrue')
          },
          sailing: {
            heel: await getLatestValue('navigation.attitude.roll'),
            pitch: await getLatestValue('navigation.attitude.pitch')
          },
          performance: {
            vmg: await getLatestValue('performance.velocityMadeGood'),
            target_vmg: await getLatestValue('performance.targetVMG')
          }
        };

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get compass direction from degrees
 */
function getCompassDir(degrees) {
  const dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(degrees / 22.5) % 16;
  return dirs[index];
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
          name: 'racing-mcp-server',
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
          // NAVIGATION
          {
            name: 'get_heading',
            description: 'Get current heading (true)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_position',
            description: 'Get current latitude and longitude',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_sog',
            description: 'Get speed over ground (boat speed vs water)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_cog',
            description: 'Get course over ground (direction of travel)',
            inputSchema: { type: 'object', properties: {} }
          },
          // PERFORMANCE
          {
            name: 'get_stw',
            description: 'Get speed through water (boat speed in water)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_vmg',
            description: 'Get velocity made good (progress toward mark)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_performance',
            description: 'Get all performance metrics (VMG, target, ratio, beat angle)',
            inputSchema: { type: 'object', properties: {} }
          },
          // WIND
          {
            name: 'get_wind_apparent',
            description: 'Get apparent wind (what crew feels)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_wind_true',
            description: 'Get true wind (actual meteorological wind)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_wind_direction',
            description: 'Get wind direction (compass bearing)',
            inputSchema: { type: 'object', properties: {} }
          },
          // WATER
          {
            name: 'get_depth',
            description: 'Get water depth',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_water_temp',
            description: 'Get water temperature',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_current',
            description: 'Get water current (speed and direction)',
            inputSchema: { type: 'object', properties: {} }
          },
          // SAILING
          {
            name: 'get_heel',
            description: 'Get boat heel (lateral tilt)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_pitch',
            description: 'Get boat pitch (front-back trim)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_attitude',
            description: 'Get complete boat attitude (roll, pitch, yaw)',
            inputSchema: { type: 'object', properties: {} }
          },
          // COMBINED
          {
            name: 'get_race_data',
            description: 'Get all race-critical data in one call (position, heading, speed, wind, sail, performance)',
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
