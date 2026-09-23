#!/usr/bin/env node

/**
 * MCP Server for Racing Data — Phase 2: Historical MCP/InfluxDB Contract
 *
 * Implements bounded-skew historical snapshot with strict contract validation.
 * - Four independent queries: latitude, longitude, speed_over_ground, course_over_ground
 * - Requires as_of_utc (ISO 8601 UTC with literal Z suffix) and window_seconds (1-3600)
 * - Preserves actual _time from each query; rejects skew > 1000 ms
 * - Fail-closed on any missing or invalid field
 * - COG arrives from Signal K in radians (SI) and is published in true
 *   degrees; every published fact carries its unit in the units block
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

// Borne haute du cap en radians, avec une marge pour l arrondi flottant :
// une valeur exactement egale a 2*PI doit passer. Declaree avant
// validateNumeric, qui s en sert.
const COG_RADIANS_MAX = 2 * Math.PI + 1e-9;

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
    // Defaut 63. Signal K sert navigation.courseOverGroundTrue en RADIANS,
    // jamais en degres : c est une unite SI, et c est aussi une mesure.
    // mesure du 2026-09-18 sur 365 jours de nos propres lignes : minimum
    // 0.000000 rad, maximum 6.281400 rad, 0 ligne(s) au-dela de 2*PI sur
    // 4078141.
    // Le domaine valide est donc [0, 2*PI] et non [0, 360] : un intervalle
    // exprime en degres contient tout l intervalle des radians, si bien
    // qu aucune valeur en radians n etait jamais signalee. Une valeur au-dela
    // de 2*PI fait desormais echouer la collecte, bruyamment, plutot que de
    // publier un cap faux.
    case 'course_over_ground':
      return (num >= 0 && num <= COG_RADIANS_MAX) ? num : null;
    default:
      return Number.isFinite(num) ? num : null;
  }
}

/**
 * Convert a Signal K course over ground from radians to true degrees.
 *
 * Signal K serves angles in SI units, that is radians in [0, 2*PI]. The
 * published contract key is `course_over_ground_degrees`, so the value has to
 * be converted exactly once, here, at the boundary of the server. Converting
 * anywhere downstream would leave the raw radian value travelling under a key
 * that claims degrees, which is defect 63.
 *
 * @param {number} radians - course over ground in radians, already validated
 * @returns {number} course over ground in true degrees, in [0, 360]
 */
function cogRadiansToDegrees(radians) {
  return radians * (180 / Math.PI);
}

/**
 * HISTORICAL DOOR - an instant and a tolerance.
 *
 * Kept verbatim so that every existing caller and every existing test keeps
 * working unchanged. It owns no collection logic whatsoever: it turns its two
 * arguments into the two bounds the single engine takes, and delegates.
 */
async function getHistoricalSnapshot(asOfUtc, windowSeconds, includeOptionalFacts = false) {
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

  return await collectSnapshot(startTime, asOfUtc, includeOptionalFacts);
}

/**
 * RANGE DOOR - two explicit bounds.
 *
 * Live consultation is not a second architecture. It is this door with
 * end_utc set to the instant the caller consults. Decided with Denis on
 * 2026-09-18: one path, and the temporal horizon is a parameter.
 *
 * A consequence worth stating, because it removes a temptation: nothing in
 * this server ever asks what time it is. There is therefore nothing here to
 * lie to in order to replay the past. A live collection and a replayed one
 * differ only by the bounds the caller passes.
 */
async function getSnapshot(startUtc, endUtc) {
  return await collectSnapshot(startUtc, endUtc, false);
}

/**
 * THE SINGLE COLLECTION ENGINE.
 *
 * Both doors above end here. This is the only function in this file that
 * builds a Flux query, and tests/mcp/test_h9_chemin_unique.py counts the
 * openings of a Flux query in this file and requires exactly one - so a
 * second engine cannot appear without turning a test red. That assertion is
 * the whole point of H9: convergence that is verified, not promised.
 *
 * Until 2026-09-18 a second, unfinished collection path asked for position,
 * SOG and COG through three separate tools that this server never declared.
 * Three calls mean three instants, which cannot be skew-checked, and that
 * path carried neither the self filter of defect 58 nor the radian
 * conversion of defect 63. Completing it would have reopened both defects on
 * the path meant for racing. It was removed instead: defect 65.
 */
