# Conversions d'unités — Queries Flux pour Grafana
**Signal K → Unités d'Affichage Nautiques**

---

## Vue d'ensemble

Signal K stocke **toutes** les données en unités SI. Grafana doit appliquer des transformations pour afficher en unités nautiques/pratiques.

**Règle absolue:** Les conversions se font **DANS les queries Flux**, JAMAIS en modifiant InfluxDB.

---

## Conversions de Base

### 1. m/s → Knots (Vitesses)

**Formule:** `valeur_m/s × 1.94384 = valeur_knots`

**Champs concernés:**
- `navigation.speedOverGround`
- `navigation.speedThroughWater`
- `environment.wind.speedTrue`
- `environment.wind.speedApparent`
- `performance.velocityMadeGood`
- `performance.current.speed`

**Snippet Flux:**
```flux
|> map(fn: (r) => ({r with _value: r._value * 1.94384}))
```

**Exemple complet:**
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
```

---

### 2. Radians → Degrés (Angles)

**Formule:** `valeur_rad × 57.2958 = valeur_°`

**Champs concernés:**
- `navigation.attitude.roll` (gîte)
- `navigation.attitude.pitch` (assiette)
- `navigation.attitude.yaw` (rotation)
- `navigation.headingTrue`
- `navigation.headingMagnetic`
- `navigation.courseOverGroundTrue`
- `environment.wind.directionTrue`
- `environment.wind.directionMagnetic`
- `environment.wind.angleApparent`
- `environment.wind.angleTrueWater`
- `navigation.leewayAngle`
- `performance.current.direction`

**Snippet Flux:**
```flux
|> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

**Exemple complet:**
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.attitude.roll")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

---

### 3. Kelvin → Celsius (Température)

**Formule:** `valeur_K − 273.15 = valeur_°C`

**Champs concernés:**
- `environment.water.temperature`
- `environment.outside.temperature`

**Snippet Flux:**
```flux
|> map(fn: (r) => ({r with _value: r._value - 273.15}))
```

**Exemple complet:**
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "environment.water.temperature")
  |> map(fn: (r) => ({r with _value: r._value - 273.15}))
```

---

### 4. Pascal → Hectopascal (Pression)

**Formule:** `valeur_Pa ÷ 100 = valeur_hPa`

**Champs concernés:**
- `environment.outside.pressure`

**Snippet Flux:**
```flux
|> map(fn: (r) => ({r with _value: r._value / 100.0}))
```

**Exemple complet:**
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "environment.outside.pressure")
  |> map(fn: (r) => ({r with _value: r._value / 100.0}))
```

---

## Conversions Composées

### Exemple 1: Vitesse + Unit Override

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
  |> map(fn: (r) => ({r with _field: "SOG (knots)"}))
```

Puis dans le panel Grafana:
- **Unit:** Velocity > knots
- **Decimal places:** 1

### Exemple 2: Angle + Unit Override

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.attitude.roll")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
  |> map(fn: (r) => ({r with _field: "Roll (degrees)"}))
```

Puis dans le panel Grafana:
- **Unit:** Degrees (0-360)
- **Decimal places:** 1

---

## Template Prêt à Copier-Coller

### SOG en knots
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
```

### Heading en degrés
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.headingTrue")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

### Roll (Gîte) en degrés
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.attitude.roll")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

### Pitch (Assiette) en degrés
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.attitude.pitch")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

### Course Over Ground en degrés
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.courseOverGroundTrue")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

### Wind Direction en degrés
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "environment.wind.directionTrue")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

### Water Temperature en °C
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "environment.water.temperature")
  |> map(fn: (r) => ({r with _value: r._value - 273.15}))
```

### Barometer Pressure en hPa
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "environment.outside.pressure")
  |> map(fn: (r) => ({r with _value: r._value / 100.0}))
```

---

## Applying to Grafana Panels

### Step-by-Step:

1. **Open dashboard** → Click panel to edit
2. **Go to Query section** (bottom)
3. **Find the `from(bucket: ...)` line**
4. **Locate the last `|>` before `|> drop()`**
5. **Add conversion line** before the drop
6. **Set Unit Override:**
   - Panel options → Field config
   - Unit: Select appropriate unit
7. **Save panel**

### Example: COCKPIT SOG Panel

**Before:**
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
```

**After (with conversion):**
```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
```

**Unit settings:**
- Field config → Unit → **Velocity > knots**

---

## Checklist: Panels à Corriger

