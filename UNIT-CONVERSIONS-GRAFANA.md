# Unit Conversions — Signal K to Grafana
**Complete audit and fixes for all 20+ measurements**

---

## Problem Statement

Signal K uses SI units (radians, m/s, Kelvin, Pascal) but Grafana dashboards should display in nautical units:
- **Angles:** radians (rad) → degrees (°)
- **Speeds:** meters/second (m/s) → knots (kt)
- **Temperature:** Kelvin (K) → Celsius (°C)
- **Pressure:** Pascal (Pa) → hectopascal (hPa)

**Current state:** Dashboards show raw Signal K values (wrong units).
**Required:** Apply Grafana unit overrides and/or field transformations.

---

## Conversion Factors

| From | To | Formula | Factor |
|------|----|---------| -------|
| rad | ° | × 57.2958 | 57.2958 |
| m/s | kt | × 1.94384 | 1.94384 |
| K | °C | − 273.15 | −273.15 (offset) |
| Pa | hPa | ÷ 100 | 0.01 |

---

## 20+ Measurements to Convert

### 1. ANGLES: Radians → Degrees (10 total)

#### Navigation Attitude
| Path | Dashboard | Method |
|------|-----------|--------|
| navigation.attitude.roll | COCKPIT, PERFORMANCE | Multiply by 57.2958 |
| navigation.attitude.pitch | COCKPIT, PERFORMANCE | Multiply by 57.2958 |
| navigation.attitude.yaw | PERFORMANCE | Multiply by 57.2958 |

**Grafana Fix:**
1. Open dashboard
2. Edit panel → Overrides → Add override
3. Match field: `navigation.attitude.roll`
4. Add override: **Unit** → **Degrees (°)**
5. Or: Add transformation: **Math** → `* 57.2958`

#### Navigation Course/Heading
| Path | Dashboard | Method |
|------|-----------|--------|
| navigation.headingTrue | COCKPIT | Multiply by 57.2958 |
| navigation.courseOverGroundTrue | COCKPIT, RACE | Multiply by 57.2958 |

**Grafana Fix:** Same as above (unit override to **Degrees**)

#### Wind Angles
| Path | Dashboard | Method |
|------|-----------|--------|
| environment.wind.directionTrue | WIND, PERFORMANCE | × 57.2958 |
| environment.wind.angleApparent | WIND | × 57.2958 |
| environment.wind.angleTrueWater | WIND, PERFORMANCE | × 57.2958 |

**Grafana Fix:** Unit override to **Degrees (°)**

#### Derived Angles
| Path | Dashboard | Method |
|------|-----------|--------|
| navigation.leewayAngle | PERFORMANCE | × 57.2958 |
| performance.current.direction | PERFORMANCE, WEATHER | × 57.2958 |

**Grafana Fix:** Unit override to **Degrees (°)**

---

### 2. SPEEDS: m/s → Knots (6 total)

#### Boat Speeds
| Path | Dashboard | Method |
|------|-----------|--------|
| navigation.speedOverGround | COCKPIT, PERFORMANCE, RACE | × 1.94384 |
| navigation.speedThroughWater | PERFORMANCE | × 1.94384 |

**Grafana Fix:**
1. Open dashboard
2. Edit panel → Overrides → Add override
3. Match field: `navigation.speedOverGround`
4. Add override: **Unit** → **Velocity > knots**
5. Or: Add transformation: **Math** → `* 1.94384`

#### Wind Speeds
| Path | Dashboard | Method |
|------|-----------|--------|
| environment.wind.speedTrue | WIND, PERFORMANCE | × 1.94384 |
| environment.wind.speedApparent | WIND | × 1.94384 |

**Grafana Fix:** Same as above (unit override to **knots**)

#### Derived Speeds
| Path | Dashboard | Method |
|------|-----------|--------|
| performance.velocityMadeGood | PERFORMANCE | × 1.94384 |
| performance.current.speed | PERFORMANCE, WEATHER | × 1.94384 |

**Grafana Fix:** Unit override to **knots**

---

### 3. TEMPERATURE: K → °C (2 total)

| Path | Dashboard | Method |
|------|-----------|--------|
| environment.outside.temperature | ENVIRONMENT | − 273.15 |
| environment.water.temperature | ENVIRONMENT | − 273.15 |

**Grafana Fix:**
1. Open dashboard
2. Edit panel → Transformations → Add transformation
3. Choose: **Organize fields** or **Math**
4. Apply: `value - 273.15`
5. Set unit override to: **Temperature > Celsius (°C)**

**Alternative:** Use Grafana unit override if it supports Kelvin→Celsius conversion.

---

### 4. PRESSURE: Pa → hPa (1 total)

| Path | Dashboard | Method |
|------|-----------|--------|
| environment.outside.pressure | ENVIRONMENT | ÷ 100 |

**Grafana Fix:**
1. Open dashboard
2. Edit panel → Overrides → Add override
3. Match field: `environment.outside.pressure`
4. Add override: **Unit** → **Pressure > hectopascal (hPa)**
5. Or: Add transformation: **Math** → `/ 100`

---

## Step-by-Step Fix Instructions

### For Each Dashboard:

**1. COCKPIT Dashboard**
Panels to fix:
- Speed Over Ground (SOG) → × 1.94384 (m/s → kt)
- Heading True → × 57.2958 (rad → °)
- Roll (Heel) → × 57.2958 (rad → °)
- Pitch → × 57.2958 (rad → °)

