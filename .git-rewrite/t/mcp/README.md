# MCP Servers — Sailing Data Access Layer

Three MCP servers providing comprehensive access to MidnightRider's sailing data.

## Overview

```
Signal K (1 Hz data collection)
        ↓
  InfluxDB (time-series storage)
        ↓
┌─────────────────────────────────────┐
│  Three MCP Servers (stdio protocol) │
├─────────────────────────────────────┤
│ 1. astronomical-server              │  ← Sun/moon/tides (planning)
│ 2. racing-server                    │  ← Performance metrics (live racing)
│ 3. Custom servers (future)          │  ← Additional data
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Claude / Cursor / IDE              │  ← AI coaching & insights
└─────────────────────────────────────┘
        ↓
      Sailor
```

## 1. Astronomical MCP Server

**Purpose:** Sun/moon/tide data for race planning and safety.

**Location:** `mcp/astronomical-server.js`

**Tools:**
- `get_sun_data` — Sunrise/sunset times
- `get_moon_data` — Moon phase, illumination, rise/set
- `get_tide_data` — High/low tide times and levels
- `get_next_event` — Next astronomical event

**Use Cases:**
- Pre-race planning (sunset time, moon phase)
- Safety (how much daylight remaining)
- Post-race analysis (compare conditions)

**Example:**
```
Claude: "What time is sunset?"
→ Sunset at 23:38 EDT (8 hours remaining)

Claude: "What's the moon phase?"
→ New moon at 9.2% illumination
```

## 2. Racing MCP Server

**Purpose:** Real-time performance metrics for live racing.

**Location:** `mcp/racing-server.js`

**Tools (16+):**

**Navigation:** heading, position, SOG, COG
**Performance:** STW, VMG, all metrics combined
**Wind:** Apparent, true, direction
**Water:** Depth, temperature, current
**Sailing:** Heel, pitch, attitude
**Combined:** Race data (all in one call)

**Use Cases:**
- Live race coaching (iPad)
- Performance analysis
- Tactical decisions
- Crew communication

**Example:**
```
Claude: "What's our VMG to the mark?"
→ 4.2 knots (62% of target 6.8kt)
  Suggest: Ease main 6", increase heel to 16°

Claude: "Complete race picture?"
→ Returns all navigation, wind, sailing, performance data
```

## Installation

### 1. Install Dependencies

```bash
cd /home/aneto/docker/signalk/mcp

# Create package.json (if not exists)
cat > package.json << 'EOF'
{
  "name": "midnightrider-mcp-servers",
  "version": "1.0.0",
  "dependencies": {
    "suncalc": "^1.9.0"
  }
}
EOF

npm install
```

### 2. Configure Claude Desktop / Cursor

Create or update `~/.config/Claude/claude_desktop_config.json` (macOS/Linux) 
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "astronomical": {
      "command": "/home/aneto/docker/signalk/mcp/astronomical-server.js",
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==",
        "INFLUX_ORG": "MidnightRider",
        "INFLUX_BUCKET": "signalk"
      }
    },
    "racing": {
      "command": "/home/aneto/docker/signalk/mcp/racing-server.js",
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==",
        "INFLUX_ORG": "MidnightRider",
        "INFLUX_BUCKET": "signalk"
      }
    }
  }
}
```

### 3. Restart Claude/Cursor

Close and reopen Claude or Cursor.

### 4. Verify Connection

Ask Claude:
```
"What tools are available?"
```

Claude should list all tools from both servers.

## Usage Examples

### Pre-Race Briefing

```
You: "Give me a pre-race briefing for today's race"

Claude: [calls get_sun_data, get_moon_data, get_tide_data, get_wind_true]

Claude: "PRE-RACE BRIEFING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Weather:
  • True wind: 10 knots from 180° (south)
  • Apparent wind: ~12 knots from 45° (with 6.8kt boat speed)
  • Freshening conditions (watch for gusts)

Daylight & Safety:
  • Sunset: 23:38 EDT (8 hours remaining)
  • Moon: New moon, low light for evening finish
  • Visibility: Good today, moderate at finish

Tides:
  • High tide: 14:30 (2.15m), optimal water level
  • Low tide: 20:45 (0.45m), careful in shallows

Recommendation:
  Start on the left (south) side for favorable current
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

### Live Race Coaching

```
Coach: "We're falling behind. What should we focus on?"

Claude: [calls get_race_data]

Claude: "LIVE COACHING ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Conditions:
  • Position: 41.05°N 73.54°W
  • Heading: 228° (SW toward mark)
  • Speed: 6.8kt through water, 6.5kt over ground
  • Wind: 11kt true from 185° (south)
  • Apparent: 14kt from 42° (perfect angle)
  • Heel: 18° (excessive for J/30)
  • Pitch: 3° bow up (good)

Performance:
  • VMG: 4.2 knots (target 6.8kt, 62%)
  • Your boat speed is good (6.8kt) but heel is wrong

Immediate Actions:
  1. Ease mainsheet 6 inches → reduce heel to 15°
  2. Move crew weight inboard slightly
  3. Sheet jib 1 inch tighter
  
Expected improvement:
  • Heel to 15° will reduce drag 3-5%
  • Should improve VMG to ~4.6kt (5 seconds per 100m)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

### Post-Race Debrief

```
You: "Analyze our best vs worst tacks"

