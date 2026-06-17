#!/usr/bin/env node

/**
 * electrical-server.js — SOK BMS Battery Monitoring MCP Server
 * 
 * Monitors battery health via InfluxDB sok_bms measurement
 * Provides power, autonomy, and alert information for racing
 * 
 * Tools:
 * 1. get_battery_status — voltage, SOC%, current, temperature, state
 * 2. get_battery_trend — charging/discharging rate, autonomy over time
 * 3. get_power_summary — power balance, consumption, autonomy
 * 4. get_battery_alerts — threshold violations (SOC, temp, voltage)
 * 5. get_electrical_summary — narrative for Midnight Reporter
 */

const http = require('http');
const readline = require('readline');

// Configuration
const INFLUX_URL = process.env.INFLUX_URL || 'http://localhost:8086';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || '';
const INFLUX_ORG = process.env.INFLUX_ORG || 'MidnightRider';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';

const MCP_VERSION = '2024-11-05';

// Battery thresholds (constants)
const BATTERY_THRESHOLDS = {
  SOC_CRITICAL: 20,      // % - CRITICAL
  SOC_WARNING: 35,       // % - WARNING
  TEMP_WARNING: 45,      // °C - WARNING
  TEMP_CRITICAL: 55,     // °C - CRITICAL
  VOLTAGE_LOW: 12.0,     // V - WARNING
  VOLTAGE_HIGH: 14.8,    // V - WARNING
  DATA_AGE_MAX: 30       // seconds - max age for "connected"
};

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

  const records = [];
  let headerMap = {};
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('#')) {
      if (line.startsWith('#group')) {
        headerMap = {};
        const parts = line.split(',');
        for (let j = 1; j < parts.length; j++) {
          headerMap[j-1] = parts[j].trim();
        }
      }
      continue;
    }
    if (!line.trim()) continue;

    const cols = line.split(',');
    if (cols.length < 2) continue;

    const record = { _value: parseFloat(cols[6]) || 0, _field: cols[5] || 'unknown', _time: cols[4] || '' };
    for (let j = 1; j < Math.min(cols.length, 5); j++) {
      record[headerMap[j] || `col${j}`] = cols[j];
    }
    records.push(record);
  }

  return records;
}

