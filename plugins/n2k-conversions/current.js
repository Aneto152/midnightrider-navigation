/**
 * N2K Conversion: Current Set & Drift
 * PGN 129291 — Standard NMEA 2000 (Set & Drift, Rapid Update)
 */
module.exports = {
  title: 'Current Set & Drift (PGN 129291)',
  description: 'Sends current direction and speed computed by P3 to N2K bus',
  optionKey: 'current',
  keys: ['environment.current.setTrue', 'environment.current.drift'],
  resendPeriod: 1000,
  callback: function(setTrue, drift) {
    if (setTrue == null || drift == null) return null
    if (isNaN(setTrue) || isNaN(drift)) return null
    return [{
      pgn: 129291,
      SID: 255,
      'Set Reference': 'True',
      'Set': setTrue,
      'Drift': drift
    }]
  }
}
