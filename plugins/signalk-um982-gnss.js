'use strict';

/**
 * signalk-um982-gnss V2.2 — CRITICAL FIELD MAPPING CORRECTION
 *
 * VERIFIED by Dust analysis 2026-06-13:
 * WRONG (V2.0/V2.1) → CORRECT (V2.2):
 * data[2] = roll° → data[2] = antennaBaseline meters (~2.85m)
 * data[3] = ignored → data[3] = heading baseline azimuth
 * data[4] = headingTrue → data[4] = roll (elevation angle)
 * data[6] = antennaBaseline → data[6] = NOT published (std_dev)
 *
 * Physical basis: athwartships mount
 * baseline_azimuth = boat_heading + 90° (port=primary, starboard=secondary)
 * boat_heading = baseline_azimuth - 90°
 * elevation ≈ 0° for horizontal baseline = heel angle
 *
 * @version 2.2.0
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
    } catch(e) { app.debug('[um982-gnss] log: ' + e.message); }
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
    const r = deg + (raw - deg * 100) / 60;
    return (dir === 'S' || dir === 'W') ? -r : r;
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
            vals.push({ path: 'navigation.gnss.methodQuality', value: GGA_QUALITY[f[6]] || 'GNSS Fix' });
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
          const magVar = parseFloat(f[10]);
          if (!isNaN(magVar) && f[10] !== '')
            vals.push({ path: 'navigation.magneticVariation', value: toRad(f[11] === 'W' ? -magVar : magVar) });
          if (f[1] && f[9] && f[1].length >= 6 && f[9].length === 6) {
            try {
              const iso = `20${f[9].substring(4,6)}-${f[9].substring(2,4)}-${f[9].substring(0,2)}T${f[1].substring(0,2)}:${f[1].substring(2,4)}:${f[1].substring(4,6)}Z`;
              vals.push({ path: 'navigation.datetime', value: iso });
            } catch(e) {}
          }
          if (vals.length) { send(vals); stats.rmc++; }
        }
      } else if (line.startsWith('#HEADINGA')) {
        const si = line.indexOf(';');
        if (si < 0) return;
        const data = line.substring(si + 1).split('*')[0].split(',');
        if (data.length < 7) return;

        const solStatus = data[0];
        if (solStatus === 'INSUFFICIENT_OBS' || solStatus === 'NONE' || 
            solStatus === 'COLD_START' || solStatus === 'NO_CONVERGENCE') return;

        // V2.2 CORRECTED FIELD MAPPING:
        const baseline = parseFloat(data[2]); // meters — antenna separation (was wrongly roll)
        const baselineAz = parseFloat(data[3]); // degrees — heading of baseline (was suppressed)
        const baselineElev = parseFloat(data[4]); // degrees — elevation = roll (was published as headingTrue)

        if (isNaN(baselineAz) || isNaN(baselineElev)) return;

        // Boat heading = baseline azimuth - antenna offset
        // Default offset=90° for port-primary athwartships mount
        let hdg = ((baselineAz - cfg.antennaOffset) + 360) % 360;
        if (cfg.reverseHeading) hdg = (hdg + 180) % 360;

        // Roll = elevation of baseline (= heel for athwartships)
        let roll = cfg.reverseRoll ? -baselineElev : baselineElev;
        roll += (cfg.rollOffset || 0);

        const vals = [
          { path: 'navigation.headingTrue', value: toRad(hdg) },
          { path: 'navigation.attitude.roll', value: toRad(roll) }
        ];

        if (!isNaN(baseline) && baseline > 0.5) {
          vals.push({ path: 'navigation.gnss.antennaBaseline', value: baseline });
        }

        send(vals);
        stats.headinga++;
        lastHdg = hdg.toFixed(1) + '°T';

        if (stats.headinga % 25 === 1) {
          log('INFO', `DATA_IN: HEADINGA — baselineAz=${baselineAz.toFixed(2)}° → hdg=${hdg.toFixed(2)}° elev=${baselineElev.toFixed(2)}° → roll=${roll.toFixed(2)}° baseline=${baseline.toFixed(3)}m sol=${solStatus}`);
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
        log('INFO', `STARTUP: Port OPEN — ${cfg.device} @ ${cfg.baudrate}`);
        app.setPluginStatus('UM982 V2.2 connected');
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
    name: 'UM982 V2.2 (corrected field mapping)',
    description: 'V2.2: data[2]=baseline(m), data[3]=heading, data[4]=roll(elevation). Athwartships antennas.',
    schema: {
      type: 'object',
      properties: {
        device: { type: 'string', default: '/dev/ttyUM982' },
        baudrate: { type: 'number', default: 115200 },
        antennaOffset: { type: 'number', title: 'Antenna offset degrees (default 90)', default: 90 },
        reverseHeading: { type: 'boolean', default: false },
        reverseRoll: { type: 'boolean', default: false },
        rollOffset: { type: 'number', default: 0 }
      }
    }
  };

  plugin.start = function(options) {
    cfg = Object.assign({ device: '/dev/ttyUM982', baudrate: 115200, antennaOffset: 90, reverseHeading: false, reverseRoll: false, rollOffset: 0 }, options || {});
    log('INFO', `STARTUP V2.2: antennaOffset=${cfg.antennaOffset}° reverseHdg=${cfg.reverseHeading} reverseRoll=${cfg.reverseRoll}`);
    app.setPluginStatus('Initializing...');
    openPort();
  };

  plugin.stop = function() {
    log('INFO', 'SHUTDOWN');
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (serialPort && serialPort.isOpen) serialPort.close();
  };

  return plugin;
};
