# 📋 Import All 28 Alerts into Grafana

**Status:** Ready to Deploy  
**Total Alerts:** 28 (Phase 1 + Phase 2)  
**Date:** 2026-04-20

---

## Quick Summary

```
28 TOTAL ALERTS CONFIGURED:

PHASE 1 (Public APIs - No Hardware):
├─ Safety (3):        SUNSET, NIGHT_CRITICAL, POOR_VISIBILITY
├─ Astronomy (4):     SUNRISE, MOONRISE, SLACK_WATER (2x)
├─ Racing (3):        DISTANCE, COUNTDOWN, OCS
├─ Weather (2):       NWS_GALE, PRESSURE_DROP
└─ Depth (1):         CRITICAL

PHASE 2 (Hardware Dependent):
├─ Performance (12):  VMG (2), ANGLE, HEEL (3), INSTABILITY (3), CURRENT (2)
├─ Wind Shifts (4):   LIFT, HEADER, PERSISTENT, GEOGRAPHIC
├─ Sails (7):         CONFIG, REDUCTION, INCREASE, SPIBOAT, DOUSE, SEAS, OPTIMAL
├─ Racing (1):        WIND_MISMATCH
└─ Navigation (2):    LAYLINES (2)
```

---

## 3 Ways to Import

### Method 1: Grafana UI Import (Recommended - 10 minutes)

1. **Open Grafana:**
   ```
   http://localhost:3001
   Login: admin / Aneto152
   ```

2. **Go to Alerting:**
   ```
   Alerting → Alert Rules → + Create Alert Rule
   ```

3. **For Each Alert:**
   - Click "+ Create Alert Rule"
   - Fill in:
     - Name: (from list below)
     - Condition: Your query (InfluxDB filter)
     - Evaluate: Every [interval]
     - For: [duration]
   - Labels: category, phase, severity
   - Save

**Benefit:** UI-friendly, can customize as you go

---

### Method 2: YAML Upload (Via Provisioning - 5 minutes)

1. **Copy YAML file to provisioning:**
   ```bash
   sudo cp all-alert-rules.yaml /etc/grafana/provisioning/alerting/
   sudo chown grafana:grafana /etc/grafana/provisioning/alerting/all-alert-rules.yaml
   sudo chmod 644 /etc/grafana/provisioning/alerting/all-alert-rules.yaml
   ```

2. **Restart Grafana:**
   ```bash
   sudo systemctl restart grafana-server
   ```

3. **Verify:**
   - Grafana → Alerting → Alert Rules
   - Should see all 28 alerts listed

**Benefit:** One-command deployment, reproducible

---

### Method 3: Terraform/IaC (Advanced - 15 minutes)

Use Grafana Terraform provider to manage alerts as code.

```bash
terraform init
terraform apply
```

**Benefit:** Version control, repeatable, team-friendly

---

## 28 Alerts Details

### 🚨 PHASE 1 (12 Alerts - Immediate)

#### Safety & Astronomy (7)
1. **SUNSET_APPROACHING**
   - Trigger: sunset < 120 min
   - Interval: 1 hour
   - Severity: WARNING

2. **NIGHT_APPROACH_CRITICAL**
   - Trigger: sunset < 30 min
   - Interval: 5 minutes
   - Severity: CRITICAL

3. **POOR_VISIBILITY**
   - Trigger: moon illumination < 20%
   - Interval: 1 hour
   - Severity: INFO

4. **SUNRISE_TIME**
   - Trigger: sunrise approaching
   - Interval: 1 hour
   - Severity: INFO

5. **MOONRISE_EVENT**
   - Trigger: moon rising
   - Interval: 1 hour
   - Severity: INFO

6. **SLACK_WATER_APPROACHING**
   - Trigger: current slack approaching
   - Interval: 30 minutes
   - Severity: INFO

7. **SLACK_WATER_30MIN**
   - Trigger: slack water in 30 min
   - Interval: 30 minutes
   - Severity: INFO

