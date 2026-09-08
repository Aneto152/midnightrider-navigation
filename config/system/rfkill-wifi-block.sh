#!/bin/bash
# Block WiFi on boot to prevent interference with Bluetooth LE (hci0)
# WiFi and BLE share the 2.4GHz radio on RPi4 — WiFi must remain OFF
rfkill block wifi
echo "[$(date -Iseconds)] WiFi blocked — BLE protected" >> /var/log/rfkill-wifi-block.log
