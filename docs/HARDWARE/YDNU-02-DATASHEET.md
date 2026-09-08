# Yacht Devices YDNU-02 — Datasheet

**Version:** 1.0  
**Date:** 2026-06-15  
**Status:** ✅ CANONICAL — Hardware specs for N2K USB bridge

> 📌 SSOT: Device specifications. Setup → `YDNU-02-INTEGRATION-GUIDE.md`
> System flow: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md §4`

---

## Role

Bidirectional N2K ↔ USB/Signal K bridge. **Critical single point of failure:**
without it, Signal K cannot transmit computed data (heading, attitude, position)
back to Vulcan 7 displays.

---

## Specifications

| Parameter | Value |
|-----------|-------|
| Model | Yacht Devices YDNU-02 |
| Manufacturer | Yacht Devices Ltd (Ukraine) |
| USB device path | `/dev/ttyACM0` (CDC ACM) |
| USB Vendor ID | 0x0483 (STMicroelectronics) |
| USB Product ID | 0xA217 (Yacht Devices) |
| N2K connector | Micro-C |
| N2K LEN | 1 |
| N2K baud rate | 250 kbps (native) |
| Direction | Bidirectional (reads + writes both networks) |
| Power | USB 5V self-powered (no separate N2K power draw) |
| Compatibility | canboat, Signal K, OpenCPN, iNavx |

---

## LED Indicators

| Color | State | Meaning | Action |
|---|---|---|---|
| Green | Steady | USB powered ✅ | — |
| Yellow | Blinking 1–2s | N2K data flowing ✅ | — |
| Yellow | Steady | No N2K traffic ⚠️ | Check N2K bus power, T-connectors |
| Red | Blinking | N2K error ⚠️ | Power cycle, check termination |
| Red | Steady | Critical fault ⚠️ | Hardware failure possible |

---

## Data Bridged

This device does not generate measurements — it **bridges** data between networks:

| Direction | Content | Typical Rate |
|---|---|---|
| **N2K → RPi/SK** | Wind (PGN 130306), pressure (130314), AIS (129038–129810), Vulcan GPS (129025/129026) | Per source |
| **RPi/SK → N2K** | Heading (PGN 127250), attitude (127257), position (129025), COG/SOG (129026) | 1–10 Hz |
| **Bridge mode** | Transparent (YDNU-02 becomes "invisible" on the wire) | All frames pass |

---

## Related Documents

- Integration: `docs/INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md`
- System: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`
