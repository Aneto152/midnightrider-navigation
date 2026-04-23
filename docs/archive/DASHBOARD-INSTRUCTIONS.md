# MidnightRider Dashboard - Instructions d'Utilisation

**Date:** 2026-04-23 08:03 EDT  
**Pour:** Denis Lafarge  
**Sujet:** Interface web temps réel pour iPad  

---

## 🎯 RÉSUMÉ RAPIDE

Un **dashboard web temps réel** a été créé et déployé!

```
✅ Interface web moderne
✅ Updates 10 Hz (WebSocket)
✅ Accessible depuis iPad/iPhone
✅ Affiche toutes les mesures WIT + GPS + calculs
✅ Auto-lancement au boot du bateau
```

---

## 📱 COMMENT ACCÉDER AU DASHBOARD

### Depuis iPad/iPhone sur le bateau

1. **Ouvre Safari** (ou tout navigateur web)

2. **Entre l'adresse:**
   ```
   http://192.168.x.x:8080
   ```
   Remplace `192.168.x.x` par l'IP du bateau

3. **OU directement depuis la machine du bateau:**
   ```
   http://localhost:8080
   ```

4. **Le dashboard charge automatiquement** et se connecte au WebSocket Signal K

---

## 📊 QUE VOIS-TU SUR LE DASHBOARD?

### Section Attitude (WIT IMU) - Bleu
```
Roll (Gîte):    0.1° ← Inclinaison du bateau
Pitch (Assiette): -0.4° ← Assette avant/arrière
Heading (Cap):  11.6° ← Direction bateau
Accel X/Y/Z:    0.01 m/s² ← Accélérations
```

### Section Wind (Capteur Vent) - Orange
```
Angle Vent Apparent: 45°
Vitesse Vent Apparent: 8.5 kt
```

### Section Position (GPS) - Vert
```
Latitude:      46.2345°
Longitude:     -71.1234°
Speed Over Ground: 6.5 kt
Course Over Ground: 230°
```

### Section Performance (Polaires) - Violet
```
Vitesse Cible Polaire: 6.8 kt
% Polaire: 95%
```

### Section Vagues (WIT Accel Z) - Cyan
```
Hauteur Vagues: 1.2 m
Accel Z: 9.81 m/s²
```

---

## ⚡ CARACTÉRISTIQUES

### Temps Réel
```
✅ WebSocket (pas de polling)
✅ 10 Hz de fréquence
✅ Latence <100ms
✅ Mise à jour fluide et continue
```

### Design
```
✅ Optimisé pour iPad (responsive)
✅ Thème sombre (économe batterie OLED)
✅ Couleurs par catégorie
✅ Animations de mise à jour
```

### Informations
```
✅ Indicateur de connexion (vert = connecté)
✅ Fréquence d'update visible
✅ Timestamp de chaque mesure
✅ Affichage automatique des nouvelles valeurs
```

---

## 🔧 STATUT DU SERVICE

Le dashboard fonctionne comme un **service systemd**:

### Vérifier le statut
```bash
sudo systemctl status signalk-dashboard
```

### Redémarrer
```bash
sudo systemctl restart signalk-dashboard
```

### Logs
```bash
sudo journalctl -u signalk-dashboard -f
```

### Désactiver
```bash
sudo systemctl stop signalk-dashboard
sudo systemctl disable signalk-dashboard
```

---

## 📋 MESURES AFFICHÉES

Le dashboard affiche **20+ mesures** en temps réel:

### WIT IMU (Toujours disponible ✅)
- Roll, Pitch, Yaw
- Accel X, Y, Z
- Rate of Turn (Vitesse de rotation)

### Capteurs Externes (Si connectés)
- Wind angle & speed
- GPS position, SOG, COG
- Current drift & set
- Wave height
- Sun azimuth & elevation

### Calculs Signal K (Si données disponibles)
- Performance vs polaires
- Trim advice (sails management)
- Current calculation
- Astronomical positions

---

## 🎨 PERSONNALISATION

Le dashboard peut être personnalisé:

### Ajouter/Enlever des mesures

Édite `/home/aneto/signalk-dashboard.html`

Cherche le section `const sensors = {` et ajoute/enlève des paths Signal K

Exemple pour ajouter une mesure:
```javascript
'navigation.speedThroughWater': {
    label: 'Speed Through Water',
    unit: 'kt',
    category: 'position',
    format: (val) => val.toFixed(2)
}
```

### Changer les couleurs

