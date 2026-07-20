
module.exports = (app, plugin) => {
  return {
    pgn: 127257,
    title: 'Attitude (127257) - Roll/Pitch/Yaw from WIT IMU',
    optionKey: 'ATTITUDE',
    keys: [
      "navigation.attitude.roll",
      "navigation.attitude.pitch",
      "navigation.attitude.yaw"
    ],
    callback: (roll, pitch, yaw) => {
      if (roll === null || pitch === null || yaw === null) return null
      return [{
        pgn: 127257,
        SID: 87,
        Pitch: pitch,
        Yaw: yaw,
        Roll: roll
      }]
    },
    tests: [
      {
        input: [ 0.042, 0.042, 1.8843 ],  // roll, pitch, yaw
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
