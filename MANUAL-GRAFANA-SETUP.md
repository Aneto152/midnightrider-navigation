# MANUAL GRAFANA SETUP (Web UI)

**If automated scripts fail**, use this guide for manual configuration via browser.

---

## 📱 STEP 1: Access Grafana Web UI

1. Open browser
2. Navigate to: **http://localhost:3001**
3. Login with password (from Grafana setup)

---

## 🔗 STEP 2: Configure InfluxDB Datasource

### Go to Data Sources
1. Click **Admin** (left sidebar, gear icon)
2. Click **Data Sources**
3. Click **Add data source**

### Configure InfluxDB
**Field** | **Value**
---------|----------
Name | `InfluxDB`
Type | `InfluxDB`
URL | `http://localhost:8086`
Auth | **None**
Organization | `MidnightRider`
Token | (paste from `.env.local`)
Default Bucket | `midnight_rider`

### Details:

1. **Name:** `InfluxDB`
2. **Type:** Select "InfluxDB" from dropdown
3. **HTTP Settings:**
   - URL: `http://localhost:8086`
   - Access: `Server` (default)
4. **InfluxDB Details:**
   - Query Language: `Flux`
   - Organization: `MidnightRider`
   - Token: (copy from `.env.local` INFLUX_TOKEN line)
   - Default Bucket: `midnight_rider`

### Get Token from .env.local
```bash
# On RPi, run:
grep INFLUX_TOKEN /home/aneto/.openclaw/workspace/.env.local

# Output:
INFLUX_TOKEN="j5zWJmdrK4BoU359...=="

# Copy the value between quotes (without quotes)
```

### Test Connection
1. Click **Save & Test**
2. Should see: **"✅ Data source is working"**
3. If error, check:
   - InfluxDB is running: `docker ps | grep influx`
   - Token is correct (no spaces)
   - Bucket name is exact (case-sensitive)

---

## 📊 STEP 3: Import Dashboards

### Go to Import
1. Click **Dashboards** (left sidebar)
2. Click **Import**

### Upload Dashboard Files
1. Click **Upload JSON file**
2. Navigate to: `/home/aneto/.openclaw/workspace/grafana-dashboards/`
3. Select: **01-cockpit.json**
4. Click **Import**

### Configure Import
- **Name:** (auto-filled, OK to keep)
- **Data source:** Select `InfluxDB` from dropdown
- Click **Import**

### Repeat for all 9 dashboards
Do the above for:
- `01-cockpit.json`
- `02-environment.json`
- `03-performance.json`
- `04-wind-current.json`
- `05-competitive.json`
- `06-electrical.json`
- `07-race.json`
- `08-alerts.json`
- `09-crew.json`

---

## ✅ STEP 4: Verify Dashboards

### Check if imported
1. Click **Dashboards** (left sidebar)
2. You should see all 9:
   - 01 — COCKPIT
   - 02 — ENVIRONMENT
   - 03 — PERFORMANCE
   - 04 — WIND & CURRENT
   - 05 — COMPETITIVE
   - 06 — ELECTRICAL
   - 07 — RACE
   - 08 — ALERTS
   - 09 — CREW

### Check if data flows
1. Click **01 — COCKPIT**
2. Should see panels loading
3. If "No data":
   - Wait 1 minute (InfluxDB needs data)
   - Check Signal K is running
   - Verify InfluxDB has data

### Test Navigation
1. Scroll down to bottom of any dashboard
2. Click navigation links
3. Should jump between dashboards

---

## 🔐 STEP 5: Set Default Dashboard

### (Optional) Make COCKPIT the home dashboard
1. Go to **Admin** → **Preferences**
2. Under "Default Dashboard"
3. Select **01 — COCKPIT (Main Navigation)**
4. Click **Save**

---

## 📱 STEP 6: iPad Setup

### WiFi Connection
1. iPad: Settings → WiFi
2. Connect to: **MidnightRider** network
3. Open Safari

### Browse Dashboard
1. Enter: `http://192.168.1.1:3001` (or RPi IP)
2. You should see Grafana login
3. Click **01 — COCKPIT**

### Kiosk Mode (hide menu bar)
**Optional:** For race cockpit display
1. URL: `http://192.168.1.1:3001/d/cockpit-main?kiosk`
2. This hides Grafana menu for clean display
3. Command+Shift+F to full screen

---

## 🛠️ TROUBLESHOOTING

### "No Data" in Panels

**Check 1: InfluxDB has data**
```bash
# SSH to RPi, run:
docker exec influxdb influx query \
  'from(bucket:"midnight_rider") |> range(start: -1h) |> limit(n: 10)' \
  --org MidnightRider
```

If no results, Signal K hasn't written data yet.

**Check 2: Signal K is running**
```bash
systemctl status signalk
```

Should show "active (running)"

**Check 3: Datasource is correct**
1. Admin → Data Sources
2. Click InfluxDB
3. Scroll to bottom: "Data Sources Tests"
4. Click "Save & Test"
5. Should show ✅

### "Unauthorized" error

**Check:**
1. Token in `.env.local` is correct
2. No spaces in token
3. Token hasn't expired
4. User/org permissions correct

### Dashboard won't load

**Check:**
1. All 9 dashboards imported?
2. Each has `InfluxDB` datasource selected?
3. InfluxDB datasource configured?
4. Grafana restarted? Try:
   ```bash
   docker restart grafana
   ```

### Navigation links broken

**Check:**
1. Dashboard UIDs match links
2. All dashboards imported
3. Check browser console for errors

---

## 📝 REFERENCE

**Credentials (from .env.local):**
- Grafana password: (ask Denis)
- InfluxDB token: (in .env.local)

**URLs:**
- Grafana: http://localhost:3001
- InfluxDB: http://localhost:8086
- iPad: http://[RPi-IP]:3001

**Files:**
- Dashboard JSONs: `/home/aneto/.openclaw/workspace/grafana-dashboards/`
- Tokens: `/home/aneto/.openclaw/workspace/.env.local` (local only)

---

**Status:** ✅ Complete  
**Last Updated:** 2026-04-26  
**Ready for:** Field test (May 19), Race day (May 22)
