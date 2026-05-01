# Polar Data — Midnight Rider Navigation

**J/30 Performance Coefficients**

## Files

| File | Boat | Source | Status |
|------|------|--------|--------|
| `j30_orc.json` | J/30 | ORC/IMS interpolated | ✅ Active |

## Format

```json
{
  "_meta": {
    "boat": "J/30",
    "source": "ORC/IMS",
    "units": {"tws": "knots", "twa": "degrees", "bsp": "knots"}
  },
  "polars": [
    {
      "tws": 10,
      "upwind": 6.4,
      "reach": 8.2,
      "downwind": 9.5,
      "upwind_angle": 30,
      "downwind_angle": 155
    }
  ]
}
```

## Signal K Integration

| Parameter | Signal K Path | Unit | Conversion |
|-----------|---|---|---|
| TWS | `environment.wind.speedTrue` | m/s | ×1.944 → knots |
| TWA | `environment.wind.angleTrueWater` | rad | ×180/π → degrees, use `abs()` |
| Target Speed (output) | `performance.targetSpeed` | m/s | knots ÷1.944 |
| Polar Efficiency | `performance.polarEfficiency` | ratio 0-1 | STW / targetSpeed |

## TWA Modes

```
TWA absolute (degrees from bow):
  0° → head-to-wind (impossible)
  30° → close-hauled typical
  90° → beam reach
  150° → broad reach
  180° → downwind

Mapping:
  < 60° → upwind (beating, close-hauled)
  60-150° → reach (beam reach, broad reach)
  > 150° → downwind (running, heavy air)
```

## Usage

Scripts that read polars:
- `scripts/target_speed_calc.py` → loads `j30_orc.json`, interpolates TWS/TWA

Configuration:
```bash
export POLAR_FILE="/home/pi/midnightrider-navigation/data/polars/j30_orc.json"
python3 scripts/target_speed_calc.py
```

## Adding New Polars

1. Create `data/polars/<boat>_<source>.json` (same format)
2. Update `scripts/target_speed_calc.py`: set `POLAR_FILE` variable
3. Update `docs/DATA-SCHEMA-MASTER.md` section "Polars"

---

**Maintained by:** OC (Open Claw)  
**Updated:** 2026-05-01  
**Reference:** DATA-SCHEMA-MASTER.md § Polars
