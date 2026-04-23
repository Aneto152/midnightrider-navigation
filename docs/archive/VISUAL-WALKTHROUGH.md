# 📸 VISUAL WALKTHROUGH — À Quoi Ça Ressemble

**Date:** 2026-04-20  
**Goal:** Show what you'll see when you open Grafana

---

## 🎯 ÉTAPE 1: Login Page

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                   Grafana                                      ║
║                   ═══════════════════════════════════          ║
║                                                                ║
║        Username: [admin________________]                      ║
║        Password: [•••••••••••]                                 ║
║                                                                ║
║              [    Sign in    ]                                 ║
║                                                                ║
║  Forgot your password? | New to Grafana?                      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

URL: http://localhost:3001
Username: admin
Password: Aneto152
```

---

## 🎯 ÉTAPE 2: Home Dashboard

```
╔════════════════════════════════════════════════════════════════╗
║  ⌂ Home        Dashboards    Alerting    Admin    Profile ≡   ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Welcome to Grafana                                            ║
║  ═════════════════════════════════════════════════════════     ║
║                                                                ║
║  [Recent Dashboards]                                           ║
║                                                                ║
║  • 01-navigation-dashboard.json         3 min ago              ║
║  • 02-race-dashboard.json               3 min ago              ║
║  • 03-astronomical-dashboard.json       3 min ago              ║
║                                                                ║
║  [Getting Started]                                             ║
║  • Create → Dashboard                                          ║
║  • Create → Alert Rule                                         ║
║  • Configuration → Data Sources                                ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🎯 ÉTAPE 3: Alerting → Alert Rules (THE MAIN VIEW)

```
╔════════════════════════════════════════════════════════════════╗
║  Alerting    [Alert Rules] [Contact points] [Notification...] ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Alert Rules (66 total)                                        ║
║  ═════════════════════════════════════════════════════════     ║
║                                                                ║
║  Filter:  [Search_______________] [All States ▼]              ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ 🌅 SUNSET_APPROACHING                   │ 🟠 WARNING   │  ║
║  │ └─ Evaluate every 1h, for 5 min        │ Phase: 1     │  ║
║  │    Sunset approaching in < 120 minutes │              │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ 🌃 NIGHT_APPROACH_CRITICAL             │ 🔴 CRITICAL  │  ║
║  │ └─ Evaluate every 1h, for 1 min        │ Phase: 1     │  ║
║  │    Night approaching in < 30 minutes   │              │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ 🏁 DISTANCE_TO_START_LINE               │ ⚠️ WARNING   │  ║
║  │ └─ Evaluate every 10s, for 10 sec      │ Phase: 1     │  ║
║  │    Distance < 300m (about 5 minutes)   │              │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ 🏁 START_COUNTDOWN                      │ 🔴 CRITICAL  │  ║
║  │ └─ Evaluate every 10s, for 5 sec       │ Phase: 1     │  ║
║  │    5/3/1/30/10 sec countdown           │              │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  [... scroll down for more alerts ...]                         ║
║                                                                ║
║  Total: 66 Alert Rules Configured ✅                          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

KEY ELEMENTS YOU'LL SEE:
  🟢 GREEN = OK/Good status
  🟠 ORANGE = WARNING (attention needed)
  🔴 RED = CRITICAL (immediate action)
  ℹ️ BLUE = INFO (just notification)

EACH ALERT SHOWS:
  • Title with emoji
  • Evaluate frequency (every 1h, 10s, etc.)
  • Duration before firing (for 5 min, etc.)
  • Description
  • Severity label (color coded)
```

---

## 🎯 ÉTAPE 4: Click on an Alert (Example: SUNSET_APPROACHING)

