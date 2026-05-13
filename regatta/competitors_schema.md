# Competitor Library Schema
*Midnight Rider Navigation System | AIS Watch Foundation*

## File: `regatta/competitors.json`

Master database of competitors in current regatta series.
Used by future `ais_watch.py` script to cross-reference AIS MMSIs.

---

## Top-level structure

```json
{
  "_meta": { ... },
  "competitors": [ ... ]
}
```

### `_meta` object

| Field | Type | Example | Note |
|-------|------|---------|------|
| description | string | "Midnight Rider — Competitor Library" | Self-describing |
| vessel | string | "Midnight Rider — J/30 hull 511" | Our boat |
| fleet | string | "Long Island Sound / Block Island Race Week" | Context |
| updated | string (ISO date) | "2026-05-13" | Last maintained |
| format_version | string | "1.0" | Schema compatibility |
| maintainer | string | "Denis Lafarge" | Who maintains |
| ais_watch_enabled | boolean | true | Watch script active? |
| note | string | "Fill in real MMSI..." | Instructions |

### `competitors[]` array — single competitor object

```json
{
  "id": "competitor_001",
  "active": true,
  "boat_name": "Pegasus",
  "sail_number": "US-12345",
  "skipper": "John Smith",
  "vessel": { ... },
  "ais": { ... },
  "ratings": { ... },
  "events": [ ... ],
  "priority": "high",
  "notes": "..."
}
```

#### competitor[].vessel

```json
{
  "make": "J/Boats",
  "model": "J/30",
  "year": 1983,
  "loa_ft": 29.9,
  "hull_color": "white",
  "keel": "fin"
}
```

#### competitor[].ais

| Field | Type | Note |
|-------|------|------|
| mmsi | string (9 digits) | Marine Mobile Service Identity — **CRITICAL for watch** |
| callsign | string | VHF call sign (often 7 chars) |
| ais_name | string | 20-char name in AIS transponder |
| note | string | How MMSI was verified (cert, MarineTraffic, etc.) |

#### competitor[].ratings

Must include at least one rating system:

| System | Fields | Note |
|--------|--------|------|
| **PHRF_LIS** | `value` (sec/mi), `unit`, `year`, `source`, `note` | Long Island Sound handicap |
| **PHRF_OFFSHORE** | Same structure | NOAA PHRF offshore |
| **IRC** | `TCC` (float), `certificate_number`, `year`, `note` | Time Correction Coefficient |
| **ORR** | `GPH` (float), `certificate_number`, `year`, `note` | General Purpose Handicap (0.9–1.1) |
| **J30_CLASS** | `one_design` (boolean), `note` | One-design class racing |

#### competitor[].events

Array of strings: race names this competitor is entered in.

```json
"events": ["Block Island Race Week 2026", "LIS Championship 2026"]
```

#### competitor[].priority

Racing priority: `"high"`, `"medium"`, `"low"`.
Used by AIS watch to prioritize alerts & Grafana display.

---

## Finding MMSI

1. **AIS transponder certificate** — printed on transponder
2. **MarineTraffic.com** — search boat name + LIS
3. **VHF DSC directory** (marine radio) — stored on VHF
4. **Call your competitor** — ask for it!

⚠️ MMSI is required for AIS watch to work.

---

## Rating systems quick reference

| System | Corrected Time Formula | When Used |
|--------|------------------------|-----------|
| **PHRF** | elapsed − (PHRF × distance) | Local & offshore handicap racing |
| **IRC** | elapsed × TCC | International Class |
| **ORR** | elapsed − (ORR × distance) | Offshore distance racing (rough) |
| **J/30 Class** | elapsed (no adjustment) | Class fleet (one-design) |

### Required fields for each system

| System | Required? | Fields | Example |
|--------|-----------|--------|---------|
| PHRF_LIS | ✅ Yes | value (0–200) | 150 sec/mile |
| PHRF_OFFSHORE | ✅ Yes | value (0–300) | 180 sec/mile |
| IRC | ⚠️ If IRC racing | TCC (0.850–1.150) | 0.985 TCC |
| ORR | ⚠️ If ORR racing | GPH (0.9–1.1) | 0.95 GPH |
| J30_CLASS | ✅ Yes (always) | one_design (true) | true |

#### PHRF corrected time formula
```
Corrected time = Elapsed time − (PHRF × Distance)
Winner = lowest corrected time
```

#### IRC corrected time formula
```
Corrected time = Elapsed time × TCC
Winner = lowest corrected time
```

---

## AIS Watch Script — Integration Points

The future `regatta/ais_watch.py` script will:

1. Load `competitors.json` → extract active MMSIs
2. Poll Signal K `GET /signalk/v1/api/vessels/` every 30s
3. Match AIS targets by MMSI
4. For each matched competitor:
   - Calculate distance (haversine_m) from Midnight Rider
   - Calculate bearing (True)
   - Calculate VMG estimate (if TWA available)
5. Write to InfluxDB measurement `competitor_tracking`
6. Grafana dashboard `COMPETITION` displays relative positions

### Signal K AIS data paths
```
/signalk/v1/api/vessels/{mmsi}/navigation/position
/signalk/v1/api/vessels/{mmsi}/navigation/speedOverGround
/signalk/v1/api/vessels/{mmsi}/navigation/courseOverGroundTrue
/signalk/v1/api/vessels/{mmsi}/name
```

### InfluxDB schema (competitor_tracking measurement)
```
measurement: competitor_tracking
tags:
  - competitor_id (competitor_001, etc.)
  - boat_name
  - mmsi
  - priority (high/medium/low)

fields:
  - distance_m (float) — distance from Midnight Rider
  - bearing_true (float) — bearing degrees True
  - sog_ms (float) — speed over ground m/s
  - cog_true (float) — course over ground degrees True
  - lat (float)
  - lon (float)
  - phrf_lis (integer) — from competitors.json
  - irc_tcc (float) — from competitors.json
```

---

## How to add a competitor

1. Copy a competitor block in `regatta/competitors.json`
2. Fill in: `boat_name`, `skipper`, `sail_number`, `mmsi`, ratings
3. Set `active: true`
4. Increment `id` (competitor_004, etc.)
5. Commit: `git add regatta/competitors.json && git commit -m "regatta: add competitor [name]"`

---
*See also: regatta/ais_watch_architecture.md for the watch script design.*
