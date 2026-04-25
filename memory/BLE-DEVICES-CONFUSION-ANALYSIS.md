# BLE Devices Confusion Analysis — WIT vs Calypso

**Date:** 2026-04-25 01:04 EDT
**Investigation:** Denis Lafarge's intuition about device confusion

---

## 🎯 KEY FINDING: Calypso UUIDs are GENERIC (Huami Smartwatch!)

### Problem Identified

**Calypso script UUIDs:**
```python
self.service_uuid = "0000ffe0-0000-1000-8000-00805f9b34fb"
self.char_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"
```

**What these UUIDs actually are:**
- `0x180D` / `0x2A39` = Calypso official (from Dev Manual 1.0)
- `0xffe0` / `0xffe1` = **Huami Smartwatch proprietary** (Mi Band, etc.)

✅ **Denis' intuition is CORRECT:** The script is using generic/wrong UUIDs!

---

## 📊 Device Status Summary

| Device | Model | MAC | Status | Issue |
|--------|-------|-----|--------|-------|
| **WIT** | WT901BLECL | E9:10:DB:8B:CE:C7 | ⏳ Offline (firmware) | BLE advertising broken |
| **Calypso** | UP10 | ??? | ⏳ Unknown (battery?) | Script won't find it anyway |
| **UM982** | Dual GNSS | /dev/ttyUSB0 | ✅ Working | NMEA sentences verified |

---

## 🔴 Calypso Script Issues (Revisited)

**The script will never work because:**

1. **Uses wrong UUIDs:** `0xffe0/0xffe1` (Huami) instead of `0x180D/0x2A39` (Calypso)
2. **Even if Calypso is powered:** It's invisible to this script
3. **Even if device found by accident:** Payload parsing is completely wrong (0x55 0xAA sync = WIT pattern)

### Hypothetical Scenario

If Denis powers on Calypso and it advertises as "ULTRASONIC-XXXX":
```
✅ Calypso is powered and advertising
❌ Script looks for "0xffe0" service (Huami)
❌ Doesn't find Calypso's actual 0x180D service
❌ Script fails with "No Calypso found"
```

---

## 🤔 Possible Real Scenarios

### Scenario 1: Calypso Battery Dead
```
Current state:
  - WIT: firmware issue (doesn't advertise)
  - Calypso: possibly battery dead (0-2.5% = invisible)

Symptom:
  - Both devices invisible in BLE scan
  - Looks like both "don't work"
  - But it's 2 different problems!
```

### Scenario 2: Calypso in Sleep Mode
```
If Calypso battery 2.5-10%:
  - BLE advertises (visible in scan)
  - But UUID 0xA001 = 0x00 (Sleep Mode)
  - No wind data available!
  - Script tries to read: FAILS

Symptom:
  - "Found Calypso but no data"
  - Even with correct UUIDs!
```

### Scenario 3: Manual Device Activation
```
If someone had manually paired WIT expecting Calypso:
  - Connected to wrong device
  - Frustrated that "Calypso" gives gyro/accel instead of wind
  - But actually connected to WIT!
```

---

## 📋 CRITICAL CHECKLIST — Before Blaming Hardware

```
FOR WIT:
[ ] 1. Is WIT powered on? (Blue LED should blink)
[ ] 2. bluetoothctl scan on → see "WT901BLE68"?
[ ] 3. If not visible → firmware issue (matches diagnosis)
[ ] 4. If visible → try connect E9:10:DB:8B:CE:C7
[ ] 5. If connected → plugin should auto-connect (100 Hz data)

FOR CALYPSO:
[ ] 1. Is Calypso powered on? (Solar panel or USB charged?)
[ ] 2. bluetoothctl scan on → see "ULTRASONIC-XXXX"?
[ ] 3. If not visible → battery dead OR device off
[ ] 4. If visible → good sign (not in Safety Mode < 2.5%)
[ ] 5. Try correct UUID: 0x180D service, 0x2A39 characteristic
[ ] 6. Read UUID 0xA001 → check battery status (0x00=sleep, 0x02=normal)
[ ] 7. If sleep mode → charge first, then retest

FOR CONFUSION PREVENTION:
[ ] Use EXPLICIT MAC addresses (not generic keywords)
[ ] Use OFFICIAL UUIDs from datasheets (not guesses)
[ ] TEST with generic BLE tools first:
    bluetoothctl scan on
    bluetoothctl connect <MAC>
    gatttool -b <MAC> -I
    char-discover
```

---

## 🎯 RECOMMENDATION

### Immediate Action: Test Both Devices Separately

**Test WIT (E9:10:DB:8B:CE:C7):**
```bash
bluetoothctl scan on
# Look for: WT901BLE68 @ E9:10:DB:8B:CE:C7

# If not visible:
echo "WIT firmware issue confirmed — needs reflash"

# If visible:
bluetoothctl connect E9:10:DB:8B:CE:C7
gatttool -b E9:10:DB:8B:CE:C7 -I
> connect
> primary    # Should list services without hanging
```

**Test Calypso (unknown MAC):**
```bash
bluetoothctl scan on
# Look for: ULTRASONIC-XXXX (or similar)
# Note the MAC address

# If not visible:
echo "Calypso not advertising — battery dead or off"
# → Charge via USB or solar panel 4-6 hours

# If visible:
bluetoothctl connect <CALYPSO_MAC>
gatttool -b <CALYPSO_MAC> -I
> char-discover
# Look for: 0x180D (Data Service) and 0x2A39 (main char)
```

---

## 📝 FINDINGS SUMMARY

✅ **Denis' intuition was spot-on:**
- Calypso script uses wrong UUIDs (Huami, not Calypso)
- Could indeed be confused with other devices or not find Calypso at all
- Explains why "Calypso" never worked (despite charging)

🔴 **Root causes identified:**
1. **WIT:** Firmware BLE advertising broken (confirmed via gatttool GATT stall)
2. **Calypso:** Script broken (wrong UUIDs + payload parsing) + possibly battery dead

⚠️ **Not necessarily confusion:** More like "2 independent problems coincidentally at same time"

---

## 🚀 NEXT STEPS (Priority Order)

1. **WIT firmware reflash** (enables BLE advertising)
   - Plugin is 100% correct, just waiting for hardware fix
   - ETA: 1-5 days

2. **Charge Calypso** (verify battery not dead)
   - USB charge 4-6 hours
   - ETA: today

3. **Rewrite Calypso script** (fix UUID + payload)
   - Use correct UUIDs from Dev Manual
   - Proper 5-byte payload parsing
   - ETA: 2-3 hours of coding

4. **Field test both devices**
   - WIT in BLE mode + Calypso in NMEA/BLE mode
   - Verify wind + attitude flowing into Signal K

---

**Conservé précieusement pour référence future! ⛵**
