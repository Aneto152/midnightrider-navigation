'use strict';
const http = require('http');

const URL_STR = process.env.INFLUX_URL || 'http://localhost:8086';
const TOKEN = process.env.INFLUX_TOKEN || '';
const ORG = process.env.INFLUX_ORG || 'MidnightRider';
const BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider';

function getHost() { try { return new URL(URL_STR).hostname; } catch { return 'localhost'; } }
function getPort() { try { return parseInt(new URL(URL_STR).port) || 8086; } catch { return 8086; } }

function queryInflux(fluxQuery) {
  const body = Buffer.from(fluxQuery);
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: getHost(), port: getPort(),
      path: '/api/v2/query?org=' + encodeURIComponent(ORG),
      method: 'POST',
      headers: {
        'Authorization': 'Token ' + TOKEN,
        'Content-Type': 'application/vnd.flux',
        'Content-Length': body.length,
      },
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        if (res.statusCode === 200) resolve(data);
        else reject(new Error('InfluxDB ' + res.statusCode));
      });
    });
    req.on('error', reject);
    req.setTimeout(10000, () => req.destroy(new Error('Timeout')));
    req.write(body);
    req.end();
  });
}

module.exports = { queryInflux, BUCKET, ORG };
