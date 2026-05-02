# Midnight Rider — Data Simulator (DEV ONLY)

⚠️ **DO NOT USE IN PRODUCTION. DO NOT DEPLOY ON BOAT.**

This simulator injects synthetic navigation, wind, and performance data into InfluxDB and Signal K for testing dashboards, alerts, and data pipelines.

## Safety Features

✅ **SIMULATOR_ENABLED=true required** — Blocks accidental execution
✅ **Isolated bucket** — Writes to `midnight_rider_sim` by default (not real data)
✅ **--live flag** — Must explicitly opt-in to write to real `midnight_rider` bucket
✅ **Max runtime** — 2 hours automatic safety stop
✅ **scripts/dev/** — Completely isolated, can be deleted without affecting production

## Usage

### List available scenarios

```bash
SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --list
```

Output:
```
Scenarios disponibles:

 calibrate       Known exact values — use to verify all field names
 upwind          Upwind beat — TWS 12kt, TWA 45°, heel 18°
 downwind        Downwind run — TWS 15kt, spinnaker
 storm-alert     ⚠️ DECLENCHE LES ALERTES — heel >25°, TWS 28kt
 anchor          Au mouillage — toutes mesures a zero
```

### Verify field names (SAFE — writes to midnight_rider_sim)

```bash
SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --verify-fields
```

This:
1. Injects "calibrate" scenario (known exact values)
2. Shows which fields were written
3. Lets you verify field names match your dashboard

### Single injection to safe bucket

```bash
SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --scenario upwind
```

Injects once, prints results, exits.

### Continuous loop (SAFE — default to midnight_rider_sim)

```bash
SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --scenario upwind --continuous

# Stop with Ctrl+C
```

Injects every 5 seconds with realistic variance.

### ⚠️ LIVE MODE — Write to real midnight_rider bucket

```bash
SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --scenario upwind --live --continuous
```

Prompts for confirmation before writing to **REAL** bucket. Used for:
- Testing dashboards with synthetic data
- Testing alert rules (storm-alert scenario triggers heel + TWS alerts)
- Verifying data flow end-to-end

### Trigger alert scenarios

```bash
# Test heel > 25° alert
SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --scenario storm-alert --live --continuous

# Monitor: http://localhost:3001/d/alerts-monitoring
# Watch for "Critical Heel Angle" and "Rapid Pressure Drop" alerts
```

## Scenarios

| Name | Description | Use Case |
|------|-------------|----------|
| `calibrate` | Known exact values | Verify field names are correct |
| `upwind` | TWS 12kt, TWA 45°, heel 18° | Test navigation/wind display |
| `downwind` | TWS 15kt, spinnaker | Test performance in strong wind |
| `storm-alert` | Heel 28°, TWS 28kt, pressure 998hPa | Test alert rules firing |
| `anchor` | All values zero | Test zero-state display |

## Cleanup

### Remove simulator from RPi

```bash
rm -rf /home/pi/midnightrider-navigation/scripts/dev/
```

### Remove from repository

```bash
git checkout main
git branch -d dev/simulator
git push origin --delete dev/simulator
git rm -r scripts/dev/
git commit -m "chore: remove dev simulator (pre-production cleanup)"
git push origin main
```

Zero production impact — simulator is completely isolated in `scripts/dev/`.

## Troubleshooting

### "SIMULATOR_ENABLED=true required"
Missing environment variable. Run:
```bash
SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --scenario upwind
```

### "influxdb-client not installed"
Install:
```bash
pip3 install influxdb-client
```

### "INFLUX_TOKEN not set"
Ensure `.env` is sourced:
```bash
source .env
```

### No data appears in bucket
- Check bucket exists: `influx bucket list`
- Verify token: `INFLUX_TOKEN=<value> influx auth list`
- Try verify-fields: `SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --verify-fields`

---

**Status**: Dev-only tool. Safe for testing. Never use in production. 🚀
