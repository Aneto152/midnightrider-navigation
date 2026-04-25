# Signal K — Inventaire Complet des Mesures

**Date:** 2026-04-21  
**Source:** Schema Signal K 1.5.1  
**Bateau:** J/30 MidnightRider

---

## 📊 Vue d'ensemble (14 catégories)

Signal K organise les données en **14 catégories principales**:

| Catégorie | Paths | Description |
|-----------|-------|-------------|
| **navigation** | 50+ | Position, vitesse, cap, routes, waypoints |
| **environment** | 30+ | Vent, température, humidité, pression, eau |
| **electrical** | 40+ | Batteries, alternateur, panneaux solaires, etc |
| **propulsion** | 20+ | Moteur (RPM, température, consommation) |
| **steering** | 10+ | Gouvernail (angle, trim) |
| **performance** | 15+ | Polaires, VMG, efficacité, heel |
| **sails** | 10+ | Configuration voiles, état |
| **tanks** | 20+ | Carburant, eau, eaux usées |
| **design** | 15+ | Caractéristiques bateau (longueur, poids) |
| **communication** | 10+ | Radio, VHF, AIS |
| **sensors** | 5+ | Capteurs disponibles |
| **resources** | variable | Routes, waypoints, marques |
| **notifications** | variable | Alertes et warnings |
| **sources** | variable | Sources de données (GPS, instruments) |

**Total: 200+ mesures disponibles**

---

## 🗺️ NAVIGATION (50+ paths)

### Position & Localisation
```
navigation.position                    - Position lat/lon (WGS84)
navigation.position.latitude           - Latitude (-90 à +90°)
navigation.position.longitude          - Longitude (-180 à +180°)
navigation.position.altitude           - Altitude (m)
navigation.position.source             - Source position (GPS, Loran, etc)
```

### Cap & Direction
```
navigation.courseOverGroundTrue        - Cap vrai au-dessus du sol (rad)
navigation.courseOverGroundMagnetic    - Cap magnétique au-dessus du sol (rad)
navigation.headingTrue                 - Cap vrai du bateau (rad)
navigation.headingMagnetic             - Cap magnétique du bateau (rad)
navigation.heading                     - Cap bateau (défaut true)
```

### Vitesse
```
navigation.speedOverGround             - Vitesse au-dessus du sol (m/s = knots)
navigation.speedThroughWater           - Vitesse bateau dans l'eau (m/s)
navigation.speedThroughWaterRaw        - Vitesse brute avant calibrage (m/s)
```

### Attitude (Gîte, Assiette, Rotation)
```
navigation.attitude.roll               - Gîte latérale (rad, + = tribord)
navigation.attitude.pitch              - Assiette long/court (rad)
navigation.attitude.yaw                - Rotation autour axe vertical (rad)
navigation.attitude.rolRate            - Vitesse gîte (rad/s)
navigation.attitude.pitchRate          - Vitesse assiette (rad/s)
navigation.attitude.yawRate            - Vitesse rotation (rad/s)
```

### Profondeur & Eau
```
navigation.waterDepth                  - Profondeur d'eau (m)
navigation.waterDepthBelowKeel         - Profondeur sous la quille (m)
navigation.waterDepthBelowSurface      - Profondeur sous surface (m)
```

### Caps & Routes
```
navigation.magneticVariation           - Déclinaison magnétique (rad)
navigation.magneticDeviation           - Déviation magnétique (rad)
navigation.distanceToArrival           - Distance jusqu'à destination (m)
navigation.destination                 - Destination actuelle
```

### Waypoints & Course
```
navigation.waypoint                    - Waypoint actuel
navigation.waypoint.position           - Position waypoint (lat/lon)
navigation.waypoint.distance           - Distance waypoint (m)
navigation.waypoint.bearing            - Cap vers waypoint (rad)
navigation.waypoint.bearingMagnetic    - Cap magnétique waypoint (rad)
```

### Racing (Régates)
```
navigation.racing.startLineStarboardHand  - Marque tribord départ
navigation.racing.startLinePortHand       - Marque bâbord départ
navigation.racing.layline                 - Layline optimal (rad)
navigation.racing.distanceToMark          - Distance à la marque (m)
navigation.racing.offsetFromLayline       - Écart du layline (m ou °)
navigation.racing.timeToMark              - Temps jusqu'à marque (s)
```

### GNSS Details
```
navigation.gnss.type                   - Type GNSS (GPS, GLONASS, etc)
navigation.gnss.sattelites             - Nombre satellites
navigation.gnss.hdop                   - Précision horizontale (HDOP)
navigation.gnss.vdop                   - Précision verticale (VDOP)
navigation.gnss.pdop                   - Précision 3D (PDOP)
navigation.gnss.geoidalSeparation      - Séparation géoïdale (m)
```

