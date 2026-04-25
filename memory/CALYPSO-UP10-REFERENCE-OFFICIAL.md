# Référence Calypso UP10 Portable Solar — Documentation officielle
# Source : Datasheet 2023 + User Manual v2.0 + Developer Manual 1.0 (firmware ≥ 2.0)

---

## Spécifications hardware

```
Modèle : Ultrasonic Portable Solar (UP10)
Dimensions : Ø 70 mm × 57 mm hauteur
Poids : 145 g
Thread montage : M16×2 (femelle)
Protection : IPX8 (30 min à 10 m)
Température : -15°C à +60°C (sans gel)

Capteurs : 4 × transducteurs ultrasoniques (aucune pièce mobile)
Alimentation : Panneau solaire intégré + batterie 500 mAh rechargeable
 Autonomie sans soleil : jusqu'à 30 jours (sleep) / 90 jours (mesure)
Bluetooth : BLE 5.1, portée 30 m en espace libre
Sample rate : 1 Hz (sortie standard)
Orientation : Marque de repère → BOW (étrave du bateau)

Vent vitesse :
 Range : 1 - 25 m/s (2.24 - 56 mph)
 Résolution : 0.01 m/s
 Précision : ±0.1 m/s à 10 m/s
 Threshold : 1 m/s (sous ce seuil = données non valides)

Vent direction :
 Range : 0 - 359°
 Résolution : 1°
 Précision : ±1°
 Convention : 0° = bow (étrave), 90° = tribord, 180° = arrière, 270° = bâbord
```

---

## Architecture BLE — Services et Caractéristiques GATT

### Service 0x180A — Device Information (READ seulement)

```
UUID 0x2A29 Manufacturer Name : "Calypso"
UUID 0x2A24 Model Number : "UP10"
UUID 0x2A26 Firmware Revision : ex. "0.47", "2.0", ...
UUID 0x2A25 Serial Number : (non utilisé)
UUID 0x2A27 Hardware Revision : (non utilisé)
UUID 0x2A28 Software Revision : (non utilisé)
```

---

### Service 0x180D — Data Service (NOTIFY + READ) ← PRINCIPAL

```
UUID 0x2A39 — Caractéristique principale, NOTIFY + READ
Taille : 5 bytes minimum

Layout du payload (little endian) :

Bytes 0-1 : Wind Speed — uint16 LE → /100 → m/s
 ex: 39 02 → 0x0239 = 569 → 5.69 m/s
 range: 0 - 40 m/s (résolution 0.01 m/s)

Bytes 2-3 : Wind Direction — uint16 LE → valeur directe en degrés
 ex: CE 00 → 0x00CE = 206 → 206°
 range: 0 - 359° (résolution 1°)

Byte 4 : Battery Level — uint8 → pourcentage direct (0-100%)
 ex: 09 → 9% (basse batterie)
 ex: 5A → 90%

UUID 0xA001 — Status (READ seulement)
 0x00 → Sleep Mode : BLE advertising uniquement, PAS de données vent
 0x02 → Normal Mode : Toutes les données disponibles

UUID 0xA002 — Data Rate (READ + WRITE)
 Écrire pour changer le taux de mise à jour :
 0x01 → 1 Hz (1 mesure/seconde)
 0x04 → 4 Hz (défaut)
 0x08 → 8 Hz (maximum)
```

---

### Service 0x181A — Environmental Sensing (NOTIFY + READ)

```
UUID 0x2A72 Apparent Wind Speed
 2 bytes little endian uint16 → valeur / 100 = m/s
 ex: 39 02 → 0x0239 = 569 → 5.69 m/s

UUID 0x2A73 Apparent Wind Direction
 2 bytes little endian uint16 → valeur / 100 = degrés
 ex: 78 50 → 0x5078 = 20600 → 206.00°
 ex: F8 75 → 0x75F8 = 30200 → 302.00°

Note : service alternatif au 0x2A39, même données mais séparées
 Utiliser 0x2A39 pour tout récupérer en un seul notify
```

---

### Service 0x180F — Battery (NOTIFY + READ)

```
UUID 0x2A19 Battery Level
 1 byte uint8 → 0 à 100%
```

---

### Modes de batterie — comportement BLE

```
SAFETY MODE : 0% - 2.5% batterie
 → Invisible BLE, aucune donnée, aucun advertising
 → Charger obligatoirement

SLEEP MODE : 2.5% - 10% batterie
 → BLE advertising actif
 → UUID 0xA001 = 0x00
 → Aucune donnée vent
 → Charger avant utilisation

NORMAL MODE : 10% - 100% batterie
 → UUID 0xA001 = 0x02
 → Toutes les données disponibles à 1/4/8 Hz
```

---

## Implémentation Python — bleak

