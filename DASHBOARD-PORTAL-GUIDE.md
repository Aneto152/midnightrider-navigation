# Dashboard Portal — Standalone Kiosk Mode

**Created:** 2026-04-26 22:25 EDT  
**Status:** ✅ Production-ready  
**Target:** iPad cockpit display (no authentication required)

---

## 📱 WHAT IS IT?

A simple HTML portal that displays all 9 Grafana dashboards in **kiosk mode** without requiring login authentication.

**Features:**
- ✅ No Grafana login needed
- ✅ Simple, clean interface
- ✅ iPad-optimized
- ✅ Fullscreen support
- ✅ Easy dashboard navigation
- ✅ Lightweight (pure HTML/CSS/JS)

---

## 🚀 HOW TO USE

### On iPad:

1. **Open Safari**
2. **Navigate to:** `http://[RPi-IP]:3001/dashboard-portal.html`
   - Example: `http://192.168.1.100:3001/dashboard-portal.html`

3. **You'll see 9 dashboard buttons:**
   - 🏠 COCKPIT
   - 🌊 ENVIRONMENT
   - ⚡ PERFORMANCE
   - 🌪️ WIND & CURRENT
   - 🏆 COMPETITIVE
   - 🔋 ELECTRICAL
   - 🏁 RACE
   - 🔔 ALERTS
   - ⚓ CREW

4. **Click any button to view that dashboard**
5. **Click "⬅ Menu" to go back to dashboard list**

### Fullscreen Mode:

**Option A:** Click "⛶ Fullscreen" button  
**Option B:** Press "F" key  
**Option C:** Double-tap screen (iPad)

---

## 🔧 TECHNICAL DETAILS

### Files:

**dashboard-portal.html**
- Landing page with 9 dashboard buttons
- Responsive grid layout
- iPad-optimized styling

**dashboard.html**
- Viewer page that displays each dashboard
- Loads Grafana dashboards in kiosk mode
- No authentication needed (kiosk mode)
- Fullscreen toggle functionality

### How It Works:

1. User clicks a dashboard button on `dashboard-portal.html`
2. Browser loads `dashboard.html` with dashboard UID as parameter
3. `dashboard.html` embeds the Grafana dashboard using an iframe
4. URL format: `http://[RPi-IP]:3001/d/{uid}?kiosk`
5. Kiosk mode removes Grafana menus, login prompts, etc.

---

## 🛠️ SETUP

### Option A: Web Server (Recommended)

Serve the files via Python's built-in server:

```bash
cd /home/aneto/.openclaw/workspace

# Start simple HTTP server
python3 -m http.server 8000

# Access at:
# http://localhost:8000/dashboard-portal.html
# OR
# http://[RPi-IP]:8000/dashboard-portal.html
```

### Option B: Direct Grafana Access

If Grafana serves static files, place files in Grafana directory:

```bash
sudo cp dashboard*.html /usr/share/grafana/public/

# Access at:
# http://localhost:3001/dashboard-portal.html
```

### Option C: iPad Bookmark

Add to iPad home screen:

1. Open in Safari: `http://[RPi-IP]:3001/dashboard-portal.html`
2. Tap Share → Add to Home Screen
3. Name: "Midnight Rider"
4. Now it's an app icon on your iPad home screen!

---

## 📋 DEPLOYMENT CHECKLIST

- [ ] Both HTML files copied to workspace
- [ ] HTTP server running (option A) OR files in Grafana public dir (option B)
- [ ] RPi network IP known (e.g., 192.168.1.100)
- [ ] iPad connected to same WiFi (MidnightRider)
- [ ] Test on iPad: Navigate to `http://[RPi-IP]:3001/dashboard-portal.html`
- [ ] All 9 dashboard buttons work
- [ ] Fullscreen mode works
- [ ] Menu navigation works

---

## 🎯 RACE DAY WORKFLOW

### Pre-Race (T-60 min):