---

## 🌊 ENVIRONMENT (30+ paths)

### Vent
```
environment.wind.speedTrue             - Vitesse vent vrai (m/s)
environment.wind.speedOverGround       - Vitesse vent au sol (m/s)
environment.wind.speedApparent         - Vitesse vent apparent (m/s)
environment.wind.directionTrue         - Direction vent vrai (rad)
environment.wind.directionMagnetic     - Direction vent magnétique (rad)
environment.wind.directionApparent     - Direction vent apparent (rad)
environment.wind.angleTrueWater        - Angle vent par rapport bateau (rad)
```

### Température
```
environment.water.temperature          - Température eau (K)
environment.air.temperature            - Température air (K)
environment.cabin.temperature          - Température cabine (K)
environment.sauna.temperature          - Température sauna (K)
environment.inside.temperature         - Température intérieur (K)
```

### Eau
```
environment.water.salinity             - Salinité (ppt, parts per thousand)
environment.water.currentSpeed         - Vitesse courant (m/s)
environment.water.currentDirection     - Direction courant (rad)
```

### Atmosphère
```
environment.outside.pressure           - Pression atmosphérique (Pa)
environment.outside.humidity           - Humidité relative (0-1)
environment.outside.illuminance        - Luminosité (lux)
```

### Marées
```
environment.tide.currentLevel          - Niveau marée actuel (m)
environment.tide.currentDirection      - Direction courant marée (rad)
environment.tide.currentSpeed          - Vitesse courant marée (m/s)
environment.tide.heightHigh            - Hauteur marée haute (m)
environment.tide.heightLow             - Hauteur marée basse (m)
environment.tide.timeTillHighWater     - Temps jusqu'à haute mer (s)
environment.tide.timeTillLowWater      - Temps jusqu'à basse mer (s)
```

---

## ⚡ ELECTRICAL (40+ paths)

### Batterie Moteur (12V)
```
electrical.batteries.12v.voltage       - Tension 12V (V)
electrical.batteries.12v.current       - Courant 12V (A, + = charge, - = décharge)
electrical.batteries.12v.temperature   - Température batterie (K)
electrical.batteries.12v.stateOfCharge - État charge SOC (0-1)
electrical.batteries.12v.capacity      - Capacité (Ah)
electrical.batteries.12v.energy        - Énergie restante (J)
electrical.batteries.12v.power         - Puissance (W)
```

### Batterie Auxiliaire (24V)
```
electrical.batteries.24v.voltage       - Tension 24V (V)
electrical.batteries.24v.current       - Courant 24V (A)
electrical.batteries.24v.temperature   - Température batterie (K)
electrical.batteries.24v.stateOfCharge - État charge SOC (0-1)
electrical.batteries.24v.power         - Puissance (W)
```

### Alternateur
```
electrical.alternator.output           - Sortie alternateur (W)
electrical.alternator.temperature      - Température (K)
electrical.alternator.rpm              - RPM (tr/min)
```

### Panneaux Solaires
```
electrical.solar.voltage               - Tension panneaux (V)
electrical.solar.current               - Courant panneaux (A)
electrical.solar.power                 - Puissance panneaux (W)
electrical.solar.temperature           - Température panneaux (K)
```

### Équipement Électrique
```
electrical.total.voltage               - Tension système (V)
electrical.total.current               - Courant total (A)
electrical.total.power                 - Puissance totale (W)
electrical.total.energy                - Énergie consommée (J)
```

### Victron Orion (via plugin)
```
electrical.victron.orion.input.voltage       - Tension alternateur (V)
electrical.victron.orion.input.current       - Courant entrée (A)
electrical.victron.orion.output.voltage      - Tension sortie (V)
electrical.victron.orion.output.current      - Courant sortie (A)
electrical.victron.orion.output.power        - Puissance (W)
electrical.victron.orion.temperature         - Température (°C)
electrical.victron.orion.chargeState         - État charge (OFF/BULK/ABS/FLOAT)
electrical.victron.orion.efficiency          - Efficacité (%)
```

---

## 🚤 PROPULSION (20+ paths)

### Moteur Diesel
```
propulsion.mainEngine.temperature       - Température moteur (K)
propulsion.mainEngine.rawWaterTemp      - Température eau brute (K)
propulsion.mainEngine.alternatorOutput  - Sortie alternateur (W)
propulsion.mainEngine.runTime           - Temps de marche (s)
propulsion.mainEngine.revolutions       - RPM (tr/min)
propulsion.mainEngine.fuelRate          - Consommation carburant (m³/s)
propulsion.mainEngine.oilPressure       - Pression huile (Pa)
propulsion.mainEngine.oilTemperature    - Température huile (K)
propulsion.mainEngine.crankCase         - Pression carter (Pa)
propulsion.mainEngine.load              - Charge moteur (%)
propulsion.mainEngine.torque            - Couple (Nm)
propulsion.mainEngine.power             - Puissance (W)
```

