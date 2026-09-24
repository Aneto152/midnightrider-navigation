# InfluxDB Data Model — SSOT

**Status:** SSOT (Single Source of Truth) for how Midnight Rider data is stored
in InfluxDB, how vessels are identified, and how to query the bucket safely.

**Scope:** identity of vessels, tag schema, source inventory, AIS semantics,
ready-to-use Flux recipes, measured pitfalls, volumetry.

**Out of scope:** instrument specifications (see `docs/HARDWARE/`), setup
procedures (see `docs/INTEGRATION/`), N2K bus topology
(see `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`).

**Last verified:** 2026-09-20, by direct measurement against the live
bucket. Revised the same day: attitude exception (2.2.1) and angular
conventions (4.4).
Every figure below was obtained by counting real points, never by reading an
index. See *Provenance* at the end.

---

## 1. Storage layout

| Item | Value |
|---|---|
| Bucket | `midnight_rider` |
| Organisation | `MidnightRider` |
| Retention | infinite |
| Shard group duration | 7 days (InfluxDB default for infinite retention) |
| Approx. size | 1.2 GB (2026-09-20) |
| Writer | Signal K plugin `signalk-to-influxdb2`, `writeInterval: 1` |
| Separate writer | machine telemetry (`system` measurement), own token, ~31 s period |

One Signal K path maps to one InfluxDB **measurement**. The measurement name is
the full dotted Signal K path, e.g. `navigation.speedThroughWater`.

---

## 2. Vessel identity — the central subtlety

### 2.1 The three identifiers

The bucket contains data for **every vessel the boat can see**, not just
Midnight Rider. On a racing day this means ~1850 to ~2040 distinct vessels.
They are distinguished by the `context` tag.

| Identifier form | Meaning | Who writes it |
|---|---|---|
| `vessels.urn:mrn:signalk:uuid:<uuid>` | **Midnight Rider, onboard instruments** | Signal K self, all onboard sources |
| `vessels.urn:mrn:imo:mmsi:<mmsi>` | an **AIS contact** | AIS receiver, via the N2K bus |
| `vessels.self` | Signal K internal alias | rarely materialised in InfluxDB |

> The MMSI form **always** designates an AIS contact — **including Midnight
> Rider's own AIS echo**, broadcast by our transponder and received back from
> the N2K bus. This is the single most common source of confusion.

### 2.2 The canonical filter: use `self`

Almost every point written for the carrying vessel also carries the tag
`self` with the value `"true"`. AIS contacts never carry this tag.

> **This filter is necessary but not sufficient.** One measured exception
> exists — read 2.2.1 before querying attitude.

```flux
|> filter(fn: (r) => r.self == "true")
```

**This is the canonical way to isolate Midnight Rider.** Prefer it over
hard-coding a UUID or an MMSI:

- it survives a change of MMSI, UUID, transponder or vessel registration;
- it exposes no vessel identifier in a public repository;
- it is the rule the Power BI exporter's README already documents.

Onboard identifiers are intentionally **not written in this document**. Read
them locally when needed:

```bash
python3 -c "import json;print(json.load(open('$HOME/.signalk/baseDeltas.json')))"
```

### 2.2.1 Measured exception — attitude from `N2K.35`

Counted on 2026-09-20 over a 10-minute window (2026-09-05 16:00-16:10 UTC):

| Measurement | Source | `self` | Points |
|---|---|---|---|
| `navigation.attitude.roll` | `Calypso.XX` | `"true"` | 1 038 |
| `navigation.attitude.roll` | `N2K.35` | **absent** | 6 000 |
| `navigation.attitude.pitch` | `N2K.35` | **absent** | 6 000 |
| `navigation.speedThroughWater` | `N2K.35` | `"true"` | 6 000 |

The same physical device (`N2K.35`) writes `speedThroughWater` **with** the
`self` tag and `attitude.roll` / `.pitch` **without** it. Two write paths
coexist for one instrument.

Consequence: `self == "true" and source == "N2K.35"` on attitude returns
**zero rows**. This silently emptied three cockpit panels between the rebuild
and its correction on 2026-09-20.

A full sweep of onboard measurements lacking the `self` tag (AIS contexts
excluded) returned **exactly two**: `navigation.attitude.roll` and
`navigation.attitude.pitch`, both from `N2K.35`. No other onboard measurement
escapes the canonical filter.

**Rule for attitude: filter on `source`, not on `self`.**

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.attitude.roll")
  // N2K.35 does not write the self tag on attitude - filter on the source
  |> filter(fn: (r) => r.source == "N2K.35")
```

Filtering on the source alone is safe here: AIS never transmits attitude, and
over the measured window the measurement had exactly two producers, both
onboard. For a query that must span attitude and other paths at once:

```flux
  |> filter(fn: (r) => r.self == "true" or r.source == "N2K.35")