#### Racing (3)
8. **DISTANCE_TO_START_LINE**
   - Trigger: distance < 300m
   - Interval: 10 seconds
   - Severity: WARNING

9. **START_COUNTDOWN**
   - Trigger: 5/3/1/30/10 sec
   - Interval: 10 seconds
   - Severity: CRITICAL

10. **OCS_EARLY_START**
    - Trigger: line crossed before gun
    - Interval: 10 seconds
    - Severity: CRITICAL

#### Weather & Depth (2)
11. **NWS_GALE_WARNING**
    - Trigger: SCA/Gale bulletin active
    - Interval: 30 minutes
    - Severity: CRITICAL

12. **PRESSURE_DROP_WARNING**
    - Trigger: pressure > 3 hPa drop in 3h
    - Interval: 30 minutes
    - Severity: WARNING

13. **DEPTH_CRITICAL**
    - Trigger: depth < 4m
    - Interval: 10 seconds
    - Severity: CRITICAL

---

### ⚙️ PHASE 2 (16 Alerts - Hardware Dependent)

#### Performance Metrics (12)
14. **VMG_BELOW_TARGET**
    - Trigger: VMG < 85% polaire
    - Interval: 10 seconds
    - Duration: 30 sec
    - Severity: WARNING

15. **VMG_EXCEEDING_TARGET**
    - Trigger: VMG > 105% polaire
    - Interval: 10 seconds
    - Duration: 30 sec
    - Severity: INFO

16. **WIND_ANGLE_SUBOPTIMAL**
    - Trigger: |TWA - optimal| > 5°
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: WARNING

17. **EXCESSIVE_HEEL**
    - Trigger: heel > 25° for 2 min
    - Interval: 10 seconds
    - Duration: 2 min
    - Severity: WARNING

18. **INSUFFICIENT_HEEL_UPWIND**
    - Trigger: heel < 8° && TWS > 12kt
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: WARNING

19. **HEEL_INSTABILITY**
    - Trigger: std(heel) > 5°/2min
    - Interval: 10 seconds
    - Duration: 2 min
    - Severity: WARNING

20. **CURRENT_VARIATION_FORCE**
    - Trigger: current magnitude change > 0.5kt/5min
    - Interval: 10 seconds
    - Duration: 5 min
    - Severity: WARNING

21. **CURRENT_VARIATION_DIRECTION**
    - Trigger: current direction change > 20°/5min
    - Interval: 10 seconds
    - Duration: 5 min
    - Severity: WARNING

22. **HELMSMAN_INSTABILITY**
    - Trigger: std(TWA) > 5°/10min
    - Interval: 10 seconds
    - Duration: 10 min
    - Severity: WARNING

23. **HEADING_DRIFT**
    - Trigger: |mean(TWA) - target| > 5° over 20min
    - Interval: 10 seconds
    - Duration: 20 min
    - Severity: WARNING

24. **HELMSMAN_DEGRADATION**
    - Trigger: helmsman stability trending down
    - Interval: 10 seconds
    - Duration: 5 min
    - Severity: WARNING

25. **ROTATION_RECOMMENDED**
    - Trigger: fatigue indicators detected
    - Interval: 10 seconds
    - Duration: 5 min
    - Severity: INFO

#### Wind Shifts (4)
26. **LIFT_FAVORABLE**
    - Trigger: wind shift > 8° favorable in 3min
    - Interval: 10 seconds
    - Duration: 3 min
    - Severity: INFO

27. **HEADER_UNFAVORABLE**
    - Trigger: wind shift > 8° unfavorable in 3min
    - Interval: 10 seconds
    - Duration: 3 min
    - Severity: WARNING

28. **PERSISTENT_SHIFT**
    - Trigger: persistent direction change > 20°/30min
    - Interval: 10 seconds
    - Duration: 30 min
    - Severity: INFO

