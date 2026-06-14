/**
 * N2K Conversion: True Heading
 * PGN 127250 — Standard NMEA 2000 (Vessel Heading)
 */
module.exports = {
  title: 'True Heading (PGN 127250)',
  description: 'Sends true heading computed by P1 to N2K bus',
  optionKey: 'headingTrue',
  keys: ['navigation.headingTrue'],
  resendPeriod: 500,
  callback: function(heading) {
    if (heading == null || isNaN(heading)) return null
    return [{
      pgn: 127250,
      SID: 255,
      Heading: heading,
      Deviation: 0,
      Variation: 0,
      Reference: 'True'
    }]
  }
}
