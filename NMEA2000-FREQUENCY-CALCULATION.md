# NMEA2000 Frequency - Calcul avec Config Actuelle

**Date:** 2026-04-23 07:52 EDT  
**Question:** À quelle fréquence j'aurais des updates sur mon réseau NMEA2000?  

---

## 🎯 RÉPONSE DIRECTE

Avec la configuration actuelle du plugin WIT:

```
Signal K → NMEA2000
Fréquence: 10 Hz (100ms batching)
```

**Mais cela dépend de COMMENT tu envoies les données à NMEA2000!**

---

## 📊 SCÉNARIOS

### Scénario 1: Plugin NMEA2000 Standard
```
Configuration actuelle:
  • batchInterval: 100ms = 10 Hz
  • Plugin envoie 10 updates/sec

NMEA2000 reçoit:
  ✅ 10 updates/sec = 10 Hz
  
Exemple: Attitude (Roll/Pitch/Yaw)
  • Tous les 100ms: nouveau message NMEA2000
  • Sur le bus: 10 messages/sec
```

### Scénario 2: Si tu augmentes à 20 Hz (50ms)
```
batchInterval: 50ms = 20 Hz

NMEA2000 reçoit:
  ✅ 20 updates/sec = 20 Hz
  
Charge bus NMEA2000:
  ⚠️ Double (200 messages/sec au lieu de 100)
```

### Scénario 3: Si tu baisse à 5 Hz (200ms)
```
batchInterval: 200ms = 5 Hz

NMEA2000 reçoit:
  ✅ 5 updates/sec = 5 Hz
  
Charge bus NMEA2000:
  ✅ Moindre charge
  ⚠️ Moins responsive
```

---

## 🔍 DÉTAILS TECHNIQUES

### Qu'est-ce qui se passe?

```
WIT IMU (100 Hz brut)
   ↓
Plugin WIT (batching 100ms)
   ↓
Signal K delta stream (10 Hz)
   ├→ REST API (0.15 Hz - throttled)
   ├→ WebSocket (10 Hz)
   ├→ InfluxDB (10 Hz)
   └→ Plugin NMEA2000 OUT ← TU ES ICI!
       ↓
   NMEA2000 Bus (10 Hz)
       ↓
   Afficheurs Vulcan, autres instruments
```

### Messages NMEA2000 Générés

Avec la config actuelle (10 Hz):

| Intervalle | Messages NMEA2000 | Fréquence |
|------------|-------------------|-----------|
| **100ms** | 1 message | 10 Hz |
| **10ms (100 Hz)** | 10 messages | 100 Hz |
| **1000ms (1 Hz)** | 0.1 message | 1 Hz |

**Actuellement: 10 Hz = 1 message NMEA2000 toutes les 100ms**

---

## 📋 QUELS MESSAGES NMEA2000?

Signal K peut envoyer vers NMEA2000:

### Attitude (Roll/Pitch/Yaw)
```
PGN 127000 (Attitude)
  • Roll (gîte)
  • Pitch (assiette)
  • Yaw (heading)
  
Fréquence: 10 Hz (100ms)
```

### Accélération
```
PGN Propriétaire (B&G, Garmin, etc.)
  • Ax, Ay, Az
  
Fréquence: 10 Hz (100ms)
```

### Angular Velocity (Vitesse de rotation)
```
PGN Propriétaire
  • Wx, Wy, Wz (rate of turn)
  
Fréquence: 10 Hz (100ms)
```

---

## ⚙️ CONFIGURATION REQUISE

Pour envoyer vers NMEA2000, tu as besoin:

### 1. Plugin NMEA2000 Output
```
Signal K doit avoir un plugin pour ENVOYER NMEA2000
Exemples:
  • signalk-to-nmea2000 (pour Actisense, CANUSB, etc.)
  • Plugin propriétaire du fabricant
```

### 2. Interface Physique
```
Exemples:
  • Actisense NGT-1 (USB → NMEA2000)
  • Digital Yacht YDNU-02 (que tu as sur J/30!)
  • CANUSB
  • Autre interface CAN
```

### 3. Configuration du Plugin
```
Doit spécifier:
  • Quel port/interface NMEA2000
  • Quels PGN envoyer
  • À quelle fréquence
```

---

## 🎯 TON CAS SPÉCIFIQUE (J/30)

### Hardware Disponible
```
✅ YDNU-02 (Digital Yacht - NMEA2000 gateway)
✅ WIT IMU USB
✅ Signal K hub
✅ Vulcan afficheur
```

