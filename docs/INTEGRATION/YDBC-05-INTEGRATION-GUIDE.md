# Yacht Devices YDBC-05 — Integration Guide

**Date:** 2026-06-15

> 📌 Plug & play device — minimal configuration.
> PGN specs → `docs/HARDWARE/YDBC-05-DATASHEET.md`
> System: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`

---

## Physical Setup

- **Connector:** Micro-C to N2K backbone drop
- **LEN:** 1
- **Power:** N2K bus supplies 12V (no separate wiring needed)
- **Configuration:** None required — auto-broadcasts pressure + temperature

---

## Verification

```bash
# Check YDBC-05 pressure in Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self | python3 -c "
import sys, json
d = json.load(sys.stdin)
p = d.get('environment', {}).get('outside', {}).get('pressure', {}).get('value')
print(f'Pressure: {p/100:.1f} hPa' if p else 'Pressure: not available')"
```

Expected: Stable value 940–1055 hPa

---

## PGNs

For detailed PGN specifications:
- **Hardware:** [docs/HARDWARE/YDBC-05-DATASHEET.md](../HARDWARE/YDBC-05-DATASHEET.md)
- **System flow:** [N2K-NETWORK-ARCHITECTURE.md §3.1](N2K-NETWORK-ARCHITECTURE.md)

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| No pressure in SK | YDNU-02 bridge down OR YDBC-05 unpowered | Check `/dev/ttyACM0`, N2K bus voltage (12V) |
| Value frozen at startup | Calibration lag | Wait 30 seconds, re-query |
| Erratic jumps (±5 hPa) | Electrical noise | Check N2K shielding, T-connector termination |

---

**Related:** `N2K-NETWORK-ARCHITECTURE.md`, `YDBC-05-DATASHEET.md`
