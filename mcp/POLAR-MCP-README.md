# Polar Performance MCP Server

MCP server for analyzing boat performance against polars (theoretical vs actual speed).

Perfect for:
- **Live racing:** Identify performance gaps in real-time
- **Trim optimization:** Understand how heel/trim affects speed
- **Performance coaching:** AI-powered improvement suggestions
- **Post-race analysis:** Compare performance across different conditions

## Overview

```
Real Boat Data → InfluxDB → Polar Analysis → Claude → Coaching
```

Access J/30 polar performance data and get intelligent recommendations for optimization.

## Tools

### 1. get_boat_efficiency

Get current boat efficiency (actual speed vs polar speed).

```
Claude: "How efficient are we right now?"
→ Response: 
  Actual: 6.8 knots
  Polar:  7.2 knots
  Efficiency: 94.4%
  Gap: -0.4 knots
  Assessment: Excellent
```

**Returns:**
- Actual speed (STW)
- Polar speed (from table)
- Efficiency percentage
- Speed gap
- Sailing mode (upwind/reach/downwind)
- True wind speed
- Current heel
- Performance assessment (Excellent/Good/Fair/Poor)

### 2. get_current_polar

Get J/30 polar speeds for the current true wind speed.

```
Claude: "What are our target speeds?"
→ Response:
  True Wind: 10 knots
  Upwind:    6.4 knots
  Reaching:  8.2 knots
  Downwind:  9.5 knots
  Upwind Angle: 30°
```

**Returns:**
- True wind speed
- Target upwind speed
- Target reaching speed
- Target downwind speed
- Optimal upwind angle

### 3. get_upwind_analysis

Detailed analysis of upwind performance vs polar.

```
Claude: "Analyze our upwind performance"
→ Response:
  Boat Speed: 6.8kt (polar 7.2kt, 94.4% efficiency)
  VMG: 4.2kt (target 6.1kt, 68.9% efficiency)
  Heel: 16° (optimal for J/30)
  Recommendations:
    - Good performance, minor trim
    - Check apparent wind trim
```

**Returns:**
- Boat speed analysis (actual vs polar)
- VMG analysis (actual vs target)
- Heel assessment (underheeled/optimal/overheeled)
- Specific recommendations for improvement

### 4. get_downwind_analysis

Detailed analysis of downwind performance vs polar.

```
Claude: "How's our downwind speed?"
→ Response:
  Actual: 8.5 knots
  Polar:  9.5 knots
  Efficiency: 89.5%
  Heel: 6° (good)
  Recommendations:
    - Consider jib size change
    - Check spinnaker trim
```

**Returns:**
- Boat speed analysis
- Heel assessment
- Trim recommendations
- Sail combination suggestions

### 5. get_all_polars

Get complete J/30 polar table for reference.

```
Claude: "Show me the complete J/30 polars"
→ Response:
  5kt:  Upwind 3.2, Reach 4.1, Downwind 4.8
  10kt: Upwind 6.4, Reach 8.2, Downwind 9.5
  15kt: Upwind 8.9, Reach 11.4, Downwind 13.0
  20kt: Upwind 10.9, Reach 13.9, Downwind 15.8
  ... (complete table)
```

**Returns:**
- J/30 performance polars for all wind speeds (5-25 knots)
- Upwind, reaching, downwind speeds
- Upwind angle for each wind speed

## J/30 Polars Reference

| Wind (kt) | Upwind | Reach | Downwind | Angle |
|-----------|--------|-------|----------|-------|
| 5         | 3.2    | 4.1   | 4.8      | 32°   |
| 6         | 3.9    | 5.0   | 5.9      | 31°   |
| 7         | 4.6    | 5.9   | 6.9      | 31°   |
| 8         | 5.2    | 6.7   | 7.8      | 31°   |
| 10        | 6.4    | 8.2   | 9.5      | 30°   |
| 12        | 7.5    | 9.6   | 11.0     | 30°   |
| 14        | 8.5    | 10.9  | 12.4     | 29°   |
| 16        | 9.4    | 12.0  | 13.7     | 29°   |
| 18        | 10.2   | 13.0  | 14.8     | 28°   |
| 20        | 10.9   | 13.9  | 15.8     | 28°   |
| 25        | 12.0   | 15.2  | 17.2     | 27°   |

## Usage Examples

### Pre-Race Performance Target

```
You: "What should our target speeds be today?"

Claude: [calls get_current_polar with 12kt wind]

Claude: "Today's conditions (12kt true wind):
         • Upwind target: 7.5 knots
         • Reaching target: 9.6 knots
         • Downwind target: 11.0 knots
         
         If achieving <90% of these targets, 
         trim needs attention."
```

### Live Race Coaching

```
Coach: "How efficient is the boat right now?"

Claude: [calls get_boat_efficiency]

Claude: "Current efficiency: 94.4% (6.8kt actual vs 7.2kt polar)
         
         Status: EXCELLENT
         
         VMG is 68.9% of target. Recommendations:
         1. Heel is 16° (good) - maintain
         2. Check jib trim (appears 2" too far inboard)
         3. Move crew weight 1 foot aft (improves VMG)"
```

### Upwind Performance Problem

