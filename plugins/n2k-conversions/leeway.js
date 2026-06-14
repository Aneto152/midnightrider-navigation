/**
 * N2K Conversion: Leeway Angle
 * PGN 128000 — Standard NMEA 2000
 * Source SK: navigation.leeway (rad) — computed by P2_leeway plugin
 */
module.exports = {
  title: 'Leeway Angle (PGN 128000)',
  description: 'Sends leeway angle computed by P2 to N2K bus',
  optionKey: 'leeway',
  keys: ['navigation.leeway'],
  resendPeriod: 1000,
  callback: function(leeway) {
    if (leeway == null || isNaN(leeway)) return null
    return [{
      pgn: 128000,
      'Leeway Angle': leeway
    }]
  }
}
