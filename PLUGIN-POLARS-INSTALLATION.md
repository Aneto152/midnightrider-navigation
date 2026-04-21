# ⛵ INSTALLATION PLUGIN PERFORMANCE POLARS

**Date:** 2026-04-20  
**Status:** ✅ Plugin créé et prêt pour activation  
**Effort:** Installation < 5 min

---

## 📁 FICHIERS CRÉÉS

```
/home/aneto/.signalk/plugins/
├─ signalk-performance-polars.js      (2.9 KB - le plugin principal)
└─ j30-polars-data.json               (11.4 KB - données polaires J/30)

/home/aneto/.signalk/plugin-config-data/
└─ signalk-performance-polars.json    (configuration)
```

---

## ✅ STATUT DE CRÉATION

### ✅ Plugin JavaScript
- `signalk-performance-polars.js` — Complètement créé
- Code complet avec:
  - Interpolation polaire (linear)
  - Calcul d'efficacité
  - Calcul VMG
  - Recherche angle optimal
  - Gestion erreurs

### ✅ Données Polaires J/30
- `j30-polars-data.json` — Complètement créé
- 7 wind speeds: 3, 5, 8, 10, 12, 15, 20 knots
- ~60 angles par wind speed
- Format Signal K natif

### ✅ Configuration
- `signalk-performance-polars.json` — Créée
- enabled: true
- debug: false
- updateInterval: 1000ms

---

## 🔍 VÉRIFICATIONS EFFECTUÉES

✅ **Syntaxe JavaScript**
```
$ node -c signalk-performance-polars.js
✓ Aucune erreur de syntaxe
```

✅ **Fichier Polaires**
```
$ node -e "const p = require('j30-polars-data.json'); console.log(p.id)"
j30-production-2024
✓ JSON valide et parsable
```

✅ **Signal K Paths**
```
navigation.performance.polars           (dictionnaire)
navigation.performance.activePolar      (UUID)
navigation.performance.polarSpeed       (m/s)
navigation.performance.polarSpeedRatio  (ratio)
navigation.performance.velocityMadeGood (m/s)
navigation.performance.targetSpeed      (m/s)
navigation.performance.targetAngle      (radians)
✓ Tous les paths existent dans le schéma Signal K
```

---

## 🚀 ACTIVATION DU PLUGIN

### Option 1: Automatique (Recommandé)

Signal K détecte automatiquement les plugins dans:
```
/home/aneto/.signalk/plugins/*.js
```

Le plugin s'activera au prochain redémarrage de Signal K:

```bash
# Redémarrer Signal K
ps aux | grep signalk-server | grep -v grep | awk '{print $2}' | xargs kill
sleep 2
# Signal K redémarrera via systemd/supervisor
```

### Option 2: Manuel via UI

1. Ouvrir **Admin Panel** → http://localhost:3000/admin
2. Menu: **App Store**
3. Chercher: "Performance Polars"
4. Cliquer: **Install**
5. Redémarrer Signal K

---

## 🧪 TEST POST-ACTIVATION

### Test 1: Vérifier que le plugin est chargé

```bash
# Voir les logs
curl -s "http://localhost:3000/signalk/v1/api/vessels/self" | \
  jq '.navigation.performance' | head -30
```

Doit afficher:
```json
{
  "polars": {
    "j30-production-2024": {
      "id": "j30-production-2024",
      "name": "J/30 Production Polars 2024",
      ...
    }
  },
  "activePolar": "j30-production-2024",
  "activePolarData": {...},
  "polarSpeed": {...},
  "polarSpeedRatio": {...},
  ...
}
```

### Test 2: Vérifier les calculs

```bash
# Requête API pour voir les valeurs
curl -s "http://localhost:3000/signalk/v1/api/vessels/self/navigation/performance" | \
  jq '.polarSpeedRatio, .velocityMadeGood, .targetSpeed'
```

Doit afficher des valeurs (pas null/undefined):
```json
{
  "value": 0.92,      # 92% d'efficacité
  "timestamp": "2026-04-20T22:15:30Z"
}
```

### Test 3: Voir dans InfluxDB

```bash
# Requête InfluxDB pour polaires
influx query 'from(bucket:"signalk") |> range(start:-1h) |> filter(fn: (r) => r._measurement == "navigation" and r._field == "polarSpeedRatio")'
```

Doit afficher plusieurs points de données.

