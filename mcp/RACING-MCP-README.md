# Racing MCP Server

Model Context Protocol (MCP) server providing comprehensive access to racing data from Signal K.

**Perfect for:**
- Live race briefings
- Pre-race planning
- Post-race debriefs
- Crew communication
- AI coaching (Claude/Cursor)

## Overview

Access **16+ racing tools** via Claude/Cursor with real-time data from InfluxDB.

```
Signal K (1 Hz) → InfluxDB → Racing MCP → Claude → Racing Insights
```

## Installation

```bash
cd /home/aneto/docker/signalk/mcp
npm install
chmod +x racing-server.js
```

## Configure in Claude Desktop or Cursor

### claude_desktop_config.json

```json
{
  "mcpServers": {
    "racing": {
      "command": "/home/aneto/docker/signalk/mcp/racing-server.js",
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "[MASKED_INFLUX_TOKEN]",
        "INFLUX_ORG": "MidnightRider",
        "INFLUX_BUCKET": "signalk"
      }
    }
  }
}
```

## Tools Available

### Navigation (4 tools)

#### get_heading
**Get boat's current heading (true bearing)**

```
Claude: "What's our heading?"
→ Response: 228 degrees (SW)
```

#### get_position
**Get latitude and longitude**

```
Claude: "Where are we?"
→ Response: 41.0534°N, 73.5387°W (Stamford Harbor)
```

#### get_sog
**Get speed over ground (movement relative to water)**

```
Claude: "How fast are we moving over the ground?"
→ Response: 6.5 knots
```

#### get_cog
**Get course over ground (direction of travel)**

```
Claude: "What direction are we heading?"
→ Response: 225 degrees
```

### Performance (3 tools)

#### get_stw
**Get speed through water (boat speed in water, not affected by current)**

```
Claude: "What's our boat speed?"
→ Response: 6.8 knots through water
```

#### get_vmg
**Get velocity made good (progress toward the mark)**

```
Claude: "How fast are we going to the windward mark?"
→ Response: 4.2 knots VMG (62% of target)
```

#### get_performance
**Get all performance metrics combined**

```
Claude: "How's our performance?"
→ Response: {
  "vmg": 4.2,
  "target_vmg": 6.8,
  "target_speed": 7.2,
  "vmg_ratio": 0.62,
  "beat_angle": 34
}
```

### Wind (3 tools)

#### get_wind_apparent
**Get apparent wind (what crew feels on deck)**

```
Claude: "What's the apparent wind?"
→ Response: 12 knots from 45 degrees (starboard)
```

#### get_wind_true
**Get true wind (actual meteorological wind)**

```
Claude: "What's the true wind?"
→ Response: 10 knots from 180 degrees (south)
```

#### get_wind_direction
**Get wind compass direction**

```
Claude: "Where's the wind coming from?"
→ Response: 180 degrees (S - South)
```

### Water (3 tools)

#### get_depth
**Get water depth**

```
Claude: "How deep is the water?"
→ Response: 15 meters (49 feet)
```

#### get_water_temp
**Get water temperature**

```
Claude: "What's the water temperature?"
→ Response: 14°C (57°F)
```

#### get_current
**Get water current speed and direction**

```
Claude: "What's the current?"
→ Response: 0.5 knots from 045 degrees (NE)
```

### Sailing (3 tools)

#### get_heel
**Get boat heel (lateral tilt)**

```
Claude: "How much heel?"
→ Response: 15 degrees to starboard (good trim)
```

#### get_pitch
**Get boat pitch (front-back trim)**

```
Claude: "What's our trim?"
→ Response: 3 degrees bow up
```

#### get_attitude
**Get complete boat attitude (all angles)**

```
Claude: "What's the boat attitude?"
→ Response: {
  "roll": 0.26 rad (15°),
  "pitch": 0.05 rad (3°),
  "yaw": 3.98 rad (228°)
}
```

### Combined (1 tool)

#### get_race_data
**Get all race-critical data in one call**

Perfect for coaching or AI analysis.

```
Claude: "Give me the complete race picture"
→ Response: {
  "position": { latitude, longitude },
  "heading": 228,
  "speed": { through_water: 6.8, over_ground: 6.5 },
  "wind": { apparent_speed, apparent_angle, true_speed, true_direction },
  "sailing": { heel, pitch },
  "performance": { vmg, target_vmg }
}
```

## Example Conversations

### Pre-Race Briefing

```
You: "What's our current wind and boat speed?"
Claude: [calls get_wind_true, get_stw]
Claude: "Current conditions: 10 knots true wind from the south, 
         boat speed 6.8 knots through water. We're well-powered up."

You: "What's our heading to the first mark?"
Claude: [calls get_position, get_heading]
Claude: "We're at 41.05°N 73.54°W. The mark is at bearing 045°. 
         We're currently heading 228° (SW), so we need to tack upwind."

You: "How's our VMG?"
Claude: [calls get_vmg, get_performance]
Claude: "VMG is 4.2 knots toward the mark (62% of target). 
         Target VMG is 6.8 knots. We need to improve our upwind sailing."
```

### Live Race Coaching