```python
#!/usr/bin/env python3
"""
Driver Calypso UP10 Portable Solar — Midnight Rider
Connexion BLE via bleak, parsing des données GATT
"""
import asyncio, struct
from bleak import BleakScanner, BleakClient

# UUIDs des caractéristiques
UUID_DATA_MAIN = "0000{:04x}-0000-1000-8000-00805f9b34fb".format(0x2A39)
UUID_STATUS = "0000a001-0000-1000-8000-00805f9b34fb"
UUID_RATE = "0000a002-0000-1000-8000-00805f9b34fb"
UUID_WIND_SPEED = "0000{:04x}-0000-1000-8000-00805f9b34fb".format(0x2A72)
UUID_WIND_DIR = "0000{:04x}-0000-1000-8000-00805f9b34fb".format(0x2A73)
UUID_BATTERY = "0000{:04x}-0000-1000-8000-00805f9b34fb".format(0x2A19)
UUID_FIRMWARE = "0000{:04x}-0000-1000-8000-00805f9b34fb".format(0x2A26)

CALYPSO_NAME = "ULTRASONIC"  # préfixe BLE advertising


async def find_calypso():
    """Découverte BLE du Calypso UP10."""
    print("Scan BLE en cours...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if d.name and CALYPSO_NAME in d.name.upper():
            print(f"✅ Calypso trouvé : {d.name} @ {d.address}")
            return d.address
    print("❌ Calypso non trouvé")
    return None


def parse_main_packet(data: bytes) -> dict:
    """
    Parse le payload de UUID 0x2A39 (5 bytes minimum).
    
    Layout :
    Bytes 0-1 : Wind Speed uint16 LE → /100 = m/s
    Bytes 2-3 : Wind Direction uint16 LE → degrés (0-359)
    Byte 4 : Battery uint8 → %
    
    Retourne None si données invalides.
    """
    if len(data) < 5:
        return None

    speed_raw = struct.unpack_from('<H', data, 0)[0]  # uint16 LE
    direction_raw = struct.unpack_from('<H', data, 2)[0]  # uint16 LE
    battery_raw = data[4]  # uint8

    speed_ms = speed_raw / 100.0
    direction = direction_raw  # degrés directs (0-359)
    battery = battery_raw  # % (0-100)

    # Valider le seuil minimum (< 1 m/s = sous le threshold)
    valid = speed_ms >= 1.0

    return {
        'wind_speed_ms': speed_ms,
        'wind_speed_kts': speed_ms * 1.944444,  # pour affichage
        'wind_dir_deg': direction,
        'wind_dir_rad': deg_to_rad_apparent(direction),
        'battery_pct': battery,
        'valid': valid
    }


def deg_to_rad_apparent(deg: float) -> float:
    """
    Convertit l'angle de vent Calypso (0-359°) en radians Signal K.
    Convention Signal K environment.wind.angleApparent :
    0 = bow (étrave)
    positif = tribord (starboard)
    négatif = bâbord (port)
    range : -π à +π
    
    Calypso 0° → SK 0
    Calypso 90° → SK +π/2 (tribord)
    Calypso 180° → SK ±π (arrière)
    Calypso 270° → SK -π/2 (bâbord)
    """
    import math
    if deg <= 180:
        return deg * math.pi / 180
    else:
        return (deg - 360) * math.pi / 180


async def connect_and_listen(address: str):
    """Connexion et écoute des notifications."""
    async with BleakClient(address) as client:
        print(f"Connecté à {address}")
        
        # Lire firmware
        fw = await client.read_gatt_char(UUID_FIRMWARE)
        print(f"Firmware : {fw.decode().strip()}")
        
        # Lire status (Sleep vs Normal)
        status = await client.read_gatt_char(UUID_STATUS)
        mode = "Sleep" if status[0] == 0x00 else "Normal"
        print(f"Mode : {mode}")
        
        # Activer notifications sur le UUID principal
        def handle_notify(sender, data):
            parsed = parse_main_packet(data)
            if parsed and parsed['valid']:
                print(f"🌬️  Wind: {parsed['wind_speed_kts']:.1f} kt @ {parsed['wind_dir_deg']:.0f}° "
                      f"| Battery: {parsed['battery_pct']}%")
        
        await client.start_notify(UUID_DATA_MAIN, handle_notify)
        print("Écoute des données en cours (Ctrl+C pour arrêter)...")
        
        try:
            await asyncio.sleep(60)  # Écouter 60 secondes
        finally:
            await client.stop_notify(UUID_DATA_MAIN)
```

---

## Paths Signal K — Calypso UP10

```
environment.wind.speedApparent       (m/s)  — Vitesse vent apparent
environment.wind.angleApparent       (rad)  — Angle vent apparent (±π)
electrical.batteries.CALYPSO.stateOfCharge  (0-1) — Batterie Calypso (0% → 100%)
```

