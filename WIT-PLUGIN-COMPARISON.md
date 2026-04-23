# Comparaison: Plugin WIT Custom vs GitHub Officiel

**Date:** 2026-04-23  
**Auteur:** Investigation

---

## 📊 Résumé Exécutif

| Aspect | Custom (v1.0.0) | GitHub Officiel (V0.3.0) |
|--------|-----------------|-------------------------|
| **Auteur** | Custom local | W-Geronius (WITMOTION) |
| **Sensor Compatibilité** | WT901BLECL | HWT901B (compatible) |
| **Multi-device** | ❌ Non | ✅ Oui (array) |
| **Calibration** | Basic | Avancée (3 niveaux) |
| **Fréquence** | Fixed 10Hz | Configurable (0.2-50Hz) |
| **Offset Heading** | ❌ Pas paramétrisé | ✅ Configurable (-180° à +180°) |
| **Checksum** | ❌ Non | ✅ Oui (validation) |
| **Acceleration Cal** | ❌ Non | ✅ Oui (command) |
| **Angle Reference** | ❌ Non | ✅ Oui (reset level) |

---

## 🔍 Détail Plugin Officiel (V0.3.0)

### Avantages Clés

#### 1️⃣ **Multi-Devices Support**
```javascript
"devices": {
  "type": "array",  // Plusieurs capteurs simultanés!
  "items": {
    "usbDevice": "/dev/ttyUSB0",
    "freq": "2Hz",
    "zOffset": 0.0
  }
}
```
**Impact:** Tu pourrais ajouter un 2e IMU sans modifier le code!

#### 2️⃣ **Fréquence Configurable**
```javascript
freqs = ["0.2Hz", "0.5Hz", "1Hz", "2Hz", "5Hz", "10Hz", "20Hz", "50Hz"]
```
**Avantage:** Adapter selon besoin (économiser CPU ou plus de précision)

#### 3️⃣ **Calibration Avancée**

**A) Accelerometer Calibration**
```
Commande: accCal = true
Effet: Auto-reset après exécution
Permet: Calibrer l'accélération sans Windows software
```

**B) Angle Reference Reset**
```
Commande: angleRef = true
Effet: Set roll & pitch to level (0°)
Permet: Niveler le bateau sans redémarrage
```

**C) Heading Offset Configurable**
```
Paramètre: zOffset (-180° à +180°)
Effet: Compenser orientation antennes
Exemple: zOffset = 45° si antennes décalées de 45°
```

#### 4️⃣ **Checksum Validation**
```javascript
// Vérifie l'intégrité des données
SUM = 0x55 + 0x53 + RollH + RollL + ...
if (checksum !== computed) reject();
```
**Avantage:** Évite données corrompues

#### 5️⃣ **Protocol Standard**
```
Sentence: 0x55 0x53 PitchL PitchH RollL RollH YawL YawH VL VH SUM
Parser: DelimiterParser (cleaner code)
```

### Calculs Précis

```javascript
// WITMOTION standard formulas
Pitch = ((PitchH << 8) | PitchL) / 32768 * 180  // degrés
Roll  = ((RollH << 8) | RollL) / 32768 * 180    // degrés
Yaw   = ((YawH << 8) | YawL) / 32768 * 180      // degrés + zOffset

// Output en radians (Signal K standard)
navigation.attitude = {
  roll:  roll_deg * π/180,
  pitch: pitch_deg * π/180,
  yaw:   null  // Magnetic heading séparé
}

navigation.headingMagnetic = yaw_deg + zOffset
```

### Reconnexion & Error Handling

```javascript
// Retry logic
plugin.reconnectDelay = 1000
serial.on('error', () => {
  setPluginError(err)
  // Auto-reconnect après délai
})
```

---

## 🎯 Comparaison Fonctionnelle

### Custom (v1.0.0) - Ton Plugin Actuel

**Strengths:**
- ✅ Simple et direct
- ✅ Compilé pour Signal K v2.25
- ✅ 10 Hz fixe (bon pour ta J/30)

**Limitations:**
- ❌ Un seul capteur
- ❌ Pas de calibration acceleromètre
- ❌ Offset heading hardcodé
- ❌ Pas de validation checksum
- ❌ Pas de reset angle reference

### GitHub V0.3.0 - Officiel

**Strengths:**
- ✅ Multi-device support
- ✅ Calibration avancée
- ✅ Fréquence configurable (0.2-50Hz)
- ✅ Offset heading ajustable
- ✅ Checksum validation
- ✅ Error handling robuste
- ✅ Mainteneur actif

**Limitations:**
- ⚠️ Marqué "BETA"
- ⚠️ Pas testé avec Signal K v2.25 (probablement OK)

---

## 🚀 Recommandation

### Pour TON CAS (J/30 Régate)

**Option A: Garder le custom (v1.0.0)**
- ✅ Fonctionne maintenant
- ✅ 10 Hz stable
- ✅ Simple maintenance

**Option B: Migrer vers V0.3.0 (recommandé)**
- ✅ Plus robuste
- ✅ Calibration facile (reset angle sans redémarrage)
- ✅ Offset heading parametrisé (intéressant si antennes non parfaitement alignées)
- ✅ Multi-device (si tu veux ajouter un 2e capteur plus tard)
- ⚠️ Beta, mais stable selon les tests

### Migration Strategy

```bash
# 1. Backup current
cp -r ~/.signalk/node_modules/signalk-wit-imu-usb ~/.signalk/node_modules/signalk-wit-imu-usb.backup

# 2. Install GitHub version
cd ~/.signalk
npm install github:W-Geronius/signalk-hwt901b-imu

# 3. Rename to match config
mv node_modules/signalk-hwt901b-imu node_modules/signalk-wit-imu-usb

# 4. Update settings.json (same plugin ID works!)
# 5. Test in Admin UI

# If issues → restore:
rm -rf node_modules/signalk-wit-imu-usb
cp -r node_modules/signalk-wit-imu-usb.backup node_modules/signalk-wit-imu-usb
```

---

## 💡 Cas d'Usage Intéressants

### 1. Offset Heading pour Antennes Décalées
Si tes antennes GPS ne sont pas parfaitement alignées avec le bateau:
```json
{
  "devices": [{
    "zOffset": 45.0  // Compense décalage 45°
  }]
}
```

### 2. Reset Angle Reference en Course
Via Admin UI, sans redémarrer:
```
Plugin Config → angleRef: true → SUBMIT
```
Le bateau se nivelle (0° roll/pitch) instantanément!

### 3. Fréquence Adaptée
- **0.5 Hz:** Économiser CPU, dashboard seulement
- **2 Hz:** Dashboard + alertes (bon compromis)
- **10 Hz:** Perf calculs précis (ta config actuelle)
- **50 Hz:** Analyse détaillée des mouvements

---

## 🎓 Conclusion

**Le plugin V0.3.0 est techniquement supérieur** mais le tien fonctionne parfaitement pour ta J/30.

**Suggestions:**
1. **Court terme:** Continue avec le custom (v1.0.0) - ça marche
2. **Moyen terme:** Migre vers V0.3.0 pour la calibration offset heading
3. **Long terme:** Envisage 2e capteur (accéléromètre indépendant?) = avantage multi-device

---

**Questions?** Je peux:
- 📥 Installer la version V0.3.0
- 🔧 Modifier le custom avec features V0.3.0
- 📖 Expliquer calibration en détail

**Quel choix?** ⛵