```
╔════════════════════════════════════════════════════════════════╗
║  ← Alert Rules                                                 ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Alert: 🌅 SUNSET_APPROACHING                                 ║
║  ═══════════════════════════════════════════════════════       ║
║                                                                ║
║  Status:       🟠 WARNING                                      ║
║  UID:          sunset_approaching                              ║
║  Evaluation:   Every 1 hour                                    ║
║  Fire after:   5 minutes                                       ║
║                                                                ║
║  Description:                                                  ║
║  ────────────                                                  ║
║  Sunset approaching in less than 2 hours.                      ║
║  Prepare return before dark.                                   ║
║                                                                ║
║  Condition:                                                    ║
║  ─────────                                                     ║
║  [No condition defined yet]                                    ║
║  (Ready to add: time < 120 minutes)                            ║
║                                                                ║
║  Labels:                                                       ║
║  ──────                                                        ║
║  • severity: warning                                           ║
║  • category: env                                               ║
║  • phase: 1                                                    ║
║                                                                ║
║  [Edit] [Delete] [Duplicate]                                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🎯 ÉTAPE 5: Navigation Dashboard (What Data Looks Like)

```
╔════════════════════════════════════════════════════════════════╗
║  Dashboards > 01-navigation-dashboard.json      [Edit] [Share] ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  MidnightRider — Navigation Dashboard                          ║
║                                                                ║
║  ┌──────────────────┬──────────────────┬──────────────────┐   ║
║  │   HEADING        │     SPEED        │      COG         │   ║
║  │                  │                  │                  │   ║
║  │      228°        │     6.2 kt       │    225°          │   ║
║  │      ↙           │      ↗           │      ↙           │   ║
║  │   SW direction   │  Good speed      │  Course toward   │   ║
║  │                  │                  │   Start line     │   ║
║  │  [1h trend ↗]    │  [1h trend ↗]    │  [1h trend ↘]    │   ║
║  └──────────────────┴──────────────────┴──────────────────┘   ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ HEADING — Last 1 Hour                                  │  ║
║  │                                                         │  ║
║  │  360°  ┌─────────────────────────────────────────┐   │  ║
║  │        │    ╱╲                        ╱╲          │   │  ║
║  │  270°  ├───╱  ╲      ╱╲      ╱╲     ╱  ╲────────├───│  ║
║  │        │  ╱    ╲    ╱  ╲    ╱  ╲   ╱    ╲       │   │  ║
║  │  180°  ├─╱──────╲──╱────╲──╱────╲─╱──────╲──────├───│  ║
║  │        │                                        │   │  ║
║  │   90°  └─────────────────────────────────────────┘   │  ║
║  │        Now                      1 hour ago           │  ║
║  │        228°                      215°                │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ RATE OF TURN — Last 1 Hour                             │  ║
║  │                                                         │  ║
║  │  15°/min  ┌────────────────────────────────────┐      │  ║
║  │           │                                    │      │  ║
║  │   0°/min  ├────────────────────────────────────┤      │  ║
║  │           │    ▁▂▃▂▁      ▂▃▄▃▂      ▁▂▁       │      │  ║
║  │  -15°/min └────────────────────────────────────┘      │  ║
║  │           Now                      1 hour ago         │  ║
║  │           +2°/min (turning right)  0°/min             │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  Auto-refresh: 10 seconds                                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🎯 ÉTAPE 6: Race Management Dashboard