### Configuration Proposée

```
WIT IMU (10 Hz via USB)
   ↓
Signal K (reçoit 10 Hz)
   ↓
Plugin NMEA2000 OUT (envoie PGN)
   ↓
YDNU-02 (convertit en NMEA2000)
   ↓
Réseau NMEA2000 du bateau
   ↓
Vulcan + autres instruments (reçoivent 10 Hz)
```

### Fréquence Résultante
```
NMEA2000 reçoit: 10 Hz (100ms batching)
  
Messages/sec:
  • PGN 127000 (Attitude): 10 msg/sec
  • PGN propriétaire (Accel): 10 msg/sec
  • PGN propriétaire (Gyro): 10 msg/sec
  
Total: ~30 messages/sec NMEA2000
```

---

## 🔧 POUR AUGMENTER LA FRÉQUENCE

Si 10 Hz n'est pas assez:

```
Actuellement: batchInterval = 100ms = 10 Hz

Pour 20 Hz:
  batchInterval = 50ms
  NMEA2000 recevrait 20 messages/sec

Pour 50 Hz:
  batchInterval = 20ms
  NMEA2000 recevrait 50 messages/sec
  ⚠️ Charge bus importante!
```

### Formule
```
Fréquence NMEA2000 = 1000 ÷ batchInterval (ms)

Actuellement: 1000 ÷ 100 = 10 Hz
```

---

## ⚠️ CONSIDÉRATIONS NMEA2000

### Bande Passante Disponible
```
NMEA2000 (CAN 250 kbps):
  • ~100 messages/sec maximum
  • Avec toi: ~30 messages/sec = 30% bande
  
✅ Largement suffisant pour 10 Hz
❌ 100 Hz serait trop (dépasserait bande)
```

### Latence
```
10 Hz = 100ms de latence
  • Acceptable pour navigation
  • Bon pour trim/réglages
  • Pas assez pour pilote automatique haute fréquence

20 Hz = 50ms de latence
  • Meilleur pour réactivité
  • Peut être nécessaire pour automation

50 Hz = 20ms de latence
  • Très réactif
  • Mais augmente charge CPU
```

---

## 🎯 RECOMMANDATION POUR TON J/30

**Configuration Recommandée:**

```
Plugin WIT: 10 Hz (batchInterval = 100ms)
  ✅ Bon compromis performance/réactivité
  ✅ Fréquence suffisante pour navigation
  ✅ Charge CPU normale

NMEA2000:
  ✅ Reçoit 10 Hz (10 messages/sec par PGN)
  ✅ Charge bus: ~30%
  ✅ Latence acceptable: 100ms

Vulcan afficheur:
  ✅ Updates fluides et réactives
  ✅ Pas de surcharge
  ✅ Performance optimale
```

**Si tu veux plus réactif:**

```
Augmente à 20 Hz (batchInterval = 50ms)
  → NMEA2000 recevra 20 messages/sec
  → Latence: 50ms
  → Charge bus: 60% (toujours acceptable)
```

---

## 📊 RÉSUMÉ RAPIDE

| Metrique | Valeur | Note |
|----------|--------|------|
| **Config actuelle** | 100ms | 10 Hz |
| **Fréquence NMEA2000** | 10 Hz | 10 msg/sec |
| **Latence** | 100ms | Acceptable |
| **Charge bus** | ~30% | Bon |
| **Pour Vulcan** | ✅ | Optimal |

---

## 🚀 PROCHAINES ÉTAPES

Si tu veux effectivement envoyer vers NMEA2000:

1. **Installer plugin NMEA2000 OUT**
   - Chercher: signalk-to-nmea2000 ou équivalent
   - Configurer le port (YDNU-02)

2. **Spécifier les PGN à envoyer**
   - PGN 127000 (Attitude)
   - PGN propriétaires (Accel/Gyro)

3. **Tester la fréquence**
   - Vérifier les messages sur le bus
   - Confirmer réception Vulcan

4. **Optimiser si nécessaire**
   - Augmenter batchInterval si trop rapide
   - Diminuer si trop lent

---

**Status:** ✅ Calculé et expliqué  
**Fréquence NMEA2000:** 10 Hz (actuellement)  
**Fréquence possible:** 5-100 Hz (configurable)  
**Recommandation:** Garder 10 Hz (optimal pour J/30)