```

This is a **defect to fix upstream** — the Signal K to InfluxDB write path
should tag attitude like every other onboard path. Until it is fixed, the rule
above is the documented behaviour.

### 2.3 Why the boat's own AIS echo is a poor source

Our AIS transponder broadcasts a small, GPS-derived subset of the boat state.
Measured on 2026-09-05, the MMSI context carried only:

| Measurement | Points / day |
|---|---|
| `navigation.position` | 178 416 |
| `sensors.ais.class` | 89 448 |
| `navigation.speedOverGround` | 89 208 |
| `navigation.courseOverGroundTrue` | 89 206 |
| `navigation.headingTrue` | 89 135 |
| `design.beam` / `design.length` / `design.aisShipType` | 240 each |
| *(unnamed measurement — see Defects)* | 89 688 |

Six usable fields, from the AIS unit's own GPS. Over the same day the onboard
identity carried **more than 70 measurements and ~22 million points**.

**Rule: never build an onboard dashboard on the MMSI context.** Use `self`.

---

## 3. Tag schema

| Tag | Present on | Values | Use |
|---|---|---|---|
| `context` | all points | `vessels.*` | vessel identity |
| `self` | onboard points, **except `navigation.attitude.*` from `N2K.35`** (see 2.2.1) | `"true"` | **canonical onboard filter** |
| `source` | all points | see below | which device or plugin produced it |

Note that `context` has very high cardinality (~2000 on a racing day). Any
query that groups by `context` without a prior filter will fan out into
hundreds of series. See *Query cost*.

---

## 4. Source inventory (onboard)

Measured 2026-09-05, a full day of sailing.

| Source | Nature | Provides |
|---|---|---|
| `N2K.1`, `N2K.2` | two GNSS receivers | `navigation.position`, `speedOverGround`, `courseOverGroundTrue`, `gnss.*`, `magneticVariation`, `datetime` |
| `N2K.35` | hull instrument (log / depth / attitude) | `speedThroughWater`, `water.temperature`, `attitude.roll`, `attitude.pitch`, `depth.belowTransducer`, `navigation.log`, `trip.log` |
| `N2K.116` | barometer | `environment.outside.pressure` |
| `N2K.5`, `N2K.8` | N2K devices | `magneticVariation` |
| `Calypso.XX` | ultrasonic wind + WIT IMU (BLE) | `wind.angleApparent`, `wind.speedApparent`, `outside.temperature`, `batteries.calypso.percent`, `acceleration.x/y/z`, `rateOfTurn`, `attitude.roll/pitch`, `headingMagnetic`, `sensors.wit.quaternion.*` |
| `signalk-truewind-calculator.XX` | plugin | `wind.angleTrueWater`, `wind.angleTrueGround`, `wind.directionTrue`, `wind.speedTrue`, `wind.speedOverGround` |
| `signalk-current-calculator.XX` | plugin | `environment.current.drift`, `environment.current.setTrue` |
| `signalk-heading-true-calculator.XX` | plugin | `navigation.headingTrue` |
| `signalk-j30-leeway.XX` | plugin, J/30 calibrated | `performance.leewayAngle` |
| `course-provider` | Signal K core | `navigation.course.calcValues.*`, `performance.velocityMadeGoodToWaypoint` |

### 4.1 Probable mapping to documented hardware

Cross-referenced with `docs/INDEX.md`. **Not yet confirmed** — confirm by
reading `GET /signalk/v1/api/sources` while the N2K bus is powered, which
returns the device name behind each `N2K.<n>` address.

| Source | Probable device | Datasheet |
|---|---|---|
| `N2K.35` | Airmar DST810 (log, depth, water temp, attitude) | `HARDWARE/AIRMAR-DST810-DATASHEET.md` |
| `N2K.116` | Yacht Devices YDBC-05 barometer | `HARDWARE/YDBC-05-DATASHEET.md` |
| `N2K.1`, `N2K.2` | Unicore UM982 GNSS and/or AIS700 internal GPS | `HARDWARE/UM982-GNSS-DATASHEET.md` |
| `N2K.5`, `N2K.8` | unidentified (Vulcan 7 FS displays?) | — |
| `Calypso.XX` | Calypso UP10 ultrasonic + WIT WT901BLECL, over BLE | `HARDWARE/CALYPSO-UP10-DATASHEET.md` |

Note that N2K device addresses are **not stable across bus restarts**. Pinning
`source` in a dashboard is correct for a given season, but must be re-checked
after any change to the bus. A durable alternative is to pin `_measurement`
plus a distinctive characteristic rather than the raw address.

### 4.2 Redundant measurements — pick one source explicitly

Several paths are written by more than one source. A query that does not pin
`source` will return **several overlapping series**.

| Measurement | Sources | Recommended |
|---|---|---|
| `navigation.attitude.roll` / `.pitch` | `N2K.35`, `Calypso.XX` | **`N2K.35`** (decided 2026-09-20) — filter on `source` only, no `self` tag, see 2.2.1 |
| `navigation.position` | `N2K.1`, `N2K.2` | pin one |
| `navigation.speedOverGround` | `N2K.1`, `N2K.2` (+ AIS echo) | pin one, and filter `self` |
| `navigation.courseOverGroundTrue` | `N2K.1`, `N2K.2` (+ AIS echo) | pin one, and filter `self` |
| `navigation.magneticVariation` | `N2K.1`, `N2K.2`, `N2K.5`, `N2K.8` | pin one |

### 4.3 Units

Signal K publishes SI. InfluxDB stores SI. Convert at query time.

| Quantity | Stored | To display |
|---|---|---|
| speed | m/s | `* 1.94384` → knots |
| angle, heading | radians | `* 180.0 / 3.14159265` → degrees |
| depth | metres | as is |
| temperature | kelvin | `- 273.15` → °C |
| pressure | pascal | `/ 100.0` → hPa |

### 4.4 Angular quantities — never average across the wrap

Signal K publishes two different kinds of angle. Mixing them up produces
graphs that look like sensor noise but are pure display artefacts.

| Path | Stored range | Convention |
|---|---|---|
| `environment.wind.angleApparent` | -pi..+pi | relative to bow, **positive to starboard** |
| `environment.wind.angleTrueWater` / `.angleTrueGround` | -pi..+pi | idem |
| `navigation.attitude.roll` / `.pitch` | small, signed | positive to starboard / bow up |
| `performance.leewayAngle` | small, signed | positive to leeward |
| `navigation.headingTrue` / `.headingMagnetic` | 0..2pi | compass direction |
| `environment.wind.directionTrue` | 0..2pi | compass direction |
| `environment.current.setTrue` | 0..2pi | compass direction |

**Measured on 2026-09-20**: downwind, `angleApparent` oscillates around pi.
Consecutive samples read +176 deg and -167 deg — the same physical direction,
1 degree apart. Plotted raw, the line crosses the whole chart at every
oscillation. Worse, `aggregateWindow(mean)` averages +176 and -167 into 4.5,
a value that corresponds to nothing.

**Rule 1 — wind angles: remap to 0..360 before aggregating.** A sailing boat
never sails with the apparent wind on the nose, so 0/360 is the safe place to
put the discontinuity. Port/starboard is preserved: 0-180 starboard,
180-360 port.

```flux
  |> map(fn: (r) => ({r with _value:
       (if r._value < 0.0 then r._value + 6.28318531 else r._value)
       * 180.0 / 3.14159265}))