```
Sailor: "We're slow upwind. What's wrong?"

Claude: [calls get_upwind_analysis]

Claude: "Upwind Analysis:
         • Boat speed: 6.2kt (polar 7.2kt) = 86% efficiency ⚠️
         • Heel: 19° (TOO MUCH for J/30)
         • VMG: 3.8kt (target 6.1kt) = 62% efficiency
         
         ROOT CAUSE: Excessive heel
         
         Actions:
         1. Ease mainsheet immediately (target 14-15° heel)
         2. Move crew inboard
         3. Tighten jib lead 1 hole
         
         Expected improvement:
         → Heel 14° should gain +0.6kt boat speed
         → Improved VMG to ~4.4kt"
```

### Downwind Optimization

```
Sailor: "Can we go faster downwind?"

Claude: [calls get_downwind_analysis]

Claude: "Downwind Analysis:
         • Current: 8.5kt (polar 9.5kt) = 89.5% efficiency
         • Heel: 6° (good - minimizes drag)
         
         Performance is decent but not optimal.
         
         Suggested improvements:
         1. Check spinnaker trim (too tight?)
         2. Easing sheet 6 inches might gain +0.3kt
         3. Slight boom vang reduction (broaching control)
         4. Consider jib2 vs jib1 (jib1 may be too big)"
```

### Post-Race Debrief

```
You: "Analyze our upwind vs downwind efficiency"

Claude: [queries historical race data]

Claude: "RACE ANALYSIS:
         
         UPWIND (14:23-15:10, 47 min):
         • Avg efficiency: 91.5%
         • Heel range: 14-16° (optimal)
         • Best tack: 14:35-14:51 (94.2% efficiency)
         
         DOWNWIND (15:12-16:00, 48 min):
         • Avg efficiency: 87.3%
         • Heel range: 5-10° (good)
         • Speed gap: -1.0kt average
         
         COMPARISON:
         • Better at upwind (+4.2% efficiency)
         • Downwind has untapped potential
         
         RECOMMENDATIONS FOR NEXT RACE:
         1. Upwind: Keep current trim, very good
         2. Downwind: Work on spinnaker trim (worth +0.5-0.8kt)
         3. Consider heavier crew roster for more heel control"
```

## Integration with Claude

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "polar": {
      "command": "/home/aneto/docker/signalk/mcp/polar-server.js",
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "...",
        "INFLUX_ORG": "MidnightRider",
        "INFLUX_BUCKET": "signalk"
      }
    }
  }
}
```

## How Efficiency is Calculated

### Boat Efficiency

```
Efficiency (%) = (Actual STW / Polar STW) × 100

Example:
  Actual Speed: 6.8 knots
  Polar Speed:  7.2 knots
  Efficiency: (6.8 / 7.2) × 100 = 94.4%

Assessment:
  > 95%  = Excellent (near-perfect trim)
  90-95% = Good (minor trim issues)
  80-90% = Fair (noticeable performance gaps)
  < 80%  = Poor (major problems to solve)
```

### VMG Efficiency

```
VMG Efficiency (%) = (Actual VMG / Target VMG) × 100

Where Target VMG = Polar Upwind Speed × 0.85

Example:
  Actual VMG: 4.2 knots
  Polar:      7.2 knots
  Target:     7.2 × 0.85 = 6.12 knots
  Efficiency: (4.2 / 6.12) × 100 = 68.6%
```

## Performance Tips

### Upwind (Common Issues)

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Too much heel** | Efficiency < 85%, heel > 18° | Ease main, move crew in |
| **Too little heel** | Efficiency < 85%, heel < 12° | Trim main, move crew out |
| **Bad jib trim** | Efficiency < 85% despite good heel | Check jib lead, fairness |
| **Wrong apparent angle** | VMG low despite good STW | Check wind angle, sail shape |

### Downwind (Common Issues)

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Spinnaker trim** | Efficiency < 85% | Adjust trim, check twist |
| **Heel too high** | Efficiency < 85%, heel > 12° | Reduce crew weight to windward |
| **Wrong sail combo** | Efficiency < 85% consistently | Try different jib size |
| **Broaching tendency** | Unstable, high heel | Reduce vang tension |

## Testing

```bash
# Start server
./polar-server.js

# Verify with sample data
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | nc localhost 8000
```

## Architecture

```
Sensors (Speed, Wind, Heel)
        ↓
Signal K Server
        ↓
InfluxDB (1 Hz data)
        ↓
Polar Server
├─ Load J/30 polars (embedded table)
├─ Query current conditions
├─ Calculate efficiency
└─ Generate recommendations
        ↓
Claude/Cursor (via MCP)
        ↓
Sailing Insights & Coaching
```

## Customization

### Update Polars

To use different polars (ORC, IMS, custom):

1. Edit `J30_POLARS` table in `polar-server.js`
2. Add/modify wind speeds and speeds
3. Restart server

Example:
```javascript
const J30_POLARS = {
  5: { upwind: 3.2, reach: 4.1, downwind: 4.8, upwindAngle: 32 },
  // ... add your own polars
};
```

### Add Boat-Specific Corrections

Could enhance with:
- Crew weight adjustments
- Sail damage coefficients
- Water temperature effects
- Fouling compensation

## Limitations

- Polars are **static** (don't account for crew weight changes)
- Based on **standard J/30 setup** (may differ from your boat)
- **Real-time only** (no historical performance curves)
- Assumes **clean bottom** (fouling not considered)

## Future Extensions

- Weather-corrected polars
- Crew weight effects
- Damage assessment (torn sail, etc.)
- Foiling optimization
- Wind range analysis
- Historical performance trends

## Author

Aneto (MidnightRider J/30 Racing)
2026-04-20

## License

MIT