#### Sail Configuration (7)
29. **SAIL_CONFIG_CHANGE**
    - Trigger: optimal sails != current
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: INFO

30. **SAIL_REDUCTION**
    - Trigger: wind increasing
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: WARNING

31. **SAIL_INCREASE**
    - Trigger: underpowered condition
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: INFO

32. **SPINNAKER_POSSIBLE**
    - Trigger: TWA > 120°, TWS < 18kt
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: INFO

33. **SPINNAKER_DOUSE**
    - Trigger: gust forecast
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: WARNING

34. **SEAS_CORRECTION**
    - Trigger: pitch/roll excessive
    - Interval: 10 seconds
    - Duration: 1 min
    - Severity: WARNING

35. **OPTIMAL_CONFIG**
    - Trigger: VMG ratio > 95% for 5 min
    - Interval: 10 seconds
    - Duration: 5 min
    - Severity: INFO

#### Racing Navigation (2)
36. **LAYLINE_STARBOARD**
    - Trigger: starboard layline achieved
    - Interval: 10 seconds
    - Duration: 10 sec
    - Severity: INFO

37. **LAYLINE_PORT**
    - Trigger: port layline achieved
    - Interval: 10 seconds
    - Duration: 10 sec
    - Severity: INFO

#### Weather (1)
38. **WIND_MISMATCH**
    - Trigger: |measured TWS - forecast| > 3kt
    - Interval: 10 seconds
    - Duration: 10 min
    - Severity: INFO

---

## Configuration Notes

### Data Requirements

For Phase 1 alerts to work:
- ✅ InfluxDB with `signalk` bucket
- ✅ Astronomical data (sunrise/sunset/moon/tides)
- ✅ Public APIs (NWS, NOAA)

For Phase 2 alerts to work:
- ⏳ YDWG-02 wind sensor (TWS, TWA, TWD)
- ⏳ BNO085 IMU or UM982 proprietary (heel, pitch, roll)
- ⏳ Sounder (depth)

### Evaluation Intervals

```
Every 1 hour:  Astronomical alerts
Every 30 min:  Weather alerts
Every 10 sec:  Racing & performance alerts
```

### Severity Levels

- 🔴 **CRITICAL**: Immediate action required (race start, OCS, depth, night)
- ⚠️ **WARNING**: Attention needed (pressure drop, excessive heel, headers)
- ℹ️ **INFO**: Monitoring/informational (lifts, optimal config, opportunities)

---

## Deployment Checklist

- [ ] Verify InfluxDB data available (at least Phase 1 data)
- [ ] Verify Grafana running (http://localhost:3001)
- [ ] Choose import method (UI, YAML, or Terraform)
- [ ] Import all 28 alerts
- [ ] Verify alerts appear in Alerting → Alert Rules
- [ ] Test with sample data
- [ ] Deploy to iPad (WiFi dashboard access)
- [ ] Monitor during first race
- [ ] Gather feedback from crew

---

## Testing Alerts

### Phase 1 Test (Can test immediately)

1. Check sunset approaching:
   - Go to Grafana now
   - Manually trigger alert (set threshold to current time)
   - Should appear in Alert Rules

2. Check depth critical:
   - If sounder data available, set low threshold
   - Alert should fire

### Phase 2 Test (When hardware connected)

1. Check VMG alerts:
   - Once wind sensor connected
   - Alerts will automatically start firing
   - Check helmsman instability

---

## Next Steps

1. **Choose import method** (UI recommended)
2. **Import all 28 alerts**
3. **Test with Phase 1 data** (available now)
4. **Deploy Phase 2 alerts** (when hardware ready)
5. **Monitor and adjust thresholds** based on feedback

---

**Status:** ✅ All 28 alerts configured and ready
**Files:** all-alert-rules.yaml (ready to import)
**Timeline:** 5-10 minutes to deploy
**Next:** Choose import method and start! 🚀
