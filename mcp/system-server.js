#!/usr/bin/env node

/**
 * system-server.js — Raspberry Pi System Health Monitoring MCP Server
 * 
 * Monitors RPi health: CPU, RAM, disk, temperature, services status
 * Provides diagnostics for race operations and remote monitoring
 * 
 * Tools:
 * 1. get_system_health — CPU%, RAM%, disk%, temp, uptime, alerts
 * 2. get_services_status — HTTP ping all 5 services (SK/InfluxDB/Grafana/Regatta/Portal)
 * 3. get_network_status — IP, URLs, hostname, interfaces
 * 4. get_performance_metrics — load average, memory, process info
 * 5. get_system_summary — French narrative for Midnight Reporter
 */

const os = require('os');
const fs = require('fs');
const http = require('http');
const readline = require('readline');
const { execSync } = require('child_process');

const MCP_VERSION = '2024-11-05';

// System thresholds (constants)
const THRESHOLDS = {
  CPU_WARNING: 80,
  CPU_CRITICAL: 95,
  RAM_WARNING: 80,
  RAM_CRITICAL: 90,
  DISK_WARNING: 80,
  DISK_CRITICAL: 90,
  TEMP_WARNING: 70,
  TEMP_CRITICAL: 80
};

// Helper: Get CPU temperature from /sys/class/thermal
function getCpuTemp() {
  try {
    const raw = fs.readFileSync('/sys/class/thermal/thermal_zone0/temp', 'utf8');
    return parseFloat(raw.trim()) / 1000; // millidegrees → °C
  } catch (e) {
    return null;
  }
}

// Helper: Get disk usage
function getDiskUsage() {
  try {
    const out = execSync('df / --output=size,used,avail,pcent -B1 | tail -1', { encoding: 'utf8' });
    const parts = out.trim().split(/\s+/);
    if (parts.length < 4) return null;
    
    const total = parseInt(parts[0]) / 1e9;
    const used = parseInt(parts[1]) / 1e9;
    const avail = parseInt(parts[2]) / 1e9;
    const pct = parseInt(parts[3]);

    return {
      total_gb: parseFloat(total.toFixed(1)),
      used_gb: parseFloat(used.toFixed(1)),
      free_gb: parseFloat(avail.toFixed(1)),
      pct: pct
    };
  } catch (e) {
    return null;
  }
}

// Helper: HTTP ping with timeout
function httpPing(url, timeoutMs = 3000) {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const timeoutHandle = setTimeout(() => {
      resolve({ status: 'timeout', response_ms: timeoutMs });
    }, timeoutMs);

    http.get(url, { timeout: timeoutMs }, (res) => {
      clearTimeout(timeoutHandle);
      const elapsed = Date.now() - startTime;
      const status = res.statusCode === 200 ? 'running' : 'error';
      resolve({ status, response_ms: elapsed, statusCode: res.statusCode });
    }).on('error', () => {
      clearTimeout(timeoutHandle);
      resolve({ status: 'down', response_ms: Date.now() - startTime });
    });
  });
}

