#!/usr/bin/env node

/**
 * MCP Server for Racing Data — Phase 2: Historical MCP/InfluxDB Contract
 *
 * Implements bounded-skew historical snapshot with strict contract validation.
 * - Four independent queries: latitude, longitude, speed_over_ground, course_over_ground
 * - Requires as_of_utc (ISO 8601 UTC with literal Z suffix) and window_seconds (1-3600)
 * - Preserves actual _time from each query; rejects skew > 1000 ms
 * - Fail-closed on any missing or invalid field
 * - Structured logging to stderr only; stdout reserved for JSON-RPC
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';
const HTTP_TIMEOUT_MS = 5000;
const SKEW_LIMIT_MS = 1000;

const MCP_VERSION = '2024-11-05';
let requestId = 0;

// Structured logging to stderr (never stdout)
const LOG_DIR = path.join(path.dirname(require.main.filename), '..', '..', 'logs', 'services');
let logStream = null;

function ensureLogDir() {
  try {
    if (!fs.existsSync(LOG_DIR)) {
      fs.mkdirSync(LOG_DIR, { recursive: true });
    }
  } catch (e) {
    // Fail silently; diagnostics go to stderr
  }
}

function logEvent(eventType, data) {
  const timestamp = new Date().toISOString();
  const logEntry = JSON.stringify({
    timestamp,
    eventType,
    ...data
  });

  // Write to stderr for diagnostics
  process.stderr.write(logEntry + '\n');

  // Try to write to persistent log (non-blocking)
  try {
    const logFile = path.join(LOG_DIR, 'racing-mcp.log');
    fs.appendFileSync(logFile, logEntry + '\n');
  } catch (e) {
    // Silently fail; diagnostics already on stderr
  }
}

function sanitizeError(err) {
  // Remove credentials and sensitive material
  const msg = err.message || String(err);
  return msg
    .replace(/Authorization[^,]*/gi, 'Authorization: [redacted]')
    .replace(/token[=:][^,\s]*/gi, 'token: [redacted]')
    .replace(/password[=:][^,\s]*/gi, 'password: [redacted]')
    .replace(/secret[=:][^,\s]*/gi, 'secret: [redacted]')
    .replace(/https?:\/\/[^@]*@/g, 'https://[redacted]@');
}

// Initialize logging directory on startup
ensureLogDir();
logEvent('STARTUP', { version: MCP_VERSION, bucket: INFLUX_BUCKET });

/**
 * Query InfluxDB with timeout and error handling
 */
async function queryInfluxDB(fluxQuery) {
  return new Promise((resolve, reject) => {
    const postData = fluxQuery;

    try {
      const url = new URL(INFLUX_URL);
      const options = {
        hostname: url.hostname,
        port: url.port || 8086,
        path: `/api/v2/query?org=${encodeURIComponent(INFLUX_ORG)}`,
        method: 'POST',
        headers: {
          'Content-Type': 'application/vnd.flux',
          'Content-Length': Buffer.byteLength(postData)
        },
        timeout: HTTP_TIMEOUT_MS
      };

      // Do NOT log Authorization header
      if (INFLUX_TOKEN) {
        options.headers['Authorization'] = `Token ${INFLUX_TOKEN}`;
      }

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          if (res.statusCode === 200) {
            logEvent('DATA_OUT', { statusCode: 200, bytes: data.length });
            resolve(parseFluxResponse(data));
          } else {
            reject(new Error(`HTTP ${res.statusCode}`));
          }
        });
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error('HTTP request timeout'));
      });

      req.on('error', reject);
      req.write(postData);
      req.end();
    } catch (e) {
      reject(e);
    }
  });
}

/**
 * Parse Flux CSV response
 * Expected format: CSV with headers including _value, _time
 */
function parseFluxResponse(csvData) {
  try {
    const lines = csvData.trim().split('\n');
    if (lines.length < 4) return [];

    const results = [];
    const headers = {};
    let inData = false;

    for (const line of lines) {
      if (!line.trim()) continue;

      // Skip metadata rows
      if (line.startsWith('#')) {
        if (line.startsWith('#datatype')) {
          inData = true;
        }
        continue;
      }

      // Parse header row
      if (inData && line.startsWith(',')) {
        const parts = line.substring(1).split(',').filter(p => p);
        headers.names = parts;
        headers.indices = {};
        parts.forEach((name, idx) => {
          headers.indices[name] = idx;
        });
        continue;
      }

      // Parse data rows
      if (inData && headers.names && !line.startsWith(',')) {
        const values = line.split(',').filter((_, idx) => idx < headers.names.length);
        const record = {};
        headers.names.forEach((name, idx) => {
          record[name] = values[idx] || null;
        });
        results.push(record);
      }
    }

    return results;
  } catch (e) {
    logEvent('ERROR', { phase: 'parse_response', error: sanitizeError(e) });
    throw new Error('Malformed CSV response from InfluxDB');
  }
}

