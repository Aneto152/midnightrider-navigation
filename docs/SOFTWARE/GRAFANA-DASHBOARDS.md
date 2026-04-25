# GRAFANA DASHBOARDS — Midnight Rider

**URL:** http://localhost:3001  
**Data Source:** InfluxDB (port 8086)  
**Update Rate:** 1 sec (real-time)  
**Date:** 2026-04-25

---

## 4 MAIN DASHBOARDS

### 1. NAVIGATION DASHBOARD

**Purpose:** Monitor position, heading, speed  
**Gauges:**
- Position (lat/lon map)
- True heading (compass rose)
- Speed over ground (knots)
- Course over ground (compass)
- Distance to waypoint

**Use:** Helm can glance at primary navigation data

---

### 2. RACE DASHBOARD

**Purpose:** Sailing performance metrics  
**Gauges:**
- VMG (Velocity Made Good)
- Heel angle (in degrees)
- Wind speed + direction
- Apparent wind angle
- Sail trim recommendations (from v2 plugin)
- Crew ratings (from polars comparison)

**Use:** Crew chief monitors performance, adjusts trim

---

### 3. ASTRONOMICAL DASHBOARD

**Purpose:** Environmental data (sun/moon/tide)  
**Gauges:**
- Sunrise/sunset time
- Moon phase + position
- Water temperature
- Air temperature
- Barometric pressure trend

**Use:** Strategic planning (e.g., sunset = mark your position)

---

### 4. ALERTS DASHBOARD

**Purpose:** System health + warnings  
**Alerts:**
- Heel > 22° (consider reefing)
- Wave Hs > 2.5m (dangerous)
- Wind gust > 25 knots (sudden change)
- GPS signal loss (red)
- IMU offline (red)
- Database storage low (orange)

**Use:** Quick scan for system problems or dangerous conditions

---

## iPad ACCESS (WiFi)

### Connection
1. iPad WiFi: Connect to `MidnightRider` network
2. Open browser: `http://192.168.x.x:3001`
3. Dashboards load in real-time

### Best Practices
- Lock iPad in landscape mode
- Use half-screen split (Grafana + Compass app)
- Keep brightness >50% (sunlight glare)
- Tap to refresh if blank (browser issue)

---

## CUSTOMIZATION

### Add New Dashboard
1. Grafana web: Click **+** → **Dashboard**
2. Add panels (gauges, graphs, tables)
3. Connect to InfluxDB queries
4. Save

### Add Alert Rule
1. **Alerting** → **Alert Rules**
2. Define condition (e.g., `heel > 22°`)
3. Set notification channel (optional)

---

## LIVE RACE DATA

**Entire race will be logged:**
```bash
SELECT * FROM signalk WHERE time > '2026-05-22T11:00:00Z' AND time < '2026-05-22T14:00:00Z'
```

Post-race analysis: Full 3-hour replay available.

---

**Status:** ✅ Ready  
**Last Updated:** 2026-04-25
