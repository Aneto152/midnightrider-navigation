# Référence UM982 — Documentation officielle Unicore R1.3/R1.4 — Midnight Rider
# Source : UM982 User Manual R1.3 + Unicore N4 Commands Reference R1.4

---

## Spécifications hardware UM982

```
Chip : NebulasIV SoC (Unicore UC9810)
Dimensions : 21 × 16 × 2.6 mm (SMD LGA 48 broches)
Tension : 3.0V ~ 3.6V DC (le NANO-HED10L embarque un régulateur)
Conso : 600 mW typique (dual antenna 10Hz PVT + heading)
Interfaces : 3 × UART (LVTTL), 1 × I2C*, 1 × SPI*, 1 × CAN*
 * interfaces réservées, non supportées actuellement
Antennes : ANT1 (maître/master) + ANT2 (esclave/slave)
Update rate : 20 Hz max (positioning + heading)

Précision RTK :
 Horizontal : 0.8 cm + 1 ppm (RMS)
 Vertical : 1.5 cm + 1 ppm (RMS)

Précision heading :
 0.1° par mètre de baseline (RMS) — ex: 0.1° pour 1m, 0.05° pour 2m

TTFF :
 Cold start : < 30 s
 Hot start : < 4 s
 Init RTK : < 5 s (typique), reliability > 99.9%

Constellations : GPS L1/L2/L5 + BDS B1I/B2I/B3I + GLONASS G1/G2
 + Galileo E1/E5a/E5b + QZSS L1/L2/L5 + SBAS
```

---

## Définition du heading UM982

```
RÈGLE FONDAMENTALE (Section 1.3 Heading Configuration) :

Heading = angle de True North vers la baseline ANT1→ANT2,
 mesuré dans le sens horaire (clockwise).

ANT1 = maître (master) → connecteur principal
ANT2 = esclave (slave) → connecteur secondaire

Si ANT1 est à TRIBORD et ANT2 à BÂBORD (transversal) :
 heading UM982 = cap du bateau + 90°
 → offset à appliquer : -90° (ou configurer dans le firmware)

Si ANT1 est à l'AVANT et ANT2 à l'ARRIÈRE (longitudinal) :
 heading UM982 = cap du bateau directement
 → offset = 0°
```

---

## Sentences de sortie UM982

### $GPHPR — Heading + Pitch + Roll (Table 7-42)

```
Format : $GPHPR,<UTC>,<Heading>,<Pitch>,<Roll>,<QF>*<checksum>

Champs :
 [1] UTC : HHMMSS.SS
 [2] Heading : degrés True North, 0.000 à 359.999
 [3] Pitch : degrés, -90 à +90
 [4] Roll : degrés, -180 à +180
 [5] QF : Quality Factor
 0 = Invalide → REJETER
 1 = Autonome → acceptable (pas de correction différentielle)
 2 = DGPS → bon
 4 = RTK Fixed → ✅ optimal (précision 0.1°/1m baseline)
 5 = RTK Float → ✅ très bon

Exemple :
$GPHPR,123456.00,184.321,-0.512,2.341,4*6A
 ↑ ↑ ↑ ↑
 Heading Pitch Roll RTK Fixed
```

### $GNTHS / $GPTHS — True Heading Status (Table 7-41)

```
Format : $GNTHS,<Heading>,<T>*<checksum>

Champs :
 [1] Heading : degrés, 0.000 à 359.999
 [2] T : T = True heading valide / V = invalide

Exemple :
$GNTHS,184.321,T*XX

Note : sentence simple, pas de pitch/roll → préférer $GPHPR
```

### $GPHPD — Position + Heading complet (Table 7-46)

```
Format :
$GPHPD,<UTC>,<status>,<lat>,<N/S>,<lon>,<E/W>,<alt>,
 <heading>,<pitch>,<roll>,<speed>,<PDOP>,<HDOP>,<VDOP>*<checksum>

Note : sentence la plus complète, position + attitude en une ligne
```

### $GNRMC — Position + SOG + COG (Table 7-12)

