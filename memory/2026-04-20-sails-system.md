# Système de Gestion des Voiles (2026-04-20)

## 📋 Réponse à la Question

**Question:** Est-ce qu'il y a un plugin pour aussi le choix des voiles en fonction de l'allure, du vent et de l'état de la mer ?

**Réponse:** 
- ✅ **Alertes partielles** — Déjà déployées dans les 60+ alertes Grafana (8 alertes voiles)
- ⏳ **Système complet** — En design, prêt pour implémentation

---

## 🎯 Système Proposé: signalk-sails-management

### Inputs

```
Données temps réel du bateau:
  • TWS (True Wind Speed) — Force vent vrai
  • TWA (True Wind Angle) — Angle par rapport vent
  • Heel, Pitch, Roll — Attitudes du bateau
  • Efficiency — Performance vs polaires
```

### Processing

```
5 étapes logiques:
  1. Classifier le vent (light/medium/fresh/strong/gale)
  2. Analyser l'allure (beating/reach/running)
  3. Évaluer état de la mer (pitch, roll, waves)
  4. Vérifier gîte (heel target vs actual)
  5. Recommander config (main + jib + spinnaker)
```

### Outputs

```
Recommandations:
  • Main sail: Full | 1Reef | 2Reef | Trysail | Down
  • Jib: Full | Genoa | Working | Storm | Out | Down
  • Spinnaker: Up | Ready | Down
  • Heel target: 12-22° selon condition
  • Raison du changement
```

---

## 📊 Matrice Décisionnelle

### Beating (Au près, TWA < 45°)

| Wind | Light | Light Air | Medium | Fresh | Strong | Gale |
|------|-------|-----------|--------|-------|--------|------|
| Main | Full | Full | Full | 1Reef | 2Reef | 2Reef |
| Jib | Genoa | Full | Working | Working | Working | Storm |
| Target | 12° | 14° | 16° | 18° | 20° | 22° |

### Reaching (Largue, 45° < TWA < 120°)

| Wind | Light | Light Air | Medium | Fresh | Strong | Gale |
|------|-------|-----------|--------|-------|--------|------|
| Main | Full | Full | Full | Full | 1Reef | 2Reef |
| Jib | Genoa | Genoa | Working | Working | Working | Working |
| Target | 15° | 16° | 18° | 20° | 22° | 20° |

### Running (Vent arrière, TWA > 160°)

| Wind | Light | Light Air | Medium | Fresh | Strong | Gale |
|------|-------|-----------|--------|-------|--------|------|
| Main | Full | Full | Full | Full | 1Reef | Down |
| Jib | Out | Out | Out | Out | Poled | Poled |
| Spi | Up | Up | Ready | Down | Down | Down |

---

## 🚨 Alertes Existantes (8 alertes déployées)

### Phase 2 (Hardware-dependent)

1. **SAIL_CONFIG** — Configuration change
   - Severity: INFO
   - Trigger: Allure ou vent change
   - Action: Adjust sails

2. **SAIL_REDUCTION** — Réduire toile
   - Severity: WARNING/CRITICAL
   - Trigger: Heel > 22°
   - Action: REEF_MAIN or FURL_JIB

3. **SAIL_INCREASE** — Augmenter toile
   - Severity: INFO/CAUTION
   - Trigger: Efficiency < 85% AND wind < 16kt
   - Action: INCREASE_SAIL

4. **SPINNAKER_UP** — Lever spinnaker
   - Severity: INFO
   - Trigger: TWA > 120° AND TWS < 16kt
   - Action: RAISE_SPINNAKER

5. **SPINNAKER_DOWN** — Dépouiller spinnaker
   - Severity: CAUTION/WARNING
   - Trigger: Gusts > 18kt OR instability
   - Action: PREPARE_TO_DOUSE

6. **REEF_MAIN** — Réduire grand voile
   - Severity: CAUTION/WARNING
   - Trigger: TWS > 14kt sustained
   - Action: REEF_1 or REEF_2

7. **UNREEF** — Agrandir grand voile
   - Severity: INFO
   - Trigger: TWS < 10kt sustained
   - Action: UNREEF

8. **SAIL_OPTIMAL** — Configuration optimale
   - Severity: INFO
   - Trigger: Heel ±2° AND Efficiency > 92%
   - Message: Sailing optimally

---

## 🎯 Cas d'Usage Réels

### Cas 1: Crise de Vent

```
Avant: TWS 10kt, Heel 16° ✓
Soudain: Rafale 22kt, Heel 25°! ❌

Alerte: SAIL_REDUCTION (critical)
Message: "Heel 25°. Reef main now!"
Action: Crew reefs main
Résultat: Heel → 18° ✓
```

### Cas 2: Air Léger

```
TWS 5kt, Full main + Working jib
Efficiency: 0.82 (low)

Alerte: SAIL_INCREASE (info)
Message: "Light air. Genoa = +0.3kt VMG"
Action: Crew switches to Genoa
Résultat: Efficiency → 0.92, VMG +0.3kt ✓
```

### Cas 3: Changement Allure