/**
 * Validate ISO 8601 UTC timestamp with literal Z suffix
 */
function validateTimestamp(ts) {
  if (!ts || typeof ts !== 'string') return null;
  if (!ts.endsWith('Z')) return null; // Reject +00:00 format

  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return null;

    // Reject future timestamps
    if (d.getTime() > Date.now()) return null;

    return d;
  } catch (e) {
    return null;
  }
}

/**
 * Validate numeric field ranges
 */
function validateNumeric(value, field) {
  if (value === null || value === undefined || value === '') return null;

  const num = parseFloat(value);
  if (!Number.isFinite(num)) return null;

  switch (field) {
    case 'latitude':
      return (num >= -90 && num <= 90) ? num : null;
    case 'longitude':
      return (num >= -180 && num <= 180) ? num : null;
    case 'speed_over_ground':
      return num >= 0 ? num : null;
    case 'course_over_ground':
      return (num >= 0 && num <= 360) ? num : null;
    default:
      return Number.isFinite(num) ? num : null;
  }
}

/**
 * Get historical snapshot at as_of_utc with bounded skew validation
 */
async function getHistoricalSnapshot(asOfUtc, windowSeconds) {
  // Validate as_of_utc
  if (!asOfUtc || typeof asOfUtc !== 'string') {
    throw new Error('as_of_utc is required and must be a string');
  }
  if (!asOfUtc.endsWith('Z')) {
    throw new Error('as_of_utc must end with \'Z\' (UTC timezone required)');
  }

  const asOfDate = validateTimestamp(asOfUtc);
  if (!asOfDate) {
    throw new Error('as_of_utc must be a valid ISO 8601 UTC timestamp with Z suffix');
  }

  // Validate window_seconds
  if (!windowSeconds || typeof windowSeconds !== 'number') {
    throw new Error('window_seconds is required and must be a number');
  }
  if (!Number.isInteger(windowSeconds) || windowSeconds < 1 || windowSeconds > 3600) {
    throw new Error('window_seconds must be an integer between 1 and 3600');
  }

  const windowMs = windowSeconds * 1000;
  const startTime = new Date(asOfDate.getTime() - windowMs).toISOString();

  logEvent('DATA_IN', { asOfUtc, windowSeconds, startTime });

  // Four independent queries
  const measurements = ['navigation_position_latitude', 'navigation_position_longitude',
                        'navigation_speedOverGround', 'navigation_courseOverGround'];

  const queryResults = {};

  for (const measurement of measurements) {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: ${startTime}, stop: ${asOfUtc})
      |> filter(fn: (r) => r._measurement == "${measurement}")
      |> last()`;

    try {
      const results = await queryInfluxDB(query);
      queryResults[measurement] = results.length > 0 ? results[0] : null;
    } catch (e) {
      logEvent('ERROR', { phase: 'query', measurement, error: sanitizeError(e) });
      throw new Error(`Failed to query ${measurement}: ${sanitizeError(e)}`);
    }
  }

  // Extract and validate all four facts
  const facts = {};
  const timestamps = {};

  // Latitude
  if (!queryResults['navigation_position_latitude'] ||
      !queryResults['navigation_position_latitude']._value ||
      !queryResults['navigation_position_latitude']._time) {
    throw new Error('Collection incomplete: latitude missing or incomplete');
  }
  facts.latitude = validateNumeric(queryResults['navigation_position_latitude']._value, 'latitude');
  timestamps.latitude = validateTimestamp(queryResults['navigation_position_latitude']._time);
  if (facts.latitude === null || !timestamps.latitude) {
    throw new Error('Collection incomplete: latitude invalid or missing timestamp');
  }

  // Longitude
  if (!queryResults['navigation_position_longitude'] ||
      !queryResults['navigation_position_longitude']._value ||
      !queryResults['navigation_position_longitude']._time) {
    throw new Error('Collection incomplete: longitude missing or incomplete');
  }
  facts.longitude = validateNumeric(queryResults['navigation_position_longitude']._value, 'longitude');
  timestamps.longitude = validateTimestamp(queryResults['navigation_position_longitude']._time);
  if (facts.longitude === null || !timestamps.longitude) {
    throw new Error('Collection incomplete: longitude invalid or missing timestamp');
  }

  // Speed over ground
  if (!queryResults['navigation_speedOverGround'] ||
      !queryResults['navigation_speedOverGround']._value ||
      !queryResults['navigation_speedOverGround']._time) {
    throw new Error('Collection incomplete: speed_over_ground missing or incomplete');
  }
  facts.speed_over_ground = validateNumeric(queryResults['navigation_speedOverGround']._value, 'speed_over_ground');
  timestamps.speed_over_ground = validateTimestamp(queryResults['navigation_speedOverGround']._time);
  if (facts.speed_over_ground === null || !timestamps.speed_over_ground) {
    throw new Error('Collection incomplete: speed_over_ground invalid or missing timestamp');
  }

  // Course over ground
  if (!queryResults['navigation_courseOverGround'] ||
      !queryResults['navigation_courseOverGround']._value ||
      !queryResults['navigation_courseOverGround']._time) {
    throw new Error('Collection incomplete: course_over_ground missing or incomplete');
  }
  facts.course_over_ground = validateNumeric(queryResults['navigation_courseOverGround']._value, 'course_over_ground');
  timestamps.course_over_ground = validateTimestamp(queryResults['navigation_courseOverGround']._time);
  if (facts.course_over_ground === null || !timestamps.course_over_ground) {
    throw new Error('Collection incomplete: course_over_ground invalid or missing timestamp');
  }

  // Validate bounded skew
  const timesMs = Object.values(timestamps).map(t => t.getTime());
  const skew = Math.max(...timesMs) - Math.min(...timesMs);

  if (skew > SKEW_LIMIT_MS) {
    throw new Error(`Historical snapshot skew ${skew}ms exceeds 1000ms limit`);
  }

  // Aggregate source_timestamp is the newest
  const sourceTimestamp = new Date(Math.max(...timesMs)).toISOString();

  logEvent('DATA_OUT', {
    latitude: facts.latitude,
    longitude: facts.longitude,
    sog: facts.speed_over_ground,
    cog: facts.course_over_ground,
    skewMs: skew,
    sourceTimestamp
  });

  return {
    status: 'COMPLETE',
    latitude: facts.latitude,
    longitude: facts.longitude,
    speed_over_ground: facts.speed_over_ground,
    course_over_ground: facts.course_over_ground,
    source_timestamp: sourceTimestamp,
    fact_timestamps: {
      latitude: timestamps.latitude.toISOString(),
      longitude: timestamps.longitude.toISOString(),
      speed_over_ground: timestamps.speed_over_ground.toISOString(),
      course_over_ground: timestamps.course_over_ground.toISOString()
    },
    bounded_skew_ms: skew
  };
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_historical_snapshot':
        return await getHistoricalSnapshot(args.as_of_utc, args.window_seconds);
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (e) {
    logEvent('ERROR', { tool: name, error: sanitizeError(e) });
    throw e;
  }
}

/**
 * MCP resource and tool definitions
 */
const tools = [
  {
    name: 'get_historical_snapshot',
    description: 'Get a bounded-skew historical snapshot at a specific UTC timestamp with four-field validation',
    inputSchema: {
      type: 'object',
      properties: {
        as_of_utc: {
          type: 'string',
          description: 'ISO 8601 UTC timestamp with literal Z suffix (e.g., 2026-09-02T14:00:00Z)'
        },
        window_seconds: {
          type: 'integer',
          description: 'Historical window in seconds (1-3600)',
          minimum: 1,
          maximum: 3600
        }
      },
      required: ['as_of_utc', 'window_seconds'],
      additionalProperties: false
    }
  }
];

/**
 * MCP server message handling
 */
function handleMessage(message) {
  const response = {
    jsonrpc: '2.0',
    id: message.id
  };

  try {
    switch (message.method) {
      case 'initialize':
        response.result = {
          protocolVersion: MCP_VERSION,
          capabilities: {
            tools: {}
          },
          serverInfo: {
            name: 'racing-mcp-server',
            version: '2.0'
          }
        };
        logEvent('STARTUP', { method: 'initialize', version: MCP_VERSION });
        break;

      case 'tools/list':
        response.result = { tools };
        logEvent('DATA_OUT', { method: 'tools/list', count: tools.length });
        break;

      case 'tools/call':
        handleTool(message.params.name, message.params.arguments).then(result => {
          response.result = result;
          process.stdout.write(JSON.stringify(response) + '\n');
        }).catch(err => {
          response.error = {
            code: -32603,
            message: sanitizeError(err)
          };
          process.stdout.write(JSON.stringify(response) + '\n');
        });
        return; // Async handling

      default:
        response.error = { code: -32601, message: `Unknown method: ${message.method}` };
    }

    // Synchronous response
    process.stdout.write(JSON.stringify(response) + '\n');
  } catch (e) {
    response.error = { code: -32603, message: sanitizeError(e) };
    process.stdout.write(JSON.stringify(response) + '\n');
  }
}

// Read and process stdin line by line
process.stdin.on('data', (data) => {
  const lines = data.toString().split('\n');
  for (const line of lines) {
    if (line.trim()) {
      try {
        const message = JSON.parse(line);
        handleMessage(message);
      } catch (e) {
        logEvent('ERROR', { phase: 'parse_input', error: sanitizeError(e) });
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0',
          error: { code: -32700, message: 'Parse error' }
        }) + '\n');
      }
    }
  }
});

process.on('exit', () => {
  logEvent('SHUTDOWN', { code: 0 });
});

process.on('error', (e) => {
  logEvent('ERROR', { phase: 'process', error: sanitizeError(e) });
});
