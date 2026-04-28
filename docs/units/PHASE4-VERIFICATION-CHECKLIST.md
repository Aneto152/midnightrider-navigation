# PHASE 4 — Verification & Cross-Validation
**Status:** READY FOR EXECUTION
**Date:** 2026-04-27 23:10 EDT

---

## Overview

This phase verifies that all unit conversions are working correctly by:
1. **Visual inspection** of Grafana dashboards
2. **Cross-comparison** with Signal K UI (reference)
3. **Live data testing** with real measurements
4. **Documentation** of all verified conversions

---

## Checklist: Visual Verification

### Step 1: Reload Grafana Dashboard

```
URL: http://localhost:3001
Action: Press F5 or click Refresh button
Wait: 3-5 seconds for data to load
```

### Step 2: Navigate to COCKPIT Dashboard

```
1. Click "Dashboards" menu
2. Search for "COCKPIT" or select from list
3. Wait for all panels to load
4. Verify real-time data appears
```

### Step 3: Verify COCKPIT Values

| Panel | Expected Range | Actual Value | Unit | Status |
|-------|---|---|---|---|
| Speed Over Ground (SOG) | 0-15 kt | ___ | knots | □ OK / □ WRONG |
| Heading True | 0-360 | ___ | degrees | □ OK / □ WRONG |
| Roll (Heel) | -45 to +45 | ___ | degrees | □ OK / □ WRONG |
| Pitch | -30 to +30 | ___ | degrees | □ OK / □ WRONG |
| Course Over Ground | 0-360 | ___ | degrees | □ OK / □ WRONG |

**Expected Values (from Phase 1 audit):**
- SOG: 3.2 m/s × 1.94384 = **6.2 knots**
- Heading: 2.2096 rad × 57.2958 = **126.6 degrees**
- Roll: -0.00518 rad × 57.2958 = **-0.30 degrees**
- Pitch: -0.02291 rad × 57.2958 = **-1.31 degrees**
- Course: 2.2096 rad × 57.2958 = **126.6 degrees**

---

## Checklist: Cross-Validation with Signal K

### Step 1: Open Signal K UI

```
URL: http://localhost:3000
Action: Navigate to Instruments view
```

### Step 2: Find Same Measurements

In Signal K, look for:
- **Navigation** section:
  - headingTrue
  - courseOverGroundTrue
  - speedOverGround
  - attitude.roll
  - attitude.pitch
  - attitude.yaw

### Step 3: Compare Values

| Measurement | Signal K Value | Grafana Value | Match? |
|---|---|---|---|
| Heading True | ___ | ___ | □ YES / □ NO |
| Course Over Ground | ___ | ___ | □ YES / □ NO |
| Speed Over Ground | ___ | ___ | □ YES / □ NO |
| Roll | ___ | ___ | □ YES / □ NO |
| Pitch | ___ | ___ | □ YES / □ NO |

**✅ Values should match exactly** (within 0.1 due to rounding)

If values don't match:
- Check Signal K is showing in same units (degrees, knots, etc.)
- Check Grafana query includes the conversion map
- Reload both dashboards

---

## Checklist: Live Data Verification

### Test 1: Real-Time Updates

```
1. Open COCKPIT dashboard
2. Watch SOG value for 10 seconds
3. Verify it updates smoothly
4. Check unit doesn't change (stays "knots")
5. Verify no gaps in data
```

**Status:** □ PASS / □ FAIL

### Test 2: Heading Change

```
1. If boat is moving, watch Heading value
2. Should change smoothly as boat turns
3. Should stay between 0-360 degrees
4. Should never show extreme values (like 1000°)
```

**Status:** □ PASS / □ FAIL

### Test 3: Roll During Movement

```
1. If boat is heeling, watch Roll value
2. Should be between -45 and +45 degrees
3. Should NOT be showing small decimals like 0.005
4. If showing 0.005: conversion not working ❌
```

**Status:** □ PASS / □ FAIL

---

## Detailed Verification: By Dashboard

### COCKPIT Dashboard

**Panel: Speed Over Ground (SOG)**
- Query measurement: `navigation.speedOverGround`
- Conversion: `× 1.94384`
- Expected: 6.2 knots
- Unit: knots
- Status: □ VERIFIED / □ NEEDS FIX

