/**
 * N2K Conversion: B&G Performance Data
 * PGN 130824 — Navico/B&G Proprietary (fast packet)
 * Displays on Vulcan 7, Zeus, Triton2
 *
 * IMPORTANT: PGN 130824 is NOT in canboatjs database.
 * Must use raw Actisense string format via nmea2000out.
 * Format: <ts>,3,130824,<src>,255,<len>,7d,99,<key>,<type>,<val_lo>,<val_hi>,...
 *
 * Source SK paths (7 total):
 * navigation.leeway (rad) → key 82,20 — Leeway Angle
 * environment.current.setTrue (rad) → key 84,20 — Tide Set
 * environment.current.drift (m/s) → key 83,20 — Tide Rate
 * performance.polarSpeed (m/s) → key 7e,20 — Polar Boat Speed
 * performance.polarSpeedRatio (ratio) → key 7c,20 — Polar Performance %
 * performance.targetAngle (rad) → key 53,20 — Target TWA
 * performance.beatAngle (rad) → key 35,20 — Optimum Wind Angle
 */

const SRC_ADDR = 14 // N2K source address

function toLE16(value) {
  const v = Math.trunc(value) & 0xffff
  const lo = (v & 0xff).toString(16).padStart(2, '0')
  const hi = ((v >> 8) & 0xff).toString(16).padStart(2, '0')
  return `${lo},${hi}`
}

function encodeRad(rad) {
  if (rad == null || isNaN(rad)) return null
  return toLE16(Math.round(rad * 10000))
}

function encodeSignedRad(rad) {
  if (rad == null || isNaN(rad)) return null
  // Wrap negative angles to positive range (0..2π)
  if (rad < 0) rad = rad + 2 * Math.PI
  return toLE16(Math.round(rad * 10000))
}

function encodeSpeed(ms) {
  if (ms == null || isNaN(ms)) return null
  return toLE16(Math.round(ms * 100))
}

function encodeRatio(ratio) {
  if (ratio == null || isNaN(ratio)) return null
  return toLE16(Math.round(ratio * 1000))
}

function buildMsg(pairs) {
  // pairs: [[keyHex, typeHex, valueHex], ...] (null entries skipped)
  const valid = pairs.filter(p => p !== null)
  if (valid.length === 0) return null
  const byteCount = 2 + valid.length * 4 // 2 bytes mfg + 4 bytes per pair
  const payload = ['7d', '99', ...valid.map(([k, t, v]) => `${k},${t},${v}`)].join(',')
  const ts = new Date().toISOString()
  return `${ts},3,130824,${SRC_ADDR},255,${byteCount},${payload}`
}

module.exports = {
  title: 'B&G Performance Data (PGN 130824 — proprietary)',
  description: 'Leeway, tide, polar speed/performance, target TWA, beat angle → Vulcan/Zeus/Triton2',
  optionKey: 'bandgPerformance',
  keys: [
    'performance.leewayAngle',
    'environment.current.setTrue',
    'environment.current.drift',
    'performance.polarSpeed',
    'performance.polarSpeedRatio',
    'performance.targetAngle',
    'performance.beatAngle'
  ],
  resendPeriod: 1000,
  isBandG: true, // flag: P5 will use nmea2000out (Actisense string)
  callback: function(leeway, currentSet, currentDrift,
    polarSpeed, polarRatio, targetAngle, beatAngle) {
    const pairs = [
      leeway != null ? ['82', '20', encodeRad(leeway)] : null,
      currentSet != null ? ['84', '20', encodeRad(currentSet)] : null,
      currentDrift != null ? ['83', '20', encodeSpeed(currentDrift)] : null,
      polarSpeed != null ? ['7e', '20', encodeSpeed(polarSpeed)] : null,
      polarRatio != null ? ['7c', '20', encodeRatio(polarRatio)] : null,
      targetAngle != null ? ['53', '20', encodeSignedRad(targetAngle)] : null,
      beatAngle != null ? ['35', '20', encodeSignedRad(beatAngle)] : null,
    ]
    const msg = buildMsg(pairs)
    if (!msg) return null
    return [{ __bandg_raw: msg }] // P5 main plugin handles nmea2000out emit
  }
}