```
Format : $GNRMC,<UTC>,<A/V>,<lat>,<N/S>,<lon>,<E/W>,<SOG>,<COG>,<date>,...*<checksum>

Champs :
 [2] A = données valides / V = invalide → rejeter si V
 [3][4] : latitude DDmm.mmmmm + N/S
 [5][6] : longitude DDDmm.mmmmm + E/W
 [7] SOG : nœuds → convertir en m/s pour Signal K (× 0.514444)
 [8] COG : degrés True → convertir en radians pour Signal K
```

### $GPGGA — Fix et qualité (Table 7-4)

```
Format : $GPGGA,<UTC>,<lat>,<N/S>,<lon>,<E/W>,<quality>,<numSV>,<HDOP>,<alt>,...

Quality :
 0 = Invalide
 1 = Autonome (GNSS)
 2 = DGPS
 4 = RTK Fixed ✅
 5 = RTK Float ✅
```

---

## Commandes Unicore — référence complète

```
Format commandes : ASCII sans checksum (défaut)
Terminator : \r\n obligatoire
```

### Commandes essentielles

```bash
# Interroger la configuration courante
version                      # version firmware
config                       # configuration actuelle des ports
mode                        # mode actif (rover/base/heading2)

# Mode rover (défaut UM982 = UAV — utiliser SURVEY pour bateau)
mode rover survey           # précision surveying mode
saveconfig

# Configuration heading (antennes fixes sur le bateau)
config heading fixlength    # baseline fixe ✅ (défaut recommandé bateau)
config heading variablelength # baseline variable (si antennes mobiles)
config heading static       # les deux antennes sont immobiles

# Configurer la longueur de baseline et tolérance
config heading length 1.0 0.10  # baseline 100cm ± 10cm
config heading length 0.95 0.10 # exemple pour J/30

# Configurer sentences NMEA de sortie
config serialport nmea gpgsv 0 10     # disable GPGSV toutes les 10 frames
config serialport nmea gphpr 1 1      # enable GPHPR chaque frame
config serialport nmea gnths 1 1      # enable GNTHS
config serialport nmea gnrmc 1 1      # enable GNRMC
config serialport nmea gpgga 1 1      # enable GPGGA

# Sauvegarder configuration en flash
saveconfig
```

### Configurer les sentences de sortie

```bash
# Format : config serialport nmea <sentence> <enable> <interval>
# enable : 0 = disabled, 1 = enabled
# interval : envoi chaque N frames (1 = chaque frame)

config serialport nmea gpgsv 0 10     # satellites (trop lourd pour NavBox)
config serialport nmea gphpr 1 1      # heading + pitch + roll (✅ recommandé)
config serialport nmea gphpd 1 1      # position + attitude complète
config serialport nmea gnths 1 1      # heading simple
config serialport nmea gnrmc 1 1      # position + speed
config serialport nmea gpgga 1 1      # fix + quality
config serialport nmea gpgst 1 1      # satellite geometry/time

saveconfig
```

### Configurer le port série

```bash
# Port UART1 (principal sur NANO-HED10L)
config serialport uart1 9600 8 N 1 N  # 9600 baud, 8N1, pas de flow control
config serialport uart1 115200 8 N 1 N # alternative haute vitesse

# Port UART2 (si utilisé)
config serialport uart2 9600 8 N 1 N

saveconfig
```

### Vérification et diagnostics via commandes

```bash
# Interroger le mode courant
mode                    # → "rover" ou "base" ou "heading2"

# Interroger la version firmware
version                 # → UM982 vX.XX

# Interroger la configuration courante
config                  # → affiche tous les paramètres

# Interroger le statut du heading (une fois fixé)
heading                 # → baseline, QF, status

# Interroger les satellites en vue
gsv                     # → constellation utilisée

# Interroger les données PVT (position + velocity + time)
pvt                     # → lat/lon/alt, SOG/COG, UTC
```

---

## Paths Signal K — conversions obligatoires

```
UM982 → Signal K conversion (IMPORTANT)

Heading (degrés) → navigation.headingTrue (radians)
  Formula: rad = deg × π/180
  Range: 0-2π (au lieu de 0-360°)

Pitch (degrés) → navigation.attitude.pitch (radians)
  Formula: rad = deg × π/180
  Range: -π/2 à +π/2

Roll (degrés) → navigation.attitude.roll (radians)
  Formula: rad = deg × π/180
  Range: -π à +π

SOG (nœuds) → navigation.speedOverGround (m/s)
  Formula: m/s = knots × 0.514444

COG (degrés) → navigation.courseOverGroundTrue (radians)
  Formula: rad = deg × π/180
```