**Panel: Heading True**
- Query measurement: `navigation.courseOverGroundTrue`
- Conversion: `× 57.2958`
- Expected: 126.6°
- Unit: degrees
- Status: □ VERIFIED / □ NEEDS FIX

**Panel: Roll (Heel)**
- Query measurement: `navigation.attitude.roll`
- Conversion: `× 57.2958`
- Expected: -0.30°
- Unit: degrees
- Status: □ VERIFIED / □ NEEDS FIX

**Panel: Pitch**
- Query measurement: `navigation.attitude.pitch`
- Conversion: `× 57.2958`
- Expected: -1.31°
- Unit: degrees
- Status: □ VERIFIED / □ NEEDS FIX

**Panel: Speed History (5 min)**
- Query measurement: `navigation.speedOverGround`
- Conversion: `× 1.94384`
- Expected: Chart shows 0-10 knot range
- Unit: knots
- Status: □ VERIFIED / □ NEEDS FIX

---

## Troubleshooting: If Values Are Wrong

### Issue: SOG shows 3.2 instead of 6.2

**Diagnosis:** Conversion not applied

**Fix:**
1. Edit panel in Grafana
2. Check query includes: `|> map(fn: (r) => ({r with _value: r._value * 1.94384}))`
3. If missing: add it manually
4. Set unit override: **Unit** → **Velocity > knots**
5. Save panel

### Issue: Heading shows 2.2 instead of 126°

**Diagnosis:** Conversion not applied to this panel

**Fix:**
1. Edit panel
2. Check query includes: `|> map(fn: (r) => ({r with _value: r._value * 57.2958}))`
3. If missing: add it manually
4. Set unit override: **Unit** → **Degrees (0-360)**
5. Save panel

### Issue: Roll shows -0.005 instead of -0.30°

**Diagnosis:** Conversion missing

**Fix:** Same as above, add `|> map(fn: (r) => ({r with _value: r._value * 57.2958}))`

### Issue: Values match Signal K but look wrong

**Examples:**
- SOG = 45 knots (too high for sailing boat) ❌
- Heading = 720° (should be 0-360) ❌
- Roll = 95° (should be -45 to +45) ❌

**Action:** Check if conversion was applied twice (factor × 2)

---

## Sign-Off: Conversions Verified

Once all checks pass, complete this sign-off:

```
PHASE 4 VERIFICATION COMPLETE

Date: _______________
Time: _______________

Verified by: _____________________________

Dashboards checked:
  ✅ COCKPIT (5 panels)
  ✅ Navigation (4 panels)
  ⏳ Others (as needed)

Cross-validation with Signal K: ✅ PASS
Live data verification: ✅ PASS
All unit overrides: ✅ CORRECT

Result: ✅ ALL CONVERSIONS WORKING CORRECTLY

Next phase: PHASE 5 (Final Report)
```

---

## PHASE 5: Final Report Template

Once verified, generate report:

**File:** `docs/UNIT-AUDIT-FINAL-REPORT.md`

**Contents:**
1. Summary of audit (Phases 1-5)
2. Conversions applied count
3. Dashboards updated
4. Verification results
5. Any issues found/fixed
6. Sign-off

**Template:**
```markdown
# Unit Audit Final Report
**Date:** 2026-04-28
**Status:** ✅ COMPLETE

## Summary
- ✅ Phase 1: InfluxDB audit complete
- ✅ Phase 2: Conversion library created
- ✅ Phase 3: Flux conversions applied (9 total)
- ✅ Phase 4: Verification complete
- ✅ Phase 5: Final report generated

## Conversions Summary
- Speeds (m/s → knots): 4 panels
- Angles (rad → °): 5 panels
- Temperature (K → °C): 0 panels (not yet in live data)
- Pressure (Pa → hPa): 0 panels (not yet in live data)

## Dashboards Updated
✅ COCKPIT (5 conversions)
✅ Navigation (4 conversions)
⚠️  Others (need manual review)

## Sign-Off
All conversions verified and working correctly.
System ready for May 19 field test and May 22 race day.
```

---

## Status: PHASE 4 READY

**Next action:** Execute verification checklist above

**Time estimate:** 10-15 minutes

**Timestamp:** 2026-04-27T23:10:00-0400 EDT
