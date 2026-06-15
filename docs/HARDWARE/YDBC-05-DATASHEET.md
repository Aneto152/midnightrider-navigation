# Yacht Devices YDBC-05 — Datasheet

**Version:** 1.0  
**Date:** 2026-06-15  
**Status:** ✅ CANONICAL — Hardware specs for NMEA 2000 barometer

> 📌 SSOT: Device specifications. Setup → `YDBC-05-INTEGRATION-GUIDE.md`
> System flow: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md §3`

---

## Role

Atmospheric pressure sensor + air temperature transmitter. Used for passage planning
and cross-checking with Vulcan 7 internal barometer.

---

## Specifications

| Parameter | Value |
|-----------|-------|
| Model | Yacht Devices YDBC-05 |
| Measurement | Barometric pressure + air temperature |
| N2K connector | Micro-C |
| N2K LEN | 1 |
| Power | 9–36V DC from N2K bus (no separate wiring) |
| Pressure range | 940–1055 hPa (normal weather) |
| Pressure accuracy | ±0.5 hPa |
| Temperature accuracy | ±1°C |
| IP rating | IP67 (submersible to 1m) |

---

## Measurements Published

| Measurement | PGN | Signal K Path | Frequency |
|---|---|---|---|
| Atmospheric pressure | 130314 | `environment.outside.pressure` | 0.5 Hz |
| Air temperature | 130312 | `environment.outside.temperature` | 0.5 Hz |

**Signal K source name:** `nmea2000_ydbc05`

---

## Notes

- **Plug & play** — no configuration required, auto-broadcasts on N2K bus
- **Redundancy** — Vulcan 7 has internal barometer; YDBC-05 is supplementary
- **No helm trim impact** — pressure data is informational only (weather planning)

---

## Related Documents

- Integration: `docs/INTEGRATION/YDBC-05-INTEGRATION-GUIDE.md`
- System: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`