### Transmission
```
propulsion.mainEngine.controlType       - Type commande (manual, joystick, etc)
propulsion.mainEngine.state             - État moteur (stopped, started, etc)
propulsion.mainEngine.startNumber       - Nombre démarrages
```

---

## 🧭 STEERING (10+ paths)

### Gouvernail
```
steering.rudderAngle                   - Angle gouvernail (rad)
steering.rudderAngleTarget             - Angle gouvernail cible (rad)
steering.rudderPosition                - Position gouvernail (0-1)
steering.autopilot.state               - État autopilote (on/off)
steering.autopilot.mode                - Mode autopilote (compass, wind, track)
steering.autopilot.headingTrue         - Cap cible autopilote (rad)
steering.autopilot.headingMagnetic     - Cap magnétique cible (rad)
steering.autopilot.courseOverGround    - Route cible autopilote (rad)
```

---

## 🎯 PERFORMANCE (15+ paths)

### Polaires & Efficacité
```
performance.targetSpeed                - Vitesse cible (polaires) (m/s)
performance.targetVMG                  - VMG cible (m/s)
performance.velocityMadeGoodRatio      - % VMG (efficacité) (0-1)
performance.beatAngle                  - Angle optimal au près (rad)
performance.gybeAngle                  - Angle optimal vent arrière (rad)
performance.leeway                     - Dérive latérale (rad)
performance.leewayAngle                - Angle dérive (rad)
performance.layline                    - Layline vers marque (rad)
performance.etaAtWaypoint              - ETA waypoint (timestamp)
performance.currentCrewCount           - Nombre équipage
performance.heelTarget                 - Gîte cible (rad)
performance.heelOptimal                - Gîte optimale (rad)
```

---

## ⛵ SAILS (10+ paths)

### Configuration Voiles
```
sails.mainSail.area                    - Surface grand-voile (m²)
sails.mainSail.state                   - État (full, reefed, out)
sails.jibs.jib1.area                   - Surface foc 1 (m²)
sails.jibs.jib1.state                  - État foc 1
sails.jibs.jib2.area                   - Surface foc 2 (m²)
sails.jibs.jib2.state                  - État foc 2
sails.spinnaker.area                   - Surface spi (m²)
sails.spinnaker.state                  - État spi (up, ready, down)
sails.configuration                    - Configuration actuelle (texte)
sails.recommendation                   - Recommandation (texte)
```

### Sails Management (custom plugin)
```
sailing.currentMain                    - Grand-voile actuelle (FULL/1REEF/2REEF)
sailing.currentJib                     - Foc actuel (GENOA/WORKING/OUT)
sailing.currentSpinnaker               - Spi actuel (UP/READY/DOWN)
sailing.heelTarget                     - Gîte cible (rad)
sailing.recommendation                 - Recommandation texte
sailing.alerts                         - Array d'alertes voiles
```

---

## 🛢️ TANKS (20+ paths)

### Fuel Tank
```
tanks.fuel.tank1.capacity              - Capacité (m³)
tanks.fuel.tank1.currentLevel          - Niveau actuel (m³)
tanks.fuel.tank1.currentLevelPercent   - Niveau (%)
tanks.fuel.tank1.temperature           - Température (K)
tanks.fuel.tank1.pressure              - Pression (Pa)
```

### Water Tank
```
tanks.wasteWater.tank1.currentLevel    - Niveau eaux usées (m³)
tanks.wasteWater.tank1.currentLevelPercent - Niveau (%)
tanks.freshWater.tank1.currentLevel    - Niveau eau douce (m³)
```

---

## 🏗️ DESIGN (15+ paths)

### Caractéristiques Bateau
```
design.displacement                    - Déplacement (kg)
design.length                          - Longueur hors-tout (m)
design.lengthWaterLine                 - Longueur ligne d'eau (m)
design.beam                            - Largeur (m)
design.draft                           - Tirant d'eau (m)
design.draftMax                        - Tirant max (m)
design.airHeight                       - Hauteur antennes (m)
design.rigType                         - Type gréement (sloop, cutter, etc)
design.sailArea                        - Surf. voilure (m²)
design.gmLength                        - Hauteur métacentre (m)
design.gm                              - Métacentre (m)
design.powerWattRatio                  - Ratio moteur (W/kg)
design.hullSurfaceArea                 - Surface coque (m²)
```

---

## 📡 COMMUNICATION (10+ paths)

### Radio VHF
```
communication.vhf.frequency            - Fréquence VHF (Hz)
communication.vhf.txPower              - Puissance TX (W)
communication.vhf.call                 - Indicatif appel
communication.vhf.dsc.lastCall         - Dernier appel DSC
```

