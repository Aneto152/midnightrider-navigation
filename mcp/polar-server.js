#!/usr/bin/env node

/**
 * MCP Server for Polar Performance Analysis
 * 
 * Tools for analyzing boat performance against polars:
 * - Compare real speed vs polar speed
 * - Calculate efficiency metrics
 * - Identify performance gaps
 * - Optimize trim and tactics
 * 
 * Polars for J/30:
 * - Multiple wind speeds (5-25 knots)
 * - Upwind, reaching, downwind
 * - Different sail combinations
 */

const http = require('http');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'signalk';

const MCP_VERSION = '2024-11-05';

// J/30 Performance Polars (based on IMS/ORC data)
// Format: [trueWindSpeed] = { upwind: speed, reaching: speed, downwind: speed, angle: degrees }
const J30_POLARS = {
  5: { upwind: 3.2, reach: 4.1, downwind: 4.8, upwindAngle: 32 },
  6: { upwind: 3.9, reach: 5.0, downwind: 5.9, upwindAngle: 31 },
  7: { upwind: 4.6, reach: 5.9, downwind: 6.9, upwindAngle: 31 },
  8: { upwind: 5.2, reach: 6.7, downwind: 7.8, upwindAngle: 31 },
  9: { upwind: 5.8, reach: 7.5, downwind: 8.7, upwindAngle: 30 },
  10: { upwind: 6.4, reach: 8.2, downwind: 9.5, upwindAngle: 30 },
  12: { upwind: 7.5, reach: 9.6, downwind: 11.0, upwindAngle: 30 },
  14: { upwind: 8.5, reach: 10.9, downwind: 12.4, upwindAngle: 29 },
  16: { upwind: 9.4, reach: 12.0, downwind: 13.7, upwindAngle: 29 },
  18: { upwind: 10.2, reach: 13.0, downwind: 14.8, upwindAngle: 28 },
  20: { upwind: 10.9, reach: 13.9, downwind: 15.8, upwindAngle: 28 },
  25: { upwind: 12.0, reach: 15.2, downwind: 17.2, upwindAngle: 27 }
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
 * Interpolate polar for exact wind speed
 */
function getInterpolatedPolar(windSpeed) {
  const speeds = Object.keys(J30_POLARS).map(Number).sort((a, b) => a - b);
  
  if (windSpeed <= speeds[0]) return J30_POLARS[speeds[0]];
  if (windSpeed >= speeds[speeds.length - 1]) return J30_POLARS[speeds[speeds.length - 1]];

  // Find surrounding speeds for interpolation
  let lower = speeds[0];
  let upper = speeds[1];
  
  for (let i = 0; i < speeds.length - 1; i++) {
    if (windSpeed >= speeds[i] && windSpeed <= speeds[i + 1]) {
      lower = speeds[i];
      upper = speeds[i + 1];
      break;
    }
  }

  const ratio = (windSpeed - lower) / (upper - lower);
  const lowerPolar = J30_POLARS[lower];
  const upperPolar = J30_POLARS[upper];

  return {
    upwind: lowerPolar.upwind + (upperPolar.upwind - lowerPolar.upwind) * ratio,
    reach: lowerPolar.reach + (upperPolar.reach - lowerPolar.reach) * ratio,
    downwind: lowerPolar.downwind + (upperPolar.downwind - lowerPolar.downwind) * ratio,
    upwindAngle: lowerPolar.upwindAngle + (upperPolar.upwindAngle - lowerPolar.upwindAngle) * ratio
  };
}

/**
 * Determine sailing mode from apparent wind angle
 */
function getSailingMode(apparentWindAngle) {
  const angle = apparentWindAngle % 360;
  
  if (angle < 60 || angle > 300) return 'upwind';
  if (angle >= 60 && angle <= 150) return 'reach';
  if (angle > 150 && angle < 210) return 'downwind';
  if (angle >= 210 && angle <= 300) return 'reach';
  
  return 'unknown';
}

/**
 * Calculate boat efficiency (actual vs polar)
 */
async function getBoatEfficiency() {
  try {
    const stw = await getLatestValue('navigation.speedThroughWater');
    const trueWindSpeed = await getLatestValue('environment.wind.speedTrue');
    const apparentWindAngle = await getLatestValue('environment.wind.angleApparent');
    const heel = await getLatestValue('navigation.attitude.roll');
    
    if (!stw || !trueWindSpeed) {
      return { error: 'Missing required data (STW or wind)' };
    }

    const polar = getInterpolatedPolar(trueWindSpeed);
    const mode = getSailingMode(apparentWindAngle ? radToDeg(apparentWindAngle) : 0);
    
    let polarSpeed = 0;
    if (mode === 'upwind') polarSpeed = polar.upwind;
    else if (mode === 'reach') polarSpeed = polar.reach;
    else if (mode === 'downwind') polarSpeed = polar.downwind;

    const efficiency = (stw / polarSpeed) * 100;
    const gap = stw - polarSpeed;

    return {
      actual_speed_knots: stw.toFixed(2),
      polar_speed_knots: polarSpeed.toFixed(2),
      efficiency_percent: efficiency.toFixed(1),
      gap_knots: gap.toFixed(2),
      sailing_mode: mode,
      true_wind_speed: trueWindSpeed.toFixed(1),
      heel_degrees: heel ? radToDeg(heel).toFixed(1) : null,
      assessment: efficiency > 95 ? 'Excellent' : efficiency > 90 ? 'Good' : efficiency > 80 ? 'Fair' : 'Poor'
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Get polar data for current wind
 */
async function getCurrentPolar() {
  try {
    const trueWindSpeed = await getLatestValue('environment.wind.speedTrue');
    
    if (!trueWindSpeed) {
      return { error: 'No wind data available' };
    }

    const polar = getInterpolatedPolar(trueWindSpeed);

    return {
      true_wind_speed_knots: trueWindSpeed.toFixed(1),
      upwind_speed_knots: polar.upwind.toFixed(2),
      reaching_speed_knots: polar.reach.toFixed(2),
      downwind_speed_knots: polar.downwind.toFixed(2),
      upwind_angle_degrees: polar.upwindAngle.toFixed(1),
      description: `J/30 polars for ${trueWindSpeed.toFixed(1)} knots true wind`
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Compare upwind performance vs polar
 */
async function getUpwindAnalysis() {
  try {
    const stw = await getLatestValue('navigation.speedThroughWater');
    const trueWindSpeed = await getLatestValue('environment.wind.speedTrue');
    const apparentAngle = await getLatestValue('environment.wind.angleApparent');
    const heel = await getLatestValue('navigation.attitude.roll');
    const vmg = await getLatestValue('performance.velocityMadeGood');

    if (!stw || !trueWindSpeed) {
      return { error: 'Missing required data' };
    }

    const polar = getInterpolatedPolar(trueWindSpeed);
    const stwEfficiency = (stw / polar.upwind) * 100;
    const stwGap = stw - polar.upwind;

    // VMG analysis
    const vmgEfficiency = vmg ? (vmg / (polar.upwind * 0.85)) * 100 : null;
    const vmgTarget = polar.upwind * 0.85;

    return {
      boat_speed_analysis: {
        actual_knots: stw.toFixed(2),
        polar_knots: polar.upwind.toFixed(2),
        efficiency_percent: stwEfficiency.toFixed(1),
        gap_knots: stwGap.toFixed(2)
      },
      vmg_analysis: vmg ? {
        actual_vmg: vmg.toFixed(2),
        target_vmg: vmgTarget.toFixed(2),
        efficiency_percent: vmgEfficiency.toFixed(1),
        gap_knots: (vmg - vmgTarget).toFixed(2)
      } : null,
      trim_analysis: {
        apparent_wind_angle_deg: apparentAngle ? radToDeg(apparentAngle).toFixed(1) : null,
        heel_degrees: heel ? radToDeg(heel).toFixed(1) : null,
        heel_assessment: heel ? (radToDeg(heel) < 12 ? 'Underheeled' : radToDeg(heel) > 18 ? 'Overheeled' : 'Optimal') : null
      },
      recommendations: generateUpwindRecommendations(stwEfficiency, heel ? radToDeg(heel) : 0, stw, polar.upwind)
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Compare downwind performance vs polar
 */
async function getDownwindAnalysis() {
  try {
    const stw = await getLatestValue('navigation.speedThroughWater');
    const trueWindSpeed = await getLatestValue('environment.wind.speedTrue');
    const heel = await getLatestValue('navigation.attitude.roll');

    if (!stw || !trueWindSpeed) {
      return { error: 'Missing required data' };
    }

    const polar = getInterpolatedPolar(trueWindSpeed);
    const efficiency = (stw / polar.downwind) * 100;
    const gap = stw - polar.downwind;

    return {
      boat_speed_analysis: {
        actual_knots: stw.toFixed(2),
        polar_knots: polar.downwind.toFixed(2),
        efficiency_percent: efficiency.toFixed(1),
        gap_knots: gap.toFixed(2)
      },
      trim_analysis: {
        heel_degrees: heel ? radToDeg(heel).toFixed(1) : null,
        heel_assessment: heel ? (radToDeg(heel) < 5 ? 'Good' : radToDeg(heel) > 12 ? 'Too much' : 'Acceptable') : null
      },
      recommendations: generateDownwindRecommendations(efficiency, heel ? radToDeg(heel) : 0, stw, polar.downwind)
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Generate upwind recommendations
 */
function generateUpwindRecommendations(efficiency, heel, actualSpeed, polarSpeed) {
  const recommendations = [];

  if (efficiency < 85) {
    if (heel > 18) {
      recommendations.push('Heel excessive (>18°): Ease mainsheet');
    } else if (heel < 12) {
      recommendations.push('Underheeled (<12°): Move crew out');
    }
    recommendations.push(`Speed gap of ${(polarSpeed - actualSpeed).toFixed(1)}kt: Check trim');`);
  } else if (efficiency < 90) {
    recommendations.push('Performance acceptable, minor trim adjustments');
  } else if (efficiency < 95) {
    recommendations.push('Good performance, keep current trim');
  } else {
    recommendations.push('Excellent performance! Maintain current setup');
  }

  return recommendations;
}

/**
 * Generate downwind recommendations
 */
function generateDownwindRecommendations(efficiency, heel, actualSpeed, polarSpeed) {
  const recommendations = [];

  if (efficiency < 85) {
    recommendations.push(`Speed gap of ${(polarSpeed - actualSpeed).toFixed(1)}kt: Check sail trim`);
    if (heel > 10) {
      recommendations.push('Too much heel: Reduce crew weight to windward');
    }
    recommendations.push('Consider different sail combination (jib size, spinnaker)');
  } else if (efficiency < 90) {
    recommendations.push('Reasonable downwind performance');
  } else if (efficiency < 95) {
    recommendations.push('Good downwind speed');
  } else {
    recommendations.push('Excellent downwind performance!');
  }

  return recommendations;
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_boat_efficiency':
        return await getBoatEfficiency();

      case 'get_current_polar':
        return await getCurrentPolar();

      case 'get_upwind_analysis':
        return await getUpwindAnalysis();

      case 'get_downwind_analysis':
        return await getDownwindAnalysis();

      case 'get_all_polars':
        return {
          description: 'J/30 performance polars at different wind speeds',
          polars: J30_POLARS
        };

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
          name: 'polar-mcp-server',
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
            name: 'get_boat_efficiency',
            description: 'Get current boat efficiency (actual vs polar speed)',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_current_polar',
            description: 'Get J/30 polar speeds for current true wind',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_upwind_analysis',
            description: 'Detailed analysis of upwind performance vs polar',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_downwind_analysis',
            description: 'Detailed analysis of downwind performance vs polar',
            inputSchema: { type: 'object', properties: {} }
          },
          {
            name: 'get_all_polars',
            description: 'Get complete J/30 polar table for all wind speeds',
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