```
╔════════════════════════════════════════════════════════════════╗
║  Dashboards > 02-race-dashboard.json           [Edit] [Share]  ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  MidnightRider — Race Management                              ║
║                                                                ║
║  ┌──────────────────┬──────────────────┬──────────────────┐   ║
║  │ HELMSMAN         │ CURRENT SAILS    │ DISTANCE TO      │   ║
║  │                  │                  │ START LINE       │   ║
║  │   Denis          │   Mainsail       │                  │   ║
║  │   On watch       │   Jib (working)  │   187 meters     │   ║
║  │   Since 12:43    │   Spinnaker      │                  │   ║
║  │   26 min         │   Down           │   YELLOW: OK     │   ║
║  │                  │                  │                  │   ║
║  │ [Rotate ▼]       │                  │ [6 min to start] │   ║
║  └──────────────────┴──────────────────┴──────────────────┘   ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ HELMSMAN ROTATION — Last 6 Hours                        │  ║
║  │                                                         │  ║
║  │ 14:00  Denis              Stable steering              │  ║
║  │ ├─────► Jean              Some drift detected          │  ║
║  │ 16:15  ├─────► Denis      Back on, excellent           │  ║
║  │ 17:30  ├─────► Sophie     New helmsman, settling       │  ║
║  │ 18:45  ├─────► Denis      Back for final leg           │  ║
║  │ Now                                                    │  ║
║  │                                                         │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ SAIL CHANGES — Last 6 Hours                             │  ║
║  │                                                         │  ║
║  │ 14:00  Mainsail up, Jib up                              │  ║
║  │ 15:30  ├─ Wind up to 14kt → Reef mainsail              │  ║
║  │ 16:45  ├─ Wind down → Shake out reef                   │  ║
║  │ 17:15  ├─ Approaching mark → Jib down, Spinnaker up    │  ║
║  │ 18:00  ├─ Rounding mark → Spinnaker down, Jib up       │  ║
║  │ 18:30  ├─ Building wind → Reef mainsail                │  ║
║  │                                                         │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  Auto-refresh: 10 seconds                                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🎯 ÉTAPE 7: Astronomical Dashboard

```
╔════════════════════════════════════════════════════════════════╗
║  Dashboards > 03-astronomical-dashboard.json  [Edit] [Share]   ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  MidnightRider — Astronomical Data                             ║
║                                                                ║
║  ┌──────────────────┬──────────────────┬──────────────────┐   ║
║  │   SUNRISE        │    SUNSET        │  MOON PHASE      │   ║
║  │                  │                  │                  │   ║
║  │  6:18 AM         │  7:52 PM         │   🌖 Waxing      │   ║
║  │  (09:42 from now)│  (01:12 from now)│   Gibbous        │   ║
║  │                  │                  │                  │   ║
║  │  🟢 Safe light   │  🟡 Caution      │   88% Full       │   ║
║  │  (6h45m until)   │  ⚠️ CRITICAL     │   (Good view)    │   ║
║  │                  │  (≈70 min left!) │                  │   ║
║  └──────────────────┴──────────────────┴──────────────────┘   ║
║                                                                ║
║  ┌──────────────────┬──────────────────┬──────────────────┐   ║
║  │ MOONRISE         │ MOONSET          │ MOON ILLUM.      │   ║
║  │                  │                  │                  │   ║
║  │ 11:15 PM         │ 10:02 AM         │  ████████░░ 88%  │   ║
║  │ (04:35 from now) │ Tomorrow         │  Bright & clear  │   ║
║  │                  │                  │  Good for night  │   ║
║  │ 🌙 Will help     │ Long night       │  navigation      │   ║
║  │ with night nav   │                  │                  │   ║
║  └──────────────────┴──────────────────┴──────────────────┘   ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ DAY/NIGHT CYCLE — Next 24 Hours                         │  ║
║  │                                                         │  ║
║  │  ☀️ Daylight                                            │  ║
║  │  ├─────────────────────────────────┬─ SUNSET (7:52 PM) │  ║
║  │  │ Now (6:40 PM)                   │                   │  ║
║  │  │                                 │                   │  ║
║  │  🌙 Night (dark)                                        │  ║
║  │  ├──────────────────────────────────┬─ SUNRISE (6:18 AM)│  ║
║  │  │ Midnight (darkest)              │                   │  ║
║  │  │                                 │                   │  ║
║  │                                                         │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  ⚠️ ALERT: SUNSET IN 71 MINUTES! 🔴                            ║
║  Prepare crew for return to anchorage before dark.             ║
║                                                                ║
║  Auto-refresh: 1 hour                                         ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🎯 ÉTAPE 8: Alert History (When Alert Fires)

```
╔════════════════════════════════════════════════════════════════╗
║  Alerting    Alert Rules    [Alert History]    Contact points  ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Alert History (showing recent activity)                       ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ Time      │ Alert Name        │ State    │ Duration    │   ║
║  ├────────────────────────────────────────────────────────┤   ║
║  │ 19:35 EDT │ 🌅 SUNSET_         │ Firing   │ 2 min       │   ║
║  │           │    APPROACHING     │ 🟠       │             │   ║
║  │           │                    │ WARNING  │             │   ║
║  ├────────────────────────────────────────────────────────┤   ║
║  │ 18:42 EDT │ 🏁 DISTANCE_TO_    │ Resolved │ 15 min      │   ║
║  │           │    START_LINE      │ ✅       │             │   ║
║  │           │                    │ OK       │             │   ║
║  ├────────────────────────────────────────────────────────┤   ║
║  │ 18:40 EDT │ 🏁 START_COUNTDOWN │ Firing   │ In progress │   ║
║  │           │                    │ 🔴       │             │   ║
║  │           │                    │ CRITICAL │             │   ║
║  ├────────────────────────────────────────────────────────┤   ║
║  │ 18:25 EDT │ 💨 LIFT_FAVORABLE  │ Resolved │ 8 min       │   ║
║  │           │                    │ ✅       │             │   ║
║  │           │                    │ OK       │             │   ║
║  └────────────────────────────────────────────────────────┘   ║
║                                                                ║
║  [← Previous Page]                      [Next Page →]          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🎯 ÉTAPE 9: iPad View (What Crew Sees in Cockpit)

```
┌──────────────────────────────────────────────────┐
│   WiFi   Battery   Location   10:15 PM          │
├──────────────────────────────────────────────────┤
│  ← Grafana — Race Dashboard                    │
├──────────────────────────────────────────────────┤
│                                                  │
│  HELMSMAN: Denis      SAILS: Mainsail + Jib    │
│  Since 12:43 (26 min) Full config              │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │  DISTANCE TO START LINE                │    │
│  │                                        │    │
│  │         ▀▀▀▀▀▀▀▀▀▀▀                     │    │
│  │      187 meters                        │    │
│  │      YELLOW (OK)                       │    │
│  │      6 minutes to start                │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  ⚠️ ALERTS ACTIVE:                             │
│     🟠 SUNSET_APPROACHING (71 min)             │
│     ℹ️ GOOD_WIND_CONDITIONS (10.2 kt, steady) │
│     ℹ️ OPTIMAL_HEEL (18°, perfect)            │
│                                                  │
│  [⟳ Refresh]                [Zoom: 110%]      │
│                                                  │
├──────────────────────────────────────────────────┤
│  Tap alerts to see details                      │
│  Swipe left for Navigation dashboard            │
│  Swipe right for Astronomical data              │
└──────────────────────────────────────────────────┘
```

---

## 🎯 ÉTAPE 10: Color Coding for Alerts

### Color Legend (What You'll See)

```
🟢 GREEN = OK / No alerts
   Status: Good, no action needed
   
