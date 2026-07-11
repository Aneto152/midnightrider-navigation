# Airmar DST810 — Datasheet

**Version**: 1.0  
**Date**: 2026-07-11  
**Status**: ✅ CANONICAL — Hardware specs for hull-mounted smart transducer

> 📌 **SSOT**: Device specifications only.  
> Setup procedures → Integration guides.  
> System flow → docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md

---

## Installation

| Parameter | Value |
|-----------|-------|
| Location | Hull-mounted through-hull transducer |
| Bus role | N2K publisher (STW + depth + water temp) |
| Connector | Micro-C (NMEA 2000) |

---

## Specifications

| Parameter | Value |
|-----------|-------|
| Model | Airmar DST810 Smart Transducer |
| Protocol | NMEA 2000 native |
| LEN | 1 |
| Power | 9–16V DC via N2K backbone |
| Waterproofing | IPX7 |
| STW sensor | Paddlewheel (speed through water) |
| Depth sensor | 200 kHz ultrasonic |
| Temp sensor | NTC thermistor (water temperature) |

---

## PGNs Published (DST810 → N2K bus → Signal K via YDNU-02)

| PGN | Data | SK Path | Frequency |
|-----|------|---------|-----------|
| 128259 | Speed Through Water (STW) | navigation.speedThroughWater | 1 Hz |
| 128267 | Water Depth (below transducer) | environment.depth.belowTransducer | 1 Hz |
| 130310 | Water Temperature | environment.water.temperature | 0.2 Hz |

---

## Role in Current Calculation Chain

`navigation.speedThroughWater` (PGN 128259) is the critical input to `signalk-current-calculator.js` (P3). Without it, the plugin skips all calculations and no current data is published.

**Chain**:
```
DST810 → PGN 128259 → YDNU-02 → Signal K
  → navigation.speedThroughWater
  → signalk-current-calculator (P3)
  → environment.current.setTrue + .drift
  → P5 (signalk-n2k-bridge)
  → PGN 129291 → N2K bus → Vulcan 7 FS
```

---

## Critical Dependencies

| Feature | Requires | If Missing |
|---------|----------|------------|
| Current calculation | PGN 128259 (STW) | P3 skips all — no current output anywhere |
| Leeway accuracy | PGN 128259 (STW) | Leeway falls back to SOG (less accurate) |
| Depth display | PGN 128267 | No depth on Vulcan or Grafana |
| Water temp logging | PGN 130310 | No water temp in InfluxDB |

---

## Maintenance Notes

- Calibrate STW vs GPS SOG periodically in flat calm conditions
- Paddlewheel susceptible to fouling — inspect annually
- Depth reference: below transducer (not keel) — set offset in Vulcan:
  Settings → System → Vessel → Depth offset

---

## Related Documents

- System flow: [N2K-NETWORK-ARCHITECTURE.md](../INTEGRATION/N2K-NETWORK-ARCHITECTURE.md)
- Architecture: [ARCHITECTURE-MASTER.md](../ARCHITECTURE-MASTER.md)