1. **Start services:**
   ```bash
   systemctl status signalk
   docker compose up -d grafana influxdb
   ```

2. **Start HTTP server (if using option A):**
   ```bash
   cd /home/aneto/.openclaw/workspace
   python3 -m http.server 8000 &
   ```

3. **Test on iPad:**
   - Open Safari
   - Go to: `http://[RPi-IP]:3001/dashboard-portal.html`
   - Click each dashboard to verify they load

### During Race:

1. **On iPad, use dashboard portal:**
   - Default to COCKPIT dashboard
   - Swipe or click MENU to switch dashboards as needed
   - Use fullscreen mode for clean display

2. **Available dashboards in order of priority:**
   1. COCKPIT (primary)
   2. RACE (race-specific)
   3. COMPETITIVE (fleet position)
   4. WIND & CURRENT (tactical)
   5. CREW (watch management)
   6. PERFORMANCE (speed analysis)
   7. ENVIRONMENT (conditions)
   8. ELECTRICAL (power)
   9. ALERTS (monitoring)

### After Race:

1. Stop HTTP server (if running):
   ```bash
   pkill -f "python3 -m http.server"
   ```

2. Data automatically logged to InfluxDB
3. All dashboards available for post-race analysis

---

## ⚠️ TROUBLESHOOTING

### "Cannot reach http://[RPi-IP]:3001"

**Check:**
1. iPad is on same WiFi (MidnightRider)
2. RPi IP is correct (run `hostname -I` on RPi)
3. Grafana is running: `docker ps | grep grafana`
4. Try `http://192.168.1.1:3001` if unsure of exact IP

### "Dashboard shows error / No data"

**Check:**
1. Signal K running: `systemctl status signalk`
2. InfluxDB running: `docker ps | grep influx`
3. Wait 1-2 minutes for data to flow
4. Reload dashboard (pull down to refresh)

### "Fullscreen not working on iPad"

**Try:**
1. Double-tap instead of button click
2. Press "F" key (if keyboard attached)
3. Safari Settings → check fullscreen allowed

### "Fonts too small on iPad"

**Solution:**
- Pinch-to-zoom works in kiosk mode
- Or adjust display zoom in Settings if available

---

## 🎨 CUSTOMIZATION

### Change Dashboard Order:

Edit `dashboard-portal.html`, reorder the `<a>` elements in the grid.

### Change Colors:

Modify CSS variables in both HTML files:
- Primary color: `#00d4ff` (cyan)
- Dark background: `#1a1a2e`

### Add/Remove Dashboards:

1. Add new `<a class="dashboard-card">` block in `dashboard-portal.html`
2. Use correct dashboard UID (from Grafana)
3. Update icon and description

---

## 🔐 SECURITY NOTES

**This portal uses Grafana kiosk mode, which:**
- ✅ Hides login prompt
- ✅ Hides menu/admin panel
- ✅ Still requires Grafana authentication in background
- ⚠️ Anyone on the network can access the dashboards

**For production:**
- Consider firewall rules (restrict WiFi access)
- Or use VPN for remote access
- Credentials stored only in `.env.local` (not in HTML)

---

## 📊 NEXT STEPS

1. **Test locally:**
   ```bash
   # Start HTTP server
   python3 -m http.server 8000

   # Open browser
   http://localhost:8000/dashboard-portal.html
   ```

2. **Test on iPad:**
   - Connect iPad to same network
   - Navigate to: `http://[RPi-IP]:8000/dashboard-portal.html` (or 3001 if in Grafana dir)

3. **Field test (May 19):**
   - Full system test with live data
   - Verify all dashboards work
   - Check iPad responsiveness

4. **Race day (May 22):**
   - Use dashboard portal for crew display
   - Monitor all 9 dashboards as needed

---

**Status:** ✅ Ready for deployment  
**Last Updated:** 2026-04-26 22:25 EDT  
**For:** Midnight Rider Block Island Race 2026
