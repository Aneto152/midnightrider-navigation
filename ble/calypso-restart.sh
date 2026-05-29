#!/bin/bash
# Redémarrer le service Calypso à la demande

set -e

echo "=== Redémarrage Service Calypso ===" 
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "1️⃣ Arrêter le service..."
sudo systemctl stop calypso-wind
sleep 2
echo "✅ Service arrêté"

echo ""
echo "2️⃣ Attendre reconnexion BLE (3s)..."
sleep 3

echo ""
echo "3️⃣ Redémarrer le service..."
sudo systemctl start calypso-wind
sleep 3
echo "✅ Service redémarré"

echo ""
echo "4️⃣ Vérifier le statut..."
sudo systemctl status calypso-wind --no-pager | head -10

echo ""
echo "5️⃣ Vérifier les données..."
sleep 2
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/wind 2>/dev/null | python3 -c "
import sys, json
try:
  d = json.load(sys.stdin)
  aws = d.get('speedApparent', {}).get('value', 'N/A')
  awa = d.get('angleApparent', {}).get('value', 'N/A')
  src = d.get('speedApparent', {}).get('\$source', 'N/A')
  print(f'✅ Données reçues:')
  print(f'   AWS: {aws} m/s')
  print(f'   AWA: {awa} rad')
  print(f'   Source: {src}')
except Exception as e:
  print(f'❌ Erreur: {e}')
" || echo "⚠️ Données pas encore disponibles (attendre 10s)"

echo ""
echo "=== Redémarrage Terminé ===" 
