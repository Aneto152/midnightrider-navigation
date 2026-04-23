# Plugin Dependencies Checklist

**Purpose:** Track all external files and dependencies required by Signal K plugins  
**Created:** 2026-04-23  
**Status:** Active maintenance document

---

## 🎯 Why This Matters

When reinstalling or migrating plugins from old to new locations, external files can be forgotten:
- Data files (polars, calibration tables, lookup data)
- Configuration files
- Resource files
- Documentation files

This checklist ensures **nothing is left behind**.

---

## 📋 Plugin Dependencies Matrix

### 1. **signalk-performance-polars**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | 9.4 KB | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | 115 B | ~/.signalk/node_modules/ | ✅ Present | Standard npm |
| **J/30 Polars Data** | j30-polars-data.json | 12 KB | ~/.signalk/node_modules/ | ✅ Present | **CRITICAL** - Polar speeds |
| **Configuration** | signalk-performance-polars.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | User settings |

**Dependencies to copy when migrating:**
- ✅ j30-polars-data.json (was in ~/.signalk/plugins/, now in node_modules/)

**Error if missing:**
```
Error: cannot find module j30-polars-data.json
Plugin fails to load - no polar calculations
```

---

### 2. **signalk-wave-height-imu**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | 9.9 KB | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | 401 B | ~/.signalk/node_modules/ | ✅ Present | Standard npm |
| **Documentation** | README.md | 9.3 KB | ~/.signalk/node_modules/ | ✅ Present | User guide |
| **Configuration** | signalk-wave-height-imu.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | User settings |

**Dependencies to copy when migrating:**
- None (self-contained plugin)

**Loads from Signal K:**
- ✅ navigation.acceleration.z (from WIT IMU)

---

### 3. **signalk-wit-imu-usb**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | 7.0 KB | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | 600 B | ~/.signalk/node_modules/ | ✅ Present | v2.1.0 |
| **Documentation** | README.md | - | workspace docs/ | ✅ Present | User guide |
| **Configuration** | signalk-wit-imu-usb.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | USB port, baud rate |

**Dependencies to copy when migrating:**
- None (self-contained)

**Hardware dependency:**
- ✅ USB device: /dev/ttyWIT (WIT WT901BLECL IMU)

---

### 4. **signalk-astronomical**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | - | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | - | ~/.signalk/node_modules/ | ✅ Present | Standard npm |
| **Configuration** | signalk-astronomical.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | NOAA station, lat/lon |

**Dependencies to copy when migrating:**
- None (uses external APIs - NOAA)

---

### 5. **signalk-sails-management-v2**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | - | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | - | ~/.signalk/node_modules/ | ✅ Present | v2.0.0 |
| **Configuration** | signalk-sails-management-v2.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | Sail config |

**Dependencies to copy when migrating:**
- None (self-contained)

---

### 6. **signalk-loch-calibration**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | - | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | - | ~/.signalk/node_modules/ | ✅ Present | Standard npm |
| **Configuration** | signalk-loch-calibration.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | Calibration factors |

**Dependencies to copy when migrating:**
- None (self-contained)

---

### 7. **signalk-current-calculator**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | - | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | - | ~/.signalk/node_modules/ | ✅ Present | Standard npm |
| **Configuration** | signalk-current-calculator.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | Window size, thresholds |

**Dependencies to copy when migrating:**
- None (self-contained)

---

### 8. **signalk-rpi-cpu-temp**

| Dependency | File | Size | Location | Status | Notes |
|------------|------|------|----------|--------|-------|
| **Main Code** | index.js | - | ~/.signalk/node_modules/ | ✅ Present | Plugin logic |
| **Package Metadata** | package.json | - | ~/.signalk/node_modules/ | ✅ Present | Standard npm |
| **Configuration** | signalk-rpi-cpu-temp.json | - | ~/.signalk/plugin-config-data/ | ✅ Present | Thresholds |

**Dependencies to copy when migrating:**
- None (self-contained)

---

## 🔍 Migration Checklist Template

When moving plugins from old to new location:

### For Each Plugin:

```markdown
Plugin: [name]
Source: ~/.signalk/plugins/
Target: ~/.signalk/node_modules/[plugin-name]/

□ Main plugin file (index.js or plugin.js)
□ Package metadata (package.json)
□ Data files:
  □ Polars/calibration data
  □ Lookup tables
  □ Configuration templates
□ Documentation (README.md, guides)
□ Configuration (plugin-config-data/*.json)
□ Hardware dependencies (USB, serial, etc.)
□ External API dependencies (NOAA, etc.)

Special notes:
_________________________________
```

---

## 📝 Critical Dependencies

### HIGH PRIORITY - Plugin Won't Load Without These

| Plugin | File | Impact |
|--------|------|--------|
| **performance-polars** | j30-polars-data.json | ❌ Plugin fails to load |
| **wave-height-imu** | - | ✅ Self-contained |
| **wit-imu-usb** | - | ✅ Self-contained |

### MEDIUM PRIORITY - Plugin Loads But Broken Features