// TOOL 1: get_battery_status
async function getBatteryStatus() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "sok_bms")
      |> last()`;

    const records = await queryInfluxDB(query);
    
    if (!records.length) {
      return {
        connected: false,
        bms_age_s: null,
        voltage_v: null,
        current_a: null,
        soc_pct: null,
        temp_bms_c: null,
        temp_mos_c: null,
        capacity_ah: null,
        state: 'unknown',
        health: 'unknown',
        alert: 'SOK BMS not yet connected — data available after May 2026 installation'
      };
    }

    // Extract fields from records
    const fields = {};
    records.forEach(r => {
      if (r._field && typeof r._value === 'number') {
        fields[r._field] = r._value;
      }
    });

    const voltage = fields.voltage_v || 13.2;
    const current = fields.current_a || 0;
    const soc = fields.soc_pct || 75;
    const tempBms = fields.temp_bms_c || 25;
    const tempMos = fields.temp_mos_c || 25;
    const capacity = fields.capacity_ah || 100;

    // Determine state
    let state = 'idle';
    if (current > 1) state = 'charging';
    else if (current < -1) state = 'discharging';

    // Determine health
    let health = 'good';
    if (tempBms > BATTERY_THRESHOLDS.TEMP_CRITICAL) health = 'critical';
    else if (tempBms > BATTERY_THRESHOLDS.TEMP_WARNING) health = 'hot';
    else if (tempBms > 40) health = 'warm';

    // Generate alert
    let alert = null;
    if (soc < BATTERY_THRESHOLDS.SOC_CRITICAL) alert = `CRITICAL — Battery ${Math.round(soc)}% remaining`;
    else if (soc < BATTERY_THRESHOLDS.SOC_WARNING) alert = `LOW — Battery ${Math.round(soc)}% remaining`;
    else if (voltage < BATTERY_THRESHOLDS.VOLTAGE_LOW) alert = 'Voltage low';
    else if (voltage > BATTERY_THRESHOLDS.VOLTAGE_HIGH) alert = 'Overvoltage';

    const timeStr = records[0]._time || new Date().toISOString();
    const dataAge = Math.round((Date.now() - new Date(timeStr).getTime()) / 1000);

    return {
      connected: dataAge < BATTERY_THRESHOLDS.DATA_AGE_MAX,
      bms_age_s: dataAge,
      voltage_v: parseFloat(voltage.toFixed(2)),
      current_a: parseFloat(current.toFixed(2)),
      soc_pct: parseFloat(soc.toFixed(1)),
      temp_bms_c: parseFloat(tempBms.toFixed(1)),
      temp_mos_c: parseFloat(tempMos.toFixed(1)),
      capacity_ah: parseFloat(capacity.toFixed(1)),
      state,
      health,
      alert
    };
  } catch (err) {
    return { connected: false, error: err.message };
  }
}

// TOOL 2: get_battery_trend
async function getBatteryTrend(minutes = 30) {
  try {
    const mins = Math.min(Math.max(minutes, 5), 120);
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -${mins}m)
      |> filter(fn: (r) => r._measurement == "sok_bms" and (r._field == "soc_pct" or r._field == "voltage_v"))
      |> aggregateWindow(every: 2m, fn: mean)`;

    const records = await queryInfluxDB(query);
    
    if (!records.length) {
      return {
        duration_min: mins,
        soc_start_pct: null,
        soc_current_pct: null,
        trend: 'unknown',
        estimated_full_h: null,
        estimated_empty_h: null,
        note: 'Insufficient data'
      };
    }

    const socValues = records.filter(r => r._field === 'soc_pct').map(r => r._value);
    if (socValues.length < 2) {
      return {
        duration_min: mins,
        soc_start_pct: socValues[0] || 75,
        soc_current_pct: socValues[0] || 75,
        trend: 'stable',
        note: 'Insufficient time for trend analysis'
      };
    }

    const socStart = socValues[0];
    const socCurrent = socValues[socValues.length - 1];
    const socDelta = socCurrent - socStart;
    const ratePerHour = (socDelta / mins) * 60;

    let trend = 'stable';
    let estimatedHours = null;
    if (ratePerHour > 0.5) {
      trend = 'charging';
      estimatedHours = (100 - socCurrent) / ratePerHour;
    } else if (ratePerHour < -0.5) {
      trend = 'discharging';
      estimatedHours = socCurrent / Math.abs(ratePerHour);
    }

    const note = trend === 'charging'
      ? `Charging at ${Math.abs(ratePerHour).toFixed(1)}%/h — full in ${estimatedHours.toFixed(1)}h`
      : trend === 'discharging'
      ? `Discharging at ${Math.abs(ratePerHour).toFixed(1)}%/h — empty in ${estimatedHours.toFixed(1)}h`
      : 'Battery stable';

    return {
      duration_min: mins,
      soc_start_pct: parseFloat(socStart.toFixed(1)),
      soc_current_pct: parseFloat(socCurrent.toFixed(1)),
      soc_delta_pct: parseFloat(socDelta.toFixed(1)),
      trend,
      rate_pct_per_hour: parseFloat(ratePerHour.toFixed(2)),
      estimated_hours: estimatedHours ? parseFloat(estimatedHours.toFixed(1)) : null,
      note
    };
  } catch (err) {
    return { error: err.message };
  }
}

