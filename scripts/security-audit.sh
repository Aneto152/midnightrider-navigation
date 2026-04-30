#!/bin/bash
# Audit sécurité hebdomadaire — MidnightRider
LOG="/home/aneto/docker/signalk/security-audit.log"
DATE=$(date '+%Y-%m-%d %H:%M')

echo "=== Audit $DATE ===" >> "$LOG"

# Firewall
UFW=$(sudo ufw status | head -1)
echo "Firewall: $UFW" >> "$LOG"

# Ports ouverts
echo "Ports:" >> "$LOG"
sudo ss -tlnp | grep -v "127.0.0.1\|::1\|[::1]" >> "$LOG"

# Containers Docker
echo "Docker:" >> "$LOG"
sudo docker ps --format "{{.Names}} {{.Status}}" >> "$LOG"

# Mises à jour disponibles
UPDATES=$(apt list --upgradable 2>/dev/null | grep -v "Listing" | wc -l)
echo "Updates disponibles: $UPDATES" >> "$LOG"

echo "===" >> "$LOG"
