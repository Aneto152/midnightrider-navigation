/**
 * Signal K Plugin: WIT WT901BLECL IMU USB Reader
 * Reads 9-axis IMU data directly and sends via app.handleMessage()
 */

const SerialPort = require('serialport').SerialPort;

module.exports = function(app) {
  let plugin = {
    id: 'signalk-wit-imu-usb',
    name: 'WIT IMU USB Reader',
    schema: {
      type: 'object',
      title: 'WIT WT901BLECL IMU Configuration',
      properties: {
        enabled: {
          type: 'boolean',
          title: 'Enable WIT IMU Reader',
          default: true
        },
        usbPort: {
          type: 'string',
          title: 'USB Port',
          default: '/dev/ttyUSB0'
        },
        baudRate: {
          type: 'number',
          title: 'Baud Rate',
          default: 115200,
          enum: [9600, 19200, 38400, 57600, 115200]
        },
        filterAlpha: {
          type: 'number',
          title: 'Low-Pass Filter (0-1)',
          default: 0.05,
          minimum: 0,
          maximum: 1
        },
        updateRate: {
          type: 'number',
          title: 'Update Rate (Hz)',
          default: 1,
          minimum: 0.1,
          maximum: 10
        },
        calibrationX: { type: 'number', title: 'Accel X Offset (g)', default: 0.0111 },
        calibrationY: { type: 'number', title: 'Accel Y Offset (g)', default: -0.0389 },
        calibrationZ: { type: 'number', title: 'Accel Z Offset (g)', default: 0.0327 },
        gyroOffsetX: { type: 'number', title: 'Gyro X Offset (°/s)', default: 0 },
        gyroOffsetY: { type: 'number', title: 'Gyro Y Offset (°/s)', default: 0 },
        gyroOffsetZ: { type: 'number', title: 'Gyro Z Offset (°/s)', default: 0 },
        angleOffsetRoll: { type: 'number', title: 'Roll Offset (°)', default: -2.1553 },
        angleOffsetPitch: { type: 'number', title: 'Pitch Offset (°)', default: -0.6157 },
        angleOffsetYaw: { type: 'number', title: 'Yaw Offset (°)', default: 69.9939 }
      }
    },
    started: false,
    port: null,
    buffer: Buffer.alloc(0),
    lastUpdate: 0,
    filteredRoll: 0,
    filteredPitch: 0,
    filteredYaw: 0,
    filterInit: false,
    packetCount: 0
  };

  plugin.start = function(opts) {
    try {
      opts = opts || {};
      const usbPort = opts.usbPort || '/dev/ttyUSB0';
      const baudRate = opts.baudRate || 115200;
      const filterAlpha = Math.max(0, Math.min(1, opts.filterAlpha || 0.05));
      const updateRate = opts.updateRate || 1;
      const updateInterval = 1000 / updateRate;

      const calib = {
        accel: [
          opts.calibrationX || 0.0111,
          opts.calibrationY || -0.0389,
          opts.calibrationZ || 0.0327
        ],
        gyro: [
          opts.gyroOffsetX || 0,
          opts.gyroOffsetY || 0,
          opts.gyroOffsetZ || 0
        ],
        angle: [
          opts.angleOffsetRoll || -2.1553,
          opts.angleOffsetPitch || -0.6157,
          opts.angleOffsetYaw || 69.9939
        ]
      };

      app.debug(`WIT IMU: Connecting to ${usbPort}`);
      app.setPluginStatus(`Connecting to ${usbPort}...`);

      plugin.port = new SerialPort({
        path: usbPort,
        baudRate: baudRate,
        autoOpen: false
      });

      plugin.port.on('open', () => {
        app.debug('WIT IMU: USB port opened');
        app.setPluginStatus('Connected');
      });

      plugin.port.on('error', (err) => {
        app.debug(`WIT IMU port error: ${err.message}`);
        app.setPluginStatus(`Error: ${err.message}`);
      });

      plugin.port.on('data', (chunk) => {
        plugin.buffer = Buffer.concat([plugin.buffer, chunk]);
        processBuffer();
      });

      function processBuffer() {
        while (plugin.buffer.length >= 20) {
          if (plugin.buffer[0] === 0x55 && plugin.buffer[1] === 0x61) {
            const packet = plugin.buffer.slice(0, 20);
            plugin.buffer = plugin.buffer.slice(20);
            decodePacket(packet);
          } else {
            plugin.buffer = plugin.buffer.slice(1);
          }
        }
      }

      function read16(buf, offset) {
        let v = (buf[offset + 1] << 8) | buf[offset];
        return v & 0x8000 ? v - 0x10000 : v;
      }

      function decodePacket(packet) {
        try {
          let accel_x = (read16(packet, 2) / 32768) * 16 - calib.accel[0];
          let accel_y = (read16(packet, 4) / 32768) * 16 - calib.accel[1];
          let accel_z = (read16(packet, 6) / 32768) * 16 - calib.accel[2];

          let gyro_x = (read16(packet, 8) / 32768) * 2000 - calib.gyro[0];
          let gyro_y = (read16(packet, 10) / 32768) * 2000 - calib.gyro[1];
          let gyro_z = (read16(packet, 12) / 32768) * 2000 - calib.gyro[2];

          let roll_deg = (read16(packet, 14) / 32768) * 180 - calib.angle[0];
          let pitch_deg = (read16(packet, 16) / 32768) * 180 - calib.angle[1];
          let yaw_deg = (read16(packet, 18) / 32768) * 180 - calib.angle[2];

          if (!plugin.filterInit) {
            plugin.filteredRoll = roll_deg;
            plugin.filteredPitch = pitch_deg;
            plugin.filteredYaw = yaw_deg;
            plugin.filterInit = true;
          } else {
            plugin.filteredRoll = filterAlpha * roll_deg + (1 - filterAlpha) * plugin.filteredRoll;
            plugin.filteredPitch = filterAlpha * pitch_deg + (1 - filterAlpha) * plugin.filteredPitch;
            plugin.filteredYaw = filterAlpha * yaw_deg + (1 - filterAlpha) * plugin.filteredYaw;
          }

          plugin.packetCount++;

          const now = Date.now();
          if (now - plugin.lastUpdate >= updateInterval) {
            plugin.lastUpdate = now;
            sendUpdate(accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z);
          }

        } catch (e) {
          app.debug(`WIT decode error: ${e.message}`);
        }
      }

      function sendUpdate(accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z) {
        try {
          const roll_rad = (plugin.filteredRoll * Math.PI) / 180;
          const pitch_rad = (plugin.filteredPitch * Math.PI) / 180;
          const yaw_rad = (plugin.filteredYaw * Math.PI) / 180;

          const gyro_x_rad = (gyro_x * Math.PI) / 180;
          const gyro_y_rad = (gyro_y * Math.PI) / 180;
          const gyro_z_rad = (gyro_z * Math.PI) / 180;

          const accel_x_ms2 = accel_x * 9.80665;
          const accel_y_ms2 = accel_y * 9.80665;
          const accel_z_ms2 = accel_z * 9.80665;

          const delta = {
            context: 'vessels.self',
            source: { label: 'signalk-wit-imu-usb' },
            timestamp: new Date().toISOString(),
            updates: [{
              source: { label: 'signalk-wit-imu-usb' },
              timestamp: new Date().toISOString(),
              values: [
                { path: 'navigation.attitude.roll', value: roll_rad },
                { path: 'navigation.attitude.pitch', value: pitch_rad },
                { path: 'navigation.attitude.yaw', value: yaw_rad },
                { path: 'navigation.rateOfTurn', value: gyro_z_rad },
                { path: 'navigation.rotation.x', value: gyro_x_rad },
                { path: 'navigation.rotation.y', value: gyro_y_rad },
                { path: 'navigation.rotation.z', value: gyro_z_rad },
                { path: 'navigation.acceleration.x', value: accel_x_ms2 },
                { path: 'navigation.acceleration.y', value: accel_y_ms2 },
                { path: 'navigation.acceleration.z', value: accel_z_ms2 }
              ]
            }]
          };

          app.handleMessage('signalk-wit-imu-usb', delta);

        } catch (e) {
          app.debug(`WIT send error: ${e.message}`);
        }
      }

      plugin.port.open((err) => {
        if (err) {
          app.setPluginStatus(`Failed to open: ${err.message}`);
        }
      });

      plugin.started = true;
      app.setPluginStatus('Running');

    } catch (e) {
      app.setPluginStatus(`Error: ${e.message}`);
      app.debug(`WIT start error: ${e.message}`);
    }
  };

  plugin.stop = function() {
    try {
      if (plugin.port && plugin.port.isOpen) {
        plugin.port.close();
      }
      plugin.started = false;
      app.setPluginStatus(`Stopped (${plugin.packetCount} packets)`);
    } catch (e) {
      app.debug(`WIT stop error: ${e.message}`);
    }
  };

  return plugin;
};
