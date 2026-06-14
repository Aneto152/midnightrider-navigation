/**
 * P5 — signalk-n2k-bridge v1.0.0
 * Signal K → NMEA 2000 bridge plugin for Midnight Rider (J/30 hull 511)
 *
 * Architecture: modular conversions loaded from plugins/n2k-conversions/
 * Each conversion file exports an object with:
 * - title, description, optionKey
 * - keys: SK paths to subscribe
 * - resendPeriod: ms between forced resends (0 = only on change)
 * - callback(values...) → [{pgn, fields}]
 *
 * To add a new PGN: create a new file in plugins/n2k-conversions/
 * No changes to this file required.
 *
 * Version: 1.0.0
 * Status: BUILT (dormant — not yet activated)
 */

const path = require('path')
const fs = require('fs')

const PLUGIN_ID = 'signalk-n2k-bridge'
const CONVERSION_DIR = path.join(__dirname, 'n2k-conversions')
const LOG_FILE = path.join(__dirname, '../logs/services/signalk-n2k-bridge.log')

// --- Logger ---
function log(level, message) {
  const ts = new Date().toISOString()
  const entry = `[${ts}] [${level}] [${PLUGIN_ID}] ${message}\n`
  try {
    fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true })
    fs.appendFileSync(LOG_FILE, entry)
  } catch(e) { /* ignore */ }
}

// --- Load conversions ---
function loadConversions() {
  const conversions = []
  try {
    if (!fs.existsSync(CONVERSION_DIR)) {
      log('WARN', 'Conversions directory not found')
      return conversions
    }
    const files = fs.readdirSync(CONVERSION_DIR).filter(f => f.endsWith('.js')).sort()
    for (const file of files) {
      try {
        const conv = require(path.join(CONVERSION_DIR, file))
        conversions.push(conv)
        log('INFO', `Loaded conversion: ${conv.title || file}`)
      } catch (e) {
        log('ERROR', `Failed to load ${file}: ${e.message}`)
      }
    }
  } catch (e) {
    log('ERROR', `Cannot read conversions directory: ${e.message}`)
  }
  return conversions
}

// --- Plugin definition ---
module.exports = function(app) {
  let unsubscribes = []
  let heartbeatTimer = null
  let stats = {}
  let n2kReady = false

  // Wait for N2K bus to be ready
  app.on('nmea2000OutAvailable', () => {
    if (!n2kReady) {
      n2kReady = true
      log('INFO', 'STARTUP: N2K bus ready')
    }
  })
  // Fallback timeout
  setTimeout(() => {
    if (!n2kReady) {
      n2kReady = true
      log('WARN', 'STARTUP: nmea2000OutAvailable timeout — assuming ready')
    }
  }, 8000)

  const conversions = loadConversions()

  // Build schema from conversions
  const schemaProperties = {}
  for (const conv of conversions) {
    schemaProperties[conv.optionKey] = {
      type: 'object',
      title: conv.title,
      description: conv.description || '',
      properties: {
        enabled: {
          type: 'boolean',
          title: 'Enabled',
          default: false
        }
      }
    }
  }

  const plugin = {
    id: PLUGIN_ID,
    name: 'N2K Bridge (P5) — SK → NMEA 2000',
    description: 'Modular Signal K → NMEA 2000 bridge for Midnight Rider',
    version: '1.0.0',

    schema: {
      type: 'object',
      title: 'N2K Bridge Configuration',
      description: 'Enable/disable each N2K conversion',
      properties: schemaProperties
    },

    start: function(options) {
      log('INFO', 'STARTUP: Plugin starting')
      log('INFO', `STARTUP: ${conversions.length} conversions loaded`)

      heartbeatTimer = setInterval(() => {
        const statStr = Object.entries(stats)
          .map(([k, v]) => `${k}=${v}`).join(', ')
        log('DEBUG', `HEARTBEAT: N2K bridge — ${statStr || 'dormant'}`)
      }, 5 * 60 * 1000)

      // Subscribe to conversions
      for (const conv of conversions) {
        const opts = (options || {})[conv.optionKey] || {}
        if (!opts.enabled) {
          log('INFO', `CONFIG: Conversion DISABLED: ${conv.optionKey}`)
          continue
        }
        log('INFO', `CONFIG: Conversion ENABLED: ${conv.optionKey}`)
        stats[conv.optionKey] = 0
        setupConversion(conv)
      }
    },

    stop: function() {
      log('INFO', 'SHUTDOWN: Plugin stopping')
      if (heartbeatTimer) clearInterval(heartbeatTimer)
      unsubscribes.forEach(f => { try { f() } catch(e) {} })
      unsubscribes = []
      log('INFO', 'SHUTDOWN: Plugin stopped cleanly')
    }
  }

  function setupConversion(conv) {
    let lastValues = new Array(conv.keys.length).fill(undefined)

    function sendValues(values) {
      try {
        const result = conv.callback.apply(conv, values)
        if (!result) return

        for (const item of result) {
          if (!item) continue
          stats[conv.optionKey] = (stats[conv.optionKey] || 0) + 1
          
          if (item.__bandg_raw) {
            // B&G proprietary PGN 130824 — raw Actisense format
            if (!n2kReady) {
              log('WARN', 'N2K not ready — dropping PGN 130824')
              continue
            }
            app.emit('nmea2000out', item.__bandg_raw)
            log('DEBUG', `DATA_OUT: PGN 130824 (B&G) — ${conv.optionKey}`)
          } else {
            // Standard NMEA 2000 PGN — JSON canboatjs format
            if (!n2kReady) {
              log('WARN', `N2K not ready — dropping PGN ${item.pgn}`)
              continue
            }
            app.emit('nmea2000JsonOut', item)
            log('DEBUG', `DATA_OUT: PGN ${item.pgn} (standard) — ${conv.optionKey}`)
          }
        }
      } catch (e) {
        log('ERROR', `Conversion error: ${e.message}`)
      }
    }

    // Subscribe to paths
    conv.keys.forEach((key, idx) => {
      const handler = (value) => {
        const raw = value && value.value !== undefined ? value.value : value
        lastValues[idx] = raw
        log('DEBUG', `DATA_IN: ${key} = ${raw}`)

        if (lastValues.every(v => v !== undefined)) {
          sendValues([...lastValues])
        }
      }

      const unsub = app.streambundle.getSelfBus(key)
        .skipDuplicates()
        .onValue(handler)
      unsubscribes.push(unsub)
    })

    // Forced resend timer
    if (conv.resendPeriod > 0) {
      const timer = setInterval(() => {
        if (lastValues.every(v => v !== undefined)) {
          sendValues([...lastValues])
        }
      }, conv.resendPeriod)
      unsubscribes.push(() => clearInterval(timer))
    }
  }

  return plugin
}

module.exports.id = PLUGIN_ID
