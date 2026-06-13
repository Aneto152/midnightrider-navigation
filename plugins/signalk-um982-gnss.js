'use strict';

/**
 * signalk-um982-gnss V2.1 — Unified UM982 Direct Serial Plugin
 * 
 * Antenna config: TRANSVERSAL (port ↔ starboard)
 * Publishes: headingTrue, roll (no pitch — athwartships), GPS quality, baseline
 * 
 * V2.1 changes:
 * - Remove navigation.attitude.pitch (meaningless for athwartships mount)
 * - Add GPS quality data: satellites, HDOP, fix quality, altitude
 * - Add magnetic variation + datetime from RMC
 * - Add baseline distance monitoring (antenna separation health check)
 * 
 * @version 2.1.0
 */

const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');
const fs = require('fs');
const path = require('path');

const GGA_QUALITY = {
  '0': 'no GPS', '1': 'GNSS Fix', '2': 'DGNSS fix',
  '3': 'Precise GNSS', '4': 'RTK fixed integer', '5': 'Float RTK',
  '6': 'Estimated (DR) mode', '7': 'Manual input', '8': 'Simulator'
};

module.exports = function(app) {
  let serialPort = null;
  let parser = null;
  let reconnectTimer = null;
  let heartbeatTimer = null;
  let cfg = {};
  let stats = { gga: 0, rmc: 0, headinga: 0, errors: 0 };
  let lastHdg = 'N/A';
  const LOG_FILE = '/home/pi/midnightrider-navigation/logs/services/um982-gnss.log';

  function log(level, msg) {
    try {
      const ts = new Date().toISOString();
      fs.appendFileSync(LOG_FILE, `[${ts}] [${level}] [um982-gnss] ${msg}\n`);
    } catch(e) { app.debug('[um982-gnss] log error: ' + e.message); }
  }

  function toRad(deg) { return deg * Math.PI / 180; }

  function send(values) {
    app.handleMessage('signalk-um982-gnss', {
      updates: [{
        source: { label: 'um982-gnss', type: 'GNSS' },
        timestamp: new Date().toISOString(),
        values
      }]
    });
  }

  function parseLatLon(val, dir) {
    if (!val || val.length < 4) return NaN;
    const raw = parseFloat(val);
    const deg = Math.floor(raw / 100);
    const min = raw - deg * 100;
    let r = deg + min / 60;
    if (dir === 'S' || dir === 'W') r = -r;
    return r;
  }

  function handleLine(line) {
    try {
      if (line.startsWith('$GNGGA') || line.startsWith('$GAGGA') || line.startsWith('$GPGGA')) {
        const f = line.split('*')[0].split(',');
        if (f.length >= 14 && f[6] && f[6] !== '0') {
          const lat = parseLatLon(f[2], f[3]);
          const lon = parseLatLon(f[4], f[5]);
          if (!isNaN(lat) && !isNaN(lon)) {
            const vals = [{ path: 'navigation.position', value: { latitude: lat, longitude: lon } }];
            
            const alt = parseFloat(f[9]);
            if (!isNaN(alt)) vals[0].value.altitude = alt;
            
            const sats = parseInt(f[7], 10);
            if (!isNaN(sats) && sats > 0) vals.push({ path: 'navigation.gnss.satellites', value: sats });
            
            const hdop = parseFloat(f[8]);
            if (!isNaN(hdop)) vals.push({ path: 'navigation.gnss.horizontalDilution', value: hdop });
            
            const qual = GGA_QUALITY[f[6]] || 'GNSS Fix';
            vals.push({ path: 'navigation.gnss.methodQuality', value: qual });
            
            const geoid = parseFloat(f[11]);
            if (!isNaN(geoid)) vals.push({ path: 'navigation.gnss.geoidalSeparation', value: geoid });

            send(vals);
            stats.gga++;
          }
        }
      } else if (line.startsWith('$GNRMC') || line.startsWith('$GPRMC')) {
        const f = line.split('*')[0].split(',');
        if (f.length >= 10 && f[2] === 'A') {
          const vals = [];
          const lat = parseLatLon(f[3], f[4]);
          const lon = parseLatLon(f[5], f[6]);
          if (!isNaN(lat) && !isNaN(lon))
            vals.push({ path: 'navigation.position', value: { latitude: lat, longitude: lon } });
          
          const sog = parseFloat(f[7]);
          if (!isNaN(sog)) vals.push({ path: 'navigation.speedOverGround', value: sog * 0.514444 });
          
          const cog = parseFloat(f[8]);
          if (!isNaN(cog)) vals.push({ path: 'navigation.courseOverGroundTrue', value: toRad(cog) });
          
          // Magnetic variation
          const magVar = parseFloat(f[10]);
          if (!isNaN(magVar) && f[10] !== '') {
            const magVarRad = toRad(f[11] === 'W' ? -magVar : magVar);
            vals.push({ path: 'navigation.magneticVariation', value: magVarRad });
          }
          
          // Datetime from RMC
          if (f[1] && f[9] && f[1].length >= 6 && f[9].length === 6) {
            try {
              const hh = f[1].substring(0,2), mm = f[1].substring(2,4), ss = f[1].substring(4,6);
              const dd = f[9].substring(0,2), mo = f[9].substring(2,4), yy = f[9].substring(4,6);
              const iso = `20${yy}-${mo}-${dd}T${hh}:${mm}:${ss}Z`;
              vals.push({ path: 'navigation.datetime', value: iso });
            } catch(e) { /* ignore date errors */ }
          }

          if (vals.length) {
            send(vals);
            stats.rmc++;
          }
        }
      } else if (line.startsWith('#HEADINGA')) {
        const si = line.indexOf(';');
        if (si < 0) return;
        const data = line.substring(si + 1).split('*')[0].split(',');
        if (data.length >= 7 && data[0] === 'SOL_COMPUTED') {
          const roll = parseFloat(data[2]);
          const hdg = parseFloat(data[4]);
          const baseline = parseFloat(data[6]);
          
          if (!isNaN(hdg) && !isNaN(roll)) {
            const hdgFinal = cfg.reverseHeading ? (hdg + 180) % 360 : hdg;
            const rollFinal = cfg.reverseRoll ? -roll : roll;
            
            const vals = [
              { path: 'navigation.headingTrue', value: toRad(hdgFinal) },
              { path: 'navigation.attitude.roll', value: toRad(rollFinal) }
              // NOTE: navigation.attitude.pitch intentionally omitted (athwartships antennas)
            ];
            
            // Baseline health check
            if (!isNaN(baseline) && baseline > 0.1) {
              vals.push({ path: 'navigation.gnss.antennaBaseline', value: baseline });
            }
            
            send(vals);
            stats.headinga++;
            lastHdg = hdgFinal.toFixed(1) + '°T';
          }
        }
      }
    } catch(e) {
      stats.errors++;
      log('ERROR', `Parse: "${line.substring(0,50)}" — ${e.message}`);
    }
  }

  function openPort() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    try {
      serialPort = new SerialPort({ path: cfg.device, baudRate: cfg.baudrate, autoOpen: false });
      parser = serialPort.pipe(new ReadlineParser({ delimiter: '\r\n' }));
      
      serialPort.on('open', () => {
        log('INFO', `STARTUP: Serial OPEN — ${cfg.device} @ ${cfg.baudrate} baud`);
        app.setPluginStatus('UM982 V2.1 connected (athwartships: no pitch)');
      });

      serialPort.on('error', (err) => {
        log('ERROR', `${err.message}`);
        reconnectTimer = setTimeout(openPort, 10000);
      });

      parser.on('data', handleLine);
      serialPort.open((err) => {
        if (err) {
          log('ERROR', `Cannot open: ${err.message}`);
          reconnectTimer = setTimeout(openPort, 10000);
        }
      });

      // Heartbeat every 5min
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      heartbeatTimer = setInterval(() => {
        log('DEBUG', `HEARTBEAT: GGA=${stats.gga} RMC=${stats.rmc} HEADINGA=${stats.headinga} errors=${stats.errors}`);
        stats = { gga: 0, rmc: 0, headinga: 0, errors: 0 };
      }, 5 * 60 * 1000);

    } catch(e) {
      log('ERROR', `Init: ${e.message}`);
      reconnectTimer = setTimeout(openPort, 10000);
    }
  }

  const plugin = {
    id: 'signalk-um982-gnss',
    name: 'UM982 Dual-Antenna GNSS (V2.1 — athwartships)',
    description: 'Direct serial for UM982 transversal mount. Publishes: headingTrue + roll (no pitch), GPS quality, baseline, magVar, datetime.',
    schema: {
      type: 'object',
      properties: {
        device: { type: 'string', default: '/dev/ttyUM982' },
        baudrate: { type: 'number', default: 115200 },
        reverseHeading: { type: 'boolean', default: false },
        reverseRoll: { type: 'boolean', default: true },
        rollOffset: { type: 'number', default: 0 }
      }
    }
  };

  plugin.start = function(options) {
    cfg = Object.assign({ device: '/dev/ttyUM982', baudrate: 115200, reverseHeading: false, reverseRoll: true, rollOffset: 0 }, options || {});
    log('INFO', `STARTUP: V2.1 — antenna=TRANSVERSAL (port-starboard), pitch=REMOVED`);
    app.setPluginStatus('Initializing...');
    openPort();
  };

  plugin.stop = function() {
    log('INFO', 'SHUTDOWN: Closing');
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (serialPort && serialPort.isOpen) serialPort.close();
  };

  return plugin;
};
