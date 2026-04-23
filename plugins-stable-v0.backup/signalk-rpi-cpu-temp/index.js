/**
 * Signal K Plugin: Raspberry Pi CPU Temperature Monitor
 * Simple version - reads CPU temp and publishes to Signal K
 */

const { execSync } = require('child_process');

module.exports = function(app) {
  let plugin = {
    id: 'signalk-rpi-cpu-temp',
    name: 'RPi CPU Temperature',
    schema: {
      type: 'object',
      properties: {
        enabled: { type: 'boolean', default: true },
        updateInterval: { type: 'number', default: 10, minimum: 5, maximum: 60 }
      }
    },
    started: false,
    interval: null
  };

  plugin.start = function(opts) {
    try {
      opts = opts || {};
      const updateInterval = ((opts && opts.updateInterval) || 10) * 1000;

      app.debug('CPU Temp: Starting');
      app.setPluginStatus('Running');

      // Poll temperature
      const poll = () => {
        try {
          let tempC = null;
          
          // Try vcgencmd
          try {
            const output = execSync('vcgencmd measure_temp', { encoding: 'utf8', timeout: 2000 });
            const match = output.match(/temp=([\d.]+)/);
            if (match) tempC = parseFloat(match[1]);
          } catch (e) {
            // Try sysfs
            try {
              const sysfs = execSync('cat /sys/class/thermal/thermal_zone0/temp', { encoding: 'utf8', timeout: 2000 });
              tempC = parseInt(sysfs) / 1000;
            } catch (e2) {
              app.debug('Could not read CPU temp');
              return;
            }
          }

          if (tempC !== null) {
            const delta = {
              context: 'vessels.self',
              source: { label: 'signalk-rpi-cpu-temp' },
              timestamp: new Date().toISOString(),
              updates: [{
                source: { label: 'signalk-rpi-cpu-temp' },
                timestamp: new Date().toISOString(),
                values: [
                  { path: 'environment.system.cpuTemperature', value: tempC }
                ]
              }]
            };
            app.handleMessage('signalk-rpi-cpu-temp', delta);
          }
        } catch (e) {
          app.debug(`CPU Temp poll error: ${e.message}`);
        }
      };

      // Start polling
      poll(); // First read immediately
      plugin.interval = setInterval(poll, updateInterval);
      plugin.started = true;

    } catch (e) {
      app.setPluginStatus(`Error: ${e.message}`);
      app.debug(`CPU Temp error: ${e.message}`);
    }
  };

  plugin.stop = function() {
    if (plugin.interval) clearInterval(plugin.interval);
    plugin.started = false;
    app.setPluginStatus('Stopped');
  };

  return plugin;
};
