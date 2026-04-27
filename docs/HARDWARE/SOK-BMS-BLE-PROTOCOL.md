# SOK Battery BMS — Protocole Bluetooth BLE

**Dernière mise à jour :** Avril 2026  
**Source :** Reverse-engineering de l'app Android ABC-BMS (com.sjty.sbs_bms)  
**Documentation uniquement** — intégration à faire quand la batterie est à bord

---

## 1. Vue d'ensemble

La SOK 12V 100Ah LiFePO4 embarque un BMS (Battery Management System) avec module Bluetooth BLE intégré. L'app officielle s'appelle ABC-BMS (iOS et Android).

Le protocole BLE a été reverse-engineeré et permet une lecture complète des données depuis un Raspberry Pi sans passer par l'app officielle.

**Mot de passe ABC-BMS (réglages avancés):** `200010`

---

## 2. Comportements importants du BMS

| Situation | Symptôme | Solution |
|-----------|----------|----------|
| Batterie en storage mode | 0V aux bornes, batterie invisible en BLE scan | Brancher un chargeur LiFePO4 quelques secondes |
| BLE inactif prolongé | BLE ne broadcast plus après inactivité | Déclencher un courant de charge ou décharge |
| État protection | CMOS ou DMOS grisé dans l'app | Voir section PROT State dans l'app |

---

## 3. Paramètres BLE

| Paramètre | Valeur |
|-----------|--------|
| Service UUID | `0000FFF0-0000-1000-8000-00805F9B34FB` |
| Notify UUID (RX) | `0000FFF1-0000-1000-8000-00805F9B34FB` |
| Write UUID (TX) | `0000FFF2-0000-1000-8000-00805F9B34FB` |
| Standard UUIDs | `00002a29` (fabricant), `00002a24` (modèle), `00002a26` (firmware), `00002a25` (n° série) |

---

## 4. Commandes disponibles

Chaque commande est un tableau de 5 bytes, suivi d'un byte CRC8 calculé à l'envoi.

| Nom | Bytes | Code réponse | Données retournées |
|-----|-------|--------------|-------------------|
| cmd_name | `[0xee, 0xc0, 0x00, 0x00, 0x00]` | 0xCCF1 | Nom du BMS (ex: "SK12V100") |
| cmd_info | `[0xee, 0xc1, 0x00, 0x00, 0x00]` | 0xccf0 | SOC, courant, cycles |
| cmd_detail | `[0xee, 0xc2, 0x00, 0x00, 0x00]` | 0xCCF4 | Tension cellules individuelles |
| cmd_setting | `[0xee, 0xc3, 0x00, 0x00, 0x00]` | 0xCCF3 | Paramètres BMS (capacité, année, etc.) |
| cmd_protection | `[0xee, 0xc4, 0x00, 0x00, 0x00]` | 0xCCF5 | États de protection (CMOS, DMOS, etc.) |
| cmd_break | `[0xdd, 0xc0, 0x00, 0x00, 0x00]` | - | Interruption de communication |

**Format d'envoi :** `command_bytes + [minicrc(command_bytes)]`

---

## 5. Format des réponses (notifications BLE)

Toutes les réponses sont vérifiées avec un CRC8 (dernier byte du message).  
Le type de message est identifié par les 2 premiers bytes.

### 0xccf0 — Status (réponse à cmd_info)

| Offset | Longueur | Type | Contenu |
|--------|----------|------|---------|
| 0-1 | 2 | uint16 BE | Type de message (`0xccf0`) |
| 2-4 | 3 | int24 LE | Tension totale (mV) |
| 5-7 | 3 | int24 LE | Courant instantané (µA, divisé par 1 000 000 pour A) |
| 8-10 | 3 | int24 LE | Puissance (W) |
| 11-13 | 3 | int24 LE | Courant moyen (µA) |
| 14-15 | 2 | uint16 LE | Nombre de cycles |
| 16-17 | 2 | uint16 LE | SOC (%) |

**Exemple :** Courant = 0x000100 (µA) → 1A

### 0xCCF1 — Nom (réponse à cmd_name)

| Offset | Longueur | Type | Contenu |
|--------|----------|------|---------|
| 0-1 | 2 | uint16 BE | Type de message (`0xccf1`) |
| 2-9 | 8 | ASCII/UTF-8 | Nom du BMS (ex: "SK12V100") |

### 0xCCF2 — Température (incluse dans cmd_info)

| Offset | Longueur | Type | Contenu |
|--------|----------|------|---------|
| 5-6 | 2 | int16 LE | Température BMS (°C, signé) |
| 7-8 | 2 | int16 LE | Température MOS (°C, signé) |

### 0xCCF3 — Infos fabricant (réponse à cmd_setting)

