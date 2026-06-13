'use strict';

/**
 * signalk-um982-gnss V2 — Unified UM982 Direct Serial Plugin
 * Opens /dev/ttyUM982 directly, parses $GNGGA, $GNRMC, #HEADINGA
 * Single source: um982-gnss
 * @version 2.0.0
 */

const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');
const fs = require('fs');
const path = require('path');

module.exports = function(app) {
  let serialPort = null;
  let parser = null;
  let heartbeatTimer = null;
  let reconnectTimer = null;
  let cfg = {};
  let stats = { gga: 0, rmc: 0, headinga: 0, errors: 0 };
  const LOG_FILE = '/home/pi/midnightrider-navigation/logs/services/um982-gnss.log';

  const plugin = {
    id: 'signalk-um982-gnss',
    name: 'UM982 Unified GNSS V2',
    description: 'Direct serial reader for UM982 — position, headingTrue, attitude',
    schema: {
      type: 'object',
      properties: {
        device: { type: 'string', default: '/dev/ttyUM982' },
        baudrate: { type: 'number', default: 115200 },
        reverseHeading: { type: 'boolean', default: false },
        reverseRoll: { type: 'boolean', default: true },
        reversePitch: { type: 'boolean', default: false },
        rollOffset: { type: 'number', default: 0 },
        pitchOffset: { type: 'number', default: 0 }
      }
    }
  };

  function log(level, msg) {
    try {
      const ts = new Date().toISOString();
      fs.appendFileSync(LOG_FILE, `[${ts}] [${level}] [um982-gnss] ${msg}\n`);
    } catch(e) { app.debug('[um982-gnss] log error: ' + e.message); }
  }

  function toRad(deg) { return deg * Math.PI / 180; }

  function send(values) {
    app.handleMessage(plugin.id, {
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
        if (f.length >= 10 && f[6] && f[6] !== '0') {
          const lat = parseLatLon(f[2], f[3]);
          const lon = parseLatLon(f[4], f[5]);
          if (!isNaN(lat) && !isNaN(lon)) {
            send([{ path: 'navigation.position', value: { latitude: lat, longitude: lon } }]);
            stats.gga++;
          }
        }
      } else if (line.startsWith('$GNRMC') || line.startsWith('$GPRMC')) {
        const f = line.split('*')[0].split(',');
        if (f.length >= 9 && f[2] === 'A') {
          const vals = [];
          const lat = parseLatLon(f[3], f[4]);
          const lon = parseLatLon(f[5], f[6]);
          if (!isNaN(lat) && !isNaN(lon))
            vals.push({ path: 'navigation.position', value: { latitude: lat, longitude: lon } });
          const sog = parseFloat(f[7]);
          if (!isNaN(sog)) vals.push({ path: 'navigation.speedOverGround', value: sog * 0.514444 });
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
          const pitch = parseFloat(data[3]);
          const hdg = parseFloat(data[4]);
          if (!isNaN(hdg) && !isNaN(roll) && !isNaN(pitch)) {
            const hdgFinal = cfg.reverseHeading ? (hdg + 180) % 360 : hdg;
            const rollFinal = cfg.reverseRoll ? -roll : roll;
            const pitchNorm = pitch > 180 ? pitch - 360 : pitch;
            const pitchFinal = cfg.reversePitch ? -pitchNorm : pitchNorm;
            send([
              { path: 'navigation.headingTrue', value: toRad(hdgFinal) },
              { path: 'navigation.attitude.roll', value: toRad(rollFinal) },
              { path: 'navigation.attitude.pitch', value: toRad(pitchFinal) }
            ]);
            stats.headinga++;
          }
        }
      }
    } catch(e) {
      stats.errors++;
      log('ERROR', `Parse: "${line.substring(0,40)}" — ${e.message}`);
    }
  }

  function openPort() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    try {
      serialPort = new SerialPort({ path: cfg.device, baudRate: cfg.baudrate, autoOpen: false });
      parser = serialPort.pipe(new ReadlineParser({ delimiter: '\r\n' }));
      
      serialPort.on('open', () => {
        log('INFO', `OPEN: ${cfg.device} @ ${cfg.baudrate} baud`);
        app.setPluginStatus('UM982 connected');
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

  plugin.start = function(options) {
    cfg = Object.assign({ device: '/dev/ttyUM982', baudrate: 115200, reverseHeading: false, reverseRoll: true, reversePitch: false, rollOffset: 0, pitchOffset: 0 }, options || {});
    log('INFO', `STARTUP: V2 plugin — device=${cfg.device} baud=${cfg.baudrate}`);
    app.setPluginStatus('Initializing...');
    openPort();
  };

  plugin.stop = function() {
    log('INFO', 'SHUTDOWN: Closing port');
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (serialPort && serialPort.isOpen) serialPort.close();
  };

  return plugin;
};
