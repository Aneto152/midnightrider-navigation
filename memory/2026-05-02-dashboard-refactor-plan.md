# Dashboard Refactor Plan — Race Interface Fusion

**Date**: 2026-05-02  
**Status**: ANALYZED, READY FOR IMPLEMENTATION  
**Scope**: Merge regatta interface into 3 Grafana dashboards

## Existing Infrastructure

### regatta/server.py Measurements
- `regatta.timer` — start_timer_seconds (timer countdown)
- `regatta.start_line` — distance_to_line_m, line_side, pin_buoy_*, pin_rc_*
- `regatta.sails` — mainsail_config, headsail_config, downwind_sail, sail_note
- `regatta.helmsman` — helm_name, helm_watch_duration_min, next_helm_name
- `regatta.events` — race events log

### regatta/index.html (19KB)
- Interactive chrono (countdown timer)
- Start line controls (pin positions, distance)
- Sail management (GV ris levels, foc type, spinnaker)
- Helm/watch management (current helm, duration, next)
- Fleet tracking

### Current Dashboards
- **07-race.json**: 7 panels (countdown gauge, marks, distance, fleet position, cumulative distance)
- **03-performance.json**: 7 panels (STW, VMG, efficiency, distance, speed vs polars)
- **09-crew.json**: 10 panels (crew names, watch times, performance per helm)

## Implementation Plan (Staged)

### Stage 1: 07-race.json — START LINE CONTROLS
Add 11 panels in new "🏁 START LINE" row:
1. ⏱️ **Chrono Départ** (stat, 8h tall) — timer_seconds from regatta.timer
2. 📏 **Distance à la ligne** (stat) — distance_to_line_m
3. 🚦 **Position / Ligne** (stat) — line_side (OCS/CLEAR/CLOSE)
4. 🟡 **Pin Bouée — Relèvement** (stat) — pin_buoy_bearing_deg
5. 🟡 **Pin Bouée — Distance** (stat) — pin_buoy_dist_m
6. 🚤 **Comité — Relèvement** (stat) — pin_rc_bearing_deg
7. 🚤 **Comité — Distance** (stat) — pin_rc_dist_m
8. 📐 **Longueur ligne** (stat) — start_line_length_m
9. ⚖️ **Biais ligne** (stat) — line_bias_deg (favorise bouée ou comité)
10. 🎛️ **Interface contrôle** (text) — link to regatta/ UI

### Stage 2: 03-performance.json — SAIL MANAGEMENT
Add 5 panels in new "🪁 GESTION DES VOILES" row at top:
1. 🪁 **Grand-voile** (stat) — mainsail_config (FULL/R1/R2/R3/FURLED)
2. 🎏 **Foc / Génois** (stat) — headsail_config (GENOA/JIB/STORM/NONE)
3. 🎈 **Spi / Asymétrique** (stat) — downwind_sail (SPI/ASYM/NONE)
4. 📝 **Config voilure** (stat) — sail_note (free text)
5. 🎛️ **Contrôle voilure** (text) — link to regatta/ UI

### Stage 3: 09-crew.json — HELM MANAGEMENT
Add 5 panels in new "🎯 BARREUR" row at top:
1. 🎯 **Barreur** (stat) — helm_name
2. ⏱️ **Durée quart actuel** (stat) — helm_watch_duration_min
3. 🔄 **Prochain relève** (stat) — next_helm_name
4. 📊 **Historique des barres** (timeseries) — helm watch duration over 24h
5. 🎛️ **Changer barreur** (text) — link to regatta/ UI

### Stage 4: Portal Configuration
- Ensure regatta/ is served from portal :8888
- Add link in portal index.html to http://midnightrider.local:8888/regatta/
- Verify all 3 dashboards load with new panels

### Stage 5: Grafana Deployment
- Redeploy 07-race.json with START LINE panels
- Redeploy 03-performance.json with SAIL MANAGEMENT panels
- Redeploy 09-crew.json with HELM MANAGEMENT panels
- Verify queries execute and display real data

## Grafana Datasource
- InfluxDB UID: `efifgp8jvgj5sf`
- Bucket: `midnight_rider`
- All queries use Flux language

## Query Pattern
```flux
from(bucket: "midnight_rider")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "regatta.start_line")
  |> filter(fn: (r) => r._field == "distance_to_line_m")
  |> last()
```

## Success Criteria
✅ All 20 new panels display in Grafana  
✅ Queries return real data from regatta.* measurements  
✅ Portal links to regatta/ UI work  
✅ Helm/sail/start-line changes in regatta UI appear in dashboards  
✅ iPad responsive design maintained  

## Notes
- Panels use `stat` type for large, readable values on iPad
- Color thresholds match tactical racing needs (red=alert, green=good)
- Text panels provide links to interactive controls in regatta/
- All timestamps use UTC per Signal K convention

---

**Next session**: Implement stages 1-5 with fresh token budget
