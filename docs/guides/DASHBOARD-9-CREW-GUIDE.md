# DASHBOARD 9 — CREW WATCH MANAGEMENT

**Created:** 2026-04-26 08:57 EDT  
**Status:** ✅ Production-ready  
**Target:** Double-handed offshore racing (Denis + Anne-Sophie)  
**Duration:** Block Island Race 2026 — ~28-32 hours

---

## 🎯 PURPOSE

Monitor crew fatigue, watch schedules, and individual performance during double-handed racing.

**Key Metric:** Fatigue is **measured by boat performance degradation** when each person is at the helm.
- If Denis at helm → boat slows down → Denis is fatigued
- If Anne-Sophie at helm → boat slows down → Anne-Sophie is fatigued

---

## 📊 DASHBOARD PANELS

### 1. CREW STATUS (Top Row — 2 large stat panels)

**Left Panel: DENIS LAFARGE**
- Shows: ⚓ AT HELM or 💤 RESTING
- Green when at helm, gray when resting
- Updates every 30 seconds from regatta interface

**Right Panel: ANNE-SOPHIE**
- Shows: ⚓ AT HELM or 💤 RESTING
- Blue when at helm, gray when resting
- Updates every 30 seconds from regatta interface

---

### 2. NEXT WATCH CHANGE COUNTDOWN (Large gauge)

**Purpose:** Critical for timing watch rotations

**Logic:**
- Current watch time: starts from 0 when someone takes helm
- **Target:** 2 hours per watch
- **Gauge colors:**
  - 🟢 Green: 30-120 min remaining (stay focused)
  - 🟡 Yellow: 10-30 min remaining (prepare handover)
  - 🔴 Red: < 10 min remaining (CHANGE NOW)

**Example:**
- 09:00 — Denis takes helm
- 11:00 — Countdown hits 00:00 → Anne-Sophie takes helm
- Watch bell or alarm should trigger at ~10:50 (10 min warning)

---

### 3. DENIS PERFORMANCE (Left timeseries — 2h window)

**Shows:** Speed Over Ground when Denis is at helm

**Interpretation:**
- **Flat line (declining trend):** Denis is getting fatigued
- **Erratic/variable:** Loss of concentration
- **Consistent high:** Denis is sharp

**Used by:** Crew coach to decide when to rotate

---

### 4. ANNE-SOPHIE PERFORMANCE (Right timeseries — 2h window)

**Shows:** Speed Over Ground when Anne-Sophie is at helm

**Same interpretation as Denis performance**

---

### 5. WATCH SCHEDULE TIMELINE (Full width — 12h history)

**Visual:**
- 🟢 Green blocks = Person at helm
- 🔵 Blue blocks = Person resting
- 🟡 Yellow = Transition/handover

**Shows:** Complete history of who was helm

**Example pattern for 28-32h race:**
```
Denis:       [HELM 2h] [REST 2h] [HELM 2h] [REST 2h] [HELM 2h] [REST 2h] [HELM 2h]
Anne-Sophie: [REST 2h] [HELM 2h] [REST 2h] [HELM 2h] [REST 2h] [HELM 2h] [REST 2h]
```

---

### 6-7. WATCH TIME TOTALS

**Denis Total Watch Time:** Cumulative hours at helm (race duration)  
**Anne-Sophie Total Watch Time:** Cumulative hours at helm (race duration)

**Color coding:**
- 🟢 Green: Balanced (0-2h)
- 🟡 Yellow: Getting tired (2-4h)
- 🔴 Red: Overextended (> 4h)

---

### 8. FATIGUE INDEX (Bottom timeseries — 6h rolling)

**Most important panel for crew decision-making**

**Calculation:**
- **Baseline:** Average boat speed when each person is fresh
- **Degradation:** Current speed vs baseline
- **Formula:** Fatigue% = 100 × (1 - current_speed / baseline_speed)

**Example:**
- Denis fresh: boat averages 6.5 knots
- Denis after 1.5h: boat averages 6.0 knots
- Fatigue = 100 × (1 - 6.0/6.5) = **7.7%**

**Thresholds for action:**
- < 10%: OK, continue
- 10-25%: Starting to fade, watch for errors
- 25-50%: Significant degradation, hand over soon
- > 50%: CRITICAL — hand over immediately

---

## 🔔 CREW ALERTS (5 Additional Alert Rules)

**Added to the 60 existing alerts:**

1. **Watch Duration > 2h 10m**
   - Alert: "Denis has been at helm 10+ min over target"
   - Action: Start handover procedure

2. **Rest Duration < 2h**
   - Alert: "Anne-Sophie has had less than 2h rest"
   - Action: Don't put them back on helm yet

