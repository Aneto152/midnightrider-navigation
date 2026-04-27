# Midnight Rider — Data Schema
**Signal K paths → InfluxDB measurements/fields**
Référence unique pour dashboards Grafana et règles d'alerte

---

## Bucket Officiel: `midnight_rider`
**Organisation:** MidnightRider | **Org ID:** d742931c93885394

---

## NAVIGATION

| Signal K Path | InfluxDB Measurement | Field | Unité | Source | Dashboards |
|---|---|---|---|---|---|
| navigation.speedOverGround | navigation.speedOverGround | value | m/s | UM982 GNSS | COCKPIT, PERFORMANCE, RACE |
| navigation.courseOverGroundTrue | navigation.courseOverGroundTrue | value | rad | UM982 dual-antenna RTK | COCKPIT, RACE |
| navigation.position.latitude | navigation.position | latitude | deg | UM982 GNSS | COMPETITIVE, RACE |
| navigation.position.longitude | navigation.position | longitude | deg | UM982 GNSS | COMPETITIVE, RACE |
| navigation.attitude.roll | navigation.attitude.roll | value | rad | WIT WT901BLECL IMU | COCKPIT, PERFORMANCE |
| navigation.attitude.pitch | navigation.attitude.pitch | value | rad | WIT WT901BLECL IMU | COCKPIT, PERFORMANCE |
| navigation.attitude.yaw | navigation.attitude.yaw | value | rad | WIT WT901BLECL IMU | PERFORMANCE |
| navigation.gnss.satellites | navigation.gnss.satellites | value | count | UM982 GNSS | ALERTS, SYSTEM |
| navigation.gnss.horizontalDilution | navigation.gnss.horizontalDilution | value | - | UM982 GNSS | ALERTS |
| navigation.gnss.dilutionOfPrecision | navigation.gnss.dilutionOfPrecision | value | - | UM982 GNSS | ALERTS |
| navigation.acceleration.x | navigation.acceleration.x | value | m/s² | WIT IMU (BLE) | PERFORMANCE |
| navigation.acceleration.y | navigation.acceleration.y | value | m/s² | WIT IMU (BLE) | PERFORMANCE |
| navigation.acceleration.z | navigation.acceleration.z | value | m/s² | WIT IMU (BLE) | PERFORMANCE |

---

## ENVIRONMENT — Wind Data

| Signal K Path | InfluxDB Measurement | Field | Unité | Source | Dashboards |
|---|---|---|---|---|---|
| _(Not yet integrated)_ | environment.wind.speedTrue | value | m/s | B&G WS320 (future) | WIND, PERFORMANCE |
| _(Not yet integrated)_ | environment.wind.directionTrue | value | rad | B&G WS320 (future) | WIND |
| _(Not yet integrated)_ | environment.wind.speedApparent | value | m/s | B&G WS320 (future) | WIND |
| _(Not yet integrated)_ | environment.wind.angleApparent | value | rad | B&G WS320 (future) | WIND |

---

## ENVIRONMENT — Weather & Sea

| Signal K Path | InfluxDB Measurement | Field | Unité | Source | Status |
|---|---|---|---|---|---|
| environment.outside.temperature | _(future)_ | - | K | NMEA2000 barometer | ⏳ Not yet |
| environment.outside.pressure | _(future)_ | - | Pa | NMEA2000 barometer | ⏳ Not yet |
| environment.water.temperature | _(future)_ | - | K | NMEA2000 temp probe | ⏳ Not yet |
| environment.water.waves.significantWaveHeight | _(future)_ | - | m | Wave Analyzer v1.1 | ⏳ Not yet |
| environment.water.waves.period | _(future)_ | - | s | Wave Analyzer v1.1 | ⏳ Not yet |
| environment.depth.belowKeel | _(future)_ | - | m | Vulcan NMEA2000 sounder | ⏳ Not yet |

---

## ELECTRICAL — Power Management

| Signal K Path | InfluxDB Measurement | Field | Unité | Source | Status |
|---|---|---|---|---|---|
| electrical.batteries.house.voltage | _(future)_ | - | V | SOK BMS (BLE) | ⏳ Not yet |
| electrical.batteries.house.current | _(future)_ | - | A | SOK BMS (BLE) | ⏳ Not yet |
| electrical.batteries.house.capacity | _(future)_ | - | % | SOK BMS (BLE) | ⏳ Not yet |
| electrical.batteries.starter.voltage | _(future)_ | - | V | Victron MPPT (future) | ⏳ Not yet |

---

## PERFORMANCE — Calculated

