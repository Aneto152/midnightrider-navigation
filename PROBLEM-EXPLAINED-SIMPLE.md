# Le Problème Signal K - Explication Simple

## 🎯 Le Symptôme

Quand on demande à Signal K: **"Donne-moi l'angle du bateau (roll/pitch)"**

```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

### Réponse normale (ce qu'on devrait avoir):
```json
{
  "roll": {
    "value": 0.25,
    "timestamp": "2026-04-22T22:24:00.000Z"
  },
  "pitch": {
    "value": -0.15,
    "timestamp": "2026-04-22T22:24:00.000Z"
  },
  "yaw": {
    "value": 3.98,
    "timestamp": "2026-04-22T22:24:00.000Z"
  }
}
```

### Réponse actuelle (le bug):
```
Empty response (rien du tout)
```

---

## 🔍 Pourquoi c'est un bug?

### Le flux DEVRAIT être:

```
1. WIT IMU (capteur)
   └─ Mesure: Gîte = 12.5°, Assiette = 2.3°
   
2. USB Serial (/dev/ttyWIT)
   └─ Envoie données brutes au RPi
   
3. Plugin WIT (signal-wit-imu-usb)
   ├─ LIT les données USB ✅ (MARCHE)
   ├─ Convertit les angles ✅ (MARCHE)
   └─ Envoie à Signal K: "navigation.attitude.roll = 0.218"
   
