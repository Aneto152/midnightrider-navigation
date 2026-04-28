# COCKPIT Dashboard — Manual Edit Guide
**Because API permissions are locked in Grafana v12**

---

## Quick Fix: Manual Panel Edit in Grafana UI

Since the API is blocking programmatic updates, edit the panels manually in Grafana. It's fast (5 minutes total).

### Step 1: Login to Grafana

1. Open: http://localhost:3001
2. Login: admin / admin
3. Search for "COCKPIT" dashboard
4. Click to open it

### Step 2: Edit Panel Type

For EACH of these 6 panels:

1. Click the panel title to open options
2. Click "Edit" (pencil icon)
3. Change panel type:
   - Top right corner, you'll see "Stat" or "Gauge"
   - Click dropdown → Select "Time series"
4. Go to "Options" tab
5. Configure:
   - **Legend:** "Table" mode, show mean/max/min/last
   - **Tooltip:** "Multi" mode
6. Click "Save"

### Panels to Convert

| # | Panel Name | Time Range | Unit |
|---|---|---|---|
| 1 | Speed Over Ground (SOG) | 10 min | knots |
| 2 | Heading True | 10 min | degrees |
| 3 | Roll (Heel) | 10 min | degrees |
| 4 | Pitch | 10 min | degrees |
| 5 | Speed History (5 min) | 1 hour | knots |
| 6 | Attitude History | 1 hour | degrees |

### Step 3: Verify Changes

After editing each panel:
- Graph should show time series (line chart)
- Legend should show statistics (mean, max, min, last)
- Unit should be correct (knots, degrees)
- Values should make sense (SOG 0-15 kt, Heading 0-360°, Roll ±45°)

### Step 4: Save Dashboard

Click "Save dashboard" button (top right)

---

## Alternative: Use Dashboard JSON Import

If you want to do it programmatically:

1. Go to Grafana UI
2. Dashboard menu → New → Import
3. Paste the JSON from `docs/grafana-dashboards/01-cockpit.json`
4. Select folder: "General"
5. Click "Import"

This will OVERWRITE the existing COCKPIT dashboard with the new time series version.

---

## What Changed in the JSON

We modified:
- Panel `type`: changed from "stat" to "timeseries"
- Panel `fieldConfig`: added unit overrides
- Panel `options`: added legend and tooltip configs

All queries stay the same (with rad→° and m/s→kt conversions already in place).

---

## Status

✅ JSON file modified: `docs/grafana-dashboards/01-cockpit.json`
✅ Changes committed to GitHub
⏳ Need to apply in Grafana UI (manual or import method)

Once done:
- Dashboard shows 6 time series charts
- Live data updates in real-time
- Full hour of historical data visible
- Ready for field test (May 19) and race day (May 22)

---

**Quick question:** Did you want to do manual edit or import JSON? Let me know and I can guide step-by-step! 🚀