🟡 YELLOW = Warning condition
   Example: Sunset < 2 hours away
   Action: Prepare for transition
   
🟠 ORANGE = Warning - attention needed
   Example: Excessive heel, wind drop
   Action: Adjust sails or course
   
🔴 RED = CRITICAL - immediate action
   Example: Race start in 30 sec, OCS, depth < 4m
   Action: NOW! Don't wait.
   
ℹ️ BLUE = Informational / Opportunity
   Example: Wind lift detected, optimal config
   Action: Consider but not urgent
```

---

## 📊 What Each Alert Looks Like When Firing

### Phase 1: Safety Alerts (Most Important)

```
🔴 CRITICAL: NIGHT_APPROACH_CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Night approaching in < 30 minutes.
Return to anchorage immediately.

Current: 30 min to sunset
Threshold: < 30 min
Status: FIRING 🔴
Duration: 3 minutes
Last triggered: 19:35 EDT
```

```
🟠 WARNING: SUNSET_APPROACHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sunset approaching in less than 2 hours.
Prepare return before dark.

Current: 71 min to sunset
Threshold: < 120 min
Status: FIRING 🟠
Duration: 5 minutes
Last triggered: 19:30 EDT
```

### Phase 2: Performance Alerts (Coaching)

```
⚠️ WARNING: VMG_BELOW_TARGET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VMG is below 85% of target.
Check sail trim, heel angle, or course angle.

Current: 5.2 kt (85% of 6.1 kt target)
Status: OK (borderline)
Target: 5.18 kt (85% threshold)
```

```
ℹ️ INFO: LIFT_FAVORABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wind shift detected (lift > 8°/3 min).
Adjust course or tack if beneficial.

Shift detected: 10° favorable
Duration: 3 min
Status: FIRING ℹ️
Action: Great opportunity!
```

---

## 🎨 Color Scheme on iPad Screen

```
NAVIGATION DASHBOARD:
┌─────────────────────────────────────────┐
│ HEADING: 228°                           │
│ ▁▂▃▄▅ ✓ (Stable)                        │
│                                         │
│ SPEED: 6.2 kt                           │
│ ▂▃▄▅▆ ✓ (Good)                          │
│                                         │
│ RATE OF TURN: +2°/min                   │
│ (Slight right turn)                     │
└─────────────────────────────────────────┘

RACE DASHBOARD:
┌─────────────────────────────────────────┐
│ DISTANCE: 187m  🟡 YELLOW (5-10 min)    │
│ • Green = >500m (plenty of time)        │
│ • Yellow = 300-500m (be ready)          │
│ • Red = <300m (HOT ZONE)                │
└─────────────────────────────────────────┘