// TOOL 1: get_system_health
async function getSystemHealth() {
  try {
    const cpuTemp = getCpuTemp();
    const diskUsage = getDiskUsage();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;
    const ramUsagePct = (usedMem / totalMem) * 100;
    
    // CPU usage from load average
    const cpus = os.cpus();
    const loadAvg = os.loadavg()[0];
    const cpuUsagePct = Math.min(100, (loadAvg / cpus.length) * 100);

    const alerts = [];
    let status = 'healthy';

    if (cpuUsagePct > THRESHOLDS.CPU_CRITICAL) {
      alerts.push(`CRITICAL — CPU ${cpuUsagePct.toFixed(1)}%`);
      status = 'critical';
    } else if (cpuUsagePct > THRESHOLDS.CPU_WARNING) {
      alerts.push(`WARNING — CPU ${cpuUsagePct.toFixed(1)}%`);
      status = 'warning';
    }

    if (ramUsagePct > THRESHOLDS.RAM_CRITICAL) {
      alerts.push(`CRITICAL — RAM ${ramUsagePct.toFixed(1)}%`);
      status = 'critical';
    } else if (ramUsagePct > THRESHOLDS.RAM_WARNING) {
      alerts.push(`WARNING — RAM ${ramUsagePct.toFixed(1)}%`);
      status = 'warning';
    }

    if (diskUsage) {
      if (diskUsage.pct > THRESHOLDS.DISK_CRITICAL) {
        alerts.push(`CRITICAL — Disk ${diskUsage.pct}%`);
        status = 'critical';
      } else if (diskUsage.pct > THRESHOLDS.DISK_WARNING) {
        alerts.push(`WARNING — Disk ${diskUsage.pct}%`);
        status = 'warning';
      }
    }

    if (cpuTemp) {
      if (cpuTemp > THRESHOLDS.TEMP_CRITICAL) {
        alerts.push(`CRITICAL — Temp ${cpuTemp.toFixed(1)}°C`);
        status = 'critical';
      } else if (cpuTemp > THRESHOLDS.TEMP_WARNING) {
        alerts.push(`WARNING — Temp ${cpuTemp.toFixed(1)}°C`);
        status = 'warning';
      }
    }

    return {
      cpu_usage_pct: parseFloat(cpuUsagePct.toFixed(1)),
      ram_total_mb: Math.round(totalMem / 1e6),
      ram_used_mb: Math.round(usedMem / 1e6),
      ram_free_mb: Math.round(freeMem / 1e6),
      ram_usage_pct: parseFloat(ramUsagePct.toFixed(1)),
      disk_total_gb: diskUsage ? diskUsage.total_gb : null,
      disk_used_gb: diskUsage ? diskUsage.used_gb : null,
      disk_free_gb: diskUsage ? diskUsage.free_gb : null,
      disk_usage_pct: diskUsage ? diskUsage.pct : null,
      cpu_temp_c: cpuTemp ? parseFloat(cpuTemp.toFixed(1)) : null,
      uptime_hours: parseFloat((os.uptime() / 3600).toFixed(2)),
      load_avg_1m: parseFloat(os.loadavg()[0].toFixed(2)),
      load_avg_5m: parseFloat(os.loadavg()[1].toFixed(2)),
      load_avg_15m: parseFloat(os.loadavg()[2].toFixed(2)),
      status,
      alerts
    };
  } catch (err) {
    return { error: err.message };
  }
}

// TOOL 2: get_services_status
async function getServicesStatus() {
  try {
    const services = {
      signalk: { port: 3000, url: 'http://localhost:3000/signalk/v1/api' },
      influxdb: { port: 8086, url: 'http://localhost:8086/health' },
      grafana: { port: 3001, url: 'http://localhost:3001/api/health' },
      regatta: { port: 5000, url: 'http://localhost:5000/' },
      portal: { port: 8888, url: 'http://localhost:8888/' }
    };

    const results = {};
    const downServices = [];
    
    for (const [name, config] of Object.entries(services)) {
      const result = await httpPing(config.url);
      results[name] = {
        status: result.status,
        response_ms: result.response_ms,
        port: config.port
      };
      if (result.status !== 'running') {
        downServices.push(name);
      }
    }

    const allHealthy = downServices.length === 0;
    const summary = allHealthy
      ? 'All 5 services operational ✅'
      : `⚠️ ${downServices.length} service(s) down: ${downServices.join(', ')}`;

    return {
      services: results,
      all_healthy: allHealthy,
      down_services: downServices,
      summary
    };
  } catch (err) {
    return { error: err.message };
  }
}

// TOOL 3: get_network_status
async function getNetworkStatus() {
  try {
    // Get hostname
    let hostname = 'unknown';
    try {
      hostname = execSync('hostname', { encoding: 'utf8' }).trim();
    } catch (e) {
      // fallback
    }

    // Get local IPs
    const interfaces = os.networkInterfaces();
    const ips = [];
    let primaryIp = null;

    for (const [ifname, addrs] of Object.entries(interfaces)) {
      for (const addr of addrs) {
        if (addr.family === 'IPv4' && !addr.internal) {
          ips.push(addr.address);
          if (!primaryIp) primaryIp = addr.address;
        }
      }
    }

    const ifaceData = {};
    for (const [ifname, addrs] of Object.entries(interfaces)) {
      for (const addr of addrs) {
        if (addr.family === 'IPv4' && !addr.internal) {
          ifaceData[ifname] = { ip: addr.address, mac: addr.mac };
        }
      }
    }

    const primaryIpStr = primaryIp || '192.168.1.131';

    return {
      hostname,
      local_ips: ips,
      primary_ip: primaryIpStr,
      interfaces: ifaceData,
      mdns_hostname: 'midnightrider.local',
      portal_url: `http://${primaryIpStr}:8888`,
      regatta_url: `http://${primaryIpStr}:8888/regatta/`,
      grafana_url: `http://${primaryIpStr}:3001`,
      signalk_url: `http://${primaryIpStr}:3000`
    };
  } catch (err) {
    return { error: err.message };
  }
}

