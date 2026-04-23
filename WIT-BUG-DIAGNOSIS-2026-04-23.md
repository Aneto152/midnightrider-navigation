# 🔴 WIT WT901BLECL BUG DIAGNOSIS - 2026-04-23

## THE PROBLEM

Plugin WIT v2.0 est installé, mais:
- ✅ Accélération ARRIVE dans Signal K (0x50)
- ❌ Attitude (Roll/Pitch/Yaw) N'arrive PAS

## ROOT CAUSE FOUND

Le WIT ENVOIE un packet type **0x61** que notre plugin ne reconnaît PAS.

### Data Analysis

```
Raw serial data observed:
55 61 18 00 b2 ff 45 08 00 00 00 00 00 00 7e fe 88 ff c6 31

Where:
  55   = Header (WIT standard)
  61   = Type byte (UNKNOWN!)
  Rest = Data payload
```

### WIT Type Codes

Standard types implemented in v2.0:
- 0x50 = Acceleration ✅
- 0x51 = Angular velocity ✅
- 0x52 = Attitude (Roll/Pitch/Yaw) ✅
- 0x53 = Magnetic field ✅
- 0x54 = Barometer ✅

**But WIT is sending:**
- 0x61 = ??? (UNKNOWN) ❌

## NEXT STEPS

### Option 1: Find WIT Documentation
- Search WT901BLECL manual for type 0x61
- Could be a VARIANT or SPECIAL MODE
- Check Witmotion (manufacturer) website

### Option 2: Reverse Engineer 0x61
Raw packet: `55 61 18 00 b2 ff 45 08 00 00 00 00 00 00 7e fe 88 ff c6 31`

Payload analysis:
- Bytes 2-3: `18 00` = 0x0018 = 24 (decimal) - Could be angle scaled differently?
- Bytes 4-5: `b2 ff` = -78 (signed int16)
- Bytes 6-7: `45 08` = 2117 (unsigned int16)
- etc.

Pattern suggests: Could be combined attitude packet or different scaling

### Option 3: Check if WIT Needs Configuration
WT901BLECL may send different formats depending on mode:
- Could need to enable specific output modes
- May require firmware command sequence
- Might have configuration register for packet types

## SYMPTOMS OBSERVED

1. Serial port active and readable ✓
2. Data flowing at correct baud rate (115200) ✓
3. Wrong packet type = packets SKIPPED ✗
4. Need to identify what 0x61 contains

## ACTION ITEMS

- [ ] Search WT901BLECL documentation for type 0x61
- [ ] Contact Witmotion support if needed
- [ ] Consider reverse-engineering the packet
- [ ] Check if firmware update available
- [ ] May need to send config commands to WT901BLECL

## CONCLUSION

**NOT a Signal K problem.**
**NOT an installation problem.**
**IS a packet format mismatch: WT901BLECL sends 0x61, we expect 0x52.**

Need to identify what 0x61 is and add handler.

---

**Date:** 2026-04-23 00:00 EDT
**Investigation:** 3.5 hours
**Status:** ROOT CAUSE IDENTIFIED ✅
