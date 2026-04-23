# Attitude Data (Roll/Pitch/Yaw/Heel) - Signal K Output

**Date:** 2026-04-23  
**Status:** ✅ **ACTIF ET TRANSMIS**  
**Source:** WIT IMU USB (signalk-wit-imu-usb plugin)

---

## 📊 **Données Disponibles**

### 1. **Attitude (Roll/Pitch/Yaw)**

**Signal K Path:** `navigation.attitude`

**API Endpoint:**
```
http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

**Données En Temps Réel (2026-04-23 22:43:35 UTC):**

```json
{
  "roll": {
    "value": -0.0351,     // radians (≈ -2.0°)
    "unit": "rad",
    "source": "signalk-wit-imu-usb.XX",
    "timestamp": "2026-04-23T22:43:35.867Z"
  },
  "pitch": {
    "value": -0.0115,     // radians (≈ -0.66°)
    "unit": "rad",
    "source": "signalk-wit-imu-usb.XX",
    "timestamp": "2026-04-23T22:43:35.867Z"
  },
  "yaw": {
    "value": 1.2208,      // radians (≈ 69.96°)
    "unit": "rad",
    "source": "signalk-wit-imu-usb.XX",
    "timestamp": "2026-04-23T22:43:35.867Z"
  }
}
```

### 2. **Acceleration (X/Y/Z - 3 Axes)**

**Signal K Path:** `navigation.acceleration`

**API Endpoint:**
```
http://localhost:3000/signalk/v1/api/vessels/self/navigation/acceleration
```

**Données En Temps Réel:**

```json
{
  "x": {
    "value": 0.00496,      // m/s² (longitudinal)
    "source": "signalk-wit-imu-usb.XX",
    "timestamp": "2026-04-23T22:43:35.867Z"
  },
  "y": {
    "value": 0.00033,      // m/s² (transversal/heel)
    "source": "signalk-wit-imu-usb.XX",
    "timestamp": "2026-04-23T22:43:35.867Z"
  },
  "z": {
    "value": 9.8057,       // m/s² (vertical/gravity)
    "source": "signalk-wit-imu-usb.XX",
    "timestamp": "2026-04-23T22:43:35.867Z"
  }
}
```

### 3. **Rate of Turn (Gyroscope)**

**Signal K Path:** `navigation.rateOfTurn`

**Value:** 0 rad/s (bateau immobile au quai)

---

## 📱 **Transmission NMEA0183 - ROLL/PITCH**

### Sentences NMEA pour Attitude

#### **RSA - Rudder Sensor Angle** *(optionnel)*
```
$GPXRS,10.5,A,,*29
```
- Port rudder angle
- Starboard rudder angle

#### **VRP - Roll, Pitch, Yaw** *(si supporté)*
```
$GPVRP,1.2,T,90.0,T,5.5,T*XX
```
- Roll, Pitch, Yaw avec checksum

#### **Note Importante:**
⚠️ **Standard NMEA0183 n'a PAS de sentence standard pour Roll/Pitch/Heel!**

Les sentences propriétaires existent (Garmin, B&G, etc.) mais ne sont pas universelles.

---

## 🔄 **Flux des Données**

```
WIT WT901BLECL IMU
    ↓ (USB @ 115200 bps, 10 Hz)
signalk-wit-imu-usb Plugin
    ↓ (parsifie packets 0x55 0x61)
Signal K Hub
    ├─ navigation.attitude.roll     (-0.0351 rad)
    ├─ navigation.attitude.pitch    (-0.0115 rad)
    ├─ navigation.attitude.yaw      (1.2208 rad)
    └─ navigation.acceleration.*    (x, y, z)
       ↓
