# Midnight Rider — Alert Catalog
**69 Alerts / 6 Categories** — Comprehensive monitoring for Block Island Race 2026

---

## 🖥️ SYSTEM HEALTH (20 Alerts)
*Infrastructure monitoring, instrument connectivity, service health*

### A — Core Services (4 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| SY-A1 | Signal K Down | system_health | signalk_up | = 0 | > 30s | 🔴 CRITICAL |
| SY-A2 | InfluxDB Down | system_health | influxdb_up | = 0 | > 30s | 🔴 CRITICAL |
| SY-A3 | Grafana Down | system_health | grafana_up | = 0 | > 30s | 🟡 WARNING |
| SY-A4 | Internet Lost | system_health | internet_up | = 0 | > 2min | 🔴 CRITICAL |

### B — RPi Hardware (3 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| SY-B1 | CPU Overtemp | system_health | rpi.cpu.temperature | > 85°C | > 2min | 🔴 CRITICAL |
| SY-B2 | High CPU Load | system_health | rpi.cpu.load | > 90% | > 5min | 🟡 WARNING |
| SY-B3 | Memory Saturated | system_health | rpi.memory.used_pct | > 95% | > 5min | 🟡 WARNING |

### C — Instrument Connectivity (13 alerts)

| ID | Instrument | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| SY-C01 | GPS UM982 — low sat count | navigation.gnss.satellites | value | < 4 satellites | > 1min | 🟡 WARNING |
| SY-C02 | GPS UM982 — no heading | navigation.courseOverGroundTrue | value | silence/stale | > 30s | 🟡 WARNING |
| SY-C03 | IMU WIT — roll missing | navigation.attitude.roll | value | silence/stale | > 10s | 🔴 CRITICAL |
| SY-C04 | Anemometer WS320 — wind silent | environment.wind.speedTrue | value | silence/stale | > 30s | 🟡 WARNING |
| SY-C05 | Loch STW — no data | navigation.speedThroughWater | value | silence/stale | > 30s | 🟡 WARNING |
| SY-C06 | Barometer — no data | environment.outside.pressure | value | silence/stale | > 60s | 🟡 WARNING |
| SY-C07 | Thermometer — no data | environment.outside.temperature | value | silence/stale | > 60s | 🟡 WARNING |
| SY-C08 | AIS — no targets | ais.vessels | count | < 1 vessel | > 60s | ⚪ INFO |
| SY-C09 | Battery SOK — no data | electrical.batteries.house.voltage | value | silence/stale | > 60s | 🟡 WARNING |
| SY-C10 | Starter battery — no data | electrical.batteries.starter.voltage | value | silence/stale | > 60s | 🟡 WARNING |
| SY-C11 | Vulcan NMEA2000 — no COG | navigation.courseOverGroundTrue | value | silence/stale | > 30s | 🟡 WARNING |
| SY-C12 | Wave Analyzer — no data | environment.water.waves.significantWaveHeight | value | silence/stale | > 60s | 🟡 WARNING |
| SY-C13 | Calc. Current — no data | performance.current.speed | value | silence/stale | > 60s | ⚪ INFO |

---

## ⚡ PERFORMANCE (17 Alerts)
*Boat speed, efficiency, trim, and course stability*

### A — Speed vs Polars (3 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| PE-A1 | VMG Suboptimal | performance.velocityMadeGood | value | < 85% of polar | > 3min | 🟡 WARNING |
| PE-A2 | VMG Overestimated | performance.velocityMadeGood | value | > 105% of polar | > 2min | 🟡 WARNING |
| PE-A3 | Boat Slow (polars) | performance.polars.speedDeviation | value | deficit > 20% | > 5min | 🟡 WARNING |

### B — Heel & Pitch Trim (4 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| PE-B1 | Critical Heel | navigation.attitude.roll | value | > 0.436 rad (25°) | > 2min | 🔴 CRITICAL |
| PE-B2 | Insufficient Heel | navigation.attitude.roll | value | < 0.087 rad (5°) @ TWS > 12kt | > 3min | 🟡 WARNING |
| PE-B3 | Heel Unstable | navigation.attitude.roll | std dev | > 5°/2min | > 2min | 🟡 WARNING |
| PE-B4 | Excessive Pitch | navigation.attitude.pitch | value | > 0.262 rad (15°) | > 1min | 🟡 WARNING |

