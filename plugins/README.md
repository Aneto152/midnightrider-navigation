# plugins/ — Midnight Rider Signal K Plugins

Custom Signal K plugins for the Midnight Rider J/30 navigation system.

> Last updated: 2026-05-29  
> Signal K runs via: systemctl (never Docker on this boat)

---

## ⚠️ MULTI-SOURCE DESIGN

Both `signalk-um982-proprietary.js` and `signalk-wit-nmea.js` write to `navigation.attitude.*`.  
This is **intentional** — Signal K tags each value with its source label. Both coexist:

| Source | Roll/Pitch | Yaw | Update rate | Value type |
|--------|-----------|-----|-------------|-----------|
| **wit-nmea** | IMU accelerometer (physical mount) | Magnetic | Real-time (~10 Hz) | Measured values |
| **um982-proprietary** | RTK GNSS dual-antenna | True (GPS) | ~1 Hz | RTK-computed attitudes |

To filter by source in Grafana, add to your Flux query:
```flux
|> filter(fn: (r) => r["source"] == "wit-nmea")
```

---

## 📋 PLUGIN REFERENCE

### 1. signalk-astronomical.js — Astronomical Data + Tides

Computes sun/moon times and fetches NOAA tide predictions for sailing decisions.

**Package:** `plugins/signalk-astronomical-package.json`  
**Version:** 1.1.0  
**Dependencies:** suncalc (npm), axios (npm, optional for tides)

**Signal K paths produced:**

| Path | Type | Description |
|------|------|-------------|
| `environment.sun.sunriseTime` | ISO datetime | Sunrise for today |
| `environment.sun.sunsetTime` | ISO datetime | Sunset for today |
| `environment.moon.moonriseTime` | ISO datetime | Moonrise for today |
| `environment.moon.moonsetTime` | ISO datetime | Moonset for today |
| `environment.moon.illumination` | 0.0–1.0 | Moon illumination fraction |
| `environment.moon.phase` | string | Phase name (new_moon, full_moon, etc.) |
| `environment.tide.tideHighTime` | ISO datetime | Next high tide |
| `environment.tide.tideHighLevel` | meters | High tide level (MLLW) |
| `environment.tide.tideLowTime` | ISO datetime | Next low tide |
| `environment.tide.tideLowLevel` | meters | Low tide level (MLLW) |

**Configuration:**
```json
{
  "enabled": true,
  "debug": false,
  "noaaStation": "8518750"
}
```

