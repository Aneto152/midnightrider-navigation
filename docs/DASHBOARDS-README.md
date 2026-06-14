# DASHBOARDS-README.md — Midnight Rider Grafana Dashboards

> Generated: 2026-05-12 14:28 EDT  
> Grafana: http://localhost:3001  
> Datasource UID: efifgp8jvgj5sf  
> InfluxDB Bucket: midnight_rider  
> InfluxDB Org: MidnightRider  

---

## Overview

Midnight Rider runs 9 custom Grafana dashboards on port 3001,
provisioned via `grafana-provisioning/dashboards/` and served from
`/var/lib/grafana/dashboards`.

All dashboards query InfluxDB bucket `midnight_rider` via Flux language.
Refresh rates vary by use case (5s–30s).

---

## Dashboard Inventory

| Dashboard | UID | Local URL |
|-----------|-----|-----------|
| 01 — COCKPIT (Main Navigation) | `cockpit-main` | http://localhost:3001/d/cockpit-main/01-e28094-cockpit-main-navigation |
| 02 — ENVIRONMENT (Sea & Weather) | `environment-conditions` | http://localhost:3001/d/environment-conditions/02-e28094-environment-sea-and-weather |
| 03 — PERFORMANCE (Speed & Efficiency) | `03-performance` | http://localhost:3001/d/03-performance/03-e28094-performance-speed-and-efficiency |
| 04 — WIND & CURRENT (Tactical Analysis) | `04-wind-current` | http://localhost:3001/d/04-wind-current/04-e28094-wind-and-current-tactical-analysis |
| 06 — ELECTRICAL (Power Management) | `electrical-power` | http://localhost:3001/d/electrical-power/06-e28094-electrical-power-management |
| 07 — RACE (Block Island Race — May 22, 2026) | `07-race` | http://localhost:3001/d/07-race/041e1f7 |
| 08 — ALERTS & MONITORING (60 Alert Rules) | `08-alerts` | http://localhost:3001/d/08-alerts/08-e28094-alerts-and-monitoring-60-alert-rules |
| 09 — CREW (Watch Management & Fatigue) | `09-crew` | http://localhost:3001/d/09-crew/09-e28094-crew-watch-management-and-fatigue |
| 05 — COMPETITIVE (Fleet Tracking) | `competitive-fleet` | http://localhost:3001/d/competitive-fleet/05-e28094-competitive-fleet-tracking |

---

## Access

| Device | URL |
|--------|-----|
| RPi local | http://localhost:3001 |
| iPad (mDNS) | http://midnightrider.local:3001 |
| iPad (IP) | http://192.168.1.131:3001 |

---

## Deployment

Dashboards are provisioned automatically at Grafana startup via:

- **Provisioning config:** `grafana-provisioning/dashboards/dashboards.yaml`
- **Dashboard JSON files:** `grafana-dashboards/*.json`
- **Grafana data volume:** `/var/lib/grafana/dashboards`

### To redeploy all dashboards:

```bash
python3 deploy-dashboards.py
```

### To restart Grafana:

```bash
docker compose restart grafana
```

---

## Dashboard Descriptions

### 🏠 01 — COCKPIT (Main Navigation) — 5s refresh
Primary helm display. Heading (°M), SOG (knots), COG (°M).
Roll, pitch, yaw angles. Dedicated to helmsman & tactician.

**Key metrics:** heading, SOG, COG, roll, pitch, yaw, wind angles

---

### 🌊 02 — ENVIRONMENT (Sea & Weather) — 30s refresh
Sea state and atmospheric conditions. Temperature, pressure, depth.
Barometric trend for passage planning.

**Key metrics:** water temp, air temp, barometric pressure, depth, trend

---

### ⚡ 03 — PERFORMANCE (Speed & Efficiency) — 5s refresh
Speed and VMG (velocity made good) metrics. Polar performance ratio,
target speed comparison. Sail plan optimization.

**Key metrics:** VMG, STW, SOG, polar ratio, target speed, sails

---

### 🌬️ 04 — WIND & CURRENT (Tactical Analysis) — 10s refresh
Wind analysis: TWS (true wind speed), TWD (true wind direction),
AWA (apparent wind angle). Current vector estimation. Layline overlay.

**Key metrics:** TWS, TWD, AWA, current vector, layline, wind shear

---

### 🏆 05 — COMPETITIVE (Fleet Tracking) — 30s refresh
Race position relative to fleet. Polars, competition benchmarks.
Distance to mark, bearing, ETA.

**Key metrics:** fleet position, distance-to-mark, bearing, ETA, polars

---

### 🔋 06 — ELECTRICAL (Power Management) — 30s refresh
SOK LiFePO4 BMS via BLE: State of Charge (%), cell voltages,
temperature, current (charge/discharge), cycle count. Energy budget.

**Key metrics:** SOC%, cell voltages, temp, current, cycle count, reserve

---

### 🏁 07 — RACE (Block Island Race — May 22, 2026) — 5s refresh
Race-specific metrics: start line analysis, mark roundings,
watch rotation, tactical timers. Distance to start, start line bias.

**Key metrics:** start bias, distance-to-mark, watch timer, tactical window

---

### 🔔 08 — ALERTS & MONITORING (60+ Alert Rules) — 10s refresh
System health monitoring. 65+ configured alerts covering:
- Navigation (heading error, off-course, approach waypoint)
- Electrical (low SOC, cell imbalance, over-temperature)
- Weather (gust, squall, pressure drop)
- System (CPU temp, disk space, memory)

**Key metrics:** active alerts, warnings, critical thresholds, trends

---

### ⛵ 09 — CREW (Watch Management & Fatigue) — 30s refresh
Watch rotation, crew assignments, rest periods, fatigue tracking.
Alert on exceeding watch limits. Shift recommendations.

**Key metrics:** watch duration, rest time, crew assignment, fatigue level

---

## Architecture Notes

- **Signal K** (port 3000) runs via `systemctl` — NEVER docker compose
- **Signal K → InfluxDB** plugin writes to bucket `midnight_rider`
- **Grafana** (port 3001) runs in Docker — managed via `docker compose`
- **Flux queries** read from InfluxDB via datasource UID `efifgp8jvgj5sf`
- **iPad access** via mDNS `midnightrider.local` or IP `192.168.1.131`
- **Workaround active:** `avahi-mdns-fix.service` since 2026-05-11

---

## Readiness

| Milestone | Date | Status |
|-----------|------|--------|
| Field Test | 2026-05-19 | ✅ READY |
| Block Island Race | 2026-05-22 | ✅ READY |

---

*Last updated: 2026-05-12 — Midnight Rider Navigation System v1.0*