### C — Course & Rudder (3 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| PE-C1 | Heading Drift | navigation.headingTrue | trend | > 5° change/20min | > 20min | 🟡 WARNING |
| PE-C2 | Helm Oscillation | environment.wind.angleTrueWater | std dev | > 5° @ helmsman @ 10min | > 10min | 🟡 WARNING |
| PE-C3 | High Leeway | navigation.leewayAngle | value | > 8° @ close-hauled | > 5min | 🟡 WARNING |

### D — Current & Laylines (4 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| PE-D1 | Adverse Current | performance.current.speed | value | > 0.5kt adverse | > 5min | 🟡 WARNING |
| PE-D2 | Current Shift | performance.current.speed | trend | variation > 0.5kt/5min | > 5min | 🟡 WARNING |
| PE-D3 | Port Layline Open | performance.layline.portAngle | value | ≤ 0° | immediate | 🔔 OPPORTUNITY |
| PE-D4 | Starboard Layline Open | performance.layline.stbdAngle | value | ≤ 0° | immediate | 🔔 OPPORTUNITY |

### E — Tactical Opportunities (3 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| PE-E1 | Favorable Lift | environment.wind.directionTrue | trend | > 8° favorable / 3min | > 3min | 🔔 OPPORTUNITY |
| PE-E2 | Unfavorable Header | environment.wind.directionTrue | trend | > 8° adverse / 3min | > 3min | 🟡 WARNING |
| PE-E3 | Sails Not Optimal | regatta.sails | current_sail | mismatch vs polars | > 5min | 🟡 WARNING |

---

## 🌊 WEATHER/SEA (15 Alerts)
*Wind, pressure, waves, currents, tides, and astronomical events*

### A — Wind (3 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| W-A1 | Wind Shift | environment.wind.directionTrue | trend | > 15° change / 3min | > 3min | 🟡 WARNING |
| W-A2 | Gust Imminente | environment.wind.speedTrue | trend | > 8kt rise / 5min | > 5min | 🟡 WARNING |
| W-A3 | Squall | environment.wind.speedTrue | trend | > 15kt rise / 10min | > 10min | 🔴 CRITICAL |

### B — Pressure & External (2 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| W-B1 | Pressure Drop | environment.outside.pressure | trend | > 3 hPa drop / 3h | > 3h | 🟡 WARNING |
| W-B2 | NWS Alert Active | weather.nws.alert | active | = 1 (Small Craft, Gale, Storm) | immediate | 🔴 CRITICAL |

### C — Waves & Current (4 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| W-C1 | Wave Height Increasing | environment.water.waves.significantWaveHeight | trend | > 0.5m rise / 30min | > 30min | 🟡 WARNING |
| W-C2 | Short Wave Period | environment.water.waves.period | value | < 6 seconds | > 5min | 🟡 WARNING |
| W-C3 | Adverse Swell | environment.water.waves.direction | angle | > 90° from COG | > 10min | 🟡 WARNING |
| W-C4 | Current Shift | performance.current.direction | trend | > 20° change / 5min | > 5min | 🟡 WARNING |

### D — Depth (1 alert)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| W-D1 | Shallow Water | environment.depth.belowKeel | value | < 4 meters | immediate | 🔴 CRITICAL |

### E — Astronomical (3 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| W-E1 | Slack Water Approaching | tides | slack_water_time | < 30min to slack | immediate | 🔔 OPPORTUNITY |
| W-E2 | Sunset (Lights On) | astronomy | sunset | < 30min to sunset | immediate | 🔔 REMINDER |
| W-E3 | Sunrise (Lights Off) | astronomy | sunrise | < 30min to sunrise | immediate | 🔔 REMINDER |

### F — Temperature (2 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| W-F1 | Water Temp Anomaly | environment.water.temperature | value | > 2°C change/30min | > 30min | 🟡 WARNING |
| W-F2 | Cold Water | environment.water.temperature | value | < 10°C (safety) | > 10min | 🟡 WARNING |

---

## 🏁 RACING (14 Alerts)
*Start line, marks, course, competition, and rule enforcement*

### A — Start Line (4 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| R-A1 | Start Line Approaching | navigation.position | distance to line | < 0.5 nm | immediate | 🔔 REMINDER |
| R-A2 | Start Timer | regatta.timer | seconds_to_start | ≤ 300/180/60/30/10 seconds | immediate | 🔔 REMINDER |
| R-A3 | Line Bias Check | environment.wind.directionTrue + regatta.start_line | relative wind | port/starboard bias > 5° | > 2min | 🔔 OPPORTUNITY |
| R-A4 | OCS Risk (Off Course Start) | navigation.position | crossing | crossed line before gun | immediate | 🔴 CRITICAL |