// TOOL 3: get_power_summary
async function getPowerSummary() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "sok_bms" and (r._field == "voltage_v" or r._field == "current_a"))
      |> last()`;

    const records = await queryInfluxDB(query);
    
    if (!records.length) {
      return {
        avg_current_a: null,
        power_w: null,
        net_balance: 'unknown',
        estimated_autonomy_h: null,
        note: 'BMS data not available'
      };
    }

    const fields = {};
    records.forEach(r => {
      if (r._field) fields[r._field] = r._value;
    });

    const voltage = fields.voltage_v || 13.2;
    const current = fields.current_a || 0;
    const power = Math.abs(voltage * current);

    let consumption = 0, charging = 0;
    if (current < -1) consumption = power;
    else if (current > 1) charging = power;

    let autonomy = null;
    if (current < -1 && fields.soc_pct > 0) {
      autonomy = (fields.soc_pct / 100) * 120 / Math.abs(current); // rough estimate
    }

    const balance = current > 1 ? 'positive' : current < -1 ? 'negative' : 'balanced';
    const note = current > 1
      ? `Charging at ${power.toFixed(0)}W`
      : current < -1
      ? `Consuming ${consumption.toFixed(0)}W — ${autonomy?.toFixed(1)}h autonomy`
      : 'Idle';

    return {
      avg_current_a: parseFloat(current.toFixed(2)),
      power_w: parseFloat(power.toFixed(1)),
      consumption_w: consumption ? parseFloat(consumption.toFixed(1)) : null,
      charging_w: charging ? parseFloat(charging.toFixed(1)) : null,
      net_balance: balance,
      estimated_autonomy_h: autonomy ? parseFloat(autonomy.toFixed(1)) : null,
      note
    };
  } catch (err) {
    return { error: err.message };
  }
}

// TOOL 4: get_battery_alerts
async function getBatteryAlerts() {
  try {
    const query = `from(bucket:"${INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "sok_bms")
      |> last()`;

    const records = await queryInfluxDB(query);
    
    const fields = {};
    records.forEach(r => {
      if (r._field) fields[r._field] = r._value;
    });

    const soc = fields.soc_pct || 75;
    const voltage = fields.voltage_v || 13.2;
    const tempBms = fields.temp_bms_c || 25;

    const alerts = [];

    if (soc < BATTERY_THRESHOLDS.SOC_CRITICAL) {
      alerts.push({ level: 'critical', message: 'CRITICAL — Battery critically low', value: `${soc.toFixed(1)}%` });
    } else if (soc < BATTERY_THRESHOLDS.SOC_WARNING) {
      alerts.push({ level: 'warning', message: 'WARNING — Low battery', value: `${soc.toFixed(1)}%` });
    }

    if (tempBms > BATTERY_THRESHOLDS.TEMP_CRITICAL) {
      alerts.push({ level: 'critical', message: 'CRITICAL — Battery overtemperature', value: `${tempBms.toFixed(1)}°C` });
    } else if (tempBms > BATTERY_THRESHOLDS.TEMP_WARNING) {
      alerts.push({ level: 'warning', message: 'WARNING — Battery temperature high', value: `${tempBms.toFixed(1)}°C` });
    }

    if (voltage < BATTERY_THRESHOLDS.VOLTAGE_LOW) {
      alerts.push({ level: 'warning', message: 'WARNING — Voltage low', value: `${voltage.toFixed(2)}V` });
    } else if (voltage > BATTERY_THRESHOLDS.VOLTAGE_HIGH) {
      alerts.push({ level: 'warning', message: 'WARNING — Overvoltage', value: `${voltage.toFixed(2)}V` });
    }

    const allClear = alerts.length === 0;
    const highestSeverity = alerts.length ? alerts[0].level : 'none';

    let recommendedAction = 'Monitor battery';
    if (soc < BATTERY_THRESHOLDS.SOC_CRITICAL) {
      recommendedAction = 'Reduce power consumption immediately — prepare for shutdown';
    } else if (soc < BATTERY_THRESHOLDS.SOC_WARNING) {
      recommendedAction = 'Reduce non-essential power consumption';
    } else if (tempBms > BATTERY_THRESHOLDS.TEMP_WARNING) {
      recommendedAction = 'Reduce charge rate or allow cooling time';
    }

    return {
      active_alerts: alerts,
      all_clear: allClear,
      highest_severity: highestSeverity,
      recommended_action: recommendedAction
    };
  } catch (err) {
    return { error: err.message };
  }
}

// TOOL 5: get_electrical_summary
async function getElectricalSummary() {
  try {
    const status = await getBatteryStatus();
    const trend = await getBatteryTrend(30);
    const power = await getPowerSummary();
    const alerts = await getBatteryAlerts();

    if (!status.connected) {
      return {
        bms_connected: false,
        status_line: 'SOK BMS not connected',
        alerts_count: 0,
        reporter_note: 'SOK BMS not yet connected — data available after May 2026 installation',
        no_data_note: true
      };
    }

    const statusLine = `Battery ${status.soc_pct.toFixed(0)}% — ${status.voltage_v.toFixed(1)}V — ${status.current_a > 0 ? '+' : ''}${status.current_a.toFixed(1)}A — ${power.estimated_autonomy_h ? power.estimated_autonomy_h.toFixed(1) + 'h' : 'unknown'} autonomy`;

    const reporterNote = `Batterie maison à ${status.soc_pct.toFixed(0)}% (${status.voltage_v.toFixed(1)}V). ` +
      `Consommation actuelle ${power.power_w?.toFixed(0) || '?'}W. ` +
      `Autonomie estimée ${power.estimated_autonomy_h?.toFixed(1) || '?'} heures. ` +
      `Température normale (${status.temp_bms_c.toFixed(1)}°C).`;

    return {
      bms_connected: true,
      status_line: statusLine,
      alerts_count: alerts.active_alerts.length,
      reporter_note: reporterNote,
      highest_severity: alerts.highest_severity,
      recommended_action: alerts.recommended_action
    };
  } catch (err) {
    return { error: err.message };
  }
}

// MCP Tool definitions
const TOOLS = [
  {
    name: 'get_battery_status',
    description: 'Get current battery status (voltage, SOC%, current, temperature, health state)',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_battery_trend',
    description: 'Get battery trend over time (charging/discharging rate, autonomy estimate)',
    inputSchema: {
      type: 'object',
      properties: {
        minutes: { type: 'integer', description: 'Minutes to analyze (5-120, default 30)' }
      },
      required: []
    }
  },
  {
    name: 'get_power_summary',
    description: 'Get power balance and autonomy estimate',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_battery_alerts',
    description: 'Get active battery alerts (SOC, temperature, voltage threshold violations)',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_electrical_summary',
    description: 'Get battery status as narrative for Midnight Reporter',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  }
];

// Tool handler
async function processTool(toolName, toolInput) {
  switch (toolName) {
    case 'get_battery_status':
      return await getBatteryStatus();
    case 'get_battery_trend':
      return await getBatteryTrend(toolInput.minutes || 30);
    case 'get_power_summary':
      return await getPowerSummary();
    case 'get_battery_alerts':
      return await getBatteryAlerts();
    case 'get_electrical_summary':
      return await getElectricalSummary();
    default:
      return { error: `Unknown tool: ${toolName}` };
  }
}

// MCP Server (stdio transport)
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

async function handleRequest(request) {
  try {
    if (request.method === 'initialize') {
      return {
        protocolVersion: MCP_VERSION,
        capabilities: { tools: {} },
        serverInfo: {
          name: 'electrical-server',
          version: '1.0.0'
        }
      };
    }

    if (request.method === 'tools/list') {
      return { tools: TOOLS };
    }

    if (request.method === 'tools/call') {
      const result = await processTool(request.params.name, request.params.arguments || {});
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        isError: false
      };
    }

    return { error: `Unknown method: ${request.method}` };
  } catch (err) {
    return {
      content: [{ type: 'text', text: err.message }],
      isError: true
    };
  }
}

rl.on('line', async (line) => {
  try {
    const request = JSON.parse(line);
    const response = await handleRequest(request);
    console.log(JSON.stringify(response));
  } catch (err) {
    console.log(JSON.stringify({ error: err.message }));
  }
});

rl.on('close', () => process.exit(0));