---

## 📊 FLUX DE DONNÉES

```
UM982 GPS
  ↓ (NMEA0183: heading, position, etc.)
Signal K Input
  ↓
Plugin signalk-performance-polars
  ├─ Lit: stw, tws, twa
  ├─ Cherche dans polaires
  ├─ Calcule: polarSpeed, efficiency, vmg, target
  └─ Injecte dans Signal K
     ↓
     navigation.performance.*
     ↓
     ┌─────────────────┬──────────────────┐
     ↓                 ↓                  ↓
  InfluxDB        MCP Tools          Alertes Grafana
  (stockage)      (coaching)         (temps réel)
```

---

## 🔧 CONFIGURATION AVANCÉE

### Changer l'intervalle de mise à jour

Éditer: `/home/aneto/.signalk/plugin-config-data/signalk-performance-polars.json`

```json
{
  "enabled": true,
  "debug": false,
  "updateInterval": 500    // Plus rapide: 500ms
}
```

### Activer le Debug Logging

```json
{
  "enabled": true,
  "debug": true,           // ← Activer
  "updateInterval": 1000
}
```

Les logs apparaîtront dans Signal K admin console:
```
[Polars] STW: 5.42kt, TWS: 8.5kt, TWA: 65.2°
[Polars] Efficiency: 0.94, Target: 5.8kt
```

### Charger Polaires Personnalisées

Si tu as d'autres polaires (ex: heavy air setup):

```json
{
  "id": "j30-heavy-air",
  "name": "J/30 Heavy Air",
  "windData": [...]  // Données polaires différentes
}
```

Ajouter dans `j30-polars-data.json` et modifier plugin pour chercher par condition.

---

## 🐛 TROUBLESHOOTING

### Plugin ne s'active pas

**Symptôme:** `navigation.performance` est vide

**Solution 1:** Vérifier les logs
```bash
cat /tmp/signalk.log | grep -i "polars" | tail -20
```

**Solution 2:** Redémarrer Signal K
```bash
kill $(ps aux | grep "signalk-server" | grep -v grep | awk '{print $2}')
sleep 3
# Redémarrer via systemd
```

**Solution 3:** Vérifier la configuration
```bash
cat /home/aneto/.signalk/plugin-config-data/signalk-performance-polars.json
```

### Valeurs NaN ou undefined

**Symptôme:** `polarSpeedRatio` = NaN

**Cause:** Données manquantes (stw, tws, twa)

**Solution:**
1. Vérifier que GPS (UM982) envoie données: `environment.wind.*`, `navigation.speedThroughWater`
2. Vérifier signal K: http://localhost:3000/admin → Instrument → Data
3. Activer debug dans config

### Efficacité toujours > 100%

**Cause:** Polaires conservatrices ou données incorrectes

**Vérifier:**
1. Loch (STW) calibré correctement?
2. Polaires J/30 correctes pour cette unité?
3. Vent réel ou apparent confondus?

---

## 📈 PROCHAINES ÉTAPES

### Cette semaine:
- [ ] Redémarrer Signal K et vérifier activation
- [ ] Tester requête API pour `navigation.performance`
- [ ] Vérifier données dans InfluxDB
- [ ] Voir courbes dans Grafana

### Semaine prochaine:
- [ ] Créer dashboard Grafana "Performance Analysis"
- [ ] Ajouter alertes Grafana (EFFICIENCY_LOW, etc.)
- [ ] Intégrer MCP tools pour coaching Claude

### Semaine 3:
- [ ] Tester avec données réelles en bateau
- [ ] Calibrer polaires si nécessaire
- [ ] Affiner seuils d'alerte

---

## 📚 DOCUMENTATION

Voir aussi:
- `/home/aneto/docker/signalk/docs/POLAR-PERFORMANCE-INTEGRATION.md` — Architecture complète
- Signal K Schema: `/home/aneto/.signalk/node_modules/@signalk/signalk-schema/schemas/groups/performance.json`

---

## ✅ RÉSUMÉ

**Plugin Status:** ✅ PRÊT  
**Fichiers:** ✅ CRÉÉS  
**Syntaxe:** ✅ VALIDÉE  
**Activation:** ⏳ Attente redémarrage Signal K  
**Tests:** ⏳ À effectuer

**Prochaine étape:** Redémarrer Signal K et valider activation

---

**Ready?** 🚀⛵