// TOOL 4: get_performance_metrics
async function getPerformanceMetrics() {
  try {
    const cpus = os.cpus();
    const cpuTemp = getCpuTemp();
    const loadAvg = os.loadavg();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();

    const performanceNote = loadAvg[0] > cpus.length
      ? 'System under heavy load'
      : loadAvg[0] > cpus.length * 0.75
      ? 'System busy'
      : 'System idle';

    return {
      current_cpu_temp_c: cpuTemp ? parseFloat(cpuTemp.toFixed(1)) : null,
      current_load: parseFloat(loadAvg[0].toFixed(2)),
      cores: cpus.length,
      load_per_core: parseFloat((loadAvg[0] / cpus.length).toFixed(2)),
      node_version: process.version,
      platform: 'linux',
      arch: os.arch(),
      total_memory_gb: parseFloat((totalMem / 1e9).toFixed(2)),
      free_memory_gb: parseFloat((freeMem / 1e9).toFixed(2)),
      process_uptime_h: parseFloat((process.uptime() / 3600).toFixed(2)),
      rpi_uptime_h: parseFloat((os.uptime() / 3600).toFixed(2)),
      performance_note: performanceNote
    };
  } catch (err) {
    return { error: err.message };
  }
}

// TOOL 5: get_system_summary
async function getSystemSummary() {
  try {
    const health = await getSystemHealth();
    const services = await getServicesStatus();
    const network = await getNetworkStatus();

    const runningServices = 5 - services.down_services.length;
    const summaryLine = `RPi 4: ${health.cpu_usage_pct.toFixed(0)}% CPU · ` +
      `${health.ram_usage_pct.toFixed(0)}% RAM · ` +
      `${health.disk_usage_pct || '?'}% disk · ` +
      `${health.cpu_temp_c || '?'}°C · ` +
      `${runningServices}/5 services ` +
      (services.all_healthy ? '✅' : '⚠️');

    const reporterNote = `Système de navigation opérationnel. ` +
      `CPU à ${health.cpu_usage_pct.toFixed(0)}%, mémoire à ${health.ram_usage_pct.toFixed(0)}%. ` +
      `Température ${health.cpu_temp_c?.toFixed(0) || '?'}°C — ` +
      (health.cpu_temp_c && health.cpu_temp_c < THRESHOLDS.TEMP_WARNING ? 'dans les normes' : 'élevée') +
      `. Les ${runningServices} services actifs. ` +
      `Autonomie système : illimitée (alimentation AC).`;

    return {
      all_operational: health.status === 'healthy' && services.all_healthy,
      summary_line: summaryLine,
      reporter_note: reporterNote,
      health_status: health.status,
      services_running: runningServices,
      alerts: health.alerts
    };
  } catch (err) {
    return { error: err.message };
  }
}

// MCP Tool definitions
const TOOLS = [
  {
    name: 'get_system_health',
    description: 'Get Raspberry Pi system health (CPU%, RAM%, disk%, temperature, uptime)',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_services_status',
    description: 'Check all 5 services status via HTTP ping (Signal K, InfluxDB, Grafana, Regatta, Portal)',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_network_status',
    description: 'Get network configuration (IP, hostname, URLs, interfaces)',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_performance_metrics',
    description: 'Get system performance metrics (load average, memory, CPU info)',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_system_summary',
    description: 'Get system status as narrative for Midnight Reporter',
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
    case 'get_system_health':
      return await getSystemHealth();
    case 'get_services_status':
      return await getServicesStatus();
    case 'get_network_status':
      return await getNetworkStatus();
    case 'get_performance_metrics':
      return await getPerformanceMetrics();
    case 'get_system_summary':
      return await getSystemSummary();
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
          name: 'system-server',
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