---

## Conversions indispensables

```
Vent vitesse (m/s → nœuds) : knots = m/s × 1.944444
Vent angle (degrés → radians) : rad = deg × π/180, avec convention ±π
Batterie (0-100% → 0-1) : soc = pct / 100.0
```

---

## Option recommandée : bibliothèque calypso-anemometer

```bash
# Installation
npm install calypso-anemometer

# Ou depuis Source
git clone https://github.com/calypsogeo/calypso-anemometer
cd calypso-anemometer
npm install
npm link ~/.signalk/node_modules/
```

**Avantages:**
- ✅ Gestion BLE automatique (reconnexion, sleep mode)
- ✅ Parsing données optimisé
- ✅ Integration Signal K native
- ✅ Maintenu par Calypso Geo

---

## NMEA sentences générées par la bibliothèque

```
$WIMWD — Wind from true direction relative to the VESSEL
 Format: $WIMWD,<direction>,T,<direction>,M,<speed>,N,<speed>,M*hh

Exemple : $WIMWD,206.0,T,225.0,M,5.69,N,10.4,M*7A
          ← 206° vrai, 225° magnétique, 5.69 nœuds

$WIMWV — Wind Speed and Angle
 Format: $WIMWV,<angle>,A,<speed>,N,A*hh

Exemple : $WIMWV,206.0,R,5.69,N,A*4B
          ← 206° relatif, 5.69 nœuds
```

---

## Plugin Signal K existant

```
Paquet : calypso-anemometer
Type : signalk-node-server-plugin

Configuration :
{
  "enabled": true,
  "debug": false,
  "characteristic": "0x2A39",
  "reconnectAttempts": 3,
  "reconnectDelay": 5000,
  "dataRate": 1  // 1, 4, ou 8 Hz
}
```

---

## Diagnostics terrain

```bash
# 1. Vérifier BLE advertising
bluetoothctl scan on | grep -i ULTRASONIC

# 2. Vérifier connexion
bluetoothctl connect <MAC>

# 3. Vérifier services disponibles
bluetoothctl info <MAC>

# 4. Lire caractéristique 0x2A39 (données vent)
gatttool -b <MAC> -I
> connect
> char-read-hnd 0x???  # UUID 0x2A39

# 5. Lire batterie
> char-read-hnd 0x???  # UUID 0x2A19

# 6. Vérifier Signal K
curl http://localhost:3000/signalk/v1/api/vessels/self/environment/wind

# 7. Monitor logs
sudo journalctl -u signalk -f | grep -i calypso
```

---

## Checklist démarrage Calypso UP10

```
PRÉ-DÉMARRAGE :

[ ] Vérifier batterie (LED solaire clignotante = en charge)
[ ] Batterie minimale requise : 10% (sinon Sleep Mode)
[ ] Attendre charge complète (4-6 heures sous soleil, ou USB)
[ ] Position montage : M16×2 thread, marque "BOW" vers étrave
[ ] Orientation : repère → étrave du bateau
[ ] Espace libre 360° autour (pas d'obstacles)

DÉMARRAGE :

[ ] Brancher USB ou placer au soleil (5V input ou charge solaire)
[ ] Attendre 3-5 secondes pour BLE advertising
[ ] Scan BLE : bluetoothctl scan on
[ ] Rechercher "ULTRASONIC-XXXX" (XXXX = numéro série)
[ ] Connecter : bluetoothctl connect <MAC>
[ ] Vérifier mode : status UUID 0xA001 = 0x02 (Normal)
[ ] Vérifier données : lire 0x2A39 → 5 bytes reçus

EN ROUTE :

[ ] Vérifier vitesse vent croît avec conditions réelles
[ ] Vérifier direction stable sur cap constant
[ ] Monitorer batterie (surtout en conditions sombres)
[ ] Si batterie < 10% → passer en Sleep Mode
[ ] Si batterie < 2.5% → mode Safety (invisible BLE)
```

---

## Priorités sources Signal K — Midnight Rider

```
PRIMARY SOURCE (si présent + batterie OK) :
 environment.wind.speedApparent ← Calypso UP10 (0x2A39)
 environment.wind.angleApparent ← Calypso UP10 (0x2A39)

FALLBACK (si Calypso absent) :
 environment.wind.* ← qtvlm (routing data)
 environment.wind.* ← calculated from attitude + polars

BATTERY MONITORING :
 electrical.batteries.CALYPSO.stateOfCharge ← Calypso battery level
 Alert si < 10% (Sleep Mode imminent)
 Alert si < 2.5% (Safety Mode — invisible BLE)
```

---

**Conservé précieusement pour référence future! ⛵**
