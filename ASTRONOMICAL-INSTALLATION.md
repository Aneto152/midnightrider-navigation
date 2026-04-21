# Astronomical Plugin Installation Checklist

## 🎯 Objectif
Installer et tester le plugin Signal K Astronomical Data + Tides pour:
- ✅ Sunrise/Sunset times
- ✅ Moonrise/Moonset + illumination + phase
- ✅ Tide predictions (NOAA Stamford, Long Island Sound)

## 📋 Pre-Installation Status (2026-04-19 20:38)

### ✅ Done
- [x] Plugin code written (345 lines)
- [x] Plugin config created (noaaStation: 8467150)
- [x] Plugin copied to `~/.signalk/plugins/`
- [x] Documentation complete
- [x] Commits pushed to GitHub (4 commits)

### ⏳ Remaining
- [ ] npm install suncalc axios (in Signal K context)
- [ ] Restart Signal K
- [ ] Enable plugin in Admin UI
- [ ] Verify in logs
- [ ] Test in Grafana

---

## 🚀 Installation Steps

### Step 1: Install Dependencies (Docker Context)
```bash
# If Signal K runs in Docker
docker exec -it signalk npm install suncalc axios

# Or if running as systemd
# cd /home/node/signalk && npm install suncalc axios
```

**Expected output:**
```
added 24 packages (or similar)
```

### Step 2: Restart Signal K
```bash
# Docker
docker restart signalk

# Or systemd
# systemctl restart signalk
```

**Wait ~10 seconds for startup**

### Step 3: Enable Plugin in Admin UI

1. Open: http://localhost:3000
2. Navigate: Admin → Appstore → Installed Plugins
3. Search: "Astronomical Data"
4. Click: **Enable**

### Step 4: Verify Installation

```bash
# Check Signal K logs for [Astro] messages
docker logs signalk 2>&1 | grep "\[Astro\]"
```

**Expected:**
```
[Astro] Plugin started
[Astro] NOAA Station: 8467150
```

---

## 📊 Data Flow Verification

### Check 1: Plugin → Signal K
```bash
# Should see values being sent
docker logs signalk 2>&1 | grep -A2 "Sending delta with"
```

### Check 2: Signal K → InfluxDB
Verify that `signalk-to-influxdb2` plugin is **ENABLED**:
1. Admin → Appstore → Installed Plugins
2. Find: "signalk-to-influxdb2"
3. Should be: **Enabled**

### Check 3: InfluxDB Has Data
```bash
# Query for sun/moon data
influx query 'from(bucket:"signalk") 
  |> range(start: -24h) 
  |> filter(fn: (r) => r._measurement =~ /environment.sun|environment.moon|environment.tide/)'
```

### Check 4: Grafana Display

Create test dashboard:
1. Grafana: + Create → Dashboard
2. Add Panel → Grafana
3. Query: `SELECT value FROM "environment.sun.sunriseTime"`
4. Should display ISO timestamp

---

## 📍 Configuration

**File:** `~/.signalk/plugin-config-data/signalk-astronomical.json`

```json
{
  "enabled": true,
  "debug": false,
  "noaaStation": "8467150"
}
```

**To change station:**
- Edit noaaStation value
- Restart Signal K
- New station data next update cycle

**Common stations:**
- 8467150 = Stamford Harbor, CT (Long Island Sound) ← CURRENT
- 8465705 = New Haven Harbor, CT
- 8510560 = Port Jefferson Harbor, NY

---

## 🧪 Expected Data Points

**First update:** Tomorrow at ~00:00 (UTC or local, depending on TZ)

### Sun (from suncalc)
```
environment.sun.sunriseTime      "2026-04-20T05:34:00Z"
environment.sun.sunsetTime       "2026-04-20T19:28:00Z"
```

### Moon (from suncalc)
```
environment.moon.moonriseTime    "2026-04-20T02:15:00Z"
environment.moon.moonsetTime     "2026-04-20T14:42:00Z"
environment.moon.illumination    0.65
environment.moon.phase           "waxing_gibbous"
```

### Tides (from NOAA)
```
environment.tide.tideHighTime    "2026-04-20T14:30:00-04:00"
environment.tide.tideHighLevel   2.15
environment.tide.tideLowTime     "2026-04-20T20:45:00-04:00"
environment.tide.tideLowLevel    0.45
```

---

## 🚨 Troubleshooting

### Plugin doesn't appear in Appstore
- Check: `ls -la ~/.signalk/plugins/signalk-astronomical.js`
- Restart Signal K
- Clear browser cache

### Plugin fails to start
```bash
docker logs signalk 2>&1 | grep -i error
```
- Check suncalc/axios installed
- Check config JSON syntax

### No data in InfluxDB
- Verify signalk-to-influxdb2 is enabled
- Check NOAA API accessible: ping api.tidesandcurrents.noaa.gov
- Wait 24h for first update (plugin checks hourly, updates daily)

### Wrong tide data
- Verify station ID in config (8467150 = Stamford, CT)
- Check NOAA availability: https://tides.noaa.gov

---

## 📝 Files

| File | Purpose | Location |
|------|---------|----------|
| signalk-astronomical.js | Main plugin (345 lines) | `/home/aneto/docker/signalk/plugins/` |
| Config JSON | Enable/disable, station ID | `~/.signalk/plugin-config-data/signalk-astronomical.json` |
| README | User guide | `/home/aneto/docker/signalk/plugins/ASTRONOMICAL-README.md` |

---

## ✅ Checklist

### Installation
- [ ] npm install suncalc axios
- [ ] Restart Signal K
- [ ] Enable in Admin UI
- [ ] See "[Astro] Plugin started" in logs

### Verification
- [ ] Signal K sends data (check logs)
- [ ] signalk-to-influxdb2 enabled
- [ ] InfluxDB has measurements
- [ ] Grafana can query environment.sun.sunriseTime

### First Data
- [ ] Wait for 00:00 UTC (or next hour boundary)
- [ ] Check InfluxDB for new measurements
- [ ] Verify values make sense (times in future, illumination 0-1)

### Done! 🎉
- [ ] Create Grafana dashboard
- [ ] Set up alerts (sunset, tides, full moon)
- [ ] Test in boat

---

## 📞 Support

All logs and source:
- GitHub: https://github.com/Aneto152/midnightrider-navigation
- Commits:
  - 8aab63d = Phase 1A (Sun/Moon)
  - 92890b8 = Environment namespace
  - d832e9e = Phase 1B (Tides)
  - b2cd5df = Long Island Sound config
