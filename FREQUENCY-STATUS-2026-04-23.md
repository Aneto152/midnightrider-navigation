# MidnightRider WIT Frequency Status - 2026-04-23

**Date:** 2026-04-23 07:47 EDT  
**Status:** ✅ OPERATIONNEL - 10 Hz ACTIF  

---

## 🎯 FRÉQUENCE ACTUELLE

| Métrique | Valeur | Statut |
|----------|--------|--------|
| **Configuration** | batchInterval = 100ms | ✅ |
| **Fréquence théorique** | 10 Hz | ✅ |
| **Fréquence plugin** | 10 updates/sec | ✅ |
| **Fréquence WebSocket** | 10 Hz | ✅ |
| **Fréquence REST API** | ~1 Hz | ⚠️ (throttled) |

---

## 📊 DONNÉES ACTUELLES

### Attitude (Roll/Pitch/Yaw)
```
Roll:  0.0023 rad = 0.1°     (niveau)
Pitch: -0.0073 rad = -0.4°   (quasi-plat)
Yaw:   0.2028 rad = 11.6°    (WSW)
```

### Calibrage
- Offsets: Tous à 0 (pas de correction)
- Gains: Tous à 1.0 (pas d'amplification)
- → Données brutes du WIT, non calibrées

---

## 🔧 CONFIGURATION ACTUELLE

```json
{
  "configuration": {
    "usbPort": "/dev/ttyWIT",
    "baudRate": 115200,
    "batchInterval": 100,           ← ✅ 10 Hz
    "attitudeCal": {
      "rollOffset": 0,
      "pitchOffset": 0,
      "yawOffset": 0,
      "rollGain": 1,
      "pitchGain": 1,
      "yawGain": 1
    },
    "accelCal": {
      "xOffset": 0,
      "yOffset": 0,
      "zOffset": 0,
      "xGain": 1,
      "yGain": 1,
      "zGain": 1
    },
    "gyroCal": {
      "wxOffset": 0,
      "wyOffset": 0,
      "wzOffset": 0,
      "wxGain": 1,
      "wyGain": 1,
      "wzGain": 1
    },
    "debug": false
  },
  "enabled": true
}
```

---

## 🔄 FLUX DE DONNÉES

```
WIT IMU (100 Hz brut)
   ↓
Plugin (batching 100ms)
   ↓ (toutes les 100ms)
10 updates/sec = 10 Hz ✅
   ↓
Signal K delta stream
   ├→ REST API: 0.2-1 Hz (throttled)
   ├→ WebSocket: 10 Hz (real-time) ✅
   └→ InfluxDB: 10 Hz (real-time) ✅
```

---

## 📈 FORMULE

```
Fréquence = 1000 ÷ batchInterval(ms)
10 Hz = 1000 ÷ 100
```

Pour changer la fréquence:
```
20 Hz: batchInterval = 50ms
10 Hz: batchInterval = 100ms (actuel) ✅
5 Hz:  batchInterval = 200ms
1 Hz:  batchInterval = 1000ms (ancien problème)
```

---

## ✅ POINTS DE VÉRIFICATION

- [x] Signal K en cours (PID 34899)
- [x] Configuration chargée (batchInterval = 100)
- [x] Données reçues (Roll/Pitch/Yaw présents)
- [x] Fréquence 10 Hz (théorique = réelle)
- [x] WebSocket streaming actif
- [x] Plugin enabled = true

---

## 🚀 AVANTAGES ACTUELS

| Aspect | Avant | Après |
|--------|-------|-------|
| Config | 1000ms (1 Hz) ❌ | 100ms (10 Hz) ✅ |
| Fréquence | 1 Hz | 10 Hz |
| Latence | 1 second | 100ms |
| Responsive | Lent | Temps réel ✅ |
| WebSocket | 1 Hz | 10 Hz ✅ |

---

## 🎯 CLIENTS AFFECTÉS

### REST API (Lent - 0.2-1 Hz)
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
# Mises à jour ~toutes les 5 secondes (throttled)
```

### WebSocket (Rapide - 10 Hz) ✅
```javascript
ws://localhost:3000/signalk/v1/stream?subscribe=self
// Reçoit les updates à 10 Hz en temps réel
```

### InfluxDB (Rapide - 10 Hz) ✅
```
Signal K → Delta Stream Listener → InfluxDB
// Stocke à 10 Hz (reçoit tous les paquets)
```

### Grafana
- Avec REST API: ~0.2 Hz (lent)
- Avec InfluxDB: 10 Hz (bon)
- Avec WebSocket: 10 Hz (excellent)

---

## 🔧 SI TU VEUX CHANGER LA FRÉQUENCE

### Augmenter à 20 Hz
```bash
# Méthode 1: Admin UI
# Admin → Plugins → signalk-wit-imu-usb → Edit
# batchInterval: 100 → 50
# Save

# Méthode 2: Ligne de commande
nano /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json
# Change: "batchInterval": 100 → "batchInterval": 50
# Ctrl+X, Y, Enter
sudo systemctl restart signalk
```

### Diminuer à 5 Hz
```
batchInterval: 100 → 200
# Résultat: 5 Hz (économe CPU)
```

---

## 📋 RÉSUMÉ RAPIDE

- ✅ **Configuration:** 100ms (10 Hz)
- ✅ **Plugin:** En cours et fonctionnel
- ✅ **Données:** Roll/Pitch/Yaw actives
- ✅ **WebSocket:** 10 Hz streaming
- ⚠️ **REST API:** Throttled (0.2-1 Hz, c'est normal)
- ✅ **InfluxDB:** 10 Hz streaming

**Système OPÉRATIONNEL à 10 Hz!** 🎉

---

**Créé:** 2026-04-23 07:47 EDT  
**Pour:** Denis Lafarge  
**Statut:** ✅ LIVE ET FONCTIONNEL
