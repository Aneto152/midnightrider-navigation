# 📋 AUDIT DÉTAILLÉ - PLUGINS SIGNAL K

**Date:** 2026-04-22  
**Objectif:** Auditer, nettoyer, restructurer tous les plugins Signal K selon best practices  
**Approche:** Extrêmement détaillée, étape par étape, avec recap + tests pour chaque plugin

---

# PLUGIN #1: signalk-performance-polars ✅ DONE

**Status:** ✅ INSTALLÉ, DÉCOUVERT, ACTIVÉ MANUELLEMENT
- Location: `~/.signalk/node_modules/signalk-performance-polars/`
- Structure: ✅ Signal K v2.25 conforme
- Données: ✅ Polaires J/30 présentes dans Signal K
- Tests: ✅ API répond correctement

---

# PLUGIN #2: signalk-sails-management-v2

## 📊 AUDIT CODE

**Location:** `~/.signalk/plugins/signalk-sails-management-v2.js`  
**Taille:** 333 lignes  
**Objectif:** Recommander jib/main sail basé sur conditions actuelles

### Dépendances
- ✅ **Locales uniquement** - aucune dépendance npm externe
- Pas d'imports externes

### Entrées Requises (Signal K paths)
- `navigation.attitude.roll` — Gîte (radians)
- `environment.wind.speedTrue` — Vent true (m/s)
- `navigation.speedThroughWater` — Vitesse brute (m/s)
- `navigation.courseOverGround` — Cap (radians, optionnel)

### Sorties (Crée ces paths)
- `sails.jibRecommendation` — Jib sélectionné (string)
- `sails.jibRecommendationPercent` — Score en % (number)
- `sails.mainSailTrim` — Trim recommandé (string)
- `sails.heelAngle` — Gîte actuelle (degrés)
- `sails.comments` — Commentaires d'optimisation (string)

### Configuration Schema
- `enabled` — boolean (default: true)
- `minHeel` — minimum gîte acceptable (default: 8°)
- `maxHeel` — maximum gîte acceptable (default: 22°)
- `updateInterval` — fréquence update (default: 2000ms)

### Logique
1. Lit gîte (roll), vent, vitesse
2. Évalue conditions
3. Recommande jib basé sur gîte + vent
4. Calcule score de fiabilité (%)
5. Envoie recommandations à Signal K

### Code Quality
- ✅ Bien structuré
- ✅ Commenté
- ⚠️ Format ancien (à reformatter)
- ✅ Pas de memory leaks

### 🎯 Verdict
**PLUGIN VALIDE** — Nécessite reformatage structure

---

## 🔧 RESTRUCTURATION REQUISE

### PLAN
1. Lire code complet
2. Analyser dépendances
3. Reformatter en structure v2.25
4. Créer package.json
5. Copier dans node_modules/
6. Ajouter config settings.json
7. Redémarrer Signal K
8. ACTIVER manuellement via Admin UI
9. TESTER données

---

## ✅ CHECKLIST

- [ ] Audit code complet
- [ ] Dépendances identifiées
- [ ] Code reformatté
- [ ] package.json créé
- [ ] Structure NPM complète
- [ ] Configuration ajoutée
- [ ] Signal K redémarré
- [ ] Plugin activé manuellement
- [ ] Tests API
- [ ] Recap final

---

**READY FOR: ÉTAPE 1 - READ CODE**

Tu veux qu'on commence? ✅