---

## Diagnostics terrain

```bash
# 1. Vérifier connexion série
cat /dev/ttyUSB0  # 9600 baud → doit afficher sentences NMEA

# 2. Vérifier que UM982 envoie des données
timeout 5 cat /dev/ttyUSB0 | grep -E "GPHPR|GNTHS|GNRMC"

# 3. Vérifier le mode courant
echo "mode" > /dev/ttyUSB0
cat /dev/ttyUSB0  # → devrait afficher "rover" ou "base" ou "heading2"

# 4. Vérifier la version firmware
echo "version" > /dev/ttyUSB0
cat /dev/ttyUSB0  # → affiche version

# 5. Vérifier le statut heading
echo "heading" > /dev/ttyUSB0
cat /dev/ttyUSB0  # → affiche baseline et QF

# 6. Vérifier que les antennes sont bien espacées
# En mouvement → SOG devrait croître, heading devrait stabiliser

# 7. Rechercher la longueur de baseline réelle
# Statique au repos, antennes espacées de 1m → heading doit être stable
# Marge d'erreur : ±0.1° (spec)
```

---

## Checklist démarrage UM982

```
PRÉ-DÉMARRAGE (avant navire) :

[ ] Vérifier alimentation 3.0-3.6V DC
[ ] Vérifier connexion des deux antennes (ANT1 + ANT2)
[ ] ANT1 = connecteur principal (maître)
[ ] ANT2 = connecteur secondaire (esclave)
[ ] Espace entre antennes : minimum 0.5m (recommandé 1.0-2.0m)
[ ] Câbles blindés LVTTL vers RPi/NavBox
[ ] Port série accessible : /dev/ttyUSB0 ou /dev/ttyUM982

DÉMARRAGE :

[ ] Envoyer commande "mode rover survey"
[ ] Envoyer "saveconfig"
[ ] Attendre fix GPS (< 30s à froid)
[ ] Attendre fix RTK heading (< 5s typique)
[ ] Vérifier sentences NMEA ($GPHPR + $GNRMC)
[ ] Vérifier QF (Quality Factor) = 4 (RTK Fixed) ou 5 (RTK Float)
[ ] Vérifier heading stable (variance < 0.1°)

EN ROUTE :

[ ] Vérifier SOG croît avec la vitesse du bateau
[ ] Vérifier COG stable sur cap constant
[ ] Vérifier pitch/roll dans limites physiques (±30° max)
[ ] Monitorer HDOP (< 1.5 idéal)
[ ] Si perte signal : RTK Float (acceptable) ou invalide (rejeter)
```

---

## Intégration Signal K

```python
# Parser minimal GPHPR
def parse_gphpr(sentence):
    """$GPHPR,<UTC>,<Heading>,<Pitch>,<Roll>,<QF>*checksum"""
    parts = sentence.split(',')
    
    qf = int(parts[5].split('*')[0])
    
    if qf == 0:
        return None  # Invalide, rejeter
    
    return {
        'navigation.headingTrue': float(parts[2]) * math.pi / 180,  # rad
        'navigation.attitude.pitch': float(parts[3]) * math.pi / 180,
        'navigation.attitude.roll': float(parts[4]) * math.pi / 180,
        'quality': qf  # 1, 2, 4, 5
    }

# Parser minimal GNRMC
def parse_gnrmc(sentence):
    """$GNRMC,<UTC>,<A/V>,<lat>,<N/S>,<lon>,<E/W>,<SOG>,<COG>,<date>..."""
    parts = sentence.split(',')
    
    if parts[2] != 'A':
        return None  # V = invalid, rejeter
    
    sog_knots = float(parts[7])
    cog_deg = float(parts[8])
    
    return {
        'navigation.speedOverGround': sog_knots * 0.514444,  # m/s
        'navigation.courseOverGroundTrue': cog_deg * math.pi / 180,  # rad
    }
```

---

**Conservé précieusement pour référence future! ⛵**