| Offset | Longueur | Type | Contenu |
|--------|----------|------|---------|
| 0-1 | 2 | uint16 BE | Type de message (`0xccf3`) |
| 2 | 1 | uint8 | Année de fabrication (ajouter 2000) |
| 3-4 | 2 | uint16 LE | Mois/jour fabrication |
| 5-7 | 3 | uint24 BE | Capacité nominale (Ah, divisée par 128) |
| 8-9 | 2 | uint16 LE | État chauffe-batterie (0=off, 1=on) |
| 10-11 | 2 | uint16 LE | Tension nominale (V × 100) |

### 0xCCF4 — Tension cellules (réponse à cmd_detail)

| Offset | Longueur | Type | Contenu |
|--------|----------|------|---------|
| 0-1 | 2 | uint16 BE | Type de message (`0xccf4`) |
| 2+(x*4) | 1 | uint8 | Index de la cellule (1-4) |
| 3+(x*4) | 2 | uint16 LE | Tension de la cellule (mV) |
| 5+(x*4) | 1 | uint8 | Réservé |

**Tension totale (calcul) :** Somme des 4 cellules / 1000 (en V)

**Exemple :**
```
Cellule 1: 3250 mV
Cellule 2: 3245 mV
Cellule 3: 3240 mV
Cellule 4: 3255 mV
Total: (3250 + 3245 + 3240 + 3255) / 1000 = 12.99 V
```

### 0xCCF5 — Protection (réponse à cmd_protection)

| Offset | Longueur | Type | Contenu |
|--------|----------|------|---------|
| 0-1 | 2 | uint16 BE | Type de message (`0xccf5`) |
| 2 | 1 | uint8 | Flags de protection |
| 3 | 1 | uint8 | État CMOS (0=normal, 1=déclenché) |
| 4 | 1 | uint8 | État DMOS (0=normal, 1=déclenché) |
| 5+ | - | - | Autres états de protection |

---

## 6. Algorithme CRC8

Utilisé pour la vérification d'intégrité des données.

```python
def minicrc(data):
    """Calcule le CRC8 pour les données BMS SOK"""
    i = 0
    for b in data:
        i ^= b & 255
        for _ in range(8):
            if (i & 1) != 0:
                i = (i >> 1) ^ 140
            else:
                i = i >> 1
    return i

# Utilisation
data = [0xee, 0xc0, 0x00, 0x00, 0x00]
crc = minicrc(data)
data_with_crc = data + [crc]
# Résultat : [0xee, 0xc0, 0x00, 0x00, 0x00, crc_value]
```

---

## 7. Données disponibles pour InfluxDB

| Measurement | Field | Unité | Source | Calcul |
|-------------|-------|-------|--------|--------|
| `sok_bms` | `soc_pct` | % | 0xccf0 offset 16 | Valeur directe |
| `sok_bms` | `voltage_v` | V | 0xccf0 offset 2 | Valeur / 1000 |
| `sok_bms` | `current_a` | A | 0xccf0 offset 5 | Valeur / 1 000 000 |
| `sok_bms` | `power_w` | W | 0xccf0 offset 8 | Valeur directe |
| `sok_bms` | `temp_bms_c` | °C | 0xCCF2 offset 5 | Valeur directe |
| `sok_bms` | `temp_mos_c` | °C | 0xCCF2 offset 7 | Valeur directe |
| `sok_bms` | `cycles` | nb | 0xccf0 offset 14 | Valeur directe |
| `sok_bms` | `cell_1_mv` | mV | 0xCCF4 | Tension cellule 1 |
| `sok_bms` | `cell_2_mv` | mV | 0xCCF4 | Tension cellule 2 |
| `sok_bms` | `cell_3_mv` | mV | 0xCCF4 | Tension cellule 3 |
| `sok_bms` | `cell_4_mv` | mV | 0xCCF4 | Tension cellule 4 |
| `sok_bms` | `cell_imbalance_mv` | mV | 0xCCF4 | Max - Min cellules |
| `sok_bms` | `capacity_ah` | Ah | 0xCCF3 | Capacité nominale |
| `sok_bms` | `year_mfg` | année | 0xCCF3 offset 2 | 2000 + valeur |
| `sok_bms` | `prot_cmos` | bool | 0xCCF5 | État CMOS |
| `sok_bms` | `prot_dmos` | bool | 0xCCF5 | État DMOS |

---

## 8. Dépendances Python requises

```bash
pip3 install bleak influxdb-client
sudo apt-get install -y python3-dbus libglib2.0-dev
```

**Dépendances:**
- **bleak** — Abstraction BLE multi-plateforme (async)
- **influxdb-client** — Client Python InfluxDB v2
- **dbus** — Interface D-Bus pour BlueZ (Linux)
- **glib2** — Bibliothèque système requise par BlueZ