ASTRONOMICAL DASHBOARD:
┌─────────────────────────────────────────┐
│ SUNSET: 7:52 PM                         │
│ ⚠️ WARNING: 71 minutes left! 🟠          │
│                                         │
│ MOON: 88% illuminated 🌖                │
│ ✓ Good for night navigation             │
└─────────────────────────────────────────┘
```

---

## 🎯 Real-World Example: During a Race

### 18:30 — Approaching Start Line

```
┌────────────────────────────────────────────────┐
│ ALERTS ACTIVE (Race Dashboard)                 │
├────────────────────────────────────────────────┤
│                                                │
│ 🟡 DISTANCE_TO_START_LINE: 450m (8 min)       │
│    Yellow: Prepare to maneuver                │
│    Focus helmsman, tighten crew positions      │
│                                                │
│ 🟠 EXCESSIVE_HEEL: 26° (target 18°)          │
│    Orange: Ease mainsheet slightly             │
│    Current config is overpowered              │
│                                                │
│ ℹ️ LIFT_FAVORABLE: +8° in last 3 min           │
│    Blue: Great timing! Good opportunity       │
│    Consider starboard tack approach            │
│                                                │
│ 🟢 VMG_OPTIMAL: 6.3 kt (105% of target)       │
│    Green: Excellent performance!              │
│    Keep doing what you're doing               │
│                                                │
├────────────────────────────────────────────────┤
│ Navigation: 228° | Speed: 6.2 kt | Turn: +2°  │
└────────────────────────────────────────────────┘
```

### 18:38 — Final Approach (Countdown!)

```
┌────────────────────────────────────────────────┐
│ 🔴 START_COUNTDOWN: 5 MIN / 3 MIN / 1 MIN!!    │
├────────────────────────────────────────────────┤
│                                                │
│ RED ALERT: CRITICAL PHASE STARTING             │
│ ────────────────────────────────────────────   │
│                                                │
│ Distance: 200m (RED ZONE!)                    │
│ Helmsman: FOCUS                                │
│ Crew: READY TO MANEUVER                        │
│                                                │
│ ACTIONS:                                       │
│  1. Denis = steady, hold course 228°          │
│  2. Trim: Main full, jib full, tight           │
│  3. Watch: Mark distance, other boats          │
│  4. Ready: Be at start line, not over          │
│                                                │
│ 5 MINUTES TO START                             │
│ ═════════════════════════════════════          │
│                                                │
└────────────────────────────────────────────────┘
```

### 18:40 — Start (All Alerts Firing!)

```
┌────────────────────────────────────────────────┐
│ 🔴🔴🔴 RACE START IN PROGRESS 🔴🔴🔴            │
├────────────────────────────────────────────────┤
│                                                │
│ 🔴 START_COUNTDOWN: 30 SECONDS                 │
│ 🔴 DISTANCE_TO_START_LINE: 50m                 │
│ 🟠 EXCESSIVE_HEEL: 28° (ease sail!)           │
│ ℹ️ WIND_ANGLE_OPTIMAL: 45° true wind          │
│ 🟢 HELMSMAN_STABLE: +1.2°/min drift           │
│                                                │
│ ALL SYSTEMS GO!                                │
│ Boat speed: 6.5 kt                             │
│ Position: Perfect on line                      │
│ Course: Holding 228°                           │
│ Start in 30 seconds...                         │
│                                                │
│ [VISUAL: Dashboard FLASHING RED + ALERTS]      │
│                                                │
│ 10...9...8...7...6...5...4...3...2...1...    │
│                                                │
│ 🎉 START! RACE BEGINS! 🎉                     │
│                                                │
└────────────────────────────────────────────────┘
```

---

## 📱 What Crew Members Say When They See This

```
Helmsman (Denis):
"OK, I see the distance countdown. I'm holding the line.
 Red alert says I'm at 28° heel - easing main a bit.
 Good, now it says optimal config. Let's go!"

Trimmer (Jean):
"I see the wind lift alert! That's 8°+ shift.
 Denis, we could tack now and get better angle.
 VMG is at 105% - we're sailing fast!"

Navigator (Sophie):
"Sunset alert shows 90 minutes left.
 After start, we're clear to race for about 2 hours.
 Moon is bright (88%), so we can sail into evening if needed."

Crew Chief:
"All alerts look good. No critical warnings.
 Let's get through the start clean and adjust from there."
```

---

## 🎯 Summary: What You Actually See

| When | What Appears | Color | Action |
|------|-------------|-------|--------|
| **Normal sailing** | Green dashboard, info alerts | 🟢 | Monitor |
| **Approaching warning** | Yellow/orange alerts | 🟡🟠 | Prepare |
| **Critical moment** | Red flashing alerts | 🔴 | ACT NOW |
| **After event** | Green again, info logged | 🟢 | Resume |

**Everything is visual, color-coded, and in real-time on your iPad.**

No confusing numbers. Just:
- 🟢 Good
- 🟡 Get ready
- 🟠 Adjust
- 🔴 NOW!

---

**This is what Grafana + Alerts looks like in action.** 🚀