```
TWA: 50° → 140° (beating → broad reach)
Current config: beating (main full + working jib)

Alerte: SAIL_CONFIG (info)
Message: "Now reaching. Ease main, jib out."
Action: Crew adjusts
Résultat: Optimal reach configuration ✓
```

### Cas 4: Spinnaker Opportunity

```
TWA 170°, TWS 8kt stable
Current: Main + jib out

Alerte: SPINNAKER_UP (info)
Message: "Downwind light. Spinnaker = faster."
Action: Crew raises spinnaker
Résultat: Speed boost (if crew confident) ✓
```

---

## 🔧 Approches Implémentation

### Option 1: Plugin Signal K ⭐ Recommandé

```
signalk-sails-management.js
  ├─ Lit: TWS, TWA, Heel, Pitch, Roll, Efficiency
  ├─ Classifie conditions
  ├─ Lookup decision matrix
  └─ Injecte recommendations + alerts dans Signal K
     ↓
     → InfluxDB (stockage)
     → Grafana (dashboards)
     → MCP Tools (coaching)
     → Alertes temps réel
```

**Avantages:**
- ✓ Real-time (2 sec updates)
- ✓ Continuous monitoring
- ✓ Feeds all downstream systems
- ✓ Native Signal K integration

**Effort:** 6-8 heures

### Option 2: MCP Tool (Standalone)

```
Claude: "What sails should I have?"
  → MPC tool analyzes conditions
  → Returns recommendation + reasoning
  → Interactive (can ask follow-ups)
```

**Avantages:**
- ✓ Interactive coaching
- ✓ Human-in-loop
- ✓ No Signal K changes

**Inconvénient:**
- ✗ Not continuous
- ✗ Only when asked

### Option 3: Both ✅ (Recommandé)

```
Plugin (continuous) + MCP tool (interactive)
  → Complete system!
```

---

## 📈 Architecture Système Complet

```
Signal K inputs (1 Hz)
  ↓ (TWS, TWA, Heel, Pitch, Roll, Efficiency)
Plugin signalk-sails-management
  ├─ Classify wind
  ├─ Analyze tack
  ├─ Evaluate sea state
  ├─ Check heel
  └─ Recommend sails
     ↓
     navigation.sailing.currentConfig
     navigation.sailing.recommendedConfig
     navigation.sailing.alerts
     ↓
     ┌─────────────────────┬──────────────┐
     ↓                     ↓              ↓
  InfluxDB           Grafana (UI)    MCP Tools
  (24h+ storage)    (dashboards)    (coaching)
                    (alerts)        (interactive)
```

---

## 📚 Documentation Complète

**File:** `/home/aneto/docker/signalk/docs/SAILS-MANAGEMENT-SYSTEM.md` (14.6 KB)

Contient:
- Tableau complet configurations
- Matrice décisionnelle complète
- Code plugin sketch
- Cas d'usage détaillés
- Signal K paths
- Grafana specs
- Test procedures
- Roadmap implémentation

---

## 🎯 Roadmap Implémentation

### Cette Semaine (2h)
- [ ] Étudier système existant
- [ ] Identifier points manquants
- [ ] Design logique complète

### Semaine 2 (6h)
- [ ] Créer plugin JavaScript
- [ ] Implémenter classifiers
- [ ] Tester avec cas simples

### Semaine 3 (3h)
- [ ] Intégrer MCP tools
- [ ] Créer Grafana dashboard
- [ ] Tester avec données réelles

### Semaine 4 (2h)
- [ ] Feedback équipage
- [ ] Ajuster seuils
- [ ] Production deployment

**TOTAL:** 13 heures spread over 4 weeks

---

## ✅ Status Final

**Alertes Voiles:**
- ✅ 8 alertes déployées dans Grafana
- ✅ Phase 2 hardware-dependent
- ✅ Prêtes pour bateau

**Système Complet:**
- ⏳ Architecture documentée
- ⏳ Matrice décisionnelle complète
- ⏳ Code sketch prêt
- ⏳ Prêt pour implémentation

**Prochaine Étape:**
- → Créer plugin signalk-sails-management.js
- → Déployer à Signal K
- → Tester avec conditions réelles

---

## 📝 Notes

### Voiles J/30 Disponibles

| Voile | Taille | Usage |
|-------|--------|-------|
| Mainsail | 200 sq ft | All conditions |
| Genoa | 180 sq ft | Light air (< 12kt) |
| Working Jib | 120 sq ft | Medium-fresh (7-18kt) |
| Storm Jib | 60 sq ft | Strong-gale (16-25kt) |
| Spinnaker | 250 sq ft | Downwind light-med (< 18kt) |

### Seuils Sécurité

| Paramètre | Limite | Action |
|-----------|--------|--------|
| Heel | 22° | Alerte reduction |
| Heel | 25° | Critical alert |
| Pitch | 20° | Reduce sail |
| Roll | 25° | Reduce sail |
| Gusts | 18kt | Spinnaker down alert |

---

**Status:** ✅ Conçu, documenté, prêt pour build  
**Effort:** 13h total (4 weeks)  
**Impact:** Intelligent real-time sail management  
**Next:** Start plugin development

Ready to build! 🚀⛵