---

## 9. Trouver la MAC address de la batterie

À faire **quand la batterie est présente et allumée** :

```bash
# Scan rapide pour SOK
sudo hcitool lescan | grep -i "SOK\|ABC\|BMS"

# Scan large si rien trouvé
sudo hcitool lescan

# Alternative avec bluetoothctl
bluetoothctl scan on
# Appuyer Ctrl+C quand MAC trouvée
```

**Important:** La batterie doit être hors "storage mode" (sinon 0V aux bornes). Brancher un chargeur LiFePO4 brièvement pour activer le BMS.

**Format MAC attendu:** `XX:XX:XX:XX:XX:XX` (ex: `4C:65:A8:D2:7C:A2`)

---

## 10. Intégration Signal K

Quand la batterie sera intégrée, créer un plugin Signal K :

```
~/.signalk/node_modules/signalk-sok-bms-ble/
├── package.json
├── index.js (plugin principal)
└── README.md
```

Le plugin doit :
1. Scanner la batterie SOK via BLE
2. Envoyer les commandes (cmd_info, cmd_detail, etc.)
3. Parser les réponses et vérifier CRC8
4. Mettre à jour les paths Signal K:
   - `electrical.batteries.main.voltage`
   - `electrical.batteries.main.current`
   - `electrical.batteries.main.temperature`
   - `electrical.batteries.main.capacity`
   - etc.

**Template de plugin :** Se référer à la documentation Signal K et aux plugins existants dans `~/.signalk/node_modules/`

---

## 11. Fichier d'intégration autonome

Pour une première intégration rapide (avant integration Signal K) :

```
/home/aneto/sok_bms_reader.py
```

Ce script autonome doit :
1. Se connecter au BMS via BLE (bleak)
2. Envoyer commandes périodiquement
3. Parser les réponses
4. Écrire dans InfluxDB
5. Tourner en service systemd ou cron

**Structure :**
```python
class SOK_BMS:
    async def connect(mac_address)
    async def read_status()      # cmd_info
    async def read_detail()      # cmd_detail
    async def read_settings()    # cmd_setting
    async def write_to_influx()
```

---

## 12. Référence complète des UUIDs

### Service Principal
- `0000FFF0-0000-1000-8000-00805F9B34FB` — Service BMS propriétaire

### Caractéristiques
- `0000FFF1-0000-1000-8000-00805F9B34FB` — RX (Notify, lecture données)
- `0000FFF2-0000-1000-8000-00805F9B34FB` — TX (Write, envoi commandes)

### Standards BLE GATT
- `00002a29-0000-1000-8000-00805f9b34fb` — Manufacturer Name
- `00002a24-0000-1000-8000-00805f9b34fb` — Model Number String
- `00002a26-0000-1000-8000-00805f9b34fb` — Firmware Revision String
- `00002a25-0000-1000-8000-00805f9b34fb` — Serial Number String

---

## 13. Notes de développement

- **Async/await:** Utiliser `bleak` et `asyncio` pour la non-bloquante
- **Timeout :** 5-10 secondes par commande (BLE peut être lent)
- **Retry:** Implémenter une logique de reconnexion en cas de déconnexion
- **Logging:** Utiliser Python `logging` pour débogage
- **Rate limiting:** Limiter à ~1 lecture par 5 secondes (batterie peut pas suivre sinon)
- **CRC8:** Vérifier CRC8 **avant** de traiter les données
- **Erreurs:** Gérer les exceptions BLE (timeout, déconnexion, parsing)

---

## 14. Exemple de flux complet

```
1. Scanner BLE → Trouver "SOK" ou "ABC-BMS"
2. Connecter (bleak.BleakClient)
3. Notifier le UUID RX (0000FFF1)
4. Écrire cmd_info sur UUID TX (0000FFF2)
5. Attendre réponse 0xccf0
6. Parser et vérifier CRC8
7. Écrire dans InfluxDB
8. Attendre 5 secondes
9. Répéter à partir de l'étape 3
```

---

## 15. Ressources externes

- **Protocole BLE:** Bluetooth SIG Specification v5.3
- **BlueZ (Linux Bluetooth):** https://github.com/bluez/bluez
- **Bleak (Python BLE):** https://github.com/hbldh/bleak
- **ABC-BMS App:** iOS/Android (reverse-engineered)
- **Dbus-serialbattery:** https://github.com/Louisvdw/dbus-serialbattery/discussions/571

---

**Documentation créée:** Avril 2026  
**Statut:** Référence pour intégration future  
**Prochain step:** Intégration quand batterie à bord (May 2026)
