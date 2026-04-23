# 🚀 7-DAY ACTION PLAN — Start This Week!

**Duration:** 3 hours total  
**Goal:** Validate Phase 1 system end-to-end  
**Timeline:** Mon-Fri this week  

---

## DAY 1-2 (Monday-Tuesday): Test Infrastructure

### ACTION 1: Test Phase 1 Alerts (45 minutes) ⭐⭐⭐

**What to do:**
```
1. Open browser: http://localhost:3001
2. Login: admin / Aneto152
3. Go to: Alerting → Alert Rules
4. Count alerts (should see 60+)
5. Click on "SUNSET_APPROACHING" alert
6. Review configuration:
   - Condition should check sunset time
   - Interval should be 1 hour
   - For duration should be 5 minutes
7. Go to Dashboards → Navigation Dashboard
   - Should see heading gauge + trend
   - Should see speed gauge + trend
8. Go to Dashboards → Race Management
   - Should see helmsman stat
   - Should see sails stat
9. Go to Dashboards → Astronomical
   - Should see sunrise/sunset times
   - Should see moon illumination
10. All 3 dashboards load correctly? ✅
```

**Expected:** All dashboards visible, 60+ alerts listed  
**Confidence gained:** 70% (structure is correct)

---

### ACTION 2: Manual Alert Fire Test (15 minutes) ⭐

**What to do:**
```
1. Go to: Alerting → Alert Rules
2. Find "SUNSET_APPROACHING" alert
3. Click "Edit" (pencil icon)
4. Look for the time threshold (currently "120" or "< 120 min")
5. Change to a smaller value (e.g., "100" or "< 100 min")
6. Save alert
7. Wait 30 seconds
8. Go to: Alerting → Alert History
9. Look for "SUNSET_APPROACHING" in the list
10. Did it fire? ✅ → Alert engine works!
11. Edit alert again, revert to "120"
12. Save
```

**Expected:** Alert appears in Alert History within 30 seconds  
**Confidence gained:** 95% (system actually fires)

---

## DAY 2-3 (Tuesday-Wednesday): Deploy Claude

### ACTION 3: Deploy MCP to Claude Desktop (30 minutes) ⭐⭐⭐

**What to do:**

**Step 1: Locate Claude config**
```bash
# Check if file exists
ls -la ~/.config/Claude/claude_desktop_config.json

# If not, create directory:
mkdir -p ~/.config/Claude
```

**Step 2: Create config from example**
```bash
# Copy example to real location
cp /home/aneto/docker/signalk/mcp/claude_desktop_config.example.json \
   ~/.config/Claude/claude_desktop_config.json
```

**Step 3: Edit config** (fix paths)
```bash
nano ~/.config/Claude/claude_desktop_config.json

# For each server, make sure paths start with /home/aneto/docker/signalk/mcp/
# Example:
#   "astronomical": {
#     "command": "node /home/aneto/docker/signalk/mcp/astronomical-server.js"
#   }
```

**Step 4: Verify syntax**
```bash
# Check JSON is valid (should output without errors):
python3 -m json.tool ~/.config/Claude/claude_desktop_config.json > /dev/null && \
echo "✅ Config syntax OK"
```

**Step 5: Restart Claude**
- Close Claude completely (Cmd-Q on Mac, Alt-F4 on Windows)
- Wait 5 seconds
- Open Claude again

**Step 6: Test in Claude**
Type in Claude chat:
```
"What's our current heading and speed?"
```

**Expected response:** Should return heading in degrees + speed in knots  
**Confidence gained:** 90% (live coaching works)

---

## DAY 3-4 (Wednesday-Thursday): Test iPad Deployment

### ACTION 4: iPad WiFi Test (30 minutes) ⭐⭐⭐

**What to do:**

**On Raspberry Pi:**
```bash
# Check boat network IP:
hostname -I
# Note the IP (e.g., 192.168.1.50)
```

**On iPad:**
1. Connect to boat WiFi network
2. Open browser (Safari)
3. Enter: `http://[IP-from-above]:3001`
   - Example: `http://192.168.1.50:3001`
4. Login: admin / Aneto152
5. Check:
   - [ ] Navigation Dashboard loads
   - [ ] Race Management Dashboard loads
   - [ ] Astronomical Dashboard loads
   - [ ] Data is fresh (not hours old)
   - [ ] Font size is readable (if not, adjust Grafana zoom)
   - [ ] Auto-refresh works (data updates every 10 sec)
6. Try clicking on an alert to see details
7. Close browser, reopen (confirm it reconnects)

**Expected:** All dashboards readable on 10" iPad screen  
**Confidence gained:** 85% (deployment viable)

---

## DAY 4-5 (Thursday-Friday): System Health Check

### ACTION 5: Cron Job Healthcheck (1 hour) ⭐⭐

**What to do:**

**Step 1: Verify cron jobs exist**
```bash
crontab -l | grep -E "weather-logger|buoy-logger|astronomical"
# Should show 3 lines with these scripts
```

**Step 2: Check logs**
```bash
# Check if cron jobs are running recently:
tail -20 /tmp/weather-logger.log
tail -20 /tmp/buoy-logger.log
tail -20 /tmp/astronomical.log

# Should see recent timestamps (< 10 minutes old)
```

