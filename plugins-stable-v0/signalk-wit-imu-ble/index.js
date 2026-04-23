/**
 * Signal K Plugin: WIT WT901BLECL IMU Bluetooth Reader v2.0 BLE
 * Added: Acceleration (x,y,z) + Rate of Turn
 * Structure Signal K v2.25 compatible
 * Connection: Bluetooth Low Energy (BLE) instead of USB
 * Backend: Native Linux gatttool / hcitool (no npm dependencies)
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

const { spawn } = require('child_process')
const { EventEmitter } = require('events')

module.exports = function(app) {
  const plugin = {}
  let bleProcess = null
  let buffer = Buffer.alloc(0)
  let isConnected = false

  plugin.id = 'signalk-wit-imu-ble'
  plugin.name = 'WIT IMU Bluetooth Reader'
  plugin.description = 'WIT WT901BLECL 9-axis IMU Bluetooth LE Reader for Signal K (native gatttool)'

  plugin.schema = {
    type: 'object',
    properties: {
      bleAddress: {
        type: 'string',
        title: 'Bluetooth MAC Address',
        default: 'E9:10:DB:8B:CE:C7',
        description: 'MAC address of WIT WT901BLECL device'
      },
      bleName: {
        type: 'string',
        title: 'Bluetooth Device Name',
        default: 'WT901BLE68',
        description: 'Name of WIT device (for reference only)'
      },
      characteristicHandle: {
        type: 'string',
        title: 'Characteristic Handle',
        default: '0x0030',
        description: 'GATT characteristic handle for data notifications (find with gatttool)'
      },
      autoReconnect: {
        type: 'boolean',
        title: 'Auto Reconnect',
        default: true,
        description: 'Automatically reconnect if device disconnects'
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
    
    const bleAddress = (options.bleAddress || 'E9:10:DB:8B:CE:C7').toUpperCase()
    const bleName = options.bleName || 'WT901BLE68'
    const charHandle = options.characteristicHandle || '0x0030'
    const autoReconnect = options.autoReconnect !== false
    
    app.debug(`WIT IMU BLE Reader starting - ${bleAddress} (${bleName})`)
    app.setPluginStatus(`Connecting to ${bleName}...`)

    const packetSize = 20

    const connectBLE = function() {
      try {
        // Use gatttool to listen for notifications
        // gatttool -b <address> -i hci0 --char-read-uuid
        // But for continuous listening, we use a persistent connection with gattool
        
        app.debug(`Starting gatttool for ${bleAddress}`)
        
        bleProcess = spawn('timeout', ['300', 'gatttool', '-b', bleAddress, '-I'], {
          stdio: ['pipe', 'pipe', 'pipe']
        })

        bleProcess.stdout.on('data', (data) => {
          handleBLEData(data, options, app, plugin)
        })

        bleProcess.stderr.on('data', (data) => {
          app.debug(`gatttool stderr: ${data.toString().trim()}`)
        })

        bleProcess.on('error', (err) => {
          app.setPluginStatus(`Error: ${err.message}`)
          app.debug(`gatttool error: ${err.message}`)
          if (autoReconnect) reconnect()
        })

        bleProcess.on('close', (code) => {
          app.debug(`gatttool closed with code ${code}`)
          if (code !== 124 && autoReconnect) { // 124 = timeout signal
            app.setPluginStatus('Reconnecting...')
            setTimeout(reconnect, 3000)
          }
        })

        // Send initial commands
        setTimeout(() => {
          bleProcess.stdin.write('connect\n')
          setTimeout(() => {
            // Listen for notifications on characteristic
            // Format: char-write-req <handle> <value> [raw]
            app.debug(`Subscribing to notifications on ${charHandle}`)
            bleProcess.stdin.write(`char-write-req ${charHandle} 0100\n`)
          }, 1000)
        }, 500)

        isConnected = true
        app.setPluginStatus(`Connected to ${bleName}`)

      } catch (err) {
        app.setPluginStatus(`Failed: ${err.message}`)
        app.debug(`Connection failed: ${err.message}`)
        if (autoReconnect) {
          setTimeout(reconnect, 3000)
        }
      }
    }

    const reconnect = function() {
      if (bleProcess) {
        try {
          bleProcess.kill()
        } catch (e) {}
      }
      app.debug('Attempting to reconnect...')
      connectBLE()
    }

    const handleBLEData = function(data, options, app, plugin) {
      const lines = data.toString().split('\n')
      
      lines.forEach(line => {
        // Parse gatttool output format: "Notification handle = 0x0030 value: 55 61 ... "
        if (line.includes('Notification') || line.includes('value:')) {
          const hexMatch = line.match(/value:\s*((?:[0-9a-f]{2}\s*)+)/i)
          
          if (hexMatch) {
            const hexString = hexMatch[1].trim()
            const bytes = hexString.split(/\s+/).map(h => parseInt(h, 16))
            const dataBuffer = Buffer.from(bytes)
            
            buffer = Buffer.concat([buffer, dataBuffer])
            processWITPackets(buffer, options, app, plugin)
          }
        }
      })
    }

    const processWITPackets = function(buf, options, app, plugin) {
      while (buf.length >= packetSize) {
        if (buf[0] === 0x55 && buf[1] === 0x61) {
          const packet = buf.slice(0, packetSize)
          buffer = buf.slice(packetSize)

          try {
            // Decode WIT packet (20 bytes, 0x55 0x61 format)
            
            // ACCELERATION (int16, /32768 × 16g)
            const accelXRaw = packet.readInt16LE(2)
            const accelYRaw = packet.readInt16LE(4)
            const accelZRaw = packet.readInt16LE(6)
            
            let accelX = (accelXRaw / 32768) * 16 * 9.81
            let accelY = (accelYRaw / 32768) * 16 * 9.81
            let accelZ = (accelZRaw / 32768) * 16 * 9.81
            
            accelX -= (options.accelXOffset || 0)
            accelY -= (options.accelYOffset || 0)
            accelZ -= (options.accelZOffset || 0)
            
            // GYROSCOPE (int16, /32768 × 2000 °/s)
            const gyroZRaw = packet.readInt16LE(12)
            
            let gyroZ = (gyroZRaw / 32768) * (2000 * Math.PI / 180)
            gyroZ -= (options.gyroZOffset || 0)
            
            // ATTITUDE/ANGLES (int16, /32768 × 180°)
            const rollRaw = packet.readInt16LE(14)
            const pitchRaw = packet.readInt16LE(16)
            const yawRaw = packet.readInt16LE(18)

            let roll = (rollRaw / 32768) * Math.PI
            let pitch = (pitchRaw / 32768) * Math.PI
            let yaw = (yawRaw / 32768) * Math.PI
            
            roll -= (options.rollOffset || 0) * Math.PI / 180
            pitch -= (options.pitchOffset || 0) * Math.PI / 180
            yaw -= (options.yawOffset || 0) * Math.PI / 180

            // Build values array
            const values = [
              { path: 'navigation.attitude.roll', value: roll },
              { path: 'navigation.attitude.pitch', value: pitch },
              { path: 'navigation.attitude.yaw', value: yaw }
            ]
            
            if (options.enableAcceleration !== false) {
              values.push(
                { path: 'navigation.acceleration.x', value: accelX },
                { path: 'navigation.acceleration.y', value: accelY },
                { path: 'navigation.acceleration.z', value: accelZ }
              )
            }
            
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

            app.debug(`WIT BLE: R=${(roll * 180 / Math.PI).toFixed(1)}° P=${(pitch * 180 / Math.PI).toFixed(1)}° ROT=${gyroZ.toFixed(3)} Az=${accelZ.toFixed(2)}m/s²`)

          } catch (e) {
            app.debug(`WIT BLE packet error: ${e.message}`)
          }
        } else {
          buf = buf.slice(1)
        }
      }
      buffer = buf
    }

    // Start connection
    connectBLE()
  }

  plugin.stop = function() {
    app.debug('WIT IMU BLE Reader stopping')
    
    try {
      if (bleProcess) {
        bleProcess.stdin.write('exit\n')
        setTimeout(() => {
          if (bleProcess) bleProcess.kill()
        }, 1000)
      }
    } catch (e) {
      if (bleProcess) bleProcess.kill()
    }
    
    isConnected = false
    app.setPluginStatus('Stopped')
  }

  return plugin
}
