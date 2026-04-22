# Docker Signal K - Plan Clean & Stable

## Objectifs
1. ✅ Image Signal K **stable & testée** (pas v2.25)
2. ✅ Garder **tous les plugins custom** réutilisables
3. ✅ Configuration **persistante** (pas de perte au redémarrage)
4. ✅ Architecture **propre** (separation native/Docker)

---

## Étape 1: Documenter les Plugins Custom

### Plugins créés pendant le projet

```
✅ signalk-wit-imu-usb
   Location: ~/.signalk/node_modules/signalk-wit-imu-usb/
   Files: index.js, package.json
   Purpose: Lire WIT IMU sur /dev/ttyWIT
   Config: usbPort, updateRate

✅ @signalk/calibration (officiel)
   Purpose: Calibrer loch speed
   Config: Points de calibration

✅ signalk-sails-management-v2
   Purpose: Recommandations jib/trimaran
   Config: Vitesse vent seuil

✅ signalk-performance-polars
   Purpose: Polaires J30
   Config: Fichier JSON polaires

✅ signalk-astronomical
   Purpose: Sunrise/sunset/moon
   Config: Position bateau

Autres (review):
  - signalk-wave-height-simple
  - signalk-current-calculator
  - signalk-loch-calibration (custom - remplacer par @signalk/calibration)
```

---

## Étape 2: Préparer les Plugins pour Docker

### Structure réutilisable

```
/home/aneto/signalk-plugins/
├── wit-imu-usb/
│   ├── index.js
│   ├── package.json
│   └── README.md
├── sails-management-v2/
├── performance-polars/
├── astronomical/
└── calibration/
    └── config-template.json
```

### Sauvegarde avant Docker

```bash
# Exporter tous les plugins custom
mkdir -p ~/signalk-plugins-backup
cp -r ~/.signalk/node_modules/signalk-wit-imu-usb ~/signalk-plugins-backup/
cp -r ~/.signalk/plugins/signalk-*.js ~/signalk-plugins-backup/
cp ~/.signalk/plugin-config-data/*.json ~/signalk-plugins-backup/config/

# Sauvegarder settings.json original
cp ~/.signalk/settings.json ~/signalk-plugins-backup/settings.json.backup
```

---

## Étape 3: Choisir Image Docker Stable

### Recommandé: Signal K officiel

```bash
# Image: signalk/signalk-server
# Versions stables:
#   2.24.0 (recommandé - LTS-like)
#   2.23.5 (très stable)
#   1.54.0 (très ancien mais ultra-stable)

# Utiliser: v2.24.0 (bon compromis)
```

### Docker Compose Setup

```yaml
version: '3.8'

services:
  signalk:
    image: signalk/signalk-server:2.24.0-armv7
    container_name: signalk
    ports:
      - "3000:3000"      # Signal K API
      - "10110:10110"    # NMEA0183 TCP (Kplex)
    environment:
      - NODE_ENV=production
      - SIGNALK_PORT=3000
    volumes:
      - ~/signalk-docker/config:/home/node/signalk
      - /dev/ttyWIT:/dev/ttyWIT  # WIT IMU passthrough
    restart: unless-stopped
    networks:
      - signalk-net

  # Optional: Grafana
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped
    networks:
      - signalk-net

networks:
  signalk-net:

volumes:
  grafana_data:
```

---

## Étape 4: Migration des Plugins à Docker

### Pour chaque plugin custom

1. **Copier dans Docker volume**
   ```bash
   cp -r ~/signalk-plugins-backup/wit-imu-usb \
     ~/signalk-docker/config/node_modules/
   ```

2. **Configurer dans settings.json**
   ```json
   {
     "plugins": {
       "signalk-wit-imu-usb": {
         "enabled": true,
         "usbPort": "/dev/ttyWIT",
         "updateRate": 8
       }
     }
   }
   ```

3. **Redémarrer Docker**
   ```bash
   docker-compose restart signalk
   ```

---

## Étape 5: Test Complet

### Checklist post-Docker

```
☐ Signal K démarre sans erreurs
☐ API responsive: curl http://localhost:3000/signalk
☐ WIT IMU data: /signalk/v1/api/vessels/self/navigation/attitude
☐ Plugins visibles: /skServer/plugins
☐ Données persistent après restart
☐ Grafana accessible sur 3001
☐ /dev/ttyWIT accessible depuis container
```

---

## Avantages Docker vs Native

| Aspect | Docker | Native |
|--------|--------|--------|
| **Stabilité** | ✅ Image testée | ❌ Dépend du système |
| **Isolation** | ✅ Sandbox complet | ❌ Partage ressources |
| **Upgrade** | ✅ Facile (nouvelle image) | ❌ Peux casser dépendances |
| **Plugins** | ✅ Volume persiste | ❌ Risk corruption |
| **Performance** | ⚠️ Overhead 5-10% | ✅ Natif rapide |
| **Troubleshoot** | ✅ Logs isolés | ❌ Mélangé système |

---

## Commandes Clés

```bash
# Démarrer
docker-compose up -d

# Logs
docker-compose logs -f signalk

# Redémarrer
docker-compose restart signalk

# Arrêter
docker-compose down

# Backup configuration
docker cp signalk:/home/node/signalk ~/signalk-backup-$(date +%s)

# Accéder shell
docker exec -it signalk bash
```

---

## Timeline Recommandée

**Demain matin (30-45 min):**
1. Créer structure Docker (5 min)
2. Préparer plugins custom (10 min)
3. Lancer container (5 min)
4. Tester WIT IMU (10 min)
5. Tester plugins (10 min)

---

## Fallback Plan

Si Docker a aussi des problèmes:
- ✅ Signal K officiel fonctionne (image maintenue)
- ✅ Tous plugins sauvegardés (réutilisables)
- ✅ Configs documentées (peut recréer facilement)
- ✅ Native install toujours là (rollback possible)

