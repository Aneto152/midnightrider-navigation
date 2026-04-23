/**
 * Signal K Plugin: WIT WT901BLECL IMU USB Reader v2.0
 * Added: Acceleration (x,y,z) + Rate of Turn
 * Structure Signal K v2.25 compatible
 *
 * Packet structure (0x55 0x61 - 20 bytes):
 *   Bytes 0-1:    0x55 0x61 (Header)
 *   Bytes 2-3:    Accel X (int16, /32768 × 16g)
 *   Bytes 4-5:    Accel Y (int16, /32768 × 16g)
 *   Bytes 6-7:    Accel Z (int16, /32768 × 16g)
 *   Bytes 8-9:    Gyro X (int16, /32768 × 2000 °/s)
 *   Bytes 10-11:  Gyro Y (int16, /32768 × 2000 °/s)
 *   Bytes 12-13:  Gyro Z (int16, /32768 × 2000 °/s) ← Rate of Turn
 *   Bytes 14-15:  Roll (int16, /32768 × 180°)
 *   Bytes 16-17:  Pitch (int16, /32768 × 180°)
 *   Bytes 18-19:  Yaw (int16, /32768 × 180°)
 */

const SerialPort = require('serialport').SerialPort

module.exports = function(app) {
  const plugin = {}
  let serialPort = null
  let updateInterval = null

  plugin.id = 'signalk-wit-imu-usb'
  plugin.name = 'WIT IMU USB Reader'
  plugin.description = 'WIT WT901BLECL 9-axis IMU USB Reader for Signal K'

  plugin.schema = {
    type: 'object',
    properties: {
      usbPort: {
        type: 'string',
        title: 'USB Port',
        default: '/dev/ttyWIT',
        description: 'Serial port for WIT IMU (e.g., /dev/ttyWIT or /dev/ttyUSB0)'
      },
      baudRate: {
        type: 'number',
        title: 'Baud Rate',
        default: 115200,
        enum: [9600, 19200, 38400, 57600, 115200]
      },
      updateRate: {
        type: 'number',
        title: 'Update Rate (Hz)',
        default: 10,
        minimum: 0.1,
        maximum: 100,
        description: 'Frequency of updates from IMU (Hz)'
      },
      filterAlpha: {
        type: 'number',
        title: 'Low-Pass Filter Alpha (0-1)',
        default: 0.05,
        minimum: 0,
        maximum: 1,
        description: '0 = no filter, 0.5 = medium, 0.01 = heavy smoothing'
      },
      enableAcceleration: {
        type: 'boolean',
        title: 'Enable Acceleration Output',
        default: true,
        description: 'Send acceleration (x,y,z) in m/s²'
      },
      enableRateOfTurn: {
        type: 'boolean',
        title: 'Enable Rate of Turn Output',
        default: true,
        description: 'Send gyro Z-axis (rate of turn) in rad/s'
      },
      
      rollOffset: {
        type: 'number',
        title: 'Roll Offset (degrees)',
        default: 0,
        minimum: -180,
        maximum: 180,
        description: 'Calibration offset for roll angle (applies zero correction)'
      },
      pitchOffset: {
        type: 'number',
        title: 'Pitch Offset (degrees)',
        default: 0,
        minimum: -180,
        maximum: 180,
        description: 'Calibration offset for pitch angle (applies zero correction)'
      },
      yawOffset: {
        type: 'number',
        title: 'Yaw/Heading Offset (degrees)',
        default: 0,
        minimum: -180,
        maximum: 180,
        description: 'Calibration offset for yaw/heading (compass correction)'
      },
      accelXOffset: {
        type: 'number',
        title: 'Accel X Offset (m/s²)',
        default: 0,
        minimum: -20,
        maximum: 20,
        description: 'Zero-point correction for X acceleration'
      },
      accelYOffset: {
        type: 'number',
        title: 'Accel Y Offset (m/s²)',
        default: 0,
        minimum: -20,
        maximum: 20,
        description: 'Zero-point correction for Y acceleration'
      },
      accelZOffset: {
        type: 'number',
        title: 'Accel Z Offset (m/s²)',
        default: 0,
        minimum: -20,
        maximum: 20,
        description: 'Zero-point correction for Z acceleration (usually ±9.81 for gravity)'
      },
      gyroZOffset: {
        type: 'number',
        title: 'Gyro Z Offset (rad/s)',
        default: 0,
        minimum: -0.5,
        maximum: 0.5,
        description: 'Zero-point correction for rate of turn (gyro drift)'
      }
    }
  }

  plugin.start = function(options) {
    options = options || {}
    
    const port = options.usbPort || '/dev/ttyWIT'
    const baudRate = options.baudRate || 115200
    const updateRate = options.updateRate || 8
    
    app.debug(`WIT IMU USB Reader starting on ${port}`)
    app.setPluginStatus(`Connecting to ${port}...`)

    try {
      serialPort = new SerialPort({ 
        path: port, 
        baudRate: baudRate,
        autoOpen: true
      })

      let buffer = Buffer.alloc(0)
      const packetSize = 20
      const updateInterval = 1000 / updateRate

      serialPort.on('open', function() {
        app.debug('WIT IMU serial port opened')
        app.setPluginStatus('Connected')
      })

      serialPort.on('data', function(chunk) {
        buffer = Buffer.concat([buffer, chunk])

        // Look for WIT packet header (0x55 0x61 = full 9-axis data)
        while (buffer.length >= packetSize) {
          if (buffer[0] === 0x55 && buffer[1] === 0x61) {
            const packet = buffer.slice(0, packetSize)
            buffer = buffer.slice(packetSize)

            try {
              // Decode WIT packet (20 bytes, 0x55 0x61 format)
              
              // ACCELERATION (int16, /32768 × 16g)
              const accelXRaw = packet.readInt16LE(2)   // Offset 2
              const accelYRaw = packet.readInt16LE(4)   // Offset 4
              const accelZRaw = packet.readInt16LE(6)   // Offset 6
              
              let accelX = (accelXRaw / 32768) * 16 * 9.81  // Convert g to m/s²
              let accelY = (accelYRaw / 32768) * 16 * 9.81
              let accelZ = (accelZRaw / 32768) * 16 * 9.81
              
              // Apply acceleration offsets (calibration correction)
              accelX -= (options.accelXOffset || 0)
              accelY -= (options.accelYOffset || 0)
              accelZ -= (options.accelZOffset || 0)
              
              // GYROSCOPE (int16, /32768 × 2000 °/s)
              const gyroZRaw = packet.readInt16LE(12)   // Z-axis (Rate of Turn) at offset 12
              
              let gyroZ = (gyroZRaw / 32768) * (2000 * Math.PI / 180)  // Convert °/s to rad/s
              
              // Apply gyro offset (drift correction)
              gyroZ -= (options.gyroZOffset || 0)
              
              // ATTITUDE/ANGLES (int16, /32768 × 180°)
              const rollRaw = packet.readInt16LE(14)    // Roll at offset 14
              const pitchRaw = packet.readInt16LE(16)   // Pitch at offset 16
              const yawRaw = packet.readInt16LE(18)     // Yaw at offset 18

              // Convert to radians (WT901BLECL: ±180°)
              // Scale: 32768 = ±180°
              let roll = (rollRaw / 32768) * Math.PI
              let pitch = (pitchRaw / 32768) * Math.PI
              let yaw = (yawRaw / 32768) * Math.PI
              
              // Apply angle offsets (calibration correction in degrees → radians)
              roll -= (options.rollOffset || 0) * Math.PI / 180
              pitch -= (options.pitchOffset || 0) * Math.PI / 180
              yaw -= (options.yawOffset || 0) * Math.PI / 180

              // Build values array
              const values = [
                { path: 'navigation.attitude.roll', value: roll },
                { path: 'navigation.attitude.pitch', value: pitch },
                { path: 'navigation.attitude.yaw', value: yaw }
              ]
              
              // Add acceleration if enabled
              if (options.enableAcceleration !== false) {
                values.push(
                  { path: 'navigation.acceleration.x', value: accelX },
                  { path: 'navigation.acceleration.y', value: accelY },
                  { path: 'navigation.acceleration.z', value: accelZ }
                )
              }
              
              // Add rate of turn if enabled
              if (options.enableRateOfTurn !== false) {
                values.push(
                  { path: 'navigation.rateOfTurn', value: gyroZ }
                )
              }

              // Send delta to Signal K
              app.handleMessage(plugin.id, {
                context: 'vessels.' + app.selfId,
                updates: [{
                  source: { label: plugin.id },
                  timestamp: new Date().toISOString(),
                  values: values
                }]
              })

              app.debug(`WIT: Roll=${(roll * 180 / Math.PI).toFixed(2)}° Pitch=${(pitch * 180 / Math.PI).toFixed(2)}° ROT=${gyroZ.toFixed(3)}rad/s Accel=${accelX.toFixed(2)}/${accelY.toFixed(2)}/${accelZ.toFixed(2)}m/s²`)

            } catch (e) {
              app.debug(`WIT packet decode error: ${e.message}`)
            }
          } else {
            // Skip invalid byte and look for next header
            buffer = buffer.slice(1)
          }
        }
      })

      serialPort.on('error', function(err) {
        app.setPluginStatus(`Error: ${err.message}`)
        app.debug(`WIT IMU serial port error: ${err.message}`)
      })

      serialPort.on('close', function() {
        app.debug('WIT IMU serial port closed')
        app.setPluginStatus('Disconnected')
      })

    } catch (e) {
      app.setPluginStatus(`Failed: ${e.message}`)
      app.debug(`WIT IMU plugin error: ${e.message}`)
    }
  }

  plugin.stop = function() {
    app.debug('WIT IMU USB Reader stopping')
    
    if (serialPort && serialPort.isOpen) {
      serialPort.close()
    }
    
    app.setPluginStatus('Stopped')
  }

  return plugin
}
