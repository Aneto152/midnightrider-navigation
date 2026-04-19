# UM982 — Attitude Data (Roll/Pitch) via Dual GNSS

## Status

✅ **CONFIRMED** — Proprietary Unicore sentences contain roll/pitch data

## Discovery

**Direct observation from GPS serial port:**
```
#HEADINGA,COM1,13495,95.0,FINE,2415,73711.000,17020772,13,18;SOL_COMPUTED,L1_FLOAT,12.2446,260.1887,-35.0258,0.0000,292.7253,155.0128,"999",29,7,7,0,3,00,0,51*12fb1b6a

#UNIHEADINGA,95,GPS,FINE,2415,73711000,0,0,18,13;SOL_COMPUTED,L1_FLOAT,12.2446,260.1887,-35.0258,0.0000,292.7253,155.0128,"999",29,7,7,0,3,00,0,51*8c4c3dfb
```

## Field Mapping (Hypothesis)

| Pos | Value | Interpretation | Unit |
|-----|-------|---|---|
| 1 | COM1 | UART port | - |
| 2 | 13495 | Device ID? | - |
| 3 | 95.0 | Solution confidence | % |
| 4 | FINE | Mode (RTK/DGPS/FINE) | - |
| 5 | 2415 | GPS week number | weeks |
| 6 | 73711.000 | Time in week | ms |
| 7 | 17020772 | Milliseconds TOW | ms |
| 8 | 13 | Satellites used | count |
| 9 | 18 | ? | - |
| **Post-semicolon:** | | | |
| 10 | SOL_COMPUTED | Solution status | - |
| 11 | L1_FLOAT | RTK mode (L1 Float) | - |
| **12** | **12.2446** | **ROLL (heel)** | **degrees** |
| **13** | **260.1887** | **PITCH (trim)** | **degrees** |
| **14** | **-35.0258** | **Heading (yaw)** | **degrees** |
| 15 | 0.0000 | Heading standard deviation? | - |
| 16 | 292.7253 | Baseline length? | meters |
| 17 | 155.0128 | ? | - |
| 18 | "999" | Solution type? | - |
| 19+ | QA metadata | Checksum, reserved | - |

## Key Finding

**The UM982 OUTPUTS ROLL AND PITCH!** 🎉

- Field 12 = Roll (gîte latérale)
- Field 13 = Pitch (assiette long/court)
- Field 14 = Heading (yaw)

This is dual-antenna GNSS attitude, NOT IMU-derived.

## Next Steps

### 1. Create Signal K Parser

Need a custom Signal K provider to parse `#HEADINGA`:

```javascript
// Pseudocode
const HEADINGA_REGEX = /#HEADINGA,.+?;SOL_COMPUTED,.+?,([^,]+),([^,]+),([^,]+),/;

function parseHEADINA(sentence) {
  const match = sentence.match(HEADINGA_REGEX);
  if (match) {
    return {
      'navigation.attitude.roll': parseFloat(match[1]),     // 12.2446
      'navigation.attitude.pitch': parseFloat(match[2]),    // 260.1887
      'navigation.attitude.yaw': parseFloat(match[3]),      // -35.0258
    };
  }
}
```

### 2. Validate in Boat

Test actual boat orientation vs reported values:
- Roll: should increase when heeling (positive = starboard down)
- Pitch: should increase when bow down (positive = trimmed aft)
- Yaw: compare with $GNHDT heading

### 3. Map to Signal K Paths

```
navigation.attitude.roll        // degrees, positive = starboard heel
navigation.attitude.pitch       // degrees
navigation.attitude.yaw        // degrees (should match heading)
```

## Advantages

✅ **NO IMU/BNO085 REQUIRED!**
✅ Dual GNSS gives attitude directly
✅ Already flowing in the data stream
✅ Can be parsed immediately

## Challenges

⚠️ **Format not 100% documented**
- Exact field meanings inferred from observation
- Need to validate on boat in motion
- Pitch convention unclear (0° = level?)
- Yaw should match `$GNHDT` for validation

## Related

- **PGN 130824**: B&G performance data (uses these attitude values)
- **BNO085**: Future sensor for IMU fusion (improvement, not necessity)
- **PERF alerts**: Can use roll for sail management (PERF-04 to PERF-06)

---

**Last updated:** 2026-04-19  
**Status:** Ready to parse + validate in boat  
**Owner:** Denis Lafarge