### COCKPIT Dashboard
- [ ] Speed Over Ground (m/s → kt)
- [ ] Heading True (rad → °)
- [ ] Roll (rad → °)
- [ ] Pitch (rad → °)
- [ ] Course Over Ground (rad → °)

### PERFORMANCE Dashboard
- [ ] Speed Through Water (m/s → kt)
- [ ] VMG (m/s → kt)
- [ ] All angles (rad → °)
- [ ] Current speed (m/s → kt)
- [ ] Current direction (rad → °)

### WIND & CURRENT Dashboard
- [ ] True Wind Speed (m/s → kt)
- [ ] Apparent Wind Speed (m/s → kt)
- [ ] Wind Direction (rad → °)
- [ ] Apparent Wind Angle (rad → °)
- [ ] Wind True Water Angle (rad → °)

### ENVIRONMENT Dashboard
- [ ] Water Temperature (K → °C)
- [ ] Outside Temperature (K → °C)
- [ ] Pressure (Pa → hPa)

---

## Testing

After each conversion:

1. **Open panel** and verify displayed value looks reasonable
2. **Compare with Signal K UI** (http://localhost:3000) — same value?
3. **Check unit label** — is it shown correctly?
4. **Verify decimals** — not too many, not too few

**Expected values (for reference):**
- SOG: 0-15 knots (typical sailing)
- STW: 0-15 knots
- Heading: 0-360 degrees
- Roll: -45 to +45 degrees (extreme: 90 = capsized)
- Pitch: -30 to +30 degrees
- Wind speed: 0-40 knots
- Water temp: -2 to +35°C
- Pressure: 950-1050 hPa

---

## Status: PHASE 2 ✅ COMPLETE

Date: 2026-04-27 22:55 EDT
Ready for PHASE 3 (Grafana panel updates)

---

## 5. Rate of Turn — rad/s → °/s

Signal K path: `navigation.rateOfTurn`
Signal K unit: rad/s (SI)
Display unit: °/s

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "navigation.rateOfTurn")
  |> filter(fn: (r) => r["_field"] == "value")
  |> aggregateWindow(every: 5s, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

---

## 6. CPU Temperature — K → °C (Raspberry Pi system stats)

Signal K path: `environment.system.cpuTemperature`
Signal K unit: Kelvin (K)
Display unit: °C
Source: `signalk-system-stats`

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "environment.system.cpuTemperature")
  |> filter(fn: (r) => r["_field"] == "value")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({r with _value: r._value - 273.15}))
```

---

## 7. SOK BMS Battery Data (direct InfluxDB — no SI conversion)

> The SOK BMS reader writes directly to InfluxDB measurement sok_bms.
> Data is already in display units — no conversion needed in Grafana.
> Source: signalk-um982-proprietary is NOT involved — SOK bypasses Signal K.
> Refresh: 0.2 Hz (1 read per 5s — BLE battery hardware limitation).

| Field | Unit stored | Display | Grafana unit |
|-------|------------|---------|--------------|
| voltage_v | V | V | none |
| current_a | A | A | none |
| soc_pct | % | % | none |
| temp_bms_c | °C | °C | none |
| temp_mos_c | °C | °C | none |
| capacity_ah | Ah | Ah | none |

```flux
// Battery SOC example
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "sok_bms")
  |> filter(fn: (r) => r["_field"] == "soc_pct")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
```

---

## 8. State of Charge — ratio 0–1 → % (when via Signal K)

Signal K path: `electrical.batteries.house.stateOfCharge`
Signal K unit: ratio 0–1 (SI)
Display unit: %

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "electrical.batteries.house.stateOfCharge")
  |> filter(fn: (r) => r["_field"] == "value")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({r with _value: r._value * 100.0}))
```

---

## Standard aggregateWindow Reference

| Dashboard | Auto-refresh | Recommended aggregateWindow |
|-----------|-------------|----------------------------|
| COCKPIT | 5s | every: 5s, fn: mean |
| PERFORMANCE | 5s | every: 5s, fn: mean |
| RACE | 5s | every: 5s, fn: mean |
| WIND & CURRENT | 10s | every: 10s, fn: mean |
| ALERTS | 10s | every: 10s, fn: last |
| ENVIRONMENT | 30s | every: 30s, fn: mean |
| ELECTRICAL | 30s | every: 30s, fn: mean |
| COMPETITIVE | 30s | every: 30s, fn: mean |
| CREW | 30s | every: 30s, fn: last |

> Always use createEmpty: false to avoid null gaps in charts.
