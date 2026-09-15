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
 * Accepts both dialects returned by /api/v2/query: annotated CSV
 * (#group / #datatype / #default rows plus a leading empty column)
 * and plain CSV (dialect.annotations = []). Requires _value and _time.
 */
function parseFluxResponse(csvData) {
  try {
    if (typeof csvData !== 'string' || csvData.trim() === '') {
      return [];
    }

    // Normalise line endings before anything else. InfluxDB terminates CSV
    // rows with CRLF; a surviving '\r' would stay glued to the last column of
    // every row and break the literal 'Z' suffix check on _time.
    const lines = csvData
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .split('\n');

    let header = null;
    const results = [];

    for (const rawLine of lines) {
      const line = rawLine.replace(/\s+$/, '');

      // Blank line: table separator in a multi-table Flux result.
      if (line === '') {
        continue;
      }

      // Annotation row: #group, #datatype, #default.
      if (line.startsWith('#')) {
        continue;
      }

      // Header and data rows are split identically and never filtered, so the
      // leading empty annotation column of annotated CSV keeps every column
      // aligned. Plain CSV (dialect.annotations = []) has no such column and
      // aligns just as well. Filtering empty cells - as the previous
      // implementation did on the header only - is what misaligned the data.
      const cells = line.split(',');

      // The first non-annotation row is the header.
      if (header === null) {
        header = cells;
        continue;
      }

      // A repeated header row marks the start of another table.
      if (cells.length === header.length &&
          cells.every((cell, idx) => cell === header[idx])) {
        continue;
      }

      if (cells.length !== header.length) {
        logEvent('ERROR', {
          phase: 'parse_response',
          reason: 'column count mismatch',
          expected: header.length,
          received: cells.length
        });
        continue;
      }

      const record = {};
      header.forEach((name, idx) => {
        // The annotation column is unnamed; it carries no data.
        if (name === '') {
          return;
        }
        // Preserve the raw cell verbatim, including '0' and ''. Coercing with
        // '||' would turn a legitimate zero into null. Completeness is decided
        // later by explicit checks, not by truthiness.
        record[name] = cells[idx] === undefined ? null : cells[idx];
      });
      results.push(record);
    }

    if (header === null) {
      logEvent('ERROR', {
        phase: 'parse_response',
        reason: 'no header row found'
      });
      return [];
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

  // Four independent queries, one per fact.
  //
  // Each fact is addressed by the measurement AND the field key that actually
  // exists in the bucket, verified against production InfluxDB on 2026-09-15:
  // navigation.position carries the field keys 'lat' and 'lon', while
  // navigation.speedOverGround and navigation.courseOverGroundTrue each carry
  // a single 'value' field. Signal K publishes dotted paths as measurement
  // names; the previous underscore names matched nothing at all.
  //
  // keep() reduces every input table to the same two columns so that tables
  // carrying different tag sets can be merged; group() collapses them into a
  // single table; sort() then last() returns exactly one record, the newest of
  // the whole window. Without this, last() returns one record per tag series
  // and the code would silently pick an arbitrary one.
  const FACT_SELECTORS = [
    { fact: 'latitude', measurement: 'navigation.position', field: 'lat' },
    { fact: 'longitude', measurement: 'navigation.position', field: 'lon' },
    { fact: 'speed_over_ground', measurement: 'navigation.speedOverGround', field: 'value' },
    { fact: 'course_over_ground', measurement: 'navigation.courseOverGroundTrue', field: 'value' }
  ];

  const queryResults = {};

  for (const selector of FACT_SELECTORS) {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: ${startTime}, stop: ${asOfUtc})
      |> filter(fn: (r) => r._measurement == "${selector.measurement}")
      |> filter(fn: (r) => r._field == "${selector.field}")
      |> keep(columns: ["_time", "_value"])
      |> group()
      |> sort(columns: ["_time"])
      |> last(column: "_time")`;

    try {
      const results = await queryInfluxDB(query);
      queryResults[selector.fact] = results.length > 0 ? results[0] : null;
    } catch (e) {
      logEvent('ERROR', {
        phase: 'query',
        fact: selector.fact,
        measurement: selector.measurement,
        field: selector.field,
        error: sanitizeError(e)
      });
      throw new Error(`Failed to query ${selector.fact}: ${sanitizeError(e)}`);
    }
  }

  // Extract and validate all four facts.
  //
  // Completeness is decided by explicit null / undefined / empty-string checks,
  // never by truthiness: a course over ground of exactly 0 means due north, a
  // speed of exactly 0 means stopped, and latitude or longitude can legitimately
  // be 0. Under `if (!value)` all four of those would be reported as missing.
  const facts = {};
  const timestamps = {};

  for (const selector of FACT_SELECTORS) {
    const row = queryResults[selector.fact];
    const missing = !row
      || row._value === null || row._value === undefined || row._value === ''
      || row._time === null || row._time === undefined || row._time === '';

    if (missing) {
      throw new Error(`Collection incomplete: ${selector.fact} missing or incomplete`);
    }

    const value = validateNumeric(row._value, selector.fact);
    const stamp = validateTimestamp(row._time);

    if (value === null || !stamp) {
      throw new Error(`Collection incomplete: ${selector.fact} invalid or missing timestamp`);
    }

    facts[selector.fact] = value;
    timestamps[selector.fact] = stamp;
  }

  // Validate bounded skew
  const timesMs = Object.values(timestamps).map(t => t.getTime());
  const skew = Math.max(...timesMs) - Math.min(...timesMs);

  if (skew > SKEW_LIMIT_MS) {
    throw new Error(`Historical snapshot skew ${skew}ms exceeds 1000ms limit`);
  }

  // Aggregate source_timestamp is the newest
  const sourceTimestamp = new Date(Math.max(...timesMs)).toISOString();

  // The boat's actual position is deliberately NOT logged. logEvent writes to
  // stderr and to logs/services/racing-mcp.log, and neither is an appropriate
  // place for coordinates; only non-locating metadata is emitted here.
  logEvent('DATA_OUT', {
    factsReturned: Object.keys(facts).length,
    positionPresent: facts.latitude !== null && facts.longitude !== null,
    sogPresent: facts.speed_over_ground !== null,
    cogPresent: facts.course_over_ground !== null,
    skewMs: skew,
    sourceTimestamp
  });

  return {
    success: true,
    status: 'COMPLETE',
    facts: {
      latitude: facts.latitude,
      longitude: facts.longitude,
      speed_over_ground_ms: facts.speed_over_ground,
      course_over_ground_degrees: facts.course_over_ground
    },
    source_timestamp: sourceTimestamp,
    fact_timestamps: {
      latitude: timestamps.latitude.toISOString(),
      longitude: timestamps.longitude.toISOString(),
      speed_over_ground_ms: timestamps.speed_over_ground.toISOString(),
      course_over_ground_degrees: timestamps.course_over_ground.toISOString()
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
          // MCP 2024-11-05 tools/call contract: the tool payload must travel
          // inside the result content envelope, as a JSON string in a text
          // block, and NOT as a bare result object. The Python consumer
          // (mediaman/mcp_client.py, _decode_mcp_result) implements the
          // specification strictly and rejected the bare object with
          // "MCP result missing 'content' field", which broke the whole
          // MediaMan historical chain on 2026-09-15 even though the snapshot
          // itself was already correct.
          response.result = {
            content: [
              { type: 'text', text: JSON.stringify(result) }
            ],
            isError: false
          };
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