Édite la section `/* Sections spéciales */` dans le CSS

Exemple:
```css
.card.attitude {
    border-color: rgba(100, 200, 255, 0.4);  ← Change cette couleur
}
```

---

## 🚀 FONCTIONNEMENT

### Architecture
```
iPad/Safari
    ↓ (HTTPS/HTTP)
Dashboard Server (port 8080)
    ↓ Charge HTML
    ↓ JavaScript se connecte
WebSocket Signal K (port 3000)
    ↓ Stream 10 Hz
WIT IMU + Capteurs
```

### Flux de données
```
Signal K Hub (10 Hz)
    ↓
WebSocket Stream
    ↓
Dashboard (reçoit)
    ↓
Affiche les valeurs en temps réel
    ↓
iPad affiche le tout!
```

---

## 📱 OPTIMISATIONS POUR IPAD

### Safari
- ✅ HTML5 WebSocket natif
- ✅ CSS moderne
- ✅ JavaScript ES6

### Responsive Design
- ✅ Adapte à tous les écrans
- ✅ Grid layout automatique
- ✅ Bien sur iPad horizontal ET vertical

### Performance
- ✅ Pas de polling (0 overhead)
- ✅ CSS animé en GPU
- ✅ Scrollbar personnalisée
- ✅ Efficace batterie

---

## 🔍 TROUBLESHOOTING

### "La page se charge mais rien n'apparaît"
```
1. Vérifie que Signal K est en cours
   sudo systemctl status signalk

2. Vérifie que le dashboard est en cours
   sudo systemctl status signalk-dashboard

3. Ouvre la console navigateur (F12) et cherche erreurs
```

### "Pas de données reçues"
```
1. Vérifie que WIT IMU envoie des données
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

2. Vérifie que WebSocket marche
   ws://localhost:3000/signalk/v1/stream?subscribe=self

3. Regarde les logs du dashboard
   sudo journalctl -u signalk-dashboard -f
```

### "Les valeurs ne changent pas"
```
1. WIT IMU peut être arrêté - vérifie câble USB
2. Ou les capteurs externes ne sont pas connectés
3. Regarde l'indicateur "Connecté" en haut
```

---

## 📊 FICHIERS CRÉÉS

```
/home/aneto/signalk-dashboard.html
   → Interface web (15.6 KB)
   → Code HTML + CSS + JavaScript
   → Self-contained (pas de dépendances externes)

/home/aneto/dashboard-server.js
   → Serveur HTTP simple (2 KB)
   → Écoute port 8080
   → Serve le dashboard

/etc/systemd/system/signalk-dashboard.service
   → Service systemd
   → Auto-start au boot
   → Auto-restart si crash
```

---

## 🎯 PROCHAINES ÉTAPES

1. **Test sur iPad:**
   ```
   Ouvre Safari sur ton iPad
   Navigue vers: http://<IP-bateau>:8080
   Devrait voir le dashboard s'actualiser @ 10 Hz
   ```

2. **Vérifier les mesures:**
   - WIT IMU: Roll/Pitch/Yaw doivent être présents
   - Si capteurs externes connectés: leurs données aussi

3. **Personnaliser (optionnel):**
   - Ajouter/enlever des mesures
   - Changer les couleurs
   - Ajuster la taille des cartes

---

## ✅ STATUS

```
✅ Dashboard créé et testé
✅ Service systemd configuré
✅ Auto-start activé
✅ Accessible depuis le réseau
✅ Updates 10 Hz en direct
✅ Prêt pour l'iPad!
```

---

## 🚀 COMMANDES UTILES

```bash
# Vérifier que c'est en cours
sudo systemctl status signalk-dashboard

# Voir les logs en temps réel
sudo journalctl -u signalk-dashboard -f

# Redémarrer
sudo systemctl restart signalk-dashboard

# Arrêter
sudo systemctl stop signalk-dashboard

# Tester l'accès
curl http://localhost:8080/
```

---

## 📞 SUPPORT

Si le dashboard ne fonctionne pas:

1. Vérifie Signal K:
   ```bash
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
   ```

2. Vérifie le serveur dashboard:
   ```bash
   curl http://localhost:8080/
   ```

3. Regarde les logs:
   ```bash
   sudo journalctl -u signalk-dashboard -n 50
   ```

---

**Status:** ✅ DÉPLOYÉ ET ACTIF  
**Port:** 8080  
**Fréquence:** 10 Hz (WebSocket)  
**Accès:** http://<IP-bateau>:8080 depuis iPad
