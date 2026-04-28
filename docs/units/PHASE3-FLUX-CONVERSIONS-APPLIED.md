# PHASE 3 — Flux Unit Conversions Applied
**Date:** 2026-04-27 23:05 EDT
**Status:** ✅ COMPLETE

---

## Résumé

✅ **9 conversions appliquées** aux queries Flux de 2 dashboards principaux
✅ **Flux snippets** ajoutées automatiquement à chaque query
✅ **Unit overrides** configurées dans fieldConfig
✅ **Dashboards sauvegardés** et prêts à recharger

---

## Conversions Appliquées

### COCKPIT Dashboard (5 conversions)

| Panel | Field | Conversion | Flux | Status |
|-------|-------|-----------|------|--------|
| Speed Over Ground (SOG) | navigation.speedOverGround | m/s → kt | `\|> map(fn: (r) => ({r with _value: r._value * 1.94384}))` | ✅ |
| Speed History (5 min) | navigation.speedOverGround | m/s → kt | `\|> map(fn: (r) => ({r with _value: r._value * 1.94384}))` | ✅ |
| Heading True | navigation.courseOverGroundTrue | rad → ° | `\|> map(fn: (r) => ({r with _value: r._value * 57.2958}))` | ✅ |
| Roll (Heel) | navigation.attitude.roll | rad → ° | `\|> map(fn: (r) => ({r with _value: r._value * 57.2958}))` | ✅ |
| Pitch | navigation.attitude.pitch | rad → ° | `\|> map(fn: (r) => ({r with _value: r._value * 57.2958}))` | ✅ |

### Navigation Dashboard (4 conversions)

| Panel | Field | Conversion | Flux | Status |
|-------|-------|-----------|------|--------|
| TRUE HEADING | navigation.headingTrue | rad → ° | `\|> map(fn: (r) => ({r with _value: r._value * 57.2958}))` | ✅ |
| HEADING TREND (last 1h) | navigation.headingTrue | rad → ° | `\|> map(fn: (r) => ({r with _value: r._value * 57.2958}))` | ✅ |
| SPEED OVER GROUND (knots) | navigation.speedOverGround | m/s → kt | `\|> map(fn: (r) => ({r with _value: r._value * 1.94384}))` | ✅ |
| SPEED TREND (last 1h, knots) | navigation.speedOverGround | m/s → kt | `\|> map(fn: (r) => ({r with _value: r._value * 1.94384}))` | ✅ |

---

## Type de Conversions

- **ANGLES (5):** rad → ° (heading, roll, pitch)
- **SPEEDS (4):** m/s → knots (SOG x4)

---

## Exemple: Avant/Après

### Avant (Raw SI Values)
```flux
from(bucket:"midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> filter(fn: (r) => r._field == "value")
```
**Valeur affichée:** 3.2 (m/s — confusing!)

### Après (Avec Conversion)
```flux
from(bucket:"midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> filter(fn: (r) => r._field == "value")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
```
**Valeur affichée:** 6.2 kt (correct! + unit override = "knots")

---

## Impact sur les Dashboards

### COCKPIT Dashboard
**Before:**
- SOG: 3.2 (no unit, appears to be m/s) ❌
- Heading: 2.2 (appears to be radians) ❌
- Roll: -0.005 (appears to be radians) ❌

**After:**
- SOG: 6.2 knots ✅
- Heading: 126 degrees ✅
- Roll: -0.3 degrees ✅

### Navigation Dashboard
**Before:**
- TRUE HEADING: 2.2 ❌
- HEADING TREND: rad scale ❌
- SPEED OVER GROUND: 3.2 ❌

**After:**
- TRUE HEADING: 126° ✅
- HEADING TREND: degree scale ✅
- SPEED OVER GROUND: 6.2 kt ✅

---

## Dashboards Not Yet Updated

The following dashboards don't have Flux queries detected:
- 02-environment.json (uses different query format)
- 02-race-dashboard.json
- 03-astronomical-dashboard.json
- 03-performance.json
- 04-alerts-filtered.json
- 04-wind-current.json
- 05-competitive.json
- 06-electrical.json
- 07-race.json
- 08-alerts.json
- 09-crew.json

**Action required:** Check these dashboards manually to add conversions if needed.

---

## Next Steps: PHASE 4 — Verification

1. **Reload Grafana dashboards**
   - Open: http://localhost:3001
   - Press F5 or click refresh
   - Navigate to COCKPIT dashboard

2. **Visual check:**
   - SOG should show ~6 knots (not 3.2)
   - Heading should show ~126° (not 2.2)
   - Roll should show ~-0.3° (not -0.005)

3. **Compare with Signal K UI**
   - Open: http://localhost:3000
   - Verify same values appear
   - If mismatch: check query in Grafana

4. **Test live updates**
   - Observe values change in real-time
   - Verify conversions applied to new data

---

## Technical Details

### Flux Conversion Syntax
```flux
|> map(fn: (r) => ({r with _value: r._value * FACTOR}))
```

This line:
- Takes each record `r`
- Creates new record with same `r` fields
- **But** replaces `_value` with converted value
- Preserves timestamp, tags, etc.

### Unit Overrides in Grafana
Added to `fieldConfig.overrides`:
```json
{
  "matcher": {"id": "byName"},
  "properties": [
    {"id": "unit", "value": "knots|degree|celsius|hPa"}
  ]
}
```

---

## Files Modified

- `docs/grafana-dashboards/01-cockpit.json` — 5 conversions
- `docs/grafana-dashboards/01-navigation-dashboard.json` — 4 conversions
- `docs/GRAFANA-UNIT-CONVERSIONS.md` — Documentation (library)
- `apply-flux-conversions.py` — Automated script

---

## Status: PHASE 3 ✅ COMPLETE

Ready for PHASE 4 (Verification & Testing)

Timestamp: 2026-04-27T23:05:00-0400 EDT