Station `8518750` = NY Harbor. See [NOAA station finder](https://www.noaa.gov/).

**Update frequency:** Once per day (checks hourly). Data fetched on startup.

**Deployment:**
```bash
mkdir -p ~/.signalk/plugins/signalk-astronomical
cp plugins/signalk-astronomical.js ~/.signalk/plugins/signalk-astronomical/
cp plugins/signalk-astronomical-package.json ~/.signalk/plugins/signalk-astronomical/package.json
cd ~/.signalk/plugins/signalk-astronomical && npm install suncalc axios
systemctl restart signalk
```

---

### 2. signalk-um982-proprietary.js — UM982 RTK Attitude Parser

Parses `#HEADINGA` proprietary sentences from the Unicore UM982 dual-antenna GNSS.  
Standard NMEA0183 parsers ignore these non-standard sentences (they start with `#`, not `$`).

**Package:** `plugins/signalk-um982-package.json`  
**Version:** 1.0.0  
**Dependencies:** none (pure Node.js)

**Signal K paths produced:**

| Path | Unit | Description |
|------|------|-------------|
| `navigation.attitude.roll` | radians | Heel angle (+ = starboard) |
| `navigation.attitude.pitch` | radians | Trim angle (+ = bow up) — **normalized from Unicore 0-360°** |
| `navigation.attitude.yaw` | radians | True heading from dual-antenna baseline |
| `navigation.attitude.yawReference` | string | Always `"TRUE"` (GPS-based) |
| `navigation.rtkMode` | string | RTK solution mode (L1_FLOAT, FIXED, etc.) |
| `navigation.gnssPositionStatus` | string | Solution status (SOL_COMPUTED, etc.) |
| `navigation.baselineDistance` | meters | Antenna separation |

**Implementation notes:**

- Hooks into `app.on('nmea0183out')` to intercept raw NMEA stream
- Discards sentences with `INSUFFICIENT_OBS` or `NONE` status (no valid RTK fix)
- **Pitch normalized from Unicore 0-360° to Signal K -180°/+180°** (bugfix 2026-05-29)
- Values in degrees converted to radians (Signal K internal standard)

**Example sentence:**
```
#HEADINGA,COM1,13495,95.0,FINE,2415,73711.000,17020772,13,18;SOL_COMPUTED,L1_FLOAT,12.24,260.18,-35.02,0.0000,292.72,155.01,"999",29,7,7,0,3,00,0,51*checksum
```

**Post-semicolon field map:**
- [0] Solution status (`SOL_COMPUTED`)
- [1] RTK mode (`L1_FLOAT`, `FIXED`)
- [2] Roll degrees → normalized → radians → `navigation.attitude.roll`
- [3] Pitch degrees → normalize 0-360 to -180/+180 → radians → `navigation.attitude.pitch` **(BUGFIXED)**
- [4] Yaw degrees → radians → `navigation.attitude.yaw`
- [5] Heading std dev
- [6] Baseline distance (meters)

**Deployment:**
```bash
mkdir -p ~/.signalk/plugins/signalk-um982-proprietary
cp plugins/signalk-um982-proprietary.js ~/.signalk/plugins/signalk-um982-proprietary/
cp plugins/signalk-um982-package.json ~/.signalk/plugins/signalk-um982-proprietary/package.json
systemctl restart signalk
```

**Grafana — convert radians to degrees:**
```flux
|> map(fn: (r) => ({ r with _value: r._value * 180.0 / 3.14159 }))
```

**Troubleshooting:**

```bash
# Check UM982 is sending #HEADINGA sentences
cat /dev/ttyUSB0 | grep HEADINGA

# Check Signal K is receiving attitude data
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

# If pitch values > 180° (before bugfix)
# → Plugin now normalizes automatically
```

---

### 3. signalk-wit-nmea.js — WIT IMU NMEA Parser

Parses `$HEATT` attitude sentences from the WIT WT901BLECL BLE IMU.

**Package:** `plugins/signalk-wit-nmea-package.json`  
**Version:** 1.0.0  
**Dependencies:** none (pure Node.js)

**Signal K paths produced:**

| Path | Unit | Description |
|------|------|-------------|
| `navigation.attitude.roll` | radians | Heel (WIT Pitch field, remapped) |
| `navigation.attitude.pitch` | radians | Trim (WIT Roll field, remapped) |
| `navigation.attitude.yaw` | radians | Magnetic heading (post-calibration) |
| `navigation.attitude` | object | Composite for PGN 127257 → Vulcan 7 |

**⚠️ AXIS REMAPPING (verified physically by Denis, 2026-05-17):**
- WIT Pitch (field[1]) → SK roll (gîte bâbord/tribord)
- WIT Roll (field[0]) → SK pitch (assiette étrave haut/bas)  
- WIT Yaw (field[2]) → SK yaw (cap magnétique)

**Do not change without physical re-verification on the boat.**

**Note:** `$HEHDT` (heading true) is already parsed by the kflex NMEA0183 provider.  
This plugin only handles `$HEATT` (attitude sentences that kflex cannot map).

**Deployment:**
```bash
mkdir -p ~/.signalk/plugins/signalk-wit-nmea
cp plugins/signalk-wit-nmea.js ~/.signalk/plugins/signalk-wit-nmea/
cp plugins/signalk-wit-nmea-package.json ~/.signalk/plugins/signalk-wit-nmea/package.json
systemctl restart signalk
```

---

## 🔧 DEPLOYMENT WORKFLOW

To deploy a modified plugin to Signal K on the Pi:

```bash
# 1. Copy to Signal K plugins directory
PLUGIN=signalk-astronomical  # or signalk-um982-proprietary or signalk-wit-nmea
mkdir -p ~/.signalk/plugins/$PLUGIN
cp plugins/$PLUGIN.js ~/.signalk/plugins/$PLUGIN/
# Copy the matching package.json as standard package.json:
cp plugins/$PLUGIN-package.json ~/.signalk/plugins/$PLUGIN/package.json

# 2. Install dependencies (if any)
cd ~/.signalk/plugins/$PLUGIN
npm install  # reads package.json dependencies

# 3. Restart Signal K
systemctl restart signalk

# 4. Verify plugin appears in Signal K Admin UI
# → http://localhost:3000/admin → Plugins tab
```

---

## 🔍 TROUBLESHOOTING

| Symptom | Action |
|---------|--------|
| Plugin not appearing in Admin UI | `journalctl -u signalk -n 50 \| grep -i error` |
| No attitude data | `curl localhost:3000/signalk/v1/api/vessels/self/navigation/attitude` |
| Values seem wrong | Enable `debug: true` in plugin config, check SK logs |
| Astronomical data stale | Plugin updates once/day — check `lastUpdateDate` in SK logs |
| UM982 pitch > 180° | Plugin now normalizes automatically (fix 2026-05-29) |

---

## 🔗 Related Documentation

- **Architecture:** docs/ARCHITECTURE-REFERENCE-2026-05-20.md
- **Data schema:** docs/DATA-SCHEMA-MASTER.md
- **UM982 datasheet:** docs/HARDWARE/UM982-GNSS-DATASHEET.md
- **WIT datasheet:** docs/HARDWARE/WIT-WT901BLECL-DATASHEET.md

---

**Status:** Production (post-audit 2026-05-29)  
**Last bugfix:** UM982 pitch normalization (2026-05-29)  
**Deployment required:** Copy `signalk-um982-proprietary.js` to Pi and restart Signal K
