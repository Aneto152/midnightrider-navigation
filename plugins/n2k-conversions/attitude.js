/**
 * attitude.js — Attitude conversion for sk-to-nmea2000
 *
 * MODIFIED VERSION — supersedes npm original:
 * plugins/sk-to-nmea2000-reference/conversions/attitude.js
 *
 * CHANGE (2026-07-21):
 * Yaw field: navigation.attitude.yaw (headingMagnetic WIT raw)
 * → navigation.headingTrue (pre-calculated by heading-true-calculator)
 *
 * REASON:
 * Original: PGN 127257 Yaw = headingMagnetic (WIT raw)
 * PGN 127250 Heading = headingTrue (Reference=True)
 * → Two different heading references on N2K bus → Vulcan 7 FS confusion
 *
 * Fixed: PGN 127257 Yaw = headingTrue
 * PGN 127250 Heading = headingTrue (Reference=True)
 * → Single coherent heading reference on N2K bus
 *
 * DEPLOYMENT:
 * cp ~/midnightrider-navigation/plugins/n2k-conversions/attitude.js \
 * ~/.signalk/node_modules/signalk-to-nmea2000/conversions/attitude.js
 * sudo systemctl restart signalk
 */

module.exports = (app, plugin) => {
  return {
    pgn: 127257,
    title: 'Attitude (127257) - Roll/Pitch from WIT IMU, Yaw from headingTrue',
    optionKey: 'ATTITUDE',
    keys: [
      "navigation.attitude.roll",
      "navigation.attitude.pitch",
      "navigation.headingTrue"
    ],
    callback: (roll, pitch, headingTrue) => {
      if (roll === null || pitch === null) return null
      return [{
        pgn: 127257,
        SID: 87,
        Pitch: pitch,
        Yaw: headingTrue !== undefined ? headingTrue : null,
        Roll: roll
      }]
    },
    tests: [
      {
        input: [ 0.042, 0.042, 1.8843 ],  // roll, pitch, headingTrue
        expected: [ {
          "dst": 255,
          "fields": {
            "Pitch": 0.042,
            "Roll": 0.042,
            "SID": 87,
            "Yaw": 1.8843
          },
          "pgn": 127257,
          "prio": 2
        }]
      }
    ]
  }
}
