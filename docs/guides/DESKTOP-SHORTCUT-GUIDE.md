# Desktop Shortcut Guide — Midnight Rider Dashboard

**Created:** 2026-04-26 22:30 EDT  
**Purpose:** Quick desktop access to Dashboard Portal  
**Platforms:** Linux/Ubuntu, macOS, Windows (manual)

---

## 🎨 ICON

**File:** `midnight-rider-icon.svg`

**Design:**
- Sailboat on waves
- Blue/cyan color scheme
- Racing flag with "MR" logo
- Compass rose (navigation symbol)
- Professional, minimal style

**Preview:**
```
     ★
    ⛵ (sails)
   /  \
  /____\  (hull)
  ≈ ≈ ≈ ≈ (waves)
```

---

## 📌 INSTALLATION

### LINUX / UBUNTU

**Automatic Installation:**

```bash
cd /home/aneto/.openclaw/workspace
bash install-desktop-shortcut.sh
```

**What it does:**
1. ✅ Creates `/home/aneto/Desktop/Midnight-Rider-Dashboard.desktop`
2. ✅ Copies icon to Desktop
3. ✅ Makes shortcut executable
4. ✅ Trusts the shortcut file

**Result:**
- Shortcut appears on Desktop
- Double-click to open Dashboard Portal
- Icon displays nicely

**Manual Installation:**

If automatic fails, do manually:

```bash
# Copy .desktop file
cp Midnight-Rider-Dashboard.desktop ~/Desktop/

# Copy icon
cp midnight-rider-icon.svg ~/Desktop/

# Make executable
chmod +x ~/Desktop/Midnight-Rider-Dashboard.desktop

# Trust it (GNOME)
gio set ~/Desktop/Midnight-Rider-Dashboard.desktop metadata::trusted true
```

### macOS

**Automatic Installation:**

```bash
cd /home/aneto/.openclaw/workspace
bash install-macos-shortcut.command
```

**What it does:**
1. ✅ Creates macOS app bundle
2. ✅ Converts SVG icon to ICNS format
3. ✅ Creates launcher script
4. ✅ Sets up Info.plist

**Result:**
- App appears on Desktop: "Midnight Rider Dashboard.app"
- Double-click to open
- Add to Dock by dragging
- Use Spotlight search (Cmd+Space)

**Manual Installation:**

If automatic fails:

1. Open Automator
2. New → Application
3. Add "Open URL" action
4. URL: `http://localhost:3001/dashboard-portal.html`
5. Save as: "Midnight Rider Dashboard" (Desktop)
6. Change icon (Get Info → Custom Icon)

### Windows (Manual)

1. Right-click Desktop → New → Shortcut
2. Location: `http://localhost:3001/dashboard-portal.html`
3. Name: `Midnight Rider Dashboard`
4. Finish

**Add Icon:**
1. Right-click shortcut → Properties
2. Shortcut tab → Change Icon
3. Browse to `midnight-rider-icon.svg`
4. OK

---

## 🚀 USAGE

### Desktop Shortcut

**Linux/macOS:**
- Double-click shortcut/app on Desktop
- Browser opens to Dashboard Portal

**Windows:**
- Double-click shortcut
- Browser opens to Dashboard Portal

**Requirements:**
- ✅ Grafana running (`docker compose up -d`)
- ✅ Network accessible at `localhost:3001`
- ✅ Default browser configured

### Add to Taskbar/Dock

**macOS:**
1. Drag app to Dock
2. Click to open anytime

**Windows:**
1. Right-click shortcut → Pin to Taskbar
2. Click to open anytime

**Linux (GNOME):**
1. Open Activities → Search "Midnight Rider"
2. Right-click → Add to Favorites
3. Click in Dock to open

---

## 🔧 TECHNICAL DETAILS