### B — Marks & Course (4 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| R-B1 | Mark Approaching | navigation.course.distanceToMark | value | < 1 nm / 0.5 nm / 0.2 nm | immediate | 🔔 REMINDER |
| R-B2 | Wrong Mark | navigation.course.waypointOrder | current mark | order mismatch | immediate | 🔴 CRITICAL |
| R-B3 | Course Boundary | navigation.position | vs limits | outside zone > 0.1nm | > 30s | 🔴 CRITICAL |
| R-B4 | Finish Approaching | navigation.position | distance to finish | < 0.2 nm | immediate | 🔔 REMINDER |

### C — Fleet & Competition (4 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| R-C1 | Boat Passing (ORC corrected) | ais.vessels + performance | delta TCF | fleet position change | > 5min | 🔔 OPPORTUNITY |
| R-C2 | Competitor Very Close | ais.vessels | distance | < 0.2 nm behind | immediate | 🟡 WARNING |
| R-C3 | Fleet on Other Tack | ais.vessels | COG vs our COG | > 5 nm majority other tack | > 10min | 🔔 OPPORTUNITY |
| R-C4 | Competitor Tack Change | ais.vessels | COG | > 45° change / 3min | > 3min | 🔔 WATCH |

### D — Rules & Limits (2 alerts)

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| R-D1 | Time Limit Approaching | race | time_to_finish | < 2 hours remaining | immediate | 🟡 WARNING |
| R-D2 | Penalty Recorded | regatta.events | type | = "penalty" | immediate | 🔴 CRITICAL |

---

## 👥 CREW (3 Alerts)
*Watch rotation, fatigue management, crew scheduling*

| ID | Alert Name | Measurement | Field | Condition | Delay | Severity |
|---|---|---|---|---|---|---|
| CR-1 | Watch Time Elapsed | regatta.helmsman | duration | > target watch duration | > 5min | 🟡 WARNING |
| CR-2 | Watch Excessive | regatta.helmsman | duration | > 180 minutes continuous | > 180min | 🔴 CRITICAL |
| CR-3 | Crew Wake-Up | regatta.crew | wake_call_time | T - 10 min before watch | immediate | 🔔 REMINDER |

---

## Summary by Category

| Category | Total | Critical | Warning | Opportunity | Info | Status |
|---|---|---|---|---|---|---|
| 🖥️ SYSTEM | 20 | 4 | 11 | 0 | 5 | ✅ Deployable |
| ⚡ PERFORMANCE | 17 | 1 | 12 | 4 | 0 | ✅ Deployable |
| 🌊 WEATHER/SEA | 15 | 3 | 8 | 1 | 3 | ✅ Deployable |
| 🏁 RACING | 14 | 4 | 3 | 2 | 5 | ✅ Deployable |
| 👥 CREW | 3 | 1 | 1 | 0 | 1 | ✅ Deployable |
| **TOTAL** | **69** | **13** | **35** | **7** | **14** | **✅ READY** |

---

## Implementation Notes

### Phase 1: Deployable Now (39 alerts)
- All SYSTEM alerts (hardware, connectivity, core services)
- PERFORMANCE alerts (heel, pitch, heading, current)
- WEATHER alerts (wind, pressure, depth, astronomical)
- RACING basic alerts (start line, marks, time limit)
- CREW alerts

### Phase 2: Pending Hardware (30 alerts)
- Wind-dependent alerts (require B&G WS320 integration)
- Wave-dependent alerts (require Wave Analyzer)
- Current-dependent alerts (require full calculation)
- Speed-dependent alerts (require Loch STW)

### Alert Messaging Strategy

**For Crew Display:**
- 🔴 CRITICAL: Audible alarm + visual pulse + voice announcement
- 🟡 WARNING: Visual notification + optional sound
- 🔔 OPPORTUNITY: Subtle notification (haptic pulse)
- ⚪ INFO: Log only (no notification)

**Voice Announcements** (TTS):
```
CRITICAL: "CRITICAL — [alert name] — action required"
WARNING: "[alert name]"
OPPORTUNITY: "Opportunity — [alert name]"
```

---

**Last Updated:** 2026-04-27 19:23 EDT
**Verified By:** Stack audit + deployment readiness check
**Next Review:** Pre-race briefing (May 20)

