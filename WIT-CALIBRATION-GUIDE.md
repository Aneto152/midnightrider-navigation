# WIT IMU Calibration Guide

## Vue d'ensemble

L'IMU WIT WT901BLECL doit être **calibré une seule fois** pour corriger les offsets matériels. Cette calibration est effectuée au démarrage et sauvegardée dans un fichier.

## Étapes de Calibration

### 1. **Préparer l'IMU**

```bash
# Arrête le lecteur USB courant
sudo systemctl stop wit-usb-reader

# Attends 5 sec
sleep 5
```

### 2. **Lancer la Calibration**

```bash
python3 /home/aneto/wit-imu-calibration.py
```

**IMPORTANT:** L'IMU doit être **IMMOBILE ET HORIZONTAL** durant tout le calibrage!

Exemple de sortie:

```
╔════════════════════════════════════════════════════════════╗
║  WIT IMU Calibration - One-Time Static Calibration        ║
╚════════════════════════════════════════════════════════════╝

⚠️  KEEP IMU COMPLETELY STILL!

Collecting 300 samples (10.0s)...

  [ 50/300] samples collected...
  [100/300] samples collected...
  [150/300] samples collected...
  [200/300] samples collected...
  [250/300] samples collected...
  [300/300] samples collected...

Calculating offsets...

Axis X:
  Accel: avg=0.0234g → offset=0.0234g
  Gyro:  avg=2.15°/s → offset=2.15°/s

Axis Y:
  Accel: avg=-0.0156g → offset=-0.0156g
  Gyro:  avg=-1.87°/s → offset=-1.87°/s

Axis Z:
  Accel: avg=10.1204g → offset=0.3104g
  Gyro:  avg=0.45°/s → offset=0.45°/s

✅ Calibration saved to /home/aneto/.signalk/wit-calibration.json
```

### 3. **Fichier de Calibration**

Le fichier `/home/aneto/.signalk/wit-calibration.json` contient:

```json
{
  "accel_offset": [0.0234, -0.0156, 0.3104],
  "gyro_offset": [2.15, -1.87, 0.45],
  "timestamp": "2026-04-22T13:57:00Z",
  "samples": 300
}
```

### 4. **Activer le Lecteur Calibré**

```bash
# Met à jour le service systemd
sudo systemctl edit wit-usb-reader
```

Change `ExecStart` en:

```
ExecStart=/usr/bin/python3 /home/aneto/wit-usb-calibrated.py
```

Puis redémarre:

```bash
sudo systemctl restart wit-usb-reader
```

### 5. **Vérifier la Calibration**

```bash
# Check logs
sudo journalctl -u wit-usb-reader -n 5 --no-pager

# Devrait afficher:
# ✅ Calibration loaded (offsets applied)
# ✅ USB port opened
# ✅ WebSocket connected
```

## Architecture

```
WIT IMU (100Hz brut)
    ↓
wit-usb-calibrated.py
    ├─ Lit packets binaires
    ├─ Applique offsets de calibration
    ├─ Filtre low-pass (α=0.05)
    └─ Envoie via WebSocket Signal K
        ↓
    Signal K API
        ↓
    Grafana
```

## Calibration vs Filtrage

| Étape | Quand | Quoi | Fichier |
|-------|-------|------|---------|
| **Calibration** | 1× au démarrage | Soustrait offsets matériels | `wit-calibration.json` |
| **Filtrage** | Chaque update | Lisse le bruit (low-pass α) | `WIT_FILTER_ALPHA` env var |

**Exemple:**
```
Valeur brute:  10.234 g
- Offset:       0.310 g
= Calibré:      9.924 g
→ Filtre α=0.05 → 9.920 g
→ Signal K
```

## Cas de Recalibration

Recalibrer **uniquement si:**
- ❌ L'IMU a reçu un choc/chute
- ❌ Les offsets dérivent (après 6+ mois)
- ❌ Les datas semblent "biaisées"

**Ne pas recalibrer** pour:
- ✅ Changements de température (filtrage gère)
- ✅ Variations mineures (< 0.5%)
- ✅ Bruits de vibration (filtrage gère)

## Paramètres à Ajuster

### Filter Alpha (WIT_FILTER_ALPHA)

```bash
# Plus lissé (moins réactif):
export WIT_FILTER_ALPHA=0.01
sudo systemctl restart wit-usb-reader

# Normal (défaut):
export WIT_FILTER_ALPHA=0.05

# Moins lissé (plus réactif):
export WIT_FILTER_ALPHA=0.1
```

### Calibration File

```bash
# Utiliser fichier custom:
export WIT_CALIBRATION=/path/to/custom-calib.json
sudo systemctl restart wit-usb-reader
```

## Monitoring

Vérifie que la calibration est appliquée:

```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | python3 -m json.tool

# Avec calibration, les values doivent être:
# - roll/pitch ~0° quand horizontal
# - yaw = heading actuel
# - accel.z ~9.81 m/s² (gravité)
```

## Résumé

1. **Immobilise l'IMU horizontalement**
2. **Lance `python3 /home/aneto/wit-imu-calibration.py`**
3. **Mets à jour le service systemd**
4. **Redémarre**
5. **Vérifiez via API Signal K**

**C'est fait!** La calibration est sauvegardée et appliquée automatiquement à chaque démarrage.