### .desktop File (Linux)

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Midnight Rider Dashboard
Exec=xdg-open http://localhost:3001/dashboard-portal.html
Icon=/path/to/icon.svg
Terminal=false
```

**Key Fields:**
- `Name`: Displayed on Desktop
- `Exec`: Command to run (opens in default browser)
- `Icon`: Path to SVG icon
- `Terminal=false`: Don't show terminal window

### macOS App Bundle

```
Midnight Rider Dashboard.app/
├── Contents/
│   ├── MacOS/
│   │   └── launcher (bash script)
│   ├── Resources/
│   │   └── icon.icns (or icon.svg)
│   └── Info.plist (app metadata)
```

**How it works:**
1. Click app → launches `launcher` script
2. Script runs: `open http://localhost:3001/dashboard-portal.html`
3. Default browser opens to Portal

---

## ⚙️ CUSTOMIZATION

### Change URL

**Linux (.desktop file):**
```ini
Exec=xdg-open http://192.168.1.100:3001/dashboard-portal.html
```

**macOS (launcher script):**
```bash
open "http://192.168.1.100:3001/dashboard-portal.html"
```

### Change Icon

Replace `midnight-rider-icon.svg` with your own SVG or PNG.

### Change Name

Edit the `Name` field in `.desktop` file or app properties.

---

## 🐛 TROUBLESHOOTING

### "Shortcut not working"

**Check:**
1. Grafana running? `docker ps | grep grafana`
2. Port 3001 accessible? `curl http://localhost:3001/api/health`
3. Browser can access? Open manually: `http://localhost:3001`

### "Icon not showing"

**Fix:**
1. Verify icon file exists: `ls ~/Desktop/midnight-rider-icon.svg`
2. Update path in `.desktop` file to absolute path
3. Refresh Desktop: `killall nautilus` (Linux) or restart Finder (Mac)

### "Opens wrong browser"

**Fix:**
1. Set default browser in system settings
2. Or edit shortcut to specify browser:
   ```
   Exec=firefox http://localhost:3001/dashboard-portal.html
   ```

### "Permission denied"

**Fix:**
```bash
chmod +x ~/Desktop/Midnight-Rider-Dashboard.desktop
chmod +x ~/Desktop/install-*.sh
```

---

## 📱 ALTERNATIVE: iPad HOME SCREEN

Instead of desktop shortcut, add to iPad home screen:

1. Open Safari: `http://[RPi-IP]:3001/dashboard-portal.html`
2. Tap Share → Add to Home Screen
3. Name: "Midnight Rider"
4. Add

Now it's an app on your iPad home screen!

---

## 📋 FILES

- `midnight-rider-icon.svg` — Icon graphic
- `Midnight-Rider-Dashboard.desktop` — Linux shortcut
- `install-desktop-shortcut.sh` — Linux installer
- `install-macos-shortcut.command` — macOS installer
- `DESKTOP-SHORTCUT-GUIDE.md` — This guide

---

## ✅ VERIFICATION

### Linux

```bash
# Check shortcut installed
ls -la ~/Desktop/Midnight-Rider-Dashboard.desktop

# Check icon
ls -la ~/Desktop/midnight-rider-icon.svg

# Test shortcut (should open browser)
xdg-open ~/Desktop/Midnight-Rider-Dashboard.desktop
```

### macOS

```bash
# Check app created
ls -la ~/Desktop/Midnight\ Rider\ Dashboard.app/

# Test (should open browser)
open ~/Desktop/Midnight\ Rider\ Dashboard.app/
```

---

## 🎯 RACE DAY WORKFLOW

**T-60 minutes:**
1. Boot RPi
2. Start Grafana: `docker compose up -d`
3. Click Desktop shortcut (or iPad app)
4. Dashboard Portal opens

**During Race:**
1. Use Dashboard Portal to navigate dashboards
2. All 9 dashboards accessible from portal
3. Fullscreen mode for clean display

---

**Status:** ✅ Complete  
**Platforms:** Linux, macOS, Windows (manual)  
**Ready:** Field test (May 19) + Race day (May 22)
