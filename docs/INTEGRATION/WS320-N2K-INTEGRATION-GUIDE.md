# B&G WS320 — N2K Integration Guide

**Date:** 2026-06-15

> 📌 Procedure only. PGN specs → `docs/HARDWARE/BG-WS320-DATASHEET.md`
> System: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`

---

## Architecture

```
WS320 Masthead Unit (wireless)
        ↓
   WS320 Base Station (N2K)
        ├─→ N2K Backbone (5 Hz, direct to Vulcan)
        │
        └─→ YDNU-02 Bridge → Signal K (1 Hz, secondary source)
```

---

## Physical Setup

- **Base station:** Micro-C to N2K backbone drop (≤6m cable)
- **LEN:** 2 (wireless base station = 2 units on N2K)
- **Power:** N2K bus (9–32V DC), no separate 12V needed
- **Masthead unit:** Battery (CR123A), typical life 2 years
- **Masthead → Base range:** Line-of-sight, typically 50–100m

---

## Signal K Source Priority

| Priority | Source | Protocol | Frequency |
|---|---|---|---|
| 1 (primary) | Calypso UP10 (`calypso-up10`) | BLE → UDP:4123 | 4 Hz |
| 2 (fallback) | WS320 (`nmea2000_ws320`) | N2K → YDNU-02 | 5 Hz (N2K), 1 Hz (SK) |

If Calypso goes offline, SK automatically switches to WS320 as wind source.

---

## Verification

```bash
# Check WS320 in Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self | python3 -c "
import sys, json
d = json.load(sys.stdin)
w = d.get('environment', {}).get('wind', {})
sources = list(w.get('angleApparent', {}).get('values', {}).keys())
print('Wind sources:', sources)"
```

Expected: both Calypso + WS320 sources if connected

---

## PGNs

For detailed PGN specifications:
- **Hardware:** [docs/HARDWARE/BG-WS320-DATASHEET.md](../HARDWARE/BG-WS320-DATASHEET.md)
- **System flow:** [N2K-NETWORK-ARCHITECTURE.md §3.1](N2K-NETWORK-ARCHITECTURE.md)

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| Wind in Vulcan but NOT in SK | YDNU-02 bridge down | Check `/dev/ttyACM0`, restart SK |
| Intermittent wind data | Masthead battery low | Replace CR123A (typical: every 2 yrs) |
| No data at all | Base station power lost OR N2K fault | Check N2K bus voltage, T-connectors |
| Base LED off | Power disconnected | Check N2K connector, bus health |

---

**Related:** `N2K-NETWORK-ARCHITECTURE.md`, `BG-WS320-DATASHEET.md`
