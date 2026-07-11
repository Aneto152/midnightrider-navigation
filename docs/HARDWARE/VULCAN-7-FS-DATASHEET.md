# B&G Vulcan 7 FS — Datasheet

**Version:** 1.0  
**Date:** 2026-06-15  
**Status:** ✅ CANONICAL — Hardware specs for helm + nav displays

> 📌 SSOT: Device specifications. Setup procedures → Integration guides.
> Integration: `docs/INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md`
> System flow: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`

---

## Units Aboard

| Unit | Position | Role |
|---|---|---|
| Vulcan 7 FS | PORT (helm station) | Primary helm display + chart plotter |
| Vulcan 7 FS | STBD (nav station) | Navigator display + secondary chart |

---

## Specifications

| Parameter | Value |
|-----------|-------|
| Model | B&G Vulcan 7 FS (SailSteer + ForwardScan) |
| Screen | 7" TFT LCD, 800×480, full sunlight readable |
| NMEA 2000 | Micro-C connector, LEN = 1 per unit (2 total) |
| Internal GPS | 10 Hz (secondary to UM982) |
| Internal barometer | Yes (redundancy) |
| Power | 10–32V DC nominal, ~0.9A per unit |
| Waterproofing | IPX6 |
| Warranty | 5 years (Raymarine B&G) |

---

## Data Consumed (from N2K + Signal K via YDNU-02)

| Measurement | Source | PGN | Rate | Priority |
|---|---|---|---|---|
| True heading | UM982 via SK+P5 | 127250 | 1 Hz | Primary |
| Roll / Pitch | WIT IMU via SK+P5 | 127257 | 10 Hz | Primary |
| Position (GNSS) | UM982 via SK+P5 | 129025 | 1 Hz | Primary |
| COG / SOG | UM982 via SK+P5 | 129026 | 1 Hz | Primary |
| Speed Through Water (STW) | Airmar DST810 direct N2K | 128259 | 1 Hz | Current calc input (P3) |
| Water Depth | Airmar DST810 direct N2K | 128267 | 1 Hz | Depth display |
| Apparent wind | WS320 direct N2K | 130306 | 5 Hz | Direct (real-time) |
| Current Set & Drift | Signal K P3 via P5 | 129291 | 1 Hz | Computed from STW+COG+heading |
| AIS targets | AIS700 direct N2K | 129038/039 | event-driven | Direct (safety-critical) |
| Pressure | YDBC-05 | 130314 | 0.5 Hz | Supplement |
| Internal position | Vulcan own GPS | 129025 | 1 Hz | Fallback (secondary) |

---

## Data Published (by Vulcan internal GPS)

| PGN | Data | Signal K Source | Priority in SK |
|-----|------|---|---|
| 129025 | GNSS position | `vulcan_internal` | Secondary (fallback) |
| 129026 | COG + SOG | `vulcan_internal` | Secondary (fallback) |

---

## Critical Dependencies

| Feature | Requires | If Missing |
|---|---|---|
| **SailSteer mode** | PGN 127250 (true heading from UM982) | No automatic tiller steering |
| **Real-time wind display** | PGN 130306 from WS320 @ 5 Hz | Falls back to 1 Hz Calypso via SK |
| **AIS radar overlay** | PGN 129038–129810 from AIS700 | No vessel targets on chart |
| **Heel display** | PGN 127257 from WIT IMU | Uses fallback inclinometer |

---

## Notes

- **SailSteer requires true heading** — magnetic compass not aboard, relies 100% on UM982 GPS dual-antenna heading via Signal K
- **STW available via Airmar DST810** — hull-mounted transducer publishes PGN 128259 on N2K bus → navigation.speedThroughWater in Signal K → primary input to current calculator (P3)
- **ForwardScan sonar NOT installed** — no depth or fish finder sonar
- **Both units synchronized** — if one loses GPS, both show fallback position until UM982 recovers

---

## Related Documents

- Integration: `docs/INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md`
- System: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`
- Architecture: `docs/ARCHITECTURE-MASTER.md`
