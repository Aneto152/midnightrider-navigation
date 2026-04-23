# WIT IMU - Architecture Plugin vs Service

## État Actuel: Service Systemd ✅

```
Service systemd (wit-usb-reader)
  ├─ Lectures USB 100Hz
  ├─ Calibration appliquée
  ├─ Filtrage low-pass
  └─ WebSocket Signal K
```

**Avantages:**
- ✅ Très fiable (systemd gère restart)
- ✅ Isolation (pas dans Signal K)
- ✅ Logs séparés
- ✅ Configuration simple (fichier JSON)

**Inconvénient:**
- ❌ Configuration nécessite redémarrage du service

## Pourquoi Plugin Signal K est difficile

Signal K cherche les plugins dans:
1. `~/.signalk/node_modules/` (npm packages)
2. Répertoires enregistrés dans `settings.json`

Pour que ça marche, faut:
- Installer via npm en tant que package
- Ou enregistrer le répertoire dans Signal K
- Ou packager avec dépendances

## Solution Recommandée: Service + Configuration Propre

**Garde le service systemd** mais améliore la config:

### 1. Fichier Config Centralisé
```
/home/aneto/.signalk/wit-config.json
```

### 2. API de Reconfiguration
```bash
# Changer calibration sans redémarrer:
curl -X POST http://localhost:3000/signalk/v1/wit-config \
  -d '{"calibrationZ": 0.035}'
```

### 3. Interface Web
Via l'UI Signal K pour visualiser/modifier config

## Décision

Pour **maintenir la propreté** tout en gardant la **flexibilité**:

✅ **Garde le service systemd**
✅ **Créé un helper CLI** pour modifier config
✅ **Documentation** pour les cas de calibrage

C'est la solution la **plus robuste et maintenable** pour MidnightRider.