function buildFluxQuery(queryBody, startTime, endTime) {
  return `from(bucket:"${INFLUX_BUCKET}")
    |> range(start: ${startTime}, stop: ${endTime})
${queryBody}`;
}

function buildFactQuery(selector, startTime, endTime) {
  const queryBody = [
    `    |> filter(fn: (r) => r._measurement == "${selector.measurement}")`,
    `    |> filter(fn: (r) => r._field == "${selector.field}")`,
    `    |> filter(fn: (r) => ${selector.source || 'r.self == "true"'})`,
    `    |> keep(columns: ["_time", "_value", "source"])`,
    '    |> group()',
    '    |> sort(columns: ["_time"])',
    '    |> last(column: "_time")'
  ].join('\n');
  return buildFluxQuery(queryBody, startTime, endTime);
}

async function collectSnapshot(startUtc, endUtc, includeOptionalFacts = false) {
  if (!startUtc || typeof startUtc !== 'string') {
    throw new Error('start_utc is required and must be a string');
  }
  if (!endUtc || typeof endUtc !== 'string') {
    throw new Error('end_utc is required and must be a string');
  }
  if (!startUtc.endsWith('Z') || !endUtc.endsWith('Z')) {
    throw new Error('start_utc and end_utc must end with \'Z\' (UTC timezone required)');
  }

  const startDate = validateTimestamp(startUtc);
  const endDate = validateTimestamp(endUtc);
  if (!startDate || !endDate) {
    throw new Error('start_utc and end_utc must be valid ISO 8601 UTC timestamps with Z suffix');
  }

  const durationMs = endDate.getTime() - startDate.getTime();
  if (durationMs <= 0) {
    throw new Error('end_utc must be strictly after start_utc');
  }
  if (durationMs > 3600 * 1000) {
    throw new Error('the interval must not exceed 3600 seconds');
  }

  // Local aliases. Everything below this line is the collection body as it
  // stood at commit e64f3ca5, moved here unchanged - extraction, not rewrite.
  // Keeping the original variable names is what makes that verifiable by
  // reading the diff rather than by trusting this comment.
  // Les deux bornes sont normalisees avant de servir. Sans cela les deux
  // portes produiraient des requetes Flux textuellement differentes pour le
  // meme intervalle - la porte historique calcule sa borne basse avec
  // toISOString() et obtient .000Z, la porte de plage recoit ce que
  // l appelant a ecrit. Meme instant, autre chaine. Normaliser ici est ce
  // qui rend la convergence verifiable au caractere pres, et non seulement
  // semantiquement.
  const startTime = startDate.toISOString();
  const asOfUtc = endDate.toISOString();

  logEvent('DATA_IN', { startTime, asOfUtc, durationMs });

  // Four independent queries, one per fact.
  //
  // Each fact is addressed by the measurement AND the field key that actually
  // exists in the bucket, verified against production InfluxDB on 2026-09-15:
  // navigation.position carries the field keys 'lat' and 'lon', while
  // navigation.speedOverGround and navigation.courseOverGroundTrue each carry
  // a single 'value' field. Signal K publishes dotted paths as measurement
  // names; the previous underscore names matched nothing at all.
  //
  // The self filter is what makes these four facts OUR facts. Measured on the
  // production bucket on 2026-09-17: navigation.position carries 3991 distinct
  // contexts, of which 3990 are AIS targets or AtoNs and exactly one is
  // Midnight Rider. The tag `self` exists with the single value "true" and is
  // carried only by our own rows; AIS rows carry no `self` tag at all, so
  // `r.self == "true"` excludes them. Without that filter the four facts below
  // came from whichever vessel wrote last: in the 300 s window ending
  // 2026-09-07T14:36:25Z the answer was an AIS target roughly 11 nautical
  // miles away, reported as moving, while Midnight Rider lay stopped. Four
  // facts out of four were another boat's. Coordinates are deliberately not
  // recorded here: see docs/DECISIONS/MEDIAMAN-HISTORICAL-DRY-RUN.md.
  // That was defect 58.
  //
  // ORDER MATTERS. This filter must stay ABOVE keep(), which drops every
  // column except _time and _value - including `self`. Moved below keep() it
  // would filter nothing and silently restore the defect. The regression test
  // tests/mcp/test_defaut_58_context_filter.py asserts the order, not just
  // the presence.
  //
  // No source is ever pinned. These three measurements each carry three source
  // tags - N2K.0, N2K.1 and N2K.2, measured 2026-09-17 - because the two
  // Vulcan 7 plotters are not always both powered. Preferring one named source
  // would leave the snapshot blind whenever that source is silent; group()
  // then last() takes the newest point whichever source wrote it.
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

  // Optional facts are opt-in so the existing four-query current path and its
  // regression tests remain unchanged. Historical MediaMan explicitly opts in.
  const OPTIONAL_FACT_SELECTORS = [
    { fact: 'speed_through_water', measurement: 'navigation.speedThroughWater', field: 'value', unit: 'm_per_s', source: 'r.source == "N2K.35"', transform: 'identity' },
    { fact: 'depth_below_transducer', measurement: 'environment.depth.belowTransducer', field: 'value', unit: 'm', source: 'r.source == "N2K.35"', transform: 'identity' },
    { fact: 'water_temperature', measurement: 'environment.water.temperature', field: 'value', unit: 'celsius', source: 'r.source == "N2K.35"', transform: 'kelvin_to_celsius' },
    { fact: 'wind_apparent_angle', measurement: 'environment.wind.angleApparent', field: 'value', unit: 'degrees_relative', source: 'r.source =~ /^Calypso\./', transform: 'radians_to_degrees' },
    { fact: 'wind_apparent_speed', measurement: 'environment.wind.speedApparent', field: 'value', unit: 'm_per_s', source: 'r.source =~ /^Calypso\./', transform: 'identity' },
    { fact: 'wind_true_angle', measurement: 'environment.wind.angleTrueWater', field: 'value', unit: 'degrees_relative', source: 'r.source =~ /^signalk-truewind-calculator\./', transform: 'radians_to_degrees' },
    { fact: 'wind_true_speed', measurement: 'environment.wind.speedTrue', field: 'value', unit: 'm_per_s', source: 'r.source =~ /^signalk-truewind-calculator\./', transform: 'identity' },
    { fact: 'wind_true_direction', measurement: 'environment.wind.directionTrue', field: 'value', unit: 'degrees_true', source: 'r.source =~ /^signalk-truewind-calculator\./', transform: 'radians_to_degrees_compass' },
    { fact: 'current_set', measurement: 'environment.current.setTrue', field: 'value', unit: 'degrees_true', source: 'r.source =~ /^signalk-current-calculator\./', transform: 'radians_to_degrees_compass' },
    { fact: 'current_drift', measurement: 'environment.current.drift', field: 'value', unit: 'm_per_s', source: 'r.source =~ /^signalk-current-calculator\./', transform: 'identity' },
    { fact: 'attitude_roll', measurement: 'navigation.attitude.roll', field: 'value', unit: 'degrees', source: 'r.source == "N2K.35"', transform: 'radians_to_degrees' },
    { fact: 'attitude_pitch', measurement: 'navigation.attitude.pitch', field: 'value', unit: 'degrees', source: 'r.source == "N2K.35"', transform: 'radians_to_degrees' },
    { fact: 'outside_temperature', measurement: 'environment.outside.temperature', field: 'value', unit: 'celsius', source: 'r.source == "N2K.116"', transform: 'kelvin_to_celsius' },
    { fact: 'outside_pressure', measurement: 'environment.outside.pressure', field: 'value', unit: 'hpa', source: 'r.source == "N2K.116"', transform: 'pascal_to_hpa' },
    { fact: 'calypso_battery_percent', measurement: 'batteries.calypso.percent', field: 'value', unit: 'percent', source: 'r.source =~ /^Calypso\./', transform: 'identity' }
  ];

  const queryResults = {};

  for (const selector of FACT_SELECTORS) {
    const query = buildFactQuery(selector, startTime, asOfUtc);

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

  const optionalResults = {};
  if (includeOptionalFacts) {
    for (const selector of OPTIONAL_FACT_SELECTORS) {
      const query = buildFactQuery(selector, startTime, asOfUtc);
      try {
        const results = await queryInfluxDB(query);
        optionalResults[selector.fact] = results.length > 0 ? results[0] : null;
      } catch (e) {
        // Optional measurements are fail-soft: one unavailable instrument must
        // not discard the four mandatory navigation facts.
        logEvent('ERROR', {
          phase: 'optional_query',
          fact: selector.fact,
          measurement: selector.measurement,
          error: sanitizeError(e)
        });
        optionalResults[selector.fact] = null;
      }
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

  const optionalFacts = {};
  const optionalUnits = {};
  const optionalTimestamps = {};
  const optionalSources = {};
  const optionalTransforms = {
    identity: value => value,
    kelvin_to_celsius: value => value - 273.15,
    pascal_to_hpa: value => value / 100.0,
    radians_to_degrees: value => value * (180 / Math.PI),
    radians_to_degrees_compass: value => ((value * (180 / Math.PI)) + 360) % 360
  };
  if (includeOptionalFacts) {
    for (const selector of OPTIONAL_FACT_SELECTORS) {
      const row = optionalResults[selector.fact];
      if (!row || row._value === null || row._value === undefined || row._value === '' || !row._time) continue;
      const raw = parseFloat(row._value);
      const stamp = validateTimestamp(row._time);
      if (!Number.isFinite(raw) || !stamp) continue;
      const transformed = optionalTransforms[selector.transform](raw);
      if (!Number.isFinite(transformed)) continue;
      optionalFacts[selector.fact] = transformed;
      optionalUnits[selector.fact] = selector.unit;
      optionalTimestamps[selector.fact] = stamp.toISOString();
      optionalSources[selector.fact] = row.source || selector.source;
    }
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
    optionalFactsReturned: Object.keys(optionalFacts).length,
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
      course_over_ground_degrees: cogRadiansToDegrees(facts.course_over_ground)
    },
    // Chaque fait publie dit son unite. Sans cela le defaut 63 a pu vivre :
    // la cle annoncait des degres, la valeur etait en radians, et aucun
    // consommateur n avait de quoi s en apercevoir.
    units: {
      latitude: 'degrees',
      longitude: 'degrees',
      speed_over_ground_ms: 'm_per_s',
      course_over_ground_degrees: 'degrees_true'
    },
    source_timestamp: sourceTimestamp,
    optional_facts: optionalFacts,
    optional_units: optionalUnits,
    optional_fact_timestamps: optionalTimestamps,
    optional_sources: optionalSources,
    fact_timestamps: {
      latitude: timestamps.latitude.toISOString(),
      longitude: timestamps.longitude.toISOString(),
      speed_over_ground_ms: timestamps.speed_over_ground.toISOString(),
      course_over_ground_degrees: timestamps.course_over_ground.toISOString()
    },
    bounded_skew_ms: skew,
    // Both bounds are echoed back to the caller. A consumer must never have
    // to guess which interval produced a fact, and an answer collected live
    // must be distinguishable from a replayed one by its content alone.
    interval: {
      start_utc: startTime,
      end_utc: asOfUtc,
      duration_seconds: Math.round(durationMs / 1000)
    }
  };
}


const TEMPORAL_SELECTORS = [
  { series: 'latitude', measurement: 'navigation.position', field: 'lat', source: 'self' },
  { series: 'longitude', measurement: 'navigation.position', field: 'lon', source: 'self' },
  { series: 'speed_over_ground', measurement: 'navigation.speedOverGround', field: 'value', source: 'self' },
  { series: 'course_over_ground', measurement: 'navigation.courseOverGroundTrue', field: 'value', source: 'self' },
  { series: 'speed_through_water', measurement: 'navigation.speedThroughWater', field: 'value', source: 'N2K.35' },
  { series: 'wind_true_angle', measurement: 'environment.wind.angleTrueWater', field: 'value', source: 'truewind' },
  { series: 'wind_true_speed', measurement: 'environment.wind.speedTrue', field: 'value', source: 'truewind' },
  { series: 'attitude_roll', measurement: 'navigation.attitude.roll', field: 'value', source: 'N2K.35' },
  { series: 'attitude_pitch', measurement: 'navigation.attitude.pitch', field: 'value', source: 'N2K.35' }
];

function buildTemporalQuery(startUtc, endUtc) {
  const measurements = [...new Set(TEMPORAL_SELECTORS.map(selector => selector.measurement))];
  const sourceClauses = TEMPORAL_SELECTORS.map(selector => {
    if (selector.source === 'self') return `(r._measurement == "${selector.measurement}" and r.self == "true")`;
    if (selector.source === 'N2K.35') return `(r._measurement == "${selector.measurement}" and r.source == "N2K.35")`;
    return `(r._measurement == "${selector.measurement}" and r.source =~ /^signalk-truewind-calculator\./)`;
  }).join(' or ');
  const queryBody = [
    `    |> filter(fn: (r) => contains(value: r._measurement, set: [${measurements.map(value => `"${value}"`).join(', ')}]))`,
    `    |> filter(fn: (r) => ${sourceClauses})`,
    '    |> keep(columns: ["_time", "_measurement", "_field", "_value", "source"])',
    '    |> group()',
    '    |> sort(columns: ["_time"])'
  ].join('\n');
  return buildFluxQuery(queryBody, startUtc, endUtc);
}

function temporalSeriesName(row) {
  const selector = TEMPORAL_SELECTORS.find(item => item.measurement === row._measurement && item.field === row._field);
  return selector ? selector.series : null;
}

function normalizeTemporalValue(series, value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  if (series === 'wind_true_angle' || series === 'attitude_roll' || series === 'attitude_pitch') {
    const degrees = numeric * 180 / Math.PI;
    return degrees > 180 ? degrees - 360 : degrees;
  }
  if (series === 'course_over_ground') {
    return ((numeric * 180 / Math.PI) + 360) % 360;
  }
  if (series === 'speed_through_water' || series === 'wind_true_speed' || series === 'speed_over_ground') return numeric;
  if (series === 'water_temperature') return numeric - 273.15;
  return numeric;
}

function downsampleTemporalRows(rows, resolutionSeconds) {
  const buckets = new Map();
  const angular = new Set(['wind_true_angle', 'course_over_ground', 'attitude_roll', 'attitude_pitch']);
  for (const row of rows) {
    const series = temporalSeriesName(row);
    if (!series || !row._time) continue;
    const value = normalizeTemporalValue(series, row._value);
    if (value === null) continue;
    const timestamp = new Date(row._time);
    if (Number.isNaN(timestamp.getTime())) continue;
    const bucket = Math.floor(timestamp.getTime() / (resolutionSeconds * 1000));
    const key = `${series}:${bucket}`;
    const previous = buckets.get(key);
    if (!previous || angular.has(series)) {
      buckets.set(key, { series, timestamp_utc: timestamp.toISOString(), value, source_id: row.source || null, sum: value, count: 1 });
    } else {
      previous.sum += value;
      previous.count += 1;
      previous.value = previous.sum / previous.count;
      previous.timestamp_utc = timestamp.toISOString();
      previous.source_id = row.source || previous.source_id;
    }
  }
  return [...buckets.values()]
    .map(({ sum, count, ...row }) => row)
    .sort((a, b) => a.timestamp_utc.localeCompare(b.timestamp_utc));
}

async function getHistoricalAnalysis(startUtc, endUtc, resolutionSeconds = 60) {
  if (!startUtc || !endUtc || !startUtc.endsWith('Z') || !endUtc.endsWith('Z')) throw new Error('start_utc and end_utc must end with Z');
  const start = validateTimestamp(startUtc);
  const end = validateTimestamp(endUtc);
  if (!start || !end || end <= start) throw new Error('invalid historical analysis interval');
  const duration = end.getTime() - start.getTime();
  if (duration > 21600 * 1000) throw new Error('historical analysis interval must not exceed 21600 seconds');
  if (!Number.isInteger(resolutionSeconds) || resolutionSeconds < 10 || resolutionSeconds > 300) throw new Error('resolution_seconds must be an integer between 10 and 300');
  logEvent('DATA_IN', { analysis: 'historical', durationSeconds: Math.round(duration / 1000), resolutionSeconds });
  const rows = await queryInfluxDB(buildTemporalQuery(start.toISOString(), end.toISOString()));
  const seriesRows = downsampleTemporalRows(rows, resolutionSeconds);
  const result = {
    success: true,
    status: 'COMPLETE',
    analysis_version: '1',
    interval: { start_utc: start.toISOString(), end_utc: end.toISOString(), duration_seconds: Math.round(duration / 1000) },
    resolution_seconds: resolutionSeconds,
    rows: seriesRows,
    query_count: 1,
    llm_status: 'not_activated'
  };
  logEvent('DATA_OUT', { analysis: 'historical', queryCount: 1, sampleCount: seriesRows.length, seriesCount: new Set(seriesRows.map(row => row.series)).size });
  return result;
}

/**
 * Handle MCP tool calls
 */
async function handleTool(name, args) {
  try {
    switch (name) {
      case 'get_historical_snapshot':
        return await getHistoricalSnapshot(args.as_of_utc, args.window_seconds, args.include_optional_facts === true);
      case 'get_snapshot':
        return await getSnapshot(args.start_utc, args.end_utc);
      case 'get_historical_analysis':
        return await getHistoricalAnalysis(args.start_utc, args.end_utc, args.resolution_seconds);
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
        },
        include_optional_facts: {
          type: 'boolean',
          description: 'Opt in to the fail-soft narrative fact expansion; default false preserves the four-fact contract'
        }
      },
      required: ['as_of_utc', 'window_seconds'],
      additionalProperties: false
    }
  },
  {
    name: 'get_historical_analysis',
    description: 'Read a bounded historical time series from InfluxDB for deterministic MediaMan analysis',
    inputSchema: {
      type: 'object',
      properties: {
        start_utc: { type: 'string', description: 'ISO 8601 UTC timestamp ending with Z' },
        end_utc: { type: 'string', description: 'ISO 8601 UTC timestamp ending with Z' },
        resolution_seconds: { type: 'integer', description: 'Temporal resolution from 10 to 300 seconds', minimum: 10, maximum: 300 }
      },
      required: ['start_utc', 'end_utc'],
      additionalProperties: false
    }
  },
  {
    name: 'get_snapshot',
    description: 'Get a bounded-skew snapshot over an explicit [start_utc, end_utc] interval. Live consultation is this tool with end_utc set to the present instant.',
    inputSchema: {
      type: 'object',
      properties: {
        start_utc: {
          type: 'string',
          description: 'ISO 8601 UTC timestamp with literal Z suffix - lower bound of the interval'
        },
        end_utc: {
          type: 'string',
          description: 'ISO 8601 UTC timestamp with literal Z suffix - upper bound of the interval, set to the present instant for a live consultation'
        }
      },
      required: ['start_utc', 'end_utc'],
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