Claude: [queries historical race data]

Claude: "RACE DEBRIEF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Best Tack: 14:23-14:47 (24 min upwind)
  • Average speed: 7.1kt through water
  • Heel: 14° (textbook J/30 trim)
  • Wind: 11kt true (consistent)
  • VMG: 5.8kt average (88% of target!)
  ✅ Why good: Good weight placement, trim neutral, not over-trimmed

Worst Tack: 15:12-15:38 (26 min upwind)
  • Average speed: 6.4kt through water
  • Heel: 18° (excessive)
  • Wind: 12kt true (slightly fresher)
  • VMG: 4.1kt average (58% of target)
  ❌ Why poor: Crew weight too far out, excessive heel, main overtrimmed

Key Lesson:
  Heel matters more than boat speed!
  +4° heel = -0.7kt VMG (worse performance despite higher boat speed)

Next Race Focus:
  1. Watch heel like a hawk (target 14-15°)
  2. Move crew inboard when wind freshens
  3. Ease main first, don't overtrim
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Architecture

### Data Flow

```
Sensors on Boat (GPS, Wind, Instruments)
        ↓
Serial/NMEA0183/NMEA2000
        ↓
Signal K Server (port 3000)
├─ um982-gps provider → heading, position
├─ wind provider → apparent, true wind
├─ speed provider → STW, SOG
└─ attitude plugin → heel, pitch, yaw
        ↓
signalk-to-influxdb2 plugin
        ↓
InfluxDB (localhost:8086, bucket: signalk)
├─ 1 Hz data points
├─ Unlimited retention
└─ All Signal K paths
        ↓
MCP Servers
├─ astronomical-server.js → Sun/moon/tides
├─ racing-server.js → Navigation/performance
└─ (Future servers)
        ↓
Claude/Cursor (MCP client)
        ↓
Racing Insights & Coaching
```

### Signal K Paths Accessed

**Navigation:**
- `navigation.headingTrue` (radians → degrees)
- `navigation.position.latitude/longitude`
- `navigation.speedOverGround`
- `navigation.courseOverGround`

**Performance:**
- `performance.velocityMadeGood`
- `performance.targetVMG`
- `performance.targetSpeed`
- `performance.velocityMadeGoodRatio`
- `performance.beatAngle`

**Wind:**
- `environment.wind.speedApparent/speedTrue`
- `environment.wind.angleApparent/angleTrue`
- `environment.wind.directionTrue`

**Water:**
- `environment.water.depth`
- `environment.water.temperature`
- `environment.current.speedOverGround`
- `environment.current.directionTrue`

**Sailing:**
- `navigation.attitude.roll` (radians → degrees = heel)
- `navigation.attitude.pitch` (radians → degrees = trim)
- `navigation.attitude.yaw`

**Astronomical:**
- `environment.sun.sunriseTime/sunsetTime`
- `environment.moon.moonriseTime/moonsetTime`
- `environment.moon.illumination`
- `environment.moon.phase`
- `environment.tide.tideHighTime/Level`
- `environment.tide.tideLowTime/Level`

## Configuration

### Environment Variables

All servers use:
```
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=<your-token>
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk
```

### Custom Coordinates

For tides server, set in environment:
```
LAT=41.0534       # Your latitude
LON=-73.5387      # Your longitude
NOAA_STATION=8467150  # Your NOAA tides station
```

## Testing

### Verify Server Starts

```bash
./racing-server.js
# Should wait for input (no errors)
# Ctrl+C to exit
```

### Check InfluxDB

```bash
curl http://localhost:8086/health
# Should return: {"status":"ok"}

# Query data
influx query 'from(bucket:"signalk") |> range(start: -1h) |> first()' \
  --org MidnightRider
```

### Test with Claude

1. Update config file
2. Restart Claude
3. Ask: `"List all MCP tools"`
4. Ask: `"What's our current heading?"`

## Troubleshooting

### MCP not showing in Claude

- Check config file syntax (JSON must be valid)
- Verify command path is absolute: `/home/aneto/docker/signalk/mcp/racing-server.js`
- Restart Claude completely
- Check Claude version (requires MCP support)

### "Tool not found" error

- Verify InfluxDB is running: `curl http://localhost:8086/health`
- Check token is valid
- Verify Data in bucket: `influx bucket list --org MidnightRider`

### No data returned

Verify data exists in InfluxDB:
```bash
influx query 'from(bucket:"signalk") |> range(start: -1h)' --org MidnightRider
```

If empty, check Signal K is running and plugins are active.

## Future Extensions

Possible additional MCP servers:

```
weather-server.js      → NOAA forecast integration
tactics-server.js      → AI-generated tactics
ais-server.js          → Competitor positions
crew-server.js         → Crew workload/positions
rules-server.js        → Racing rules lookup
log-server.js          → Race history analysis
```

## Files

```
mcp/
├── astronomical-server.js       (4 tools)
├── racing-server.js             (16 tools)
├── ASTRONOMICAL-MCP-README.md   (documentation)
├── RACING-MCP-README.md         (documentation)
├── README.md                    (this file)
└── package.json                 (dependencies)
```

## Author

Aneto (MidnightRider J/30)
2026-04-20

## License

MIT

---

**Ready to race with AI coaching!** 🏁⛵