**Step 3: Create simple healthcheck script**
```bash
cat > /tmp/healthcheck.sh << 'BASH'
#!/bin/bash

echo "🔍 Checking data freshness..."

for log in weather-logger buoy-logger astronomical; do
  FILE="/tmp/${log}.log"
  if [ ! -f "$FILE" ]; then
    echo "❌ $log.log missing"
    continue
  fi
  
  AGE=$(($(date +%s) - $(stat -c %Y "$FILE" 2>/dev/null || stat -f %m "$FILE" 2>/dev/null)))
  MINS=$((AGE / 60))
  
  if [ $MINS -lt 10 ]; then
    echo "✅ $log OK ($MINS min ago)"
  elif [ $MINS -lt 20 ]; then
    echo "⚠️ $log stale ($MINS min ago)"
  else
    echo "❌ $log dead ($MINS min ago)"
  fi
done
BASH

chmod +x /tmp/healthcheck.sh
/tmp/healthcheck.sh
```

**Step 4: Add to crontab (hourly check)**
```bash
crontab -e

# Add this line at the end:
0 * * * * /tmp/healthcheck.sh >> /tmp/healthcheck-results.log 2>&1

# Save (Ctrl-X then Y)
```

**Step 5: Check InfluxDB data**
```bash
# Verify data is flowing (example query):
curl -s "http://localhost:8086/api/v2/query?org=MidnightRider" \
  --data-urlencode 'query=from(bucket:"signalk") |> range(start: -1h)' \
  -H "Authorization: Bearer $INFLUXDB_TOKEN" | head -20

# Should show recent measurements
```

**Expected:** All cron jobs running, data < 10 min old  
**Confidence gained:** 80% (pipeline reliable)

---

## CHECKLIST: 7-DAY COMPLETION

By Friday, you should have:

```
DAY 1-2: ✅ Test Phase 1 Alerts
  [ ] Logged in to Grafana
  [ ] Saw 60+ alerts
  [ ] Saw 3 dashboards
  [ ] Triggered SUNSET_APPROACHING manually
  [ ] Verified alert fired

DAY 2-3: ✅ Deploy Claude MCP
  [ ] Created claude_desktop_config.json
  [ ] Verified JSON syntax
  [ ] Restarted Claude
  [ ] Asked "What's our heading?" → Got answer

DAY 3-4: ✅ Test iPad WiFi
  [ ] Connected iPad to boat WiFi
  [ ] Accessed Grafana at http://IP:3001
  [ ] Logged in
  [ ] Verified 3 dashboards load
  [ ] Checked font is readable

DAY 4-5: ✅ System Health
  [ ] Verified cron jobs exist
  [ ] Checked log files are fresh
  [ ] Created healthcheck script
  [ ] Added to crontab

FINAL VERIFICATION:
  [ ] Go back to Grafana, all still working
  [ ] All dashboards refresh
  [ ] No alerts stuck
  [ ] iPad still connects
```

---

## 🎯 SUCCESS CRITERIA

If all checkboxes above are ✅, you have achieved:

```
✅ Phase 1 Alerts:   Verified to work
✅ Live Coaching:    Claude responds with live data
✅ iPad Access:      Grafana accessible on boat
✅ Data Pipeline:    All 3 cron jobs healthy
✅ System Ready:     Move to beta test phase
```

---

## 📊 AFTER THIS WEEK

Once all 7-day items are ✅, you're ready for:

### NEXT: Practice Race Beta Test (Week 2)
```
1. Deploy on boat during practice race
2. Have crew test dashboards
3. Collect feedback on alerts (useful/noise)
4. Note which alerts fire, which don't
5. Debrief after race
```

### THEN: Hardware Installation (Weeks 2-3)
```
1. Install YDWG-02 (wind sensor)
2. Install depth sounder
3. Configure loch (STW sensor)
4. Watch Phase 2 alerts auto-activate
```

### THEN: Production Deployment (Weeks 4+)
```
1. Live race with Phase 1+2
2. Tune thresholds based on feedback
3. Add race-specific Claude prompts
4. Iterate and improve
```

---

## ⚠️ TROUBLESHOOTING

**If Grafana won't load:**
```bash
# Check if running:
docker ps | grep grafana

# If not, restart:
docker-compose -f /home/aneto/docker/signalk/docker-compose.yml up -d
```

**If Claude doesn't respond:**
```bash
# Check if MCP servers running:
ps aux | grep -E "astronomical|racing|polar|crew|race|weather|buoy" | grep -v grep

# If not, start manually:
cd /home/aneto/docker/signalk/mcp
node astronomical-server.js &
node racing-server.js &
# ... etc
```

**If iPad can't connect:**
```bash
# Check Raspberry Pi network:
hostname -I

# Check firewall (allow 3001):
sudo ufw allow 3001

# Try from Mac first:
curl http://localhost:3001/api/health
```

---

## 📞 SUPPORT

If stuck:
1. Check GitHub: `/docker/signalk/` for examples
2. Check memory: `/home/aneto/.openclaw/workspace/MEMORY.md` for context
3. Check recovery guide: `RECOVERY-GUIDE.md` for full rebuild

---

## ✅ FINAL STATUS

After completing this 7-day plan:

| Check | Status |
|-------|--------|
| Phase 1 Alerts Fire | ✅ Verified |
| Claude Coaching Works | ✅ Live data |
| iPad Deployment Ready | ✅ Accessible |
| Data Pipeline Healthy | ✅ All jobs running |
| **Overall** | **✅ BETA READY** |

---

**Estimated Time:** 3 hours spread over 5 days  
**Confidence Level:** Very high (system end-to-end tested)  
**Next Step:** Practice race beta test (Week 2)

**Start this Monday! 🚀**
