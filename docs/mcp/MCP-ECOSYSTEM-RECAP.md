# 📊 Complete MCP Ecosystem Recap

## MCP Servers: 7 Total | Tools: 37 Total

---

## 🌍 MCP #1: ASTRONOMICAL (4 tools)

**File:** `mcp/astronomical-server.js`  
**Data Source:** InfluxDB (populated by `scripts/astronomical-data.sh`)  
**Update:** Once per day (0 0 * * * cron)

### Tools:
1. **get_sun_data** - Sunrise/sunset, solar noon, day length, sun position
2. **get_moon_data** - Moon phase, age, rise/set, illumination, next event
3. **get_tide_data** - Current tide level, high/low times, tide direction, rate
4. **get_next_event** - Next sunset, next tide, moon phase event, alarms

### Use Cases:
- Pre-race planning: sunset, tide, moon phase
- Safety: "Sunset in 2 hours, head back"
- Navigation: Plan passages with tide

---

## ⛵ MCP #2: RACING (16+ tools)

**File:** `mcp/racing-server.js`  
**Data Source:** InfluxDB (from Signal K + boat sensors)  
**Update:** Real-time (1 Hz)

### Tools by Category:

**Navigation (4):**
- `get_heading` - TRUE heading (UM982 dual-antenna)
- `get_position` - Lat/lon GPS
- `get_sog` - Speed over ground
- `get_cog` - Course over ground

**Wind (3):**
- `get_apparent_wind` - Relative to boat motion
- `get_true_wind` - Relative to water/ground
- `get_wind_direction` - Compass reference

**Performance (3):**
- `get_stw` - Speed through water (impeller)
- `get_vmg` - Velocity made good (upwind/downwind)
- `get_all_performance_metrics` - Complete snapshot

**Water (3):**
- `get_water_depth` - Depth sounder
- `get_water_temperature` - Temperature sensor
- `get_water_current` - Tidal current

**Sailing (3):**
- `get_heel` - Boat lean angle (UM982)
- `get_pitch` - Bow up/down (UM982)
- `get_attitude` - Combined angles

**Combined (1):**
- `get_race_data` - EVERYTHING in one call

### Use Cases:
- Live coaching: "What's our speed?"
- Trim optimization: "Are we heeled too much?"
- Strategy: "What's our VMG?"
- Real-time monitoring

---

## 📊 MCP #3: POLAR (5 tools)

**File:** `mcp/polar-server.js`  
**Data Source:** InfluxDB + J/30 embedded polar table  
**Update:** Real-time (when wind/heading changes)

### Tools:
1. **get_boat_efficiency** - Actual vs target speed (%)
2. **get_current_polar** - What we should do right now
3. **get_upwind_analysis** - Detailed upwind breakdown
4. **get_downwind_analysis** - Detailed downwind breakdown
5. **get_all_polars** - Complete J/30 polar table (5-25 knots)

### Use Cases:
- Trim optimization: "Are we fast enough?"
- Angle selection: "Pinch or foot?"
- Sail selection: "Main + Jib1 vs Jib2?"
- Performance debugging: "Why are we slow?"

---

## 👥 MCP #4: CREW (3 tools)

**File:** `mcp/crew-server.js`  
**Data Source:** InfluxDB (manual crew logging)  
**Update:** Manual (entered by crew)

### Tools:
1. **get_helmsman_status** - Who's at wheel, time on helm, performance
2. **get_crew_rotation_history** - All helmsmen today, times, performance
3. **get_workload_assessment** - Current load level, recommendations

### Use Cases:
- Crew management: "Time for a rotation?"
- Strategy: Compare helmsman performance
- Safety: Assess fatigue
- Analysis: Post-race comparison

---

## 🏁 MCP #5: RACE MANAGEMENT (4 tools)

**File:** `mcp/race-server.js`  
**Data Source:** InfluxDB + manual race configuration  
**Update:** Variable (static + real-time)

### Tools:
1. **get_current_sails** - What sails deployed, trim, recommendations
2. **get_race_start** - Start time, countdown, flag sequence
3. **get_distance_to_line** - Distance to start line, over-early assessment
4. **get_race_marks** - Course marks, positions, rounding order, ETA

### Use Cases:
- Pre-race setup: Which sails?
- Start line: "Time to start?"
- Tactics: "Over early?"
- Navigation: "Where's the next mark?"

---

## 🌦️ MCP #6: WEATHER (3 tools)

**File:** `mcp/weather-server.js`  
**Data Source:** InfluxDB (populated by `scripts/weather-logger.sh`)  
**Update:** Every 5 minutes (*/5 * * * *)  
**Original Source:** Open-Meteo API (free, no key)

### Tools:
1. **get_current_weather** - Temp, humidity, pressure, wind, condition
2. **get_weather_trend** - Temperature/pressure trend, assessment
3. **get_wind_assessment** - Sailing condition, sail recommendations

