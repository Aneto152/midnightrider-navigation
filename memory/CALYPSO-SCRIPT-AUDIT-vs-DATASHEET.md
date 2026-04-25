# Audit: Calypso BLE Reader vs Documentation officielle

**Date:** 2026-04-25 01:02 EDT
**Comparaison:** calypso-ble-reader.py vs Datasheet 2023 + User Manual v2.0 + Developer Manual 1.0

---

## 🔴 CRITIQUE — UUIDs Incorrects

**Doc officielle (Developer Manual 1.0):**
```
Service 0x180A — Device Information (READ)
  UUID 0x2A29 Manufacturer Name
  UUID 0x2A24 Model Number
  UUID 0x2A26 Firmware Revision

Service 0x180D — Data Service (NOTIFY + READ) ← PRINCIPAL
  UUID 0x2A39 — Wind speed + direction + battery (5 bytes)
  UUID 0xA001 — Status (READ)
  UUID 0xA002 — Data Rate (READ + WRITE)

Service 0x181A — Environmental Sensing (NOTIFY + READ)
  UUID 0x2A72 — Apparent Wind Speed
  UUID 0x2A73 — Apparent Wind Direction

Service 0x180F — Battery (NOTIFY + READ)
  UUID 0x2A19 — Battery Level
```

**Script actuel:**
```python
self.service_uuid = "0000ffe0-0000-1000-8000-00805f9b34fb"  # ❌ WRONG
self.char_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"    # ❌ WRONG
```

**Analyse:**
- `0xffe0/0xffe1` = Propriétaire Huami (smartwatch), PAS Calypso
- Correct: `0x180D` + `0x2A39` (ou 0x181A + 0x2A72/0x2A73)
- Doc clairement spécifie UUIDs officiels GATT

🔴 **IMPACT:** Script ne trouvera JAMAIS le Calypso!

---

## ❌ INCORRECT — Payload Format (Binary Decoding)

**Doc officielle (Developer Manual 1.0):**
```
UUID 0x2A39 payload (5 bytes, little endian):
  Bytes 0-1 : Wind Speed uint16 LE → /100 = m/s
    ex: 39 02 → 0x0239 = 569 → 5.69 m/s
  
  Bytes 2-3 : Wind Direction uint16 LE → degrés directs
    ex: CE 00 → 0x00CE = 206 → 206°
  
  Byte 4 : Battery uint8 → 0-100%
    ex: 5A → 90%
```

**Script actuel:**
```python
def decode_calypso_binary(self, data):
    if data[0] == 0x55 and data[1] == 0xAA:  # ❌ WRONG SYNC PATTERN
        wind_speed = struct.unpack('>H', bytes([data[2], data[3]]))[0] / 100.0
        wind_angle = struct.unpack('>H', bytes([data[4], data[5]]))[0] / 100.0
        # Bytes offset: data[2-3] pour speed (CORRECT), data[4-5] pour angle
        # Mais: WRONG byte offsets! Doc dit bytes 0-1, 2-3, not 2-3, 4-5
```

**Problèmes identifiés:**

1. **Sync pattern 0x55 0xAA:** ❌ C'est WIT, pas Calypso!
   - Calypso n'a PAS de sync pattern
   - Format directement: [speed_L, speed_H, dir_L, dir_H, battery]

2. **Byte order:** ❌ Utilise big-endian (`'>H'`)
   - Doc dit little-endian (`'<H'`)
   - Conversion erronée!

3. **Byte offsets:** ❌ data[2-3] pour speed
   - Doc dit bytes 0-1 pour speed
   - Offset wrong!

**Correction requise:**
```python
def decode_calypso_payload(self, data):
    """Parse 5-byte Calypso UP10 payload"""
    if len(data) < 5:
        return None
    
    # Little-endian uint16 for speed (bytes 0-1)
    speed_raw = struct.unpack('<H', data[0:2])[0]
    speed_ms = speed_raw / 100.0  # m/s
    
    # Little-endian uint16 for direction (bytes 2-3)
    dir_raw = struct.unpack('<H', data[2:4])[0]
    direction_deg = dir_raw  # degrés directs (0-359)
    
    # Uint8 for battery (byte 4)
    battery_pct = data[4]
    
    return {
        'speed_ms': speed_ms,
        'direction_deg': direction_deg,
        'battery_pct': battery_pct,
        'valid': speed_ms >= 1.0  # threshold
    }
```