| Signal K Path | InfluxDB Measurement | Field | Unité | Source | Status |
|---|---|---|---|---|---|
| _(Calculated)_ | performance.velocityMadeGood | value | m/s | SOG + TWA calculation | ⏳ Not yet |
| _(Calculated)_ | performance.polars.speedDeviation | value | % | Signal K ORC polars | ⏳ Not yet |
| _(Calculated)_ | performance.leewayAngle | value | rad | (STW − SOG)·sin(COG) | ⏳ Not yet |

---

## SYSTEM HEALTH

| Metric | InfluxDB Measurement | Field | Values | Frequency | Source |
|---|---|---|---|---|---|
| Signal K API | system_health | signalk_up | 0/1 | 30s | health-check.py |
| InfluxDB API | system_health | influxdb_up | 0/1 | 30s | health-check.py |
| Grafana API | system_health | grafana_up | 0/1 | 30s | health-check.py |
| Internet connectivity | system_health | internet_up | 0/1 | 60s | health-check.py (ping) |
| RPi CPU load | system_health | rpi.cpu.load | % | 60s | /proc/stat |
| RPi CPU temperature | system_health | rpi.cpu.temperature | °C | 60s | /sys/class/thermal |
| RPi memory usage | system_health | rpi.memory.used_pct | % | 60s | /proc/meminfo |

---

## REGATTA — Race Interface

| Endpoint | InfluxDB Measurement | Fields | Source | Status |
|---|---|---|---|---|
| POST /api/sail | regatta.sails | sail (string), change_time (timestamp) | Regatta UI | ✅ Active |
| POST /api/helmsman | regatta.helmsman | name (string), start_time (timestamp) | Regatta UI | ✅ Active |
| POST /api/timer | regatta.timer | seconds_to_start (int), active (0/1), label (string) | Regatta UI | ✅ Added 2026-04-27 |
| POST /api/event | regatta.events | note (string), type (string), timestamp | Regatta UI | ⏳ Not yet |
| POST /api/crew/wake_call | regatta.crew | wake_call_minutes (int), crew_name (string) | Regatta UI | ⏳ Not yet |

---

## EXTERNAL APIs (via MCPs)

| Data Source | InfluxDB Measurement | Field | Frequency | Status |
|---|---|---|---|---|
| NDBC Buoys (Block Island vicinity) | buoy | wind.speed, wind.direction | 30 min | ⏳ MCP future |
| NOAA Astronomical | tides | slack_water, high_low (times) | 6h | ⏳ MCP future |
| NWS Alerts | weather | nws.alert.type, nws.alert.active | 30 min | ⏳ MCP future |

---

## AIS Targets (Vessels)

| Data | InfluxDB Measurement | Field | Update Frequency | Source |
|---|---|---|---|---|
| Vessel position | ais.vessels | mmsi, name, latitude, longitude | Varies (AIS Class B: 30s @ <2kt) | AIS transponder |
| Vessel velocity | ais.vessels | sog, cog | Per AIS transmission | AIS transponder |
| TCPA / CPA | ais.vessels | tcpa, cpa | Calculated every 30s | Signal K calculation |

---

## Summary: Measurements Actually Transmitted

**Currently active to InfluxDB (600+ records/min):**
```
✅ navigation.acceleration.x/y/z
✅ navigation.attitude.roll/pitch/yaw
✅ navigation.courseOverGroundTrue
✅ navigation.gnss.* (satellites, dilution, antenna altitude)
✅ navigation.position (lat/lon)
✅ navigation.speedOverGround
✅ environment.moon.* (phase, rise/set times)
✅ environment.sun.* (rise/set times)
✅ environment.system.cpuTemperature
✅ regatta.sails (via API)
✅ regatta.helmsman (via API)
✅ regatta.timer (via API, added 2026-04-27)
✅ navigation.rateOfTurn
```

**Awaiting hardware/integration:**
```
⏳ environment.wind.* (B&G WS320 not yet integrated)
⏳ environment.outside.* (barometer/thermometer not yet)
⏳ electrical.batteries.* (SOK BMS BLE integration)
⏳ environment.water.waves.* (Wave Analyzer v1.1)
⏳ navigation.speedThroughWater (Loch integration)
⏳ performance.* (calculations pending speed/wind data)
```

---

## Data Consistency Matrix

| Component | Bucket | Org | Status |
|---|---|---|---|
| Signal K plugin | midnight_rider | MidnightRider | ✅ |
| regatta/server.py | midnight_rider | MidnightRider | ✅ |
| Grafana datasource | midnight_rider | MidnightRider | ✅ |
| health-check.py | midnight_rider | MidnightRider | ⏳ Deploy |

**Conclusion:** Full alignment on `midnight_rider` bucket. No data fragmentation.

---

**Last Updated:** 2026-04-27 19:23 EDT
**Verified By:** Audit + inventory check