### Sailing Conditions:
- <5kt: Light wind (challenging)
- 5-8kt: Light breeze (training)
- 8-12kt: Moderate (optimal ✅)
- 12-16kt: Fresh breeze (good racing)
- 16-20kt: Strong breeze (manageable)
- 20-25kt: Strong gale (expert)
- >25kt: Severe (dangerous)

### Auto Sail Suggestions:
- <5kt: Main + Jib1 (max area)
- 8-12kt: Main + Jib2
- 12-16kt: Main + Jib3 or Jib2
- 16-20kt: Main (reefed) + Jib3
- >20kt: Storm jib only

---

## 🌊 MCP #7: BUOY (2 tools)

**File:** `mcp/buoy-server.js`  
**Data Source:** InfluxDB (populated by `scripts/buoy-logger.sh`)  
**Update:** Every 5 minutes (*/5 * * * *)  
**Original Source:** NOAA API (free, real observations!)

### Buoys in Long Island Sound:
- **NOAA 44065** (Stamford, 41.063°N, 73.591°W, 5nm)
- **NOAA 44025** (Central LIS, 40.876°N, 73.100°W, 20nm)
- **NOAA 44008** (Block Island, 40.502°N, 71.029°W, 50nm)

### Tools:
1. **get_buoy_data** - All measurements from all buoys
2. **get_wind_comparison** - Strongest/weakest/average wind

### Data Logged per Buoy:
- Wind direction (degrees)
- Wind speed (knots) ← REAL observation
- Wind gust (knots)
- Wave height (meters)
- Water temperature (°C)

### Use Cases:
- Pre-race wind check: Real conditions (not forecast)
- Wind pattern analysis: Increasing east?
- Tactical: Where's strongest/weakest wind?
- Real vs forecast comparison

---

## 📊 Summary Statistics

| Category | Tools | Server |
|----------|-------|--------|
| Navigation & Heading | 4 | Racing |
| Wind & Performance | 10 | Racing + Polar |
| Sailing State | 5 | Racing + Attitude |
| Polar Analysis | 5 | Polar |
| Race Management | 4 | Race |
| Crew Management | 3 | Crew |
| Astronomical & Tides | 4 | Astronomical |
| Weather Forecast | 3 | Weather |
| Real Observations | 2 | Buoy |
| **TOTAL** | **37** | **7 servers** |

---

## 🔌 Integration Checklist

File: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "astronomical": {
      "command": "/home/aneto/docker/signalk/mcp/astronomical-server.js",
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "...",
        "INFLUX_ORG": "MidnightRider",
        "INFLUX_BUCKET": "signalk"
      }
    },
    "racing": { "command": ".../racing-server.js", "env": {...} },
    "polar": { "command": ".../polar-server.js", "env": {...} },
    "crew": { "command": ".../crew-server.js", "env": {...} },
    "race": { "command": ".../race-server.js", "env": {...} },
    "weather": { "command": ".../weather-server.js", "env": {...} },
    "buoy": { "command": ".../buoy-server.js", "env": {...} }
  }
}
```

---

## 💬 Example Race Coaching

**Pre-Race:**
```
You: "Give me the pre-race briefing"
Claude: [calls 6 tools: weather, wind, buoys, sun, tide, polars]
Claude: "PRE-RACE BRIEFING
         WEATHER: 12kt SW (forecast), 12-17kt (buoys)
         SAILS: Main + Jib2 (optimal)
         TIDE: Ebbing, low at 14:30
         LIGHT: Sunset 19:34 (4h 30m)
         TARGETS: 6.1kt upwind, 5.8kt downwind
         RACE: Starts in 1h 45m"
```

**2 Minutes to Start:**
```
You: "Are we ready?"
Claude: [calls 4 tools: start, distance, sails, position]
Claude: "READY TO START
         Position: 18m BEHIND (good!)
         Sails: Main + Jib2 (perfect)
         Wind: 12.5kt true SW
         Countdown: 1:45 to GO"
```

**During Race:**
```
You: "Why are we slow?"
Claude: [calls 3 tools: efficiency, upwind, heel]
Claude: "PROBLEM DIAGNOSIS
         Target: 6.1kt, Actual: 5.4kt (88%)
         Issue: Heel 22° (too much, target 18°)
         Action: Ease mainsheet 5cm"
```

---

## ✅ Status

- ✅ All 7 servers created & tested
- ✅ All data logged to InfluxDB
- ✅ Cron jobs installed (weather + buoy every 5 min)
- ✅ Astronomical updates daily (0 0 * * *)
- ✅ Committed to GitHub
- ⏳ Add to claude_desktop_config.json
- ⏳ Restart Claude/Cursor
- ⏳ Test in live racing

---

**Last Update:** 2026-04-19 22:53 EDT  
**Total Commits:** 7 MCP servers + 2 logging scripts + 2 cron jobs