```
You: "We're falling behind. What should we focus on?"
Claude: [calls get_race_data]
Claude: "Analysis shows:
         - Heel is excessive (18°, target 14°)
         - Wind is from 185° (freshening)
         - Apparent wind angle optimal (45°)
         
         Recommendation: 
         1. Ease mainsheet slightly (reduce heel)
         2. Sheet jib 1 inch tighter
         3. Keep weight on rail (good sailing trim)"
```

### Post-Race Debrief

```
You: "What was our best tack?"
Claude: [queries race data from specific time range]
Claude: "Your best tack was from 14:23-14:47:
         - Consistent 7.1 knots STW
         - Heel 14° (optimal for J/30)
         - VMG 5.8 knots (88% of target)
         - Wind average 11 knots true
         
         This was significantly better than your 14:52-15:10 tack
         where heel went to 18° and VMG dropped to 4.5 knots."
```

## Data Mapping (Signal K Specification)

| Tool | Signal K Path | Unit | Notes |
|------|-----------------|------|-------|
| get_heading | navigation.headingTrue | radians → degrees | True bearing (compass) |
| get_position | navigation.position.{latitude,longitude} | degrees | Decimal format |
| get_sog | navigation.speedOverGround | m/s → knots | Effect of current |
| get_cog | navigation.courseOverGround | radians → degrees | Direction of travel |
| get_stw | navigation.speedThroughWater | m/s → knots | Boat speed in water |
| get_vmg | performance.velocityMadeGood | m/s → knots | Progress to mark |
| get_wind_apparent | environment.wind.speed/angleApparent | m/s & radians | Felt by crew |
| get_wind_true | environment.wind.speed/angleTrue | m/s & radians | Meteorological |
| get_wind_direction | environment.wind.directionTrue | radians → degrees | Compass bearing |
| get_depth | environment.water.depth | m → feet | Water depth |
| get_water_temp | environment.water.temperature | K → C/F | Water temperature |
| get_current | environment.current.speed/directionTrue | m/s & radians | Water flow |
| get_heel | navigation.attitude.roll | radians → degrees | Lateral tilt |
| get_pitch | navigation.attitude.pitch | radians → degrees | Longitudinal trim |
| get_attitude | navigation.attitude.{roll,pitch,yaw} | radians | All angles |

## Architecture

```
Signal K Server (port 3000)
        ↓
  Provider plugins parse NMEA/NMEA2000
        ↓
  Navigation, Wind, Performance data
        ↓
  signalk-to-influxdb2 plugin
        ↓
  InfluxDB (localhost:8086)
        ↓
  Racing MCP Server
        ↓
  Claude/Cursor (stdio transport)
        ↓
  Racing Insights & Coaching
```

## Testing

### Manual Test

```bash
./racing-server.js
# Server listens on stdin/stdout
```

Then in another terminal:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | nc localhost 8000
```

### With Claude

1. Update claude_desktop_config.json
2. Restart Claude/Cursor
3. Ask: "What's our complete race picture?"

## Use Cases

### 1. Live Race Coaching

Coach on iPad gives voice commands:
```
Coach: "Helm, what's our VMG?"
Helm: [checks Claude] "4.2 knots, 62% of target"
Coach: "Ease main 6 inches, increase heel to 16°"
```

### 2. Pre-Race Planning

```
Claude: "Based on current conditions (10kt true wind, 
calm seas), the beat angle is 34° and VMG target is 6.8kt. 
Suggest flat trim, 12-14° heel, mainsail 2, jib 1."
```

### 3. Tactical Analysis

```
Claude: "Boat A is 2° lower than us (faster downwind path). 
Suggest: 
- Fall off 4° 
- Ease main 4 inches
- Move crew weight forward"
```

### 4. Post-Race Analysis

```
Claude: "Best performance: 14:23-14:47 tack
Worst performance: 15:12-15:38 tack (excessive heel, 18°)

Recommendations for next race:
1. Maintain heel 14-15° (not 18°)
2. Tighter jib trim upwind
3. Earlier tack when wind shifts"
```

## Limitations

- **Data latency:** ~1-5 seconds (1 Hz input)
- **InfluxDB required:** Must have working local instance
- **Token required:** Valid InfluxDB token needed
- **On-boat only:** Data from Signal K on this boat only

## Troubleshooting

### MCP not connecting

```bash
# Verify server starts
./racing-server.js
# Should wait for input (no error)

# Check InfluxDB
curl http://localhost:8086/health
# Should return {"status":"ok"}
```

### "Tool not found" error

Update Claude/Cursor to latest version (MCP support varies by version).

### No data returned

Verify data exists in InfluxDB:

```bash
influx query 'from(bucket:"signalk") |> range(start: -1h)' --org MidnightRider
```

## Future Extensions

Possible additional tools:

```
- get_compass_bearing (with magnetic variation)
- get_layline (computed to weather mark)
- get_bad_air (estimated interference)
- get_crew_positions (from sensors)
- get_race_timing (start sequence)
- get_rival_positions (AIS data)
- get_weather_forecast (integration with NOAA)
- get_tactics (AI-generated strategy)
```

## Author

Aneto (MidnightRider J/30 Racing)
2026-04-20

## License

MIT
