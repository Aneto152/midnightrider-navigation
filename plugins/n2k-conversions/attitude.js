/**
 * N2K Conversion: Vessel Attitude
 * PGN 127257 — Standard NMEA 2000 (Attitude)
 */
module.exports = {
  title: 'Vessel Attitude — Heel/Pitch (PGN 127257)',
  description: 'Sends heel (roll) and pitch from IMU to N2K bus',
  optionKey: 'attitude',
  keys: [
    'navigation.attitude.roll',
    'navigation.attitude.pitch',
    'navigation.attitude.yaw'
  ],
  resendPeriod: 500,
  callback: function(roll, pitch, yaw) {
    if (roll == null && pitch == null) return null
    return [{
      pgn: 127257,
      SID: 255,
      Yaw: yaw || 0,
      Pitch: pitch || 0,
      Roll: roll || 0
    }]
  }
}