3. **Fatigue Index > 25%**
   - Alert: "Person at helm showing fatigue signs"
   - Action: Reduce sail plan or hand over sooner

4. **Performance Drop > 15% (1h window)**
   - Alert: "Speed down 15% — crew fatigue likely"
   - Action: Hand over immediately, rest

5. **Imbalance in Watch Time**
   - Alert: "One crew has > 2h more watch time than other"
   - Action: Rebalance workload

---

## 💾 DATA STORAGE

**Where it lives:**
- Regatta interface logs all watch changes → InfluxDB
- Each watch change creates event in `crew` measurement
- Performance data stored in `navigation` measurement (linked to crew member)

**InfluxDB schema (expected):**
```
crew,skipper=Denis,status=helm value=1, timestamp=1714139400000000000
crew,skipper=Anne-Sophie,status=rest value=1, timestamp=1714139400000000000
navigation,skipper=Denis,speedOverGround value=6.5, timestamp=1714139410000000000
```

---

## 📱 RACE DAY USAGE

### Pre-Race Setup
1. Test watch change interface in regatta app
2. Verify both crew members show in dashboard
3. Test countdown timer (should be at 00:00 initially)

### During Race

**Every 15-30 minutes:**
- Check **Fatigue Index** — is anyone degrading?
- Check **Watch Time Total** — is load balanced?
- Check **Performance panels** — any sudden drops?

**At watch change time (every 2h):**
1. Look at **Countdown timer** → should show "00:00 CHANGE NOW"
2. Current helmsperson hands over wheel
3. New helmsperson confirms in regatta interface
4. **Watch History** timeline updates
5. **Fatigue Index** resets baseline for new helmsperson

**Emergency scenarios:**
- If Fatigue Index > 40% and < 30 min to scheduled change → **hand over early**
- If someone appears disoriented → **immediate hand over**
- If weather worsens → **consider shorter watches (1.5h)**

---

## ⚙️ INTEGRATION WITH REGATTA INTERFACE

**Assumptions:**
- Regatta interface has a **"Change Helm" button** or API endpoint
- When clicked, it logs timestamp + new skipper name to InfluxDB
- Dashboard reads these events to update crew status

**Required data flow:**
```
Regatta Interface (iPad app)
    ↓ (button: "Denis → Anne-Sophie")
InfluxDB (crew measurement)
    ↓ (Grafana reads latest crew status)
Dashboard 9 (crew-management)
    ↓ (shows Anne-Sophie at helm, countdown resets)
```

---

## 🔗 CROSS-LINKS

**Dashboard 9 links to all others:**
- Cockpit (main nav)
- Environment (conditions)
- Crew (this dashboard)
- Performance (speed analysis)
- Wind (tactical)
- Competitive (fleet)
- Electrical (power)
- Race (race metrics)
- Alerts (system health)

**All other dashboards link back to Crew**

---

## 📋 DEPLOYMENT CHECKLIST

- [ ] Regatta interface configured to send crew events to InfluxDB
- [ ] InfluxDB receiving crew measurement data
- [ ] Dashboard 9 JSON imported into Grafana
- [ ] Test crew status shows (Denis/Anne-Sophie toggle)
- [ ] Test watch change simulation (manual data insert or button)
- [ ] Fatigue Index calculated correctly
- [ ] All 5 crew alerts created in Grafana Alerting
- [ ] iPad displays dashboard correctly
- [ ] Navigation links work (all 9 dashboards)
- [ ] Ready for field test (May 19)

---

## 📞 TROUBLESHOOTING

**"No Data" in crew status panels:**
- Check: Regatta interface is sending crew events to InfluxDB
- Verify: `crew` measurement exists in InfluxDB
- Test: `docker exec influxdb influx query 'from(bucket:"midnight_rider") |> filter(fn: (r) => r._measurement == "crew")'`

**Fatigue Index not calculating:**
- Check: Performance baseline is set correctly
- Verify: `navigation` measurement has speedOverGround data
- Ensure: Query includes `skipper` tag to separate Denis vs Anne-Sophie

**Countdown not updating:**
- Check: Watch change logged to InfluxDB with new timestamp
- Verify: Query pulls `min(watch_start_time)` correctly
- Test: Manual data insert to debug query

---

## 🎯 SUCCESS CRITERIA

✅ **Dashboard 9 is working if:**
- Crew status updates within 30 seconds of watch change
- Countdown timer reaches 00:00 at 2h mark
- Fatigue Index rises gradually during watch, resets at handover
- All alerts fire at correct thresholds
- iPad displays everything readably in kiosk mode

---

**Status:** ✅ Ready for integration  
**Next Step:** Configure regatta interface data export to InfluxDB  
**Target:** Field test (May 19, 2026)