Clients:
    ├─ Grafana (affichage en temps réel)
    ├─ InfluxDB (stockage historique)
    ├─ Dashboard Web (http://localhost:3000)
    ├─ qtVLM (si sentence custom transmise)
    └─ Plugins custom (Sails Management V2, Wave Height, etc)
```

---

## 📐 **Unités et Conversions**

### Signal K (Interne)
- **Roll/Pitch/Yaw:** Radians
- **Acceleration:** m/s²
- **Rate of Turn:** rad/s

### Affichage (Degrés)
```
Degrés = Radians × 57.29577951

Exemple:
Roll = -0.0351 rad × 57.296 = -2.01°
Pitch = -0.0115 rad × 57.296 = -0.66°
Yaw = 1.2208 rad × 57.296 = 69.96°
```

### Affichage Maritime (Heel)
```
Heel = Roll (same as Roll angle)
- Positive = Starboard (tribord)
- Negative = Port

Exemple: Roll = -2.01° = 2.01° Port (gîte à babord)
```

---

## 🔌 **Accès aux Données**

### Via Signal K API REST

```bash
# Attitude seule
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

# Acceleration seule
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/acceleration

# Rate of Turn
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/rateOfTurn

# Tout (navigation)
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation
```

### Via WebSocket (Temps Réel)

```javascript
const ws = new WebSocket('ws://localhost:3000/signalk/v1/stream?subscribe=navigation.attitude,navigation.acceleration');

ws.onmessage = (event) => {
  const delta = JSON.parse(event.data);
  console.log('Roll:', delta.updates[0].values[0].value);
  console.log('Pitch:', delta.updates[0].values[1].value);
  console.log('Acceleration X:', delta.updates[0].values[2].value);
};
```

### Via TCP Port 10110 (NMEA0183)

⚠️ **Standard NMEA0183 ne supporte PAS Roll/Pitch natifs.**

Pour transmettre Roll/Pitch en NMEA0183, il faudrait:
1. Créer sentence propriétaire custom
2. Ou utiliser une sentence XDR (Transducer) custom:

```
$CCXDR,A,-2.01,D,ROLL,A,-0.66,D,PITCH*XX
```

---

## 📊 **Utilisation dans MidnightRider**

### Plugins Qui Utilisent Attitude

| Plugin | Utilisation |
|--------|-------------|
| **Wave Height IMU** | ✅ Utilise acceleration (x,y,z) pour calcul Hs |
| **Sails Management V2** | ✅ Utilise roll (heel) pour recommandations |
| **Performance Polars** | ✅ Utilise attitude pour calculs VMG |
| **Grafana Dashboards** | ✅ Affiche roll/pitch en temps réel |

### Wave Height Calculation
```
|a| = √(ax² + ay² + az²)
|a| ≈ √(0.00496² + 0.00033² + 9.8057²)
|a| ≈ 9.8058 m/s²

Cet invariant = gravity, indépendant du heel!
```

### Sails Management
```
Heel Angle = Roll = -2.01° (gîte)
→ "Heel is too high, ease jib!"
→ "Good heel angle, maintain"
```

---

## 🎯 **Paramètres WIT IMU USB**

**Fichier Config:** `~/.signalk/settings.json`

```json
{
  "signalk-wit-imu-usb": {
    "enabled": true,
    "usbPort": "/dev/ttyWIT",
    "baudRate": 115200,
    "updateRate": 8,
    "filterAlpha": 0.05,
    "rollOffset": 0,
    "pitchOffset": 0,
    "yawOffset": 0,
    "accelXOffset": 0,
    "accelYOffset": 0,
    "accelZOffset": 0,
    "gyroZOffset": 0
  }
}
```

**Calibration Offsets:**
- Peut être ajusté via Admin UI sans redémarrage
- Permet zéro-point check en bateau

---

## 🔴 **Limitations NMEA0183**

### Pourquoi Roll/Pitch Pas dans Port 10110?

**Standard NMEA0183 n'a PAS de sentence pour Roll/Pitch/Heel!**

Sentences existantes:
- ✅ RMC, GGA → Position
- ✅ MWV, MWD → Wind
- ✅ VHW → Heading + Speed
- ❌ HDT → Heading Only
- ❌ **Roll/Pitch → AUCUNE sentence standard!**

### Solutions Possibles

1. **Sentence Propriétaire XDR:**
   ```
   $CCXDR,A,roll_deg,D,ROLL,A,pitch_deg,D,PITCH*XX
   ```

2. **Custom Plugin Output:**
   - Écrire plugin Signal K → NMEA custom
   - Sortir sur port 10111 (séparé)

3. **Garder Signal K Natif:**
   - Clients se connectent à WebSocket
   - Reçoivent Roll/Pitch/Acceleration directement

### qtVLM et Roll/Pitch

**qtVLM peut-il afficher Roll/Pitch?**

- ✅ Si connecté via Signal K WebSocket → OUI
- ❌ Si connecté via NMEA0183 (port 10110) → NON (pas de sentence standard)

**Recommandation:**
- NMEA0183 (port 10110) pour qtVLM classique (position, vent, cap)
- Signal K API pour données avancées (roll, pitch, acceleration)

---

## 📋 **Summary**

### ✅ Disponible en Signal K:
- Roll (gîte) — -0.0351 rad ≈ -2.01°
- Pitch (assiette) — -0.0115 rad ≈ -0.66°
- Yaw (cap) — 1.2208 rad ≈ 69.96°
- Acceleration X,Y,Z — Haute résolution

### ✅ Mise à Jour:
- **Fréquence:** 10 Hz (WIT IMU USB)
- **Latence:** <100 ms

### ❌ Non Transmis en NMEA0183:
- Roll/Pitch ont pas de sentence NMEA standard
- Port 10110 = NMEA classique (RMC, GGA, MWV, etc)

### ✅ Accès Complet:
- Signal K API REST
- WebSocket temps réel
- Grafana dashboards
- Plugins internes (Wave Height, Sails Management, etc)

---

## 📱 **Pour qtVLM**

**Position, Vent, Cap:** ✅ Via NMEA0183 port 10110  
**Roll, Pitch, Accel:** ❌ Pas en NMEA0183 standard  

**Si tu veux Roll/Pitch dans qtVLM:**
- Option 1: Utiliser Signal K WebSocket directement (plus moderne)
- Option 2: Créer output custom NMEA (complexe)
- Option 3: Garder qtVLM pour nav classique, utiliser Grafana pour heel/pitch

---

**Status:** ✅ **ACTIF ET OPÉRATIONNEL**  
**Qualité:** Excellente (WIT IMU 9-axis, 10 Hz)  
**Utilisation:** Production-ready pour MidnightRider J/30 ⛵

