# Signal K Plugin Configuration - Quick Reference

**Résumé rapide pour Denis**

---

## 📍 OÙ EST LA CONFIGURATION?

```
/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json
```

C'est un fichier **JSON** avec tous les paramètres du plugin.

---

## 📂 STRUCTURE SIMPLIFIÉE

```
SIGNAL K
│
├── CODE (logique du plugin)
│   └── ~/.signalk/node_modules/signalk-wit-imu-usb/index.js
│
└── CONFIG (paramètres)
    └── ~/.signalk/plugin-config-data/signalk-wit-imu-usb.json  ← ICI!
```

---

## 🔧 PARAMÈTRES PRINCIPAUX

| Paramètre | Valeur | Signification |
|-----------|--------|---|
| `batchInterval` | 100 | Fréquence en ms (100ms = 10 Hz) |
| `usbPort` | /dev/ttyWIT | Port USB du WIT |
| `baudRate` | 115200 | Vitesse de transmission |
| `enabled` | true | Plugin actif/inactif |
| `debug` | false | Logs détaillés (oui/non) |

---

## 🎯 COMMENT ÇA MARCHE

```
1. Signal K démarre
2. Lit le fichier JSON
3. Extrait les paramètres
4. Appelle plugin.start(paramètres)
5. Plugin utilise les paramètres
   → batchInterval = 100ms
   → Crée un timer toutes les 100ms
   → Envoie les données à 10 Hz
```

---

## 🔄 CYCLE: 100ms → 10 Hz

```
Temps    USB reçoit        Buffer accumule         Action
────────────────────────────────────────────────────────
0-100ms  10 paquets        [pkt1...pkt10]         Accumule
100ms    Timer déclenche!  → Envoyer + Reset       ENVOIE!
100-200ms 10 paquets       [pkt11...pkt20]         Accumule
200ms    Timer déclenche!  → Envoyer + Reset       ENVOIE!
```

**Résultat:** 2 envois en 200ms = 10 Hz ✅

---

## 🎛️ MODIFIER LA FRÉQUENCE

### Formule
```
Fréquence (Hz) = 1000 ÷ batchInterval (ms)
```

### Exemples
```
batchInterval = 50ms   → 1000 ÷ 50 = 20 Hz (double vitesse)
batchInterval = 100ms  → 1000 ÷ 100 = 10 Hz (normal)
batchInterval = 200ms  → 1000 ÷ 200 = 5 Hz (demi vitesse)
batchInterval = 1000ms → 1000 ÷ 1000 = 1 Hz (très lent!)
```

---

## ✅ MÉTHODE 1: Interface Admin (RECOMMANDÉ)

```
1. http://localhost:3000
2. Admin (coin supérieur droit)
3. Installed Plugins
4. signalk-wit-imu-usb
5. Edit (icône)
6. Change batchInterval: 100
7. Save
8. Plugin redémarre automatiquement
```

**Avantages:**
- Simple
- Pas de risque d'erreur
- Redémarrage automatique

---

## ✅ MÉTHODE 2: Édition Directe (AVANCÉ)

```bash
nano /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json
```

**Avant:**
```json
"batchInterval": 1000,
```

**Après:**
```json
"batchInterval": 100,
```

**Sauvegarde:**
- Ctrl+X
- Y (oui)
- Enter

**Redémarre:**
```bash
sudo systemctl restart signalk
```

---

## 📋 FICHIER COMPLET

```json
{
  "configuration": {
    "usbPort": "/dev/ttyWIT",
    "baudRate": 115200,
    "batchInterval": 100,
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

## 🔑 POINTS CLÉS

1. **Code = Logique** (unchangé)
   - Où: `~/.signalk/node_modules/signalk-wit-imu-usb/index.js`
   - Utilise la configuration

2. **Config = Paramètres** (change facilement)
   - Où: `~/.signalk/plugin-config-data/signalk-wit-imu-usb.json`
   - Définit le comportement

3. **Signal K = Glue** (relie les deux)
   - Lit la config
   - Lance le code
   - Passe les paramètres

4. **Fréquence** = `1000 ÷ batchInterval`
   - 100ms → 10 Hz ✅
   - 50ms → 20 Hz 🚀

---

## 💾 FICHIERS IMPORTANTS

| Fichier | Type | Rôle |
|---------|------|------|
| index.js | Code | Logique du plugin |
| signalk-wit-imu-usb.json | Config | Paramètres |
| settings.json | Config | Config globale Signal K |

---

## 🚀 RÉSUMÉ ULTRA-COURT

**Où?**
→ `/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json`

**Comment?**
→ Signal K lit le JSON, le passe au plugin

**Quoi modifier?**
→ `batchInterval` pour changer la fréquence

**Valeur actuelle?**
→ 100ms = 10 Hz ✅

---

**Pour plus de détails:** Voir `SIGNALK-PLUGIN-CONFIGURATION-EXPLAINED.md`