```

**Rule 2 — compass directions (heading, wind direction, current set): a plain
mean is invalid.** Averaging 359 deg and 1 deg gives 180 deg, the exact
opposite. Either display instantaneous values (`last()`, no aggregation), or
compute a circular mean:

```flux
import "math"
// mean of the unit vectors, then back to an angle
  |> reduce(identity: {s: 0.0, c: 0.0, n: 0.0}, fn: (r, accumulator) => ({
       s: accumulator.s + math.sin(x: r._value),
       c: accumulator.c + math.cos(x: r._value),
       n: accumulator.n + 1.0}))
  |> map(fn: (r) => ({_value:
       math.atan2(y: r.s, x: r.c) * 180.0 / 3.14159265}))
  |> map(fn: (r) => ({r with _value:
       if r._value < 0.0 then r._value + 360.0 else r._value}))
```

**Rule 3 — small signed angles** (roll, pitch, leeway) never wrap. Plain mean
is correct for them.

Known remaining gap: the cockpit's *Courant — drift et set* panel still takes
a plain mean of `setTrue`. Its direction is unreliable whenever the current
sets near north. Tracked, not yet fixed.


---

## 5. Ready-to-use Flux recipes

### 5.1 Onboard time series (dashboard panel)

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedThroughWater")
  |> filter(fn: (r) => r.self == "true")
  |> filter(fn: (r) => r.source == "N2K.35")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> keep(columns: ["_time", "_value"])
  |> set(key: "_field", value: "Boat speed")
  |> group(columns: ["_field"])
```

### 5.2 Onboard single value (gauge / stat panel)

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.headingTrue")
  |> filter(fn: (r) => r.self == "true")
  |> map(fn: (r) => ({r with _value: r._value * 180.0 / 3.14159265}))
  |> last()
  |> keep(columns: ["_time", "_value"])
```

Always span the **whole selected window** and take `last()`. Never anchor a
gauge to a fixed sub-window such as `date.sub(d: 5m, from: v.timeRangeStop)`:
it returns nothing as soon as the user inspects a past date.

### 5.3 The fleet, excluding ourselves (tactical dashboards)

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> filter(fn: (r) => r.context =~ /urn:mrn:imo:mmsi/)
```

### 5.4 Cheap existence check before an expensive query

```flux
from(bucket: "midnight_rider")
  |> range(start: <day>, stop: <day+1>)
  |> filter(fn: (r) => r._measurement == "<measurement>")
  |> filter(fn: (r) => r.self == "true")
  |> group()
  |> count()
```

---

### 5.5 Boat track for a map panel (Geomap)

