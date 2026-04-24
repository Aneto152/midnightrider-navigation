# UM982 GPS — Activer Proprietary Sentences (#HEADINGA)

## 📖 Source Documentation
**From:** Control commands for the GNSS receiver UM982 by Satoshi Takahashi  
**URL:** https://s-taka.org/en/control-command-for-gnss-receiver-um982/

---

## 🎯 PROBLEM
UM982 envoie actuellement des sentences **STANDARD NMEA** seulement:
- ✅ `$GNGGA` — Position + altitude
- ✅ `$GNHDT` — Heading true  
- ✅ `$GNRMC` — Position + speed
- ✅ `$GNROT` — Rate of turn
- ✅ `$GNVTG` — Speed + track

❌ **PAS:** `#HEADINGA` (proprietary Unicore avec roll/pitch/yaw)

---

## 💾 SOLUTION: Enable Proprietary Sentences

### Step 1: Connect via TCP (Recommended)
Instead of direct serial, use RTKLIB str2str to access via TCP:

```bash
# On MidnightRider (or wherever UM982 is connected):
sudo apt-get install -y rtklib

# Start RTKLIB bridge:
str2str -in serial://ttyUM982:115200 -out tcpsvr://:2001 -b 1

# From another terminal (or remote):
nc localhost 2001
```

### Step 2: Send Control Commands
Commands are case-insensitive. Press ENTER after each command.

**First, disable all output:**
```
unlog
```
Response: `$command,unlog,response: OK*xx`

**Enable HEADINGA (proprietary sentences with attitude):**
```
headinga 10
```
This outputs #HEADINGA sentences every 10 seconds.

**Or with finer control:**
```
headinga onchanged
```
Outputs HEADINGA only when value changes (recommended for real-time).

**To check if it's working:**
```
screen /dev/ttyUM982 115200
```
Look for: `#HEADINGA,COM1,...` sentences

**To save configuration permanently:**
```
saveconfig
```

---

## 📊 Expected Output Format

When #HEADINGA is enabled, you'll see:
```
#HEADINGA,COM1,13495,95.0,FINE,2415,73711.000,17020772,13,18;SOL_COMPUTED,L1_FLOAT,12.2446,260.1887,-35.0258,0.0000,292.7253,155.0128,"999",29,7,7,0,3,00,0,51*12fb1b6a
```

**Key fields:**
- Field 12: Roll (degrees)
- Field 13: Pitch (degrees)
- Field 14: Yaw/Heading (degrees)

---

## 🔧 Direct Serial Configuration (Without TCP)

If you prefer direct serial without TCP bridge:

```bash
# Connect directly
cat /dev/ttyUM982

# In separate terminal, use minicom or picocom:
picocom -b 115200 /dev/ttyUM982
```

Type commands and press ENTER:
```
unlog
headinga 10
```

---

## 🧪 Test in Signal K Plugin

Once #HEADINGA is flowing, the plugin will:
1. Receive `#HEADINGA` sentences
2. Parse roll/pitch/yaw fields
3. Inject into Signal K paths:
   - `navigation.attitude.roll` (radians)
   - `navigation.attitude.pitch` (radians)
   - `navigation.attitude.yaw` (radians)
   - `navigation.um982.rollDegrees` (raw degrees)
   - `navigation.um982.pitchDegrees` (raw degrees)
   - `navigation.um982.yawDegrees` (raw degrees)

Check Signal K Admin UI → Signal K API to verify data flowing.

---

## 📋 Other Useful Commands

| Command | Effect |
|---------|--------|
| `unlog` | Disable all output |
| `gngga 10` | Position every 10s |
| `gnhdt 1` | Heading every 1s |
| `gnrot 1` | Rate of turn every 1s |
| `headinga 10` | **#HEADINGA every 10s** ⭐ |
| `headinga onchanged` | **#HEADINGA on change** ⭐ |
| `config` | Show all settings |
| `saveconfig` | Save permanently |
| `reset` | Reset all changes |
| `freset` | Factory reset |

---

## ⚙️ Configuration Example

Recommended setup for sailing:

```bash
# Connect
nc localhost 2001

# Disable everything
unlog

# Enable essentials
gngga 1        # Position every 1 second
gnhdt 1        # Heading every 1 second
headinga 1     # Attitude every 1 second
gnrot 1        # Rate of turn every 1 second

# Save
saveconfig
```

---

## 🚀 Next Steps

1. **Try activating via TCP first** (easier to test)
2. **Monitor /dev/ttyUM982 for #HEADINGA sentences**
3. **If data arrives → Signal K plugin will parse automatically**
4. **If no data → Check GPS configuration / power / cable**

---

## 📚 Full Documentation Source
**File:** `/home/aneto/.openclaw/workspace/UM982-PROPRIETARY-SENTENCES-GUIDE.md`  
**Original:** https://s-taka.org/en/control-command-for-gnss-receiver-um982/