Steps:
1. Open: http://localhost:3001/d/01-cockpit
2. Click: **Edit** (pencil icon)
3. For each panel:
   - Click panel title → **Edit**
   - Go to: **Overrides** tab
   - Click: **Add override** or **Add field override**
   - Select field matching the measurement name
   - Add **Unit** override with correct conversion
   - Save

**2. PERFORMANCE Dashboard**
Panels to fix (most conversions here):
- Speed Through Water → × 1.94384
- VMG → × 1.94384
- All angles → × 57.2958
- Current speed → × 1.94384
- Current direction → × 57.2958

**3. WIND & CURRENT Dashboard**
Panels to fix:
- True Wind Speed → × 1.94384
- Apparent Wind Speed → × 1.94384
- Wind Direction → × 57.2958
- Apparent Wind Angle → × 57.2958

**4. ENVIRONMENT Dashboard**
Panels to fix:
- Outside Temperature → − 273.15
- Water Temperature → − 273.15
- Pressure → ÷ 100

---

## Alternative: Use Unit Override in Grafana UI

**Fastest method:**

1. Go to dashboard
2. Click panel **Edit**
3. Scroll right to **Overrides** section
4. Click **+ Add override**
5. Choose **Match all fields**
6. Add override property: **Unit**
7. Set value to correct unit:
   - `degree` (for angles)
   - `velocityms` → change to `velocity` unit type
   - `temp` → `celsius`
   - `pressure` → `hPa`

---

## Alert Rules Unit Fixes

Same conversions apply to alert rules in `alert-rules-complete.yaml`:

### Examples:

```yaml
# ALERT: Critical Heel
# Current: checks if roll > 0.436 (rad)
# Should be: checks if roll > 0.436 rad (which is ~25°)
# Fix: Leave threshold, but document in description that 0.436 rad = 25°

# ALERT: Shallow Water
# Current: depth < 4 (already in meters, correct)
# No fix needed

# ALERT: Wind Shift
# Current: wind direction change > 15°/3min
# Already in degrees (after conversion), OK

# ALERT: Speed Alerts
# Current: comparing m/s values
# Should convert thresholds to kt or apply unit override
# Example: if VMG < 2 m/s (actual), set threshold to 2 m/s in alert
```

---

## Implementation Plan

### Phase 1: Audit (DONE)
- ✅ Identified 20+ measurements needing conversion
- ✅ Documented conversion factors
- ✅ Listed affected dashboards and panels

### Phase 2: Fix Dashboards (TO DO)
1. Fix COCKPIT dashboard (5 panels)
2. Fix PERFORMANCE dashboard (12 panels)
3. Fix WIND & CURRENT dashboard (6 panels)
4. Fix ENVIRONMENT dashboard (3 panels)
5. Fix COMPETITIVE dashboard (if any speed/angle panels)
6. Fix RACE dashboard (if any angle panels)

### Phase 3: Fix Alerts (TO DO)
1. Review all alert thresholds
2. Add unit context in alert descriptions
3. Ensure alert thresholds use correct units

### Phase 4: Verify (TO DO)
1. Check each dashboard visually
2. Verify numbers make sense (e.g., speed < 10 kt, not < 0.5 m/s)
3. Test alert firing with correct unit interpretation

---

## Quick Reference: Grafana Unit Names

| Conversion | Grafana Unit Name |
|-----------|-------------------|
| rad → ° | `degree` or `degrees` |
| m/s → kt | `velocitymeterssec` (needs math transform) → select `velocity` type |
| K → °C | `celsius` (may need math: `value - 273.15`) |
| Pa → hPa | `hPa` or `hectopascal` |

---

## Tools Available

**Option 1: Manual UI Override**
- Slowest but most visual
- Edit each panel, add override

**Option 2: Field Transformation**
- Add transformation in panel query
- Apply math: `* 57.2958` or `- 273.15`

**Option 3: Auto-conversion Script**
- Can create Python script to modify all dashboard JSONs
- Apply conversions automatically
- Upload fixed dashboards back to Grafana

**Option 4: Grafana Plugin**
- Some plugins offer auto-conversion
- Might be overkill for this use case

---

## Example: Roll Angle Fix

**Before:**
- Panel shows: `0.436` (radians, confusing)
- No unit indicator

**After (Option A - Unit Override):**
- Panel shows: `25.0°` (degrees, clear)
- Unit label visible

**After (Option B - Math Transform):**
- Query: `field_value * 57.2958`
- Panel shows: `25.0°`

---

## Status

| Component | Status | Priority |
|-----------|--------|----------|
| COCKPIT | ❌ Needs fixing | HIGH |
| PERFORMANCE | ❌ Needs fixing | HIGH |
| WIND & CURRENT | ❌ Needs fixing | HIGH |
| ENVIRONMENT | ❌ Needs fixing | MEDIUM |
| COMPETITIVE | ⚠️ Check if needed | LOW |
| RACE | ⚠️ Check if needed | LOW |
| Alert Rules | ❌ Needs review | MEDIUM |

---

## Next Steps

1. **Decide approach:** Manual UI vs Python script vs Grafana plugins
2. **Start with COCKPIT:** Most critical, visible to crew
3. **Test conversions:** Verify numbers make sense
4. **Update alerts:** Ensure thresholds use correct logic
5. **Document:** Update dashboards with unit labels
6. **Field test (May 19):** Verify all conversions look correct

---

**Ready to fix? Let me know which approach you prefer!** 🚀