### AIS
```
communication.ais.version              - Version AIS
communication.ais.type                 - Type bateau AIS
communication.ais.mmsi                 - MMSI
communication.ais.callsign             - Indicatif radio
communication.ais.status               - Statut navigationnel
```

---

## 📍 RESOURCES (Variable)

### Routes
```
resources.routes.route1.bounds         - Limites route
resources.routes.route1.distance       - Distance totale (m)
resources.routes.route1.active         - Route active?
```

### Waypoints
```
resources.waypoints.waypoint1.position - Position (lat/lon)
resources.waypoints.waypoint1.distance - Distance (m)
resources.waypoints.waypoint1.bearing  - Cap (rad)
```

### Marques (Racing)
```
resources.marks.mark1.position         - Position marque (lat/lon)
resources.marks.mark1.type             - Type (start, leeward, etc)
```

---

## 🚨 NOTIFICATIONS & ALERTS

### Alertes Standard
```
notifications.navigation.positionLost  - Position perdue
notifications.navigation.anchor        - Mouillage
notifications.electrical.lowVoltage    - Tension basse
notifications.electrical.overVoltage   - Tension haute
notifications.propulsion.engineStop    - Arrêt moteur
notifications.sails.reefing            - Nécessité reef
notifications.sails.spinnaker          - Action spi
```

---

## 📊 SOURCES

Chaque path a une source indiquant d'où vient la donnée:

```
Sources possibles:
  • um982-gps.GN          GPS UM982 (GLONASS)
  • um982-gps.GP          GPS UM982 (GPS)
  • signalk-performance   Plugin performance polars
  • signalk-sails         Plugin gestion voiles
  • signalk-astronomical  Plugin astronomique
  • victron-orion-ble     Orion Bluetooth
  • victron-orion-modbus  Orion Modbus
  • nmea0183-instruments  Instruments NMEA
  • manual-input          Saisie manuelle
```

---

## 📈 Utilisation dans Grafana

### Exemples de Panels

**Panel 1: Navigation**
```
- navigation.position (map)
- navigation.courseOverGroundTrue (gauge)
- navigation.speedOverGround (gauge)
- navigation.waterDepth (gauge)
```

**Panel 2: Vent**
```
- environment.wind.speedTrue (line chart)
- environment.wind.directionTrue (gauge)
- environment.wind.speedApparent (line chart)
```

**Panel 3: Performance**
```
- performance.velocityMadeGoodRatio (gauge %)
- performance.heelOptimal vs actual (line chart)
- performance.targetSpeed (line chart)
```

**Panel 4: Électrique**
```
- electrical.batteries.12v.voltage (gauge)
- electrical.batteries.24v.current (line chart)
- electrical.total.power (area chart)
```

**Panel 5: Moteur**
```
- propulsion.mainEngine.revolutions (gauge)
- propulsion.mainEngine.temperature (gauge)
- propulsion.mainEngine.fuelRate (area chart)
```

**Panel 6: Sails**
```
- sailing.recommendation (stat)
- sailing.currentMain (stat)
- sailing.heelTarget (gauge)
```

---

## 📝 Notes Pratiques

### Unités Signal K Standard

Signal K utilise les unités SI:

```
Position:    radians (lat/lon) et mètres
Vitesse:     m/s (conversion: 1 knot = 0.51 m/s)
Angle:       radians (conversion: 1° = 0.0175 rad)
Température: Kelvin (conversion: °C = K - 273.15)
Pression:    Pa (conversion: 1 bar = 100000 Pa)
Puissance:   W (watts)
Énergie:     J (joules)
```

### Conversion Common

```
Knots → m/s:      * 0.51
m/s → Knots:      / 0.51
Degrees → rad:    * π/180
rad → Degrees:    * 180/π
K → °C:           - 273.15
°C → K:           + 273.15
```

---

## 🔍 Comment Chercher une Mesure

1. **Catégorie d'abord**: navigation? electrical? environment?
2. **Ensemble logique**: batteries.12v? wind? propulsion?
3. **Path complet**: electrical.batteries.12v.voltage

Exemple requête:
```
curl http://localhost:3000/signalk/v1/api/self/navigation/position
curl http://localhost:3000/signalk/v1/api/self/environment/wind
curl http://localhost:3000/signalk/v1/api/self/electrical/batteries/12v
```

---

## 🎓 Pour Approfondir

- **Signal K Spec:** https://signalk.org/specification/1.5.1/
- **Schema complet:** https://github.com/SignalK/signalk-schema
- **Examples:** https://signalk.org/appstore

---

**Total: ~250+ mesures disponibles dans Signal K!**

Laquelle veux-tu explorer ou utiliser pour ton prochain plugin?