---

## ⚠️ INCORRECT — Angle Conversion to Radians

**Doc officielle:**
```
Convention Calypso (0-359°):
  0° = bow (étrave)
  90° = starboard (tribord)
  180° = stern (arrière)
  270° = port (bâbord)

Signal K convention (angleApparent, radians, -π to +π):
  0 = bow
  +π/2 = starboard
  ±π = stern
  -π/2 = port

Conversion:
  if deg <= 180: rad = deg × π/180
  if deg > 180: rad = (deg - 360) × π/180
```

**Script actuel:**
```python
def degrees_to_radians(self, degrees):
    return (degrees % 360) * 3.14159265359 / 180.0
    # ❌ WRONG: retourne toujours 0-2π, jamais négatif!
    # Doc dit convention ±π (signed)
```

**Problème:**
- Script retourne 0 à 2π
- Signal K s'attend à -π à +π (signed)
- Exemple:
  - Script: 270° → 4.71 rad (positif!)
  - Correct: 270° → -π/2 = -1.57 rad (négatif, port)

**Correction requise:**
```python
import math

def degrees_to_radians_signed(self, degrees):
    """Convert 0-359° to -π to +π convention"""
    if degrees <= 180:
        return degrees * math.pi / 180
    else:
        return (degrees - 360) * math.pi / 180
```

---

## ❌ INCORRECT — Unit Conversions (knots to m/s)

**Doc officielle:**
```
Calypso outputs: m/s (données brutes)
Signal K expects: m/s
1 knot = 0.514444 m/s
```

**Script actuel:**
```python
# In NMEA decode:
speed = float(parts[3])
if unit == 'M':
    speed = speed * 1.94384  # ❌ BACKWARDS!
    # Script fait: m/s → knots (1.94384)
    # Should be: knots → m/s (0.514444)
elif unit == 'K':
    speed = speed / 1.85200  # ❌ Wrong conversion ratio
    # 1 km/h = 0.277778 m/s (not 0.539975)

# In send_to_signalk:
speed_ms = data['speed'] * 0.51444
# ❌ Assume data['speed'] is knots
# But Calypso sends m/s directly!
```

**Problems:**

1. **Calypso native format:** Sends m/s directly
   - No conversion needed!
   - Script wrongly assumes knots input

2. **NMEA conversions:** 
   - m/s → knots: multiply by 1.94384 ✅
   - But then multiply by 0.51444 to convert back to m/s? ❌ Double conversion!

**Correction:**
```python
def decode_calypso_payload(self, data):
    # Calypso sends m/s directly — no conversion!
    speed_raw = struct.unpack('<H', data[0:2])[0]
    speed_ms = speed_raw / 100.0  # Already m/s!
    
    return {
        'speed_ms': speed_ms,  # Ready for Signal K
        'direction_deg': ...,
        'battery_pct': ...
    }

async def send_to_signalk(self, data):
    # Signal K expects m/s
    # NO conversion needed if Calypso gives m/s
    payload = {
        "values": [
            {
                "path": "environment.wind.speedApparent",
                "value": data['speed_ms']  # Already m/s
            },
            {
                "path": "environment.wind.angleApparent",
                "value": math.radians(data['direction_deg']) if deg <= 180 else ...
            }
        ]
    }
```

---

## ⚠️ MISSING — Battery Monitoring

**Doc officielle:**
```
Calypso modes:
  SAFETY MODE : 0-2.5% batterie
    → Invisible BLE
    → Charger obligatoirement

  SLEEP MODE : 2.5-10% batterie
    → BLE advertising actif
    → Status = 0x00
    → Aucune donnée vent
    → Charger avant utilisation

  NORMAL MODE : 10-100% batterie
    → Status = 0x02
    → Toutes données disponibles
```