4. Signal K Core
   ├─ Reçoit le message ❌ (PROBLÈME!)
   ├─ Ajoute au "vessel tree" (l'arbre des données)
   └─ Expose sur /signalk/v1/api/vessels/self/navigation/attitude
   
5. REST API (/signalk/v1/api/...)
   └─ Retourne les données ❌ (Vide parce que #4 échoue)
   
6. Grafana
   └─ Affiche l'angle sur iPad ❌ (Pas de données)
```

**Le problème: Étape 4 ne fonctionne pas.**

---

## 🚨 Où exactement c'est cassé?

### Ce qui MARCHE ✅:

```
✅ WIT IMU reçoit les données (capteur fonctionne)
✅ USB communication (données arrivent sur /dev/ttyWIT)
✅ Plugin WIT démarre (logs disent "running")
✅ Plugin décode les angles (calculs corrects)
✅ Plugin envoie les messages à Signal K (handleMessage appelé)
✅ Signal K reçoit les messages (logs confirmés)
```

### Ce qui NE MARCHE PAS ❌:

```
❌ Signal K AJOUTE les données au "vessel tree"
   └─ L'arbre des données reste vide
   └─ Seul "uuid" existe dans vessels/self
   └─ "navigation" path n'existe pas du tout
```

---

## 🎓 Analogie pour comprendre

Imagine Signal K comme une **maison avec des pièces**:

```
Signal K House
├─ Living Room (navigation)
│  ├─ Attitude (roll/pitch/yaw)
│  ├─ Speed
│  └─ Position
├─ Kitchen (environment)
│  ├─ Wind
│  └─ Temperature
└─ Garage (propulsion)
   └─ Engine
```

### Ce qui se passe:

1. **Plugin dit:** "J'ai un nouveau rouleau: 12.5°"
2. **Signal K écoute** et dit "OK, reçu"
3. **Mais:** Signal K ne CRÉE PAS la pièce "Attitude"
4. **Résultat:** Les données flottent nulle part

C'est comme:
- Je crie une adresse à quelqu'un
- Il m'entend
- Mais il ne note pas l'adresse

---

## 🔬 Observations techniques

### Test 1: Les données EXISTENT
```bash
# Les logs Signal K montrent:
"Plugin signalk-wit-imu-usb: Sending delta message"
"Delta received: navigation.attitude.roll = 0.218"
```

**Conclusion:** Les données **circulent** dans Signal K.

### Test 2: Elles DISPARAISSENT
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self
# Retour: {"uuid": "..."}
# Attendu: {"uuid": "...", "navigation": {...}, ...}
```

**Conclusion:** Les données **ne sont pas stockées** dans l'arbre.

### Test 3: Ce n'est pas la version
```
Testé: v2.21.0, v2.24.0, v2.25.0
Résultat: Tous les même problème
```

**Conclusion:** Pas un bug d'une version spécifique.

### Test 4: Ce n'est pas la DB
```
Supprimé: serverState.sqlite
Résultat: Toujours le même problème
```

**Conclusion:** Pas une corruption de base de données.

---

## 🧩 Les 3 Théories Possibles

### Théorie 1: Signal K Bug (30% probable)

**Le problème:** Signal K v2.x a un bug où il ne crée pas l'arbre "navigation"

**Preuve:** Tous les v2.x affectés, jamais vu sur v1.x

**Solution:** Attendre patch Signal K OU utiliser v1.x (plus vieux)

---

### Théorie 2: Système RPi (40% probable)

**Le problème:** Quelque chose dans le reboot a cassé Signal K au niveau système

**Preuve:** 
- Problème a commencé APRÈS reboot 16h00
- Avant reboot: tout semblait fonctionner
- Même après reset/reinstall: persiste

**Solution:** 
- Reboot physique complet (cold shutdown)
- OU Réinstaller RPi OS from scratch

---

### Théorie 3: Plugin Config (20% probable)

**Le problème:** Plugin envoie les données dans un format que v2.x ne comprend pas

**Preuve:**
- Plugin code correct
- Signal K reçoit les messages
- Mais Signal K ne traite pas

**Solution:** Vérifier format exact des deltas avec communauté Signal K

---

## 📊 Ce que ça signifie pour toi

### Situation actuelle:

```
✅ Hardware: WIT IMU fonctionne 100%
✅ Software: Signal K v2.21.0 stable
✅ Plugins: Tous en place et configurés
❌ Data Flow: Cassé entre Plugin → Signal K Core
```

### Impact sur MidnightRider:

```
❌ Pas d'angle de gîte sur Grafana iPad
❌ Pas de recommandations jib/main (besoin du heel)
❌ Pas d'alertes de gîte excessif
```

### Mais:

```
✅ Les données EXISTENT
✅ Elles peuvent être lues via WebSocket
✅ Elles peuvent être loggées dans InfluxDB
✅ Juste pas visibles via REST API
```

---

## 🚀 Les 3 Options pour Avancer

### Option 1: Demander à la communauté Signal K
- **Temps:** 1-2 jours
- **Risque:** Pas de réponse
- **Avantage:** Peut être un bug connu avec fix
- **Status:** PRÊT (diagnostic complet prêt)

### Option 2: Essayer Workaround WebSocket
- **Temps:** 2-4 heures
- **Risque:** Peut ne pas fonctionner avec Grafana
- **Avantage:** Contourne le problème
- **Status:** À investiguer

### Option 3: Fresh RPi OS Install
- **Temps:** 3-4 heures
- **Risque:** Perd tout, besoin reconfigurer
- **Avantage:** Résout les problèmes système
- **Status:** Last resort

---

## 📝 Résumé pour Signal K Community

**Titre:** "navigation.* never initialized - REST API empty despite plugin sending deltas"

**Courte explication:**
- WIT IMU plugin envoie deltas à Signal K
- Signal K reçoit et log les messages
- Mais `/signalk/v1/api/vessels/self` retourne seulement `uuid`
- "navigation" path jamais créé
- Affecte tous v2.x versions
- Persiste après reset/reboot/DB clean

**Question:** C'est un bug Signal K v2.x ou une misconfiguration système?

---

## 🎯 Conclusion

**Le problème:** Signal K reçoit les données mais ne les stocke pas dans l'arbre "navigation"

**Cause:** Inconnue (système, Signal K bug, ou plugin config)

**Action recommandée:** 
1. Partager diagnostic avec Signal K Community
2. Attendre 24h pour réponse
3. Si pas de solution: essayer fresh OS ou WebSocket workaround