| Plugin | File | Impact |
|--------|------|--------|
| All plugins | plugin-config-data/*.json | ⚠️ Default config, user loses settings |

### LOW PRIORITY - Nice to Have

| Plugin | File | Impact |
|--------|------|--------|
| All plugins | README.md, docs | ℹ️ Users can't find help |

---

## 🚀 Prevention Strategy

### Before Migration:

1. **Audit source directory**
   ```bash
   ls -lh ~/.signalk/plugins/
   # List ALL files - not just .js
   ```

2. **Document dependencies**
   ```bash
   grep -r "require.*\\.json" ~/.signalk/plugins/*.js
   # Find all data file references
   ```

3. **Create migration checklist**
   ```bash
   for file in ~/.signalk/plugins/*; do
     echo "- [ ] $(basename $file)"
   done
   ```

### During Migration:

```bash
# Copy plugin code
cp -r ~/.signalk/plugins/signalk-NAME.js \
  ~/.signalk/node_modules/signalk-NAME/index.js

# Copy ALL related files
cp ~/.signalk/plugins/*.json \
  ~/.signalk/node_modules/signalk-NAME/ 2>/dev/null || true

# Verify nothing left behind
diff <(ls ~/.signalk/plugins/) \
     <(find ~/.signalk/node_modules/signalk-* -type f)
```

### After Migration:

```bash
# Test plugin loads
curl http://localhost:3000/skServer/plugins | grep signalk-NAME

# Check for errors in logs
journalctl -u signalk -f | grep -i "cannot find\|require"

# Verify all features work
curl http://localhost:3000/signalk/v1/api/vessels/self/
```

---

## 📊 Dependency Tracking by Category

### Data Files (Must Copy!)

```
✅ j30-polars-data.json
   └─ Needed by: signalk-performance-polars
   └─ Size: 12 KB
   └─ Critical: YES (plugin won't load without it)
```

### Configuration Files (Auto-restored)

```
✅ plugin-config-data/*.json
   └─ Auto-restored from settings.json on restart
   └─ Location: ~/.signalk/plugin-config-data/
   └─ Critical: NO (defaults used if missing)
```

### Code Files (Must Copy!)

```
✅ index.js (or plugin.js)
   └─ Main plugin code
   └─ Required for all plugins
   └─ Critical: YES
```

### Metadata Files (Must Copy!)

```
✅ package.json
   └─ NPM package metadata
   └─ Required for Discovery
   └─ Critical: YES
```

### Documentation (Nice to Have)

```
✅ README.md
   └─ User documentation
   └─ Not critical for functionality
   └─ Critical: NO (but helpful)
```

### Hardware Dependencies (Verify!)

```
✅ /dev/ttyWIT (WIT IMU)
   └─ Must exist for signalk-wit-imu-usb
   └─ Check: ls /dev/ttyWIT
   └─ Critical: YES

✅ /dev/ttyUSB0 (GPS, other serial)
   └─ Varies by hardware
   └─ Check: ls /dev/ttyUSB*
   └─ Critical: YES
```

---

## 🎓 Lessons Learned

### What Went Wrong (April 23)

```
❌ Performance Polars plugin reinstalled
❌ j30-polars-data.json NOT copied
❌ Plugin tried to require() missing file
❌ Result: Plugin crash - "cannot find module"
```

### How to Prevent

```
✅ Audit ALL files before migration (ls -lh)
✅ Grep for external file references (require, readFile)
✅ Document dependencies in this checklist
✅ Copy ALL files, not just .js
✅ Test after migration (curl endpoints)
✅ Check logs for errors (journalctl)
```

---

## 📝 Maintenance Schedule

### Weekly
- [ ] Verify all 9 plugins load without errors
  ```bash
  curl http://localhost:3000/skServer/plugins
  ```

### Monthly
- [ ] Review this checklist for accuracy
- [ ] Update dependencies if plugins changed
- [ ] Verify all data files present
  ```bash
  ls -lh ~/.signalk/node_modules/signalk-*/
  ```

### Quarterly
- [ ] Full plugin audit
- [ ] Test migration procedure
- [ ] Update migration documentation

---

## 🔗 Related Documents

- `PLUGINS-REINSTALLED-2026-04-23.md` - Original plugin recovery
- `BUGFIX-POLARS-J30-2026-04-23.md` - The polars data fix
- `SESSION-FINAL-RECAP-2026-04-23.md` - Complete session summary

---

## ✅ Verification Checklist

### Current Status (2026-04-23)

- [x] signalk-performance-polars - j30-polars-data.json present
- [x] signalk-wave-height-imu - No external dependencies
- [x] signalk-wit-imu-usb - No missing files
- [x] signalk-astronomical - NOAA API (external)
- [x] signalk-sails-management-v2 - Self-contained
- [x] signalk-loch-calibration - Self-contained
- [x] signalk-current-calculator - Self-contained
- [x] signalk-rpi-cpu-temp - Self-contained

**Overall Status:** ✅ **ALL DEPENDENCIES SATISFIED**

---

## 📞 Quick Reference

### If a plugin fails to load:

1. **Check error message:**
   ```bash
   journalctl -u signalk -f | grep ERROR
   ```

2. **If "cannot find module":**
   - Look for required .json file in ~/.signalk/plugins/
   - Copy to plugin's node_modules/ directory
   - Restart Signal K

3. **If "require() error":**
   - Check package.json exists in plugin directory
   - Verify index.js exists and is readable

4. **If feature missing:**
   - Check plugin-config-data/*.json exists
   - Verify configuration in settings.json
   - Check for errors in app logs

---

**Last Updated:** 2026-04-23  
**Maintained By:** Denis Lafarge  
**Status:** ✅ Active document  
**Review Frequency:** Monthly