`navigation.position` needs its own recipe. It carries a high-cardinality
`s2_cell_id` tag (see 6.5), so the naive query silently pairs a latitude from
one S2 cell with a longitude from another. `group(columns: ["_field"])`
collapses every tag except the field name, which is what makes the `pivot`
trustworthy. `sort` is not optional: without it the route layer draws the
samples out of order.

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.position")
  // Filtre canonique du bord, le meme que pour toutes les autres mesures.
  // Les cibles AIS et les aides a la navigation portent un contexte MMSI
  // et n ont PAS ce tag : elles sont exclues ici, sans filtre de source.
  |> filter(fn: (r) => r.self == "true")
  |> filter(fn: (r) => r._field == "lat" or r._field == "lon")
  // Ecrase les tags s2_cell_id, context et source. Sans cette ligne, le
  // bateau change de cellule S2 en avancant, chaque cellule devient une
  // serie, et le pivot apparie des lat et des lon issues de cellules
  // differentes -> des sauts de 20 milles en 30 secondes.
  |> group(columns: ["_field"])
  // createEmpty reste a false : sur cette mesure les fenetres nulles
  // detruisent la trace (mesure : 70 positions survivantes sur 2880).
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
  |> keep(columns: ["_time", "lat", "lon"])
```

Do **not** add `createEmpty: true` here — see 6.5.

---

## 6. Measured pitfalls

These cost real debugging time on 2026-09-20. Read them before writing a
query or drawing a conclusion.

### 6.1 `aggregateWindow` labels each window by its END

`aggregateWindow(every: 1d, ...)` stamps a bucket with its **stop** boundary.
A row dated `2026-09-08` contains the data of **September 7**. Cross-check any
daily histogram against a `last()` before drawing conclusions.

### 6.2 `schema.*` functions return a SUPERSET of the window

`schema.measurements()`, `schema.tagValues()` and friends read the **series
index**, whose granularity is the shard (7 days here), not the requested
range. Asking for one day can return everything written that week.

**Never conclude from `schema.*` that data exists on a given day.** Count.

### 6.3 Grafana 12 no longer uses the datasource proxy for InfluxDB v2

Testing a panel through `/api/datasources/proxy/` returns
`Authentication to data source failed` even when the datasource works. The
route actually used by panels is:

```
POST /api/ds/query
```

Test through that route, or the diagnosis will be wrong.

### 6.4 High-cardinality scans can freeze the Pi

A query such as `range(start: -400d)` combined with a group-by over `context`
fans out across ~18 000 series and exhausted memory on 2026-09-20, taking the
whole machine down. Systemd journal is volatile on this host, so the crash
left no explanation.

**Always** bound the range, filter before grouping, and escalate in stages:
one hour, then one day. Diagnostic scripts in this project use a memory guard
(floor 2000 MB, abort 1500 MB, max cost 1200 MB).

---

### 6.5 `navigation.position` carries an `s2_cell_id` tag

Measured group key:

```
[_start, _stop, _field, _measurement, context, s2_cell_id, source]
```

`s2_cell_id` is an S2 geographic cell. The boat moves, it crosses a cell
boundary, InfluxDB opens a **new series**. A single day of sailing produced
26 distinct series for one `(measurement, field, source, self)` combination.

Two consequences, both measured on 2026-09-05:

| Query | Rows | Valid positions | Jumps > 1 NM |
|---|---|---|---|
| `createEmpty: true`, no regrouping | 2880 | **70** | 0 (nothing left to jump) |
| `createEmpty: false`, no regrouping | 2880 | 2880 | **28, worst 23.2 NM** |
| `createEmpty: false` + `group(columns: ["_field"])` + `sort` | 2880 | 2880 | see 5.5 |

1. **Never use `createEmpty: true` on `navigation.position`.** `aggregateWindow`
   runs per series, so each S2 cell manufactures a full set of empty windows.
   The `pivot` then drowns the real values in nulls: 70 positions survived out
   of 2880 windows, and the Geomap drew a 3 NM fragment of a 59 NM day.
2. **Always `group(columns: ["_field"])` before aggregating.** Two samples 30 s
   apart cannot be 23 NM apart (that would be 2800 knots). Those jumps were
   latitudes and longitudes from different S2 cells paired by `_time`.

The same trap applies to any future measurement written with a geohash-style
tag. The symptom is always the same: a plausible row count with impossible
values.

---

## 7. Volumetry

Measured on 2026-09-05 (full day of sailing), onboard identity only:

| Measurement | Source | Points / day | Effective rate |
|---|---|---|---|
| `navigation.position` | `N2K.1` | 1 705 120 | ~20 Hz |
| `navigation.position` | `N2K.2` | 1 704 690 | ~20 Hz |
| `environment.water.temperature` | `N2K.35` | 1 061 156 | ~12 Hz |
| `navigation.speedThroughWater` | `N2K.35` | 863 466 | ~10 Hz |
| `navigation.speedThroughWaterReferenceType` | `N2K.35` | 863 466 | ~10 Hz |
| `navigation.attitude.roll` / `.pitch` | `N2K.35` | 863 464 each | ~10 Hz |
| `navigation.datetime` | `N2K.1` + `N2K.2` | 340 253 | ~4 Hz |

**Total: more than 22 million points for a single day.**

This is the root cause of two operational problems:

1. the daily Power BI export overwhelms the Pi;
2. the bucket grew to 1.2 GB with infinite retention and no downsampling.

Several of these paths carry no analytical value at that rate: water
temperature at 12 Hz, `speedThroughWaterReferenceType` (a constant) at 10 Hz,
`navigation.datetime` (the clock) at 4 Hz, and duplicated position from two
GNSS receivers.

**Recommendation (not yet implemented):** a downsampling task and a retention
policy, plus write-side filtering in the Signal K plugin.

---

## 8. Consistency with the Power BI exporter

`tools/influx_powerbi_export/classifier.py` implements the same doctrine as
this document:

```python
if "mmsi" in context and "urn" in context:
    return "ais"