**Script actuel:**
```python
# Décodes battery from payload (byte 4)
battery_pct = data[4]

# But NEVER checks status UUID 0xA001!
# If battery < 10%:
#   - Status will be 0x00 (Sleep Mode)
#   - Wind data will NOT be available!
#   - Script will keep trying to read = waste + errors
```

**Missing implementation:**
```python
async def check_status(self):
    """Read Status UUID 0xA001 before attempting wind data"""
    try:
        status_data = await self.client.read_gatt_char("0000a001-0000-1000-8000-00805f9b34fb")
        mode = status_data[0]
        
        if mode == 0x00:
            return "Sleep Mode (battery < 10%)"
        elif mode == 0x02:
            return "Normal Mode (battery OK)"
        else:
            return f"Unknown Mode ({mode})"
    except:
        return None
```

---

## ❌ MISSING — Characteristic Subscriptions

**Doc officielle:**
```
To receive notifications on UUID 0x2A39:
  1. Write 0x0100 (CCCD) to enable notifications
  2. Listen for notifications on characteristic handle
```

**Script actuel:**
```python
await self.client.start_notify(self.char_uuid, self.notification_handler)
# ✅ Correct method (bleak handles CCCD automatically)
# But: using WRONG UUID! (0xffe1 instead of 0x2A39)
```

---

## ✅ CORRECT — Signal K Delta Format

**Script:**
```python
payload = {
    "updates": [{
        "source": {
            "label": "calypso-anemometer",
            "type": "NMEA0183"
        },
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "values": [...]
    }]
}

requests.post(SIGNALK_URL, json=payload, timeout=1)
```

✅ **CORRECT** — Delta format is valid

---

## 🔴 VERDICT FINAL

| Aspect | Status | Severity | Notes |
|--------|--------|----------|-------|
| BLE UUIDs | ❌ | CRITICAL | Using Huami 0xffe0/0xffe1, not Calypso 0x180D |
| Payload parsing | ❌ | CRITICAL | Wrong sync pattern (0x55 0xAA = WIT), byte offsets wrong |
| Byte order | ❌ | CRITICAL | Using big-endian, doc says little-endian |
| Angle conversion | ❌ | HIGH | Signed convention (-π to +π) not implemented |
| Speed conversion | ❌ | HIGH | Double/wrong conversions, confuses m/s and knots |
| Battery status | ❌ | MEDIUM | Doesn't check Sleep Mode (battery < 10%) |
| Delta format | ✅ | - | Signal K format correct |

---

## 🚨 RECOMMENDATION

**❌ CURRENT SCRIPT IS NON-FUNCTIONAL**

The script will:
1. ❌ Never find Calypso (wrong UUIDs)
2. ❌ Never parse payload correctly (wrong format)
3. ❌ Send wrong values to Signal K (unit conversion errors)
4. ❌ Ignore battery status (will crash in Sleep Mode)

**ACTION REQUIRED:** Complete rewrite using official Calypso documentation

---

## 📋 CORRECTED IMPLEMENTATION CHECKLIST

```python
✅ 1. Use correct UUIDs:
      - Service 0x180D, Characteristic 0x2A39
      - Or Service 0x181A, Characteristics 0x2A72/0x2A73

✅ 2. Correct payload parsing:
      - NO sync pattern
      - Bytes 0-1: speed (little-endian, /100 = m/s)
      - Bytes 2-3: direction (little-endian, degrés)
      - Byte 4: battery (0-100%)

✅ 3. Correct angle conversion:
      - Input: 0-359° (Calypso convention)
      - Output: -π to +π (Signal K convention)

✅ 4. NO speed conversion:
      - Calypso delivers m/s
      - Signal K expects m/s
      - Just pass through!

✅ 5. Battery status checking:
      - Read UUID 0xA001 before wind data
      - If status = 0x00 → Sleep Mode → wait/fail gracefully
      - If status = 0x02 → Normal Mode → proceed

✅ 6. Service discovery:
      - Don't hardcode UUIDs
      - Use BLE service discovery
      - More robust against firmware variations
```

---

**Conservé précieusement pour référence future! ⛵**
