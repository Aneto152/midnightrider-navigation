#!/usr/bin/env node
/**
 * competitor.js — AIS Fleet Tracking MCP Server v2.0
 * Thin wrapper over AIS module REST API (SSOT)
 */

'use strict';
const http = require('http');

const AIS_HOST = process.env.AIS_API_HOST || 'localhost';
const AIS_PORT = parseInt(process.env.AIS_API_PORT || '5000', 10);
const MCP_VERSION = '2024-11-05';

function aisGet(endpoint) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { hostname: AIS_HOST, port: AIS_PORT, path: endpoint, method: 'GET' },
      (res) => {
        let buf = '';
        res.on('data', c => buf += c);
        res.on('end', () => {
          if (res.statusCode === 200) {
            try { resolve(JSON.parse(buf)); }
            catch (e) { reject(new Error('JSON parse: ' + e.message)); }
          } else {
            reject(new Error('HTTP ' + res.statusCode + ': ' + endpoint));
          }
        });
      }
    );
    req.on('error', reject);
    req.setTimeout(8000, () => req.destroy(new Error('Timeout')));
    req.end();
  });
}

async function getCompetitorFleet(args) {
  const nm = args.radius_nm || 15;
  const mode = args.vmg_mode || 'wind';
  const data = await aisGet('/api/competitors?radius_nm=' + nm + '&vmg_mode=' + mode);
  if (data.error === 'no_position') return '⚠️ No GPS fix';
  const comps = (data.competitors || []).sort((a,b) => (a.dist_nm||99) - (b.dist_nm||99));
  const red = comps.filter(c => c.color === 'red');
  const green = comps.filter(c => c.color === 'green');
  let t = '**AIS Fleet — ' + nm + 'nm | VMG: ' + mode + '**\n\n';
  t += comps.length + ' boats | 🔴 ' + red.length + ' gaining | 🟢 ' + green.length + ' losing\n\n';
  for (const c of comps) {
    const icon = c.color === 'red' ? '🔴' : c.color === 'green' ? '🟢' : '⚪';
    const vmg = (mode === 'mark' ? c.vmg_mark_kts : c.vmg_wind_kts) || 0;
    t += icon + ' **' + (c.name || c.mmsi) + '** (' + (c.sail_num||'—') + ') | '
       + (c.dist_nm||0).toFixed(2) + 'nm @ ' + Math.round(c.bearing||0) + '° | VMG ' + vmg.toFixed(2) + 'kt\n';
  }
  return t;
}

async function getNearestCompetitor(args) {
  const nm = args.radius_nm || 15;
  const data = await aisGet('/api/competitors?radius_nm=' + nm + '&vmg_mode=wind');
  if (data.error === 'no_position') return '⚠️ No GPS fix';
  const comps = data.competitors || [];
  if (!comps.length) return 'No competitors within ' + nm + 'nm';
  const nearest = [...comps].sort((a,b) => (a.dist_nm||99) - (b.dist_nm||99))[0];
  let t = '**Nearest: ' + (nearest.name||nearest.mmsi) + '**\n';
  t += '  ' + (nearest.dist_nm||0).toFixed(2) + 'nm @ ' + Math.round(nearest.bearing||0) + '°\n';
  return t;
}

async function getFleetPressure(args) {
  const nm = args.radius_nm || 15;
  const data = await aisGet('/api/competitors?radius_nm=' + nm + '&vmg_mode=wind');
  if (data.error === 'no_position') return '⚠️ No GPS fix';
  const comps = data.competitors || [];
  let t = '**Fleet Pressure — ' + nm + 'nm**\n';
  t += '  Total: ' + comps.length + ' boats\n';
  return t;
}

async function getFleetSummary(args) {
  const nm = args.radius_nm || 15;
  const data = await aisGet('/api/competitors?radius_nm=' + nm + '&vmg_mode=wind');
  const red = (data.competitors || []).filter(c => c.color === 'red');
  let t = '**Fleet Briefing**\n';
  t += '  Fleet: ' + (data.competitors || []).length + ' boats\n';
  t += '  🔴 Threats: ' + red.length + '\n';
  return t;
}

async function findCompetitor(args) {
  const q = (args.query || '').toLowerCase();
  const data = await aisGet('/api/fleet_db');
  const hits = (data.competitors || []).filter(c =>
    (c.name||'').toLowerCase().includes(q) || (c.sail_num||'').includes(q) || (c.mmsi||'').includes(q)
  );
  if (!hits.length) return 'No competitor found: ' + args.query;
  let t = '**Search: ' + args.query + '** — ' + hits.length + ' result(s)\n\n';
  for (const c of hits) {
    t += '**' + (c.name||'—') + '** | Sail: ' + (c.sail_num||'—') + ' | MMSI: ' + (c.mmsi||'—') + '\n';
  }
  return t;
}

const TOOLS = [
  { name: 'get_competitor_fleet', description: 'AIS competitors in range, GREEN/RED VMG',
    inputSchema: { type: 'object', properties: {
      radius_nm: { type: 'number', default: 15 },
      vmg_mode: { type: 'string', enum: ['wind','mark'], default: 'wind' }
    }}},
  { name: 'get_nearest_competitor', description: 'Closest competitor + analysis',
    inputSchema: { type: 'object', properties: { radius_nm: { type: 'number', default: 15 }}}},
  { name: 'get_fleet_pressure', description: 'Fleet distribution by sector',
    inputSchema: { type: 'object', properties: { radius_nm: { type: 'number', default: 15 }}}},
  { name: 'get_fleet_summary', description: 'Narrative race briefing',
    inputSchema: { type: 'object', properties: { radius_nm: { type: 'number', default: 15 }}}},
  { name: 'find_competitor', description: 'Search by name, sail#, MMSI, skipper',
    inputSchema: { type: 'object', required: ['query'], properties: {
      query: { type: 'string' }
    }}},
];

const HANDLERS = {
  get_competitor_fleet, get_nearest_competitor, get_fleet_pressure, get_fleet_summary, find_competitor
};

function send(obj) { process.stdout.write(JSON.stringify(obj) + '\n'); }

async function dispatch(msg) {
  const { id, method, params = {} } = msg;
  if (method === 'initialize') {
    send({ jsonrpc: '2.0', id, result: {
      protocolVersion: MCP_VERSION,
      capabilities: { tools: {} },
      serverInfo: { name: 'competitor', version: '2.0.0' }
    }});
  } else if (method === 'tools/list') {
    send({ jsonrpc: '2.0', id, result: { tools: TOOLS }});
  } else if (method === 'tools/call') {
    const fn = HANDLERS[params.name];
    if (!fn) {
      send({ jsonrpc: '2.0', id, error: { code: -32601, message: 'Unknown: ' + params.name }});
      return;
    }
    try {
      const text = await fn(params.arguments || {});
      send({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text }] }});
    } catch (err) {
      send({ jsonrpc: '2.0', id, result: {
        content: [{ type: 'text', text: '❌ ' + err.message }],
        isError: true
      }});
    }
  }
}

let buf = '';
process.stdin.setEncoding('utf8').on('data', chunk => {
  buf += chunk;
  const lines = buf.split('\n');
  buf = lines.pop();
  lines.filter(l => l.trim()).forEach(l => {
    try { dispatch(JSON.parse(l)); }
    catch(e) { process.stderr.write('Parse: ' + e.message + '\n'); }
  });
}).resume();