# all remaining records are Midnight Rider onboard data
return "midnight_rider"
```

This is **correct**. Two documentation defects were found alongside it:

| Defect | Detail |
|---|---|
| README vs code | the README states the rule as `self == "true" OR self == ""`; the code never reads the `self` tag |
| Output file name | the README announces `AIS_VESSELS_EVENTS.csv`; the code writes `AIS_EVENTS_RAW.csv` |

A third, unnamed measurement (empty string, 89 688 points/day under the MMSI
context) is written to the bucket and is not documented anywhere.

---

## 9. Provenance

Every figure in this document comes from a counted query run against the live
bucket on 2026-09-20, not from an index or from prior documentation.

| Claim | How it was established |
|---|---|
| onboard identity is the Signal K UUID | counted `environment.wind.*`, `sensors.wit.*`, `performance.*` grouped by `context` — AIS cannot produce these paths |
| `self == "true"` exists | `schema.tagValues(tag: "self", ...)` returned exactly one value |
| attitude from `N2K.35` carries no `self` tag | counted by `(source, self)` over 10 minutes, then a full sweep of onboard measurements without the tag |
| source inventory | counted, grouped by `_measurement` and `source`, 1 h then 24 h |
| AIS field list | counted, filtered on the MMSI context |
| volumetry | same counts, 2026-09-05 |
| `navigation.position` carries `s2_cell_id` | dumped the full group key of a raw sample, then counted valid positions and impossible jumps for three query variants over 2026-09-05 |

Reports are kept on the Pi under `~/diagnostics/`.

---

## 10. Cross-references

- `docs/ARCHITECTURE-MASTER.md` — system overview
- `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md` — N2K bus and PGN flow
- `docs/HARDWARE/` — per-instrument specifications
- `docs/DASHBOARDS-README.md` — Grafana dashboard reference
- `tools/influx_powerbi_export/README.md` — export classification rules

## Measured InfluxDB measurement dictionary — Saturday 2026-09-05 ET

This section is the measured inventory for the complete local ET day
`2026-09-05 00:00–24:00 ET`, queried as the UTC interval
`2026-09-05T04:00:00Z` → `2026-09-06T04:00:00Z`. It is the SSOT for the
observed InfluxDB measurement dictionary. The inventory is empirical: a row
exists only when at least one point was present in that interval.

The table reports the measurement path, fields, source tags, point count and
observed temporal bounds. InfluxDB does not carry a reliable universal unit
schema in the measurement name; a unit marked `UNRESOLVED` must be verified
against the producer and documented here before a selector, detector or
article uses it.

| Measurement | Fields | Sources/tags | Points in day | First → last UTC | Documentation | Storage unit / status |
|---|---|---|---:|---|---|---|
| `<empty>` | `value` | `N2K.0` | 576344 | 2026-09-05T04:00:00.209Z → 2026-09-06T03:59:59.907Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `atonType` | `value` | `N2K.0` | 75434 | 2026-09-05T04:00:01.024Z → 2026-09-06T03:59:59.907Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `design.aisShipType` | `value` | `N2K.0` | 31478 | 2026-09-05T04:00:02.265Z → 2026-09-06T03:59:59.092Z | documented | UNRESOLVED — verify producer contract before use |
| `design.beam` | `value` | `N2K.0` | 43302 | 2026-09-05T04:00:02.265Z → 2026-09-06T03:59:59.092Z | documented | UNRESOLVED — verify producer contract before use |
| `design.draft` | `value` | `N2K.0` | 6358 | 2026-09-05T04:00:18.271Z → 2026-09-06T03:59:58.752Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `design.length` | `value` | `N2K.0` | 43201 | 2026-09-05T04:00:02.265Z → 2026-09-06T03:59:59.092Z | documented | UNRESOLVED — verify producer contract before use |
| `electrical.batteries.calypso.percent` | `value` | `Calypso.XX` | 345004 | 2026-09-05T04:00:00.001Z → 2026-09-06T03:59:59.936Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `electrical.displays.navico.default.brightness` | `value` | `N2K.11`, `N2K.9` | 32 | 2026-09-05T10:19:58.562Z → 2026-09-06T01:17:24.515Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `environment.current.drift` | `value` | `signalk-current-calculator.XX` | 655820 | 2026-09-05T04:00:00.084Z → 2026-09-06T03:59:59.91Z | documented | UNRESOLVED — verify producer contract before use |
| `environment.current.setTrue` | `value` | `signalk-current-calculator.XX` | 655820 | 2026-09-05T04:00:00.084Z → 2026-09-06T03:59:59.91Z | documented | UNRESOLVED — verify producer contract before use |
| `environment.depth.belowTransducer` | `value` | `N2K.35`, `N2K.4` | 86352 | 2026-09-05T04:00:00.558Z → 2026-09-06T03:59:59.116Z | observed — documentation gap | metres in storage |
| `environment.outside.pressure` | `value` | `Calypso.XX`, `N2K.116` | 343782 | 2026-09-05T04:00:00.353Z → 2026-09-06T03:59:59.608Z | documented | pascal in storage |
| `environment.outside.temperature` | `value` | `Calypso.XX` | 345004 | 2026-09-05T04:00:00.001Z → 2026-09-06T03:59:59.936Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `environment.water.temperature` | `value` | `N2K.35` | 1061156 | 2026-09-05T04:00:00.081Z → 2026-09-06T03:59:59.925Z | documented | kelvin in storage |
| `environment.wind.angleApparent` | `value` | `Calypso.XX` | 345004 | 2026-09-05T04:00:00.001Z → 2026-09-06T03:59:59.936Z | documented | UNRESOLVED — verify producer contract before use |
| `environment.wind.angleTrueGround` | `value` | `signalk-truewind-calculator.XX` | 344758 | 2026-09-05T04:00:00Z → 2026-09-06T03:59:59.935Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `environment.wind.angleTrueWater` | `value` | `signalk-truewind-calculator.XX` | 344758 | 2026-09-05T04:00:00Z → 2026-09-06T03:59:59.935Z | documented | radian in storage; signed relative angle |
| `environment.wind.directionTrue` | `value` | `signalk-truewind-calculator.XX` | 344758 | 2026-09-05T04:00:00Z → 2026-09-06T03:59:59.935Z | documented | radian in storage; compass direction |
| `environment.wind.speedApparent` | `value` | `Calypso.XX` | 345004 | 2026-09-05T04:00:00.001Z → 2026-09-06T03:59:59.936Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `environment.wind.speedOverGround` | `value` | `signalk-truewind-calculator.XX` | 344758 | 2026-09-05T04:00:00Z → 2026-09-06T03:59:59.935Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `environment.wind.speedTrue` | `value` | `signalk-truewind-calculator.XX` | 344758 | 2026-09-05T04:00:00Z → 2026-09-06T03:59:59.936Z | observed — documentation gap | m/s |
| `navigation.acceleration.x` | `value` | `Calypso.XX` | 602137 | 2026-09-05T04:00:00.133Z → 2026-09-06T03:59:59.755Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.acceleration.y` | `value` | `Calypso.XX` | 602134 | 2026-09-05T04:00:00.133Z → 2026-09-06T03:59:59.755Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.acceleration.z` | `value` | `Calypso.XX` | 602133 | 2026-09-05T04:00:00.133Z → 2026-09-06T03:59:59.755Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.attitude.pitch` | `value` | `Calypso.XX`, `N2K.35` | 1028002 | 2026-09-05T04:00:00.056Z → 2026-09-06T03:59:59.981Z | documented | radian in storage |
| `navigation.attitude.roll` | `value` | `Calypso.XX`, `N2K.35` | 1028002 | 2026-09-05T04:00:00.056Z → 2026-09-06T03:59:59.981Z | documented | radian in storage |
| `navigation.course.arrivalCircle` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.392Z → 2026-09-06T02:44:02.307Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.bearingMagnetic` | `value` | `course-provider` | 293785 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.bearingTrackMagnetic` | `value` | `course-provider` | 303173 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.bearingTrackTrue` | `value` | `course-provider` | 305205 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.bearingTrue` | `value` | `course-provider` | 295605 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.calcMethod` | `value` | `course-provider` | 309042 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.crossTrackError` | `value` | `course-provider` | 301192 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.distance` | `value` | `course-provider` | 297429 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.estimatedTimeOfArrival` | `value` | `course-provider` | 277794 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.previousPoint.distance` | `value` | `course-provider` | 299317 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.timeToGo` | `value` | `course-provider` | 279589 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.calcValues.velocityMadeGood` | `value` | `course-provider` | 291824 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.nextPoint` | `value` | `N2K.8` | 11 | 2026-09-05T14:52:54.392Z → 2026-09-06T02:44:02.307Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.previousPoint` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.392Z → 2026-09-06T02:44:02.307Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.course.startTime` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.392Z → 2026-09-06T02:44:02.307Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.activeRoute.startTime` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.bearingTrackTrue` | `value` | `N2K.5`, `N2K.8` | 167164 | 2026-09-05T04:00:00.66Z → 2026-09-06T03:59:59.44Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.crossTrackError` | `value` | `N2K.5`, `N2K.8` | 167199 | 2026-09-05T04:00:00.653Z → 2026-09-06T03:59:59.435Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.nextPoint.arrivalCircle` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.nextPoint.bearingTrue` | `value` | `N2K.5`, `N2K.8` | 167164 | 2026-09-05T04:00:00.661Z → 2026-09-06T03:59:59.44Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.nextPoint.distance` | `value` | `N2K.5`, `N2K.8` | 167164 | 2026-09-05T04:00:00.661Z → 2026-09-06T03:59:59.44Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.nextPoint.position` | `value` | `N2K.5`, `N2K.8`, `courseApi` | 167176 | 2026-09-05T04:00:00.661Z → 2026-09-06T03:59:59.44Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.nextPoint.timeToGo` | `value` | `N2K.5`, `N2K.8` | 164385 | 2026-09-05T04:00:00.661Z → 2026-09-06T03:59:59.44Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.nextPoint.value.type` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.nextPoint.velocityMadeGood` | `value` | `N2K.5`, `N2K.8` | 167164 | 2026-09-05T04:00:00.661Z → 2026-09-06T03:59:59.44Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.previousPoint.position` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseGreatCircle.previousPoint.value.type` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseOverGroundTrue` | `value` | `N2K.0`, `N2K.1`, `N2K.2` | 1030015 | 2026-09-05T04:00:00.084Z → 2026-09-06T03:59:59.91Z | documented | radian in storage |
| `navigation.courseRhumbline.activeRoute.startTime` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseRhumbline.crossTrackError` | `value` | `N2K.8` | 2 | 2026-09-05T14:53:23.962Z → 2026-09-05T22:14:11.086Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseRhumbline.nextPoint.arrivalCircle` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseRhumbline.nextPoint.position` | `value` | `N2K.5`, `N2K.8`, `courseApi` | 2830 | 2026-09-05T14:52:54.391Z → 2026-09-06T03:59:59.485Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseRhumbline.nextPoint.value.type` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseRhumbline.previousPoint.position` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.courseRhumbline.previousPoint.value.type` | `value` | `courseApi` | 11 | 2026-09-05T14:52:54.391Z → 2026-09-06T02:44:02.306Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.currentRoute.name` | `value` | `N2K.5`, `N2K.8` | 573 | 2026-09-05T14:52:55.41Z → 2026-09-06T03:59:55.161Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.currentRoute.waypoints` | `value` | `N2K.5`, `N2K.8` | 34367 | 2026-09-05T04:00:01.886Z → 2026-09-06T03:59:56.406Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.datetime` | `value` | `N2K.1`, `N2K.2` | 340253 | 2026-09-05T04:00:00.396Z → 2026-09-06T03:59:59.465Z | documented | UNRESOLVED — verify producer contract before use |
| `navigation.destination.commonName` | `value` | `N2K.0` | 7123 | 2026-09-05T04:00:18.271Z → 2026-09-06T03:59:58.752Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.antennaAltitude` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.geoidalSeparation` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.horizontalDilution` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.integrity` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.methodQuality` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.positionDilution` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.satellites` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.satellitesInView` | `value` | `N2K.1`, `N2K.2` | 169906 | 2026-09-05T04:00:00.723Z → 2026-09-06T03:59:59.834Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.gnss.type` | `value` | `N2K.1`, `N2K.2` | 170081 | 2026-09-05T04:00:00.652Z → 2026-09-06T03:59:59.465Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.headingMagnetic` | `value` | `Calypso.XX` | 164538 | 2026-09-05T04:00:00.379Z → 2026-09-06T03:59:59.981Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.headingTrue` | `value` | `N2K.0`, `signalk-heading-true-calculator.XX` | 439791 | 2026-09-05T04:00:00.379Z → 2026-09-06T03:59:59.981Z | documented | radian in storage |
| `navigation.log` | `value` | `N2K.35` | 86349 | 2026-09-05T04:00:00.266Z → 2026-09-06T03:59:59.119Z | documented | UNRESOLVED — verify producer contract before use |
| `navigation.magneticVariation` | `value` | `N2K.1`, `N2K.2`, `N2K.5`, `N2K.8` | 340282 | 2026-09-05T04:00:00.197Z → 2026-09-06T03:59:59.685Z | documented | UNRESOLVED — verify producer contract before use |
| `navigation.position` | `lat`, `lon` | `N2K.0`, `N2K.1`, `N2K.2` | 4429712 | 2026-09-05T04:00:00.046Z → 2026-09-06T03:59:59.983Z | documented | lat/lon coordinate fields; verify coordinate unit per field |
| `navigation.rateOfTurn` | `value` | `Calypso.XX`, `N2K.0` | 727473 | 2026-09-05T04:00:00.133Z → 2026-09-06T03:59:59.755Z | observed — documentation gap | radian/second in storage |
| `navigation.specialManeuver` | `value` | `N2K.0` | 228181 | 2026-09-05T04:00:01.517Z → 2026-09-06T03:59:59.36Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.speedOverGround` | `value` | `N2K.0`, `N2K.1`, `N2K.2` | 1071538 | 2026-09-05T04:00:00.084Z → 2026-09-06T03:59:59.91Z | documented | m/s |
| `navigation.speedThroughWater` | `value` | `N2K.35` | 863466 | 2026-09-05T04:00:00.073Z → 2026-09-06T03:59:59.914Z | documented | m/s |
| `navigation.speedThroughWaterReferenceType` | `value` | `N2K.35` | 863466 | 2026-09-05T04:00:00.073Z → 2026-09-06T03:59:59.914Z | documented | UNRESOLVED — verify producer contract before use |
| `navigation.state` | `value` | `N2K.0` | 184033 | 2026-09-05T04:00:01.517Z → 2026-09-06T03:59:59.36Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `navigation.trip.log` | `value` | `N2K.35` | 86349 | 2026-09-05T04:00:00.266Z → 2026-09-06T03:59:59.119Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `notifications.ais.AIS12Valarm` | `value` | `N2K.0` | 39 | 2026-09-05T10:47:10.724Z → 2026-09-05T15:41:56.74Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `notifications.ais.unknown113` | `value` | `N2K.0` | 2787 | 2026-09-05T04:00:19.9Z → 2026-09-06T03:59:47.267Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `notifications.navigation.course.perpendicularPassed` | `value` | `course-provider` | 6 | 2026-09-05T20:22:06.81Z → 2026-09-06T02:44:03.169Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `notifications.server.newVersion` | `value` | `signalk-server` | 1 | 2026-09-05T15:44:13.05Z → 2026-09-05T15:44:13.05Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `offPosition` | `value` | `N2K.0` | 75434 | 2026-09-05T04:00:01.024Z → 2026-09-06T03:59:59.907Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `performance.leewayAngle` | `value` | `signalk-j30-leeway.XX` | 164538 | 2026-09-05T04:00:00.377Z → 2026-09-06T03:59:59.979Z | documented | radian in storage; signed |
| `performance.velocityMadeGoodToWaypoint` | `value` | `course-provider` | 290271 | 2026-09-05T04:00:00.474Z → 2026-09-06T03:59:59.939Z | documented | UNRESOLVED — verify producer contract before use |
| `sensors.ais.class` | `value` | `N2K.0` | 552252 | 2026-09-05T04:00:00.209Z → 2026-09-06T03:59:59.907Z | documented | UNRESOLVED — verify producer contract before use |
| `sensors.ais.fromBow` | `value` | `N2K.0` | 30616 | 2026-09-05T04:00:02.265Z → 2026-09-06T03:59:59.093Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.ais.fromCenter` | `value` | `N2K.0` | 28937 | 2026-09-05T04:00:02.265Z → 2026-09-06T03:59:59.093Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.magneticField.x` | `value` | `Calypso.XX` | 49760 | 2026-09-05T04:00:00.62Z → 2026-09-06T03:59:57.688Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.magneticField.y` | `value` | `Calypso.XX` | 49760 | 2026-09-05T04:00:00.621Z → 2026-09-06T03:59:57.688Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.magneticField.z` | `value` | `Calypso.XX` | 49760 | 2026-09-05T04:00:00.621Z → 2026-09-06T03:59:57.688Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.quaternion.w` | `value` | `Calypso.XX` | 164538 | 2026-09-05T04:00:00.379Z → 2026-09-06T03:59:59.982Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.quaternion.x` | `value` | `Calypso.XX` | 164538 | 2026-09-05T04:00:00.379Z → 2026-09-06T03:59:59.982Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.quaternion.y` | `value` | `Calypso.XX` | 164538 | 2026-09-05T04:00:00.379Z → 2026-09-06T03:59:59.982Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.quaternion.z` | `value` | `Calypso.XX` | 164538 | 2026-09-05T04:00:00.379Z → 2026-09-06T03:59:59.982Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `sensors.wit.temperature` | `value` | `Calypso.XX` | 49760 | 2026-09-05T04:00:00.621Z → 2026-09-06T03:59:57.688Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |
| `virtual` | `value` | `N2K.0` | 75434 | 2026-09-05T04:00:01.024Z → 2026-09-06T03:59:59.907Z | observed — documentation gap | UNRESOLVED — verify producer contract before use |

### SSOT rules for future additions or modifications

A new measurement may be added to this dictionary only after the following
metadata is verified from the producer and a real InfluxDB sample:

1. exact `_measurement` and `_field` names;
2. source tag and producer/plugin identity;
3. storage unit and any conversion applied at the MCP boundary;
4. expected refresh rate and whether `aggregateWindow(last)` is valid;
5. whether the source is ambiguous and therefore must be pinned explicitly;
6. first/last observed timestamps and a representative point count;
7. owning SSOT section in this file, with no duplicate PGN table in
   `docs/INTEGRATION/` or `docs/HARDWARE/`;
8. a regression test for the selector, source filter and unit conversion.

Measurements marked `observed — documentation gap` or
`UNRESOLVED — verify producer contract before use` are inventory facts only.
They must not be wired into historical analysis until their producer, units,
source semantics and documentation owner are validated.

This inventory was generated deterministically from InfluxDB. No LLM was
activated and no Telegram publication was performed.
