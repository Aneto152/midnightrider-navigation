# B&G AIS700 — Integration Guide

**Date:** 2026-06-15

> 📌 Procedure only. PGN specs → `docs/HARDWARE/AIS700-DATASHEET.md`
> System: `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`

---

## Physical Setup

- **Connector:** Micro-C to N2K backbone drop (preferably ≤6m cable)
- **LEN budget:** 1 — see [N2K-NETWORK-ARCHITECTURE.md §2](N2K-NETWORK-ARCHITECTURE.md) for bus capacity
- **Power:** Supplied by N2K bus (12V nominal, 9–32V range)
- **Location:** Below waterline antenna mount (ideally on cabin trunk)

---

## Configuration (via Vulcan 7)

Program the following via Vulcan 7:
1. **Menu** → **Settings** → **Communication** → **AIS**
2. Set: **MMSI**, vessel name, call sign, vessel type, dimensions, stiffness
3. Verify: Transponder LED flashing (heartbeat) ✅

⚠️ **Security:** Never commit MMSI, vessel name, or call sign to git.

---

## Signal K Verification

```bash
# Check AIS targets visible in Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels | python3 -c "
import sys, json
v = json.load(sys.stdin)
targets = [k for k in v.keys() if 'self' not in k]
print(f'AIS targets visible: {len(targets)}')"
```

Expected: Non-empty list if vessels in range

---

## PGNs

For detailed PGN specifications:
- **Hardware:** [docs/HARDWARE/AIS700-DATASHEET.md](../HARDWARE/AIS700-DATASHEET.md)
- **System flow:** [N2K-NETWORK-ARCHITECTURE.md §3.1](N2K-NETWORK-ARCHITECTURE.md)

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| No TX (not broadcasting) | MMSI not programmed OR no GPS fix | Program MMSI, wait for GPS lock |
| No RX targets in SK | YDNU-02 bridge down | Check `/dev/ttyACM0`, restart SK |
| No RX targets in Grafana | Dashboard Flux query broken | Verify dashboard 05 filter syntax |
| Transponder LED not flashing | Power lost or N2K fault | Check N2K bus voltage (12V), T-connectors |

---

**Related:** `N2K-NETWORK-ARCHITECTURE.md`, `AIS700-DATASHEET.md`
