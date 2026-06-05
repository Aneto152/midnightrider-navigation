'use strict';

module.exports = function(app) {

  let listener = null;

  const plugin = {
    id: 'signalk-um982-gnss',
    name: 'UM982 Dual-Antenna GNSS',
    description: 'Position, SOG, COG, true heading and attitude from Unicore UM982',
    schema: {
      type: 'object',
      properties: {
        reverseHeading: { type: 'boolean', title: 'Reverse heading', default: false },
        rollOffset: { type: 'number', title: 'Roll offset (deg)', default: 0 },
        pitchOffset: { type: 'number', title: 'Pitch offset (deg)', default: 0 },
        reverseRoll: { type: 'boolean', title: 'Reverse roll', default: true },
        reversePitch: { type: 'boolean', title: 'Reverse pitch', default: false }
      }
    }
  };

  plugin.start = function(options) {
    const cfg = Object.assign({
      reverseHeading: false, rollOffset: 0, pitchOffset: 0,
      reverseRoll: true, reversePitch: false
    }, options || {});

    app.setPluginStatus('Listening for UM982 NMEA sentences...');

    listener = function(sentence) {
      if (!sentence) return;
      try {
        const L = sentence.trim();
        if (L.startsWith('$GNGGA') || L.startsWith('$GPGGA')) handleGGA(L);
        else if (L.startsWith('$GNRMC') || L.startsWith('$GPRMC')) handleRMC(L);
        else if (L.startsWith('#UNIHEADINGA')) handleUNIHEADING(L, cfg);
        else if (L.startsWith('#HEADINGA')) handleHEADINGA(L, cfg);
      } catch(e) {
        app.debug('UM982 parse error: ' + e.message);
      }
    };

    app.on('nmea0183out', listener);
  };

  plugin.stop = function() {
    if (listener) { app.removeListener('nmea0183out', listener); listener = null; }
  };

  function toRad(deg) { return deg * Math.PI / 180; }

  function fields(line) { return line.split('*')[0].split(','); }

  function postSemi(line) {
    const si = line.indexOf(';');
    if (si < 0) return null;
    return line.substring(si + 1).split('*')[0].split(',');
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

  function send(values) {
    app.handleMessage(plugin.id, {
      updates: [{ source: { label: 'um982-gnss', type: 'GNSS' }, timestamp: new Date().toISOString(), values }]
    });
  }

  function handleGGA(line) {
    const f = fields(line);
    if (f.length < 10 || f[6] === '0' || !f[6]) return;
    const lat = parseLatLon(f[2], f[3]);
    const lon = parseLatLon(f[4], f[5]);
    if (isNaN(lat) || isNaN(lon)) return;
    const pos = { latitude: lat, longitude: lon };
    const alt = parseFloat(f[9]);
    if (!isNaN(alt)) pos.altitude = alt;
    send([{ path: 'navigation.position', value: pos }]);
    app.setPluginStatus('Pos: ' + lat.toFixed(4) + ' ' + lon.toFixed(4));
  }

  function handleRMC(line) {
    const f = fields(line);
    if (f.length < 9 || f[2] !== 'A') return;
    const vals = [];
    const lat = parseLatLon(f[3], f[4]);
    const lon = parseLatLon(f[5], f[6]);
    if (!isNaN(lat) && !isNaN(lon))
      vals.push({ path: 'navigation.position', value: { latitude: lat, longitude: lon } });
    const sog = parseFloat(f[7]);
    if (!isNaN(sog)) vals.push({ path: 'navigation.speedOverGround', value: sog * 0.514444 });
    const cog = parseFloat(f[8]);
    if (!isNaN(cog)) vals.push({ path: 'navigation.courseOverGroundTrue', value: toRad(cog) });
    if (vals.length) send(vals);
  }

  function handleUNIHEADING(line, cfg) {
    const data = postSemi(line);
    if (!data || data.length < 4) return;
    const hdgRaw = parseFloat(data[3]);
    if (isNaN(hdgRaw)) return;
    let hdg = hdgRaw;
    if (cfg.reverseHeading) hdg = (hdg + 180) % 360;
    app.setPluginStatus('Hdg: ' + hdg.toFixed(1) + 'T [' + (data[0] || '?') + ']');
    send([{ path: 'navigation.headingTrue', value: toRad(hdg) }]);
  }

  function handleHEADINGA(line, cfg) {
    const data = postSemi(line);
    if (!data || data.length < 5) return;
    let roll = parseFloat(data[2]);
    let pitch = parseFloat(data[3]);
    if (isNaN(roll) || isNaN(pitch)) return;
    if (cfg.reverseRoll) roll = -roll;
    if (cfg.reversePitch) pitch = -pitch;
    roll += cfg.rollOffset || 0;
    pitch += cfg.pitchOffset || 0;
    send([
      { path: 'navigation.attitude.roll', value: toRad(roll) },
      { path: 'navigation.attitude.pitch', value: toRad(pitch) }
    ]);
  }

  return plugin;
};
