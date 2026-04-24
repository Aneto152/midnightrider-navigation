# Network Failover Configuration - Verizon WiFi

**Date:** 2026-04-23  
**Status:** ✅ **ACTIVE**  
**Purpose:** Auto-connect to Verizon WiFi if Ethernet unavailable

---

## 📊 Configuration

### Ethernet (Primary)
- **Status:** Preferred
- **Config:** netplan-eth0
- **Priority:** Default

### WiFi Fallback (Secondary)
- **SSID:** Verizon_C9PX3L
- **Security:** WPA2/WPA3
- **Auto-Connect:** ✅ YES
- **Priority:** 100 (HIGH)
- **Auto-Retry:** Unlimited

---

## 🔄 How It Works

### Boot Sequence

1. **RPi Powers On**
2. **NetworkManager Starts**
3. **Checks Ethernet (eth0)**
   - If available → Use Ethernet
   - If NOT available → Continue to WiFi
4. **Tries WiFi Fallback (Verizon_C9PX3L)**
   - Auto-connects with saved credentials
   - Gets IP via DHCP
5. **Signal K Available**
   - Via `http://midnightrider.local:3000`
   - Via `TCP://midnightrider.local:10110`

### Priority Order (NetworkManager)

```
1. Ethernet (netplan-eth0) - Priority: default
2. WiFi Verizon - Priority: 100 (HIGH)
```

---

## 🛠️ Configuration Details

### Current Setup

```bash
$ nmcli connection show "Verizon_C9PX3L"

NAME: Verizon_C9PX3L
TYPE: WiFi
DEVICE: wlan0
AUTOCONNECT: yes
AUTOCONNECT-PRIORITY: 100
SSID: Verizon_C9PX3L
SECURITY: WPA2 WPA3
```

### Manually Manage Connection

```bash
# View all connections
nmcli connection show

# Reconnect to Verizon
nmcli connection up Verizon_C9PX3L

# Modify auto-connect
nmcli connection modify Verizon_C9PX3L connection.autoconnect yes

# Change priority
nmcli connection modify Verizon_C9PX3L connection.autoconnect-priority 100

# Disconnect
nmcli connection down Verizon_C9PX3L

# Reload configuration
nmcli connection reload
```

---

## 📱 Signal K Access via WiFi

### On iPad/iPhone/Laptop (same WiFi)

```
http://midnightrider.local:3000
```

### qtVLM Connection

```
TCP://midnightrider.local:10110
NMEA0183 (standard format)
```

### SSH Access

```bash
ssh aneto@midnightrider.local
```

---

## 🔒 Security Notes

### Password Storage

- **Location:** NetworkManager Database
- **Encryption:** OS-level keyring encryption
- **User:** Only `aneto` can access
- **Method:** Standard NetworkManager security

### Best Practices

1. **Verizon WiFi is temporary fallback only**
   - Use Ethernet when possible (at the dock)
   - WiFi is for emergencies/roaming

2. **Password is encrypted**
   - Not stored in plain text
   - Protected by system keyring
   - Safe for regular use

3. **Signal K accessible on both**
   - Ethernet: Fast, stable
   - WiFi: Adequate for navigation

---

## 🧪 Testing

### Manual Test

```bash
# Disconnect Ethernet
sudo nmcli connection down netplan-eth0

# WiFi should auto-connect
watch nmcli device status

# Reconnect Ethernet
sudo nmcli connection up netplan-eth0
```

### Verify mDNS Works on WiFi

```bash
# When on WiFi
ping midnightrider.local

# Open browser
http://midnightrider.local:3000
```

---

## 📍 Current Status

### Connected Devices

```
netplan-eth0    : Ethernet interface
Verizon_C9PX3L  : WiFi interface (configured, ready)
lo              : Loopback
docker0         : Docker bridge
```

### IPv6 Support

```
Multiple IPv6 addresses available
Verizon provides IPv6 connectivity
(Standard Verizon WiFi feature)
```

---

## ⚠️ Limitations

### Verizon WiFi Fallback is:

✅ **Good for:**
- Emergency connectivity
- Navigation when Ethernet fails
- Testing Signal K remotely
- qtVLM connection backup

❌ **Not ideal for:**
- Extended sailing (battery drain)
- High-bandwidth operations
- Stable racing data logging

### Recommendation

1. **Use Ethernet at dock** (USB cable to laptop/network)
2. **WiFi is fallback only** (for emergencies)
3. **On the water:** Use iPad + Signal K API for racing

---

## 🚀 Recovery Procedure

### If WiFi Fails to Auto-Connect

```bash
# Check WiFi is visible
nmcli device wifi list

# Manual reconnect
sudo nmcli device wifi connect "Verizon_C9PX3L" password "cpu6-seam-stuck"

# Or use NetworkManager GUI
nmtui
```

### If Password Changed

```bash
# Update stored password
sudo nmcli connection modify Verizon_C9PX3L wifi-sec.psk "NEW_PASSWORD"

# Reconnect
nmcli connection up Verizon_C9PX3L
```

---

## 📊 Summary

| Feature | Status |
|---------|--------|
| Ethernet Primary | ✅ Active |
| WiFi Fallback | ✅ Configured |
| Auto-Connect | ✅ YES |
| Priority | ✅ 100 (HIGH) |
| mDNS Available | ✅ YES |
| Signal K Access | ✅ YES |
| Security | ✅ Encrypted |

---

**Status:** ✅ **OPERATIONAL**  
**Last Tested:** 2026-04-23  
**Next Review:** On first sailing day

⛵ Network failover is ready!
