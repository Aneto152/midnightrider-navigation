# Network Issue — iPad Access (2026-05-11)

## Problem
iPad cannot access Portal (:5000) or Grafana (:3001) via mDNS hostname `midnightrider.local`.

## Root Causes
1. **mDNS (avahi-daemon)** resolves to link-local IPv6 (169.254.119.236) instead of WiFi IP (192.168.1.167)
2. **Grafana alerts** reference non-existent bucket 'weather_lis' (causing errors in logs)
3. **Dashboard provisioning** has duplicate UID 07-race

## Immediate Workaround
Instead of `midnightrider.local`, use direct IP:
- Portal: **http://192.168.1.167:5000**
- Grafana: **http://192.168.1.167:3001**
- Signal K: **http://192.168.1.167:3000**

## Service Status
✅ Portal :5000 → HTTP 200 (accessible locally)
✅ Grafana :3001 → HTTP 200 (accessible locally)  
✅ Signal K :3000 → Running (systemd)
✅ InfluxDB :8086 → HTTP 200 (Docker)

## Fixes Required
1. Edit `/etc/avahi/avahi-daemon.conf` → bind to wlan0
2. Remove duplicate `07-race` dashboard UID from provisioning
3. Update alert rules → remove/fix `weather_lis` bucket references

## Field Test Status (May 19)
**NOT CRITICAL** — Direct IP access works fine for iPad.
Fix before race day if needed, but workaround is stable.
