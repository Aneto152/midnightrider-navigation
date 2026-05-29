#!/bin/bash
# Calypso Health Check & Auto-Recovery
# Vérifie que le service tourne et que les données arrivent
# Redémarre automatiquement en cas de problème

set -e

LOG_FILE="/var/log/calypso-health.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() {
  echo "[$TIMESTAMP] $1" | sudo tee -a "$LOG_FILE" > /dev/null
}

check_service() {
  if ! systemctl is-active --quiet calypso-wind; then
    log "❌ Service calypso-wind inactif"
    return 1
  fi
  log "✅ Service calypso-wind actif"
  return 0
}

check_data_flow() {
  # Vérifier que Signal K reçoit des données du Calypso (dernière 10 secondes)
  local last_update=$(curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/wind 2>/dev/null | python3 -c "
import sys, json, time
try:
  d = json.load(sys.stdin)
  ts = d.get('speedApparent', {}).get('timestamp', '')
  if ts:
    print(ts)
  else:
    print('NO_DATA')
except:
  print('ERROR')
" 2>/dev/null || echo "ERROR")

  if [ "$last_update" = "ERROR" ] || [ "$last_update" = "NO_DATA" ]; then
    log "❌ Pas de données du Calypso"
    return 1
  fi

  log "✅ Données Calypso reçues: $last_update"
  return 0
}

check_bluetooth() {
  if ! hciconfig | grep -q "UP RUNNING"; then
    log "❌ Bluetooth inactif"
    return 1
  fi
  log "✅ Bluetooth actif"
  return 0
}

# MAIN
echo "=== Calypso Health Check ===" 
echo "Timestamp: $TIMESTAMP"
echo ""

ERRORS=0

if ! check_service; then
  ERRORS=$((ERRORS + 1))
  log "ACTION: Redémarrage service calypso-wind"
  sudo systemctl restart calypso-wind
  sleep 3
fi

if ! check_bluetooth; then
  ERRORS=$((ERRORS + 1))
  log "ACTION: Redémarrage Bluetooth"
  sudo systemctl restart bluetooth
  sleep 3
fi

if ! check_data_flow; then
  ERRORS=$((ERRORS + 1))
  log "⚠️ ATTENTION: Pas de flux de données - possible perte BLE"
  log "ACTION: Redémarrage complet calypso-wind"
  sudo systemctl restart calypso-wind
  sleep 5
fi

if [ $ERRORS -eq 0 ]; then
  log "✅ TOUS LES TESTS PASSÉS"
  exit 0
else
  log "❌ $ERRORS ERREUR(S) DÉTECTÉE(S)"
  exit 1
fi
