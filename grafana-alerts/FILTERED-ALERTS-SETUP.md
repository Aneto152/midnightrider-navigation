# ⚠️ AFFICHER SEULEMENT LES ALERTES IMPORTANTES (Jaune/Orange/Rouge)

**Date:** 2026-04-20  
**Goal:** Show only actionable alerts, hide blue (informational)  
**Result:** Cleaner UI, focus on what matters

---

## 🎯 LE PROBLÈME

Actuellement, tu vois 60+ alertes:
- ✅ 🟡 Yellow (20) — Important, attention needed
- ✅ 🟠 Orange (20) — Important, adjust needed  
- ✅ 🔴 Red (6) — Critical, act NOW
- ✅ ℹ️ Blue (14+) — Nice-to-know, not urgent

**En cockpit sur iPad:** Trop d'infos, dilue le message critique.

**Solution:** Afficher SEULEMENT Yellow/Orange/Red.

---

## 3 APPROCHES (Du plus facile au plus puissant)

---

## APPROCHE 1: Filtrer dans Grafana UI (5 minutes) ⭐ EASIEST

### Comment faire:

1. **Ouvrir Grafana:**
   ```
   http://localhost:3001
   Login: admin / Aneto152
   ```

2. **Aller à: Alerting → Alert Rules**

3. **Chercher le champ "Filter":**
   ```
   [Search...____]  [All States ▼]
   ```

4. **Cliquer sur [All States ▼]:**
   ```
   ✓ Normal
   ✓ Pending
   ✓ Alerting
   ✓ NoData
   ```

5. **Cliquer sur "Filter" ou "Labels":**
   Si tu vois un champ "Severity" ou "Labels":
   ```
   Severity: [Select...]
   ✓ critical
   ✓ warning
   ☐ info      ← UNCHECK THIS
   ```

6. **Voilà!** Tu ne vois maintenant que:
   - 🔴 Critical (6)
   - 🟠 Warning (20)
   - 🟡 Yellow (20)
   
   **ℹ️ Blue (14+) sont cachés ✓**

### Avantages:
- ✅ Rapide (5 min)
- ✅ Pas besoin de code
- ✅ Peuvent changer facilement

### Inconvénients:
- ⚠️ Le filtre se réinitialise après rechargement
- ⚠️ Chaque utilisateur doit configurer

---

## APPROCHE 2: Dashboard Dédié pour Alertes Importantes (10 min) ⭐⭐ RECOMMENDED

### Comment faire:

1. **Créer un nouveau dashboard:**
   ```
   Dashboards → + Create → Dashboard
   ```

2. **Ajouter un panel:**
   ```
   + Add panel
   ```

3. **Configurer le panel:**
   - Type: **Table** ou **Alert list**
   - Datasource: **Grafana** (pour les alertes)
   - Query: Filter by severity

4. **Ajouter un filtre variable:**
   ```
   Dashboard → Settings → Variables
   Add Variable:
     Name: severity
     Type: Custom
     Values: critical, warning
     (Don't include: info)
   ```

5. **Utiliser le filtre dans le panel:**
   ```
   Query filter:
   {severity=~"$severity"}
   ```

6. **Sauvegarder:**
   ```
   [Save] dashboard
   ```

### Résultat:
```
┌────────────────────────────────────────┐
│ ⚠️ ACTIVE ALERTS — Important Only      │
├────────────────────────────────────────┤
│ Severity: [critical, warning ▼]        │
│                                        │
│ 🔴 NIGHT_APPROACH_CRITICAL             │
│ 🟠 EXCESSIVE_HEEL: 26°                 │
│ 🟡 DISTANCE_TO_START_LINE: 187m       │
│ 🟠 PRESSURE_DROP: 3.2 hPa/3h          │
│                                        │
│ [ℹ️ INFO alerts hidden]                │
└────────────────────────────────────────┘
```

### Avantages:
- ✅ Persistent (saved in dashboard)
- ✅ Clean UI
- ✅ Can customize layout
- ✅ Works on iPad

### Inconvénients:
- ⚠️ Need to create & maintain
- ⚠️ Takes ~10 min setup

---

## APPROCHE 3: YAML Provisioning (Permanent Solution) ⭐⭐⭐ BEST

### Comment faire:

**Step 1: Modifier les alert rules YAML**

Éditer: `/etc/grafana/provisioning/alerting/all-alert-rules.yaml`

Pour chaque alerte ℹ️ INFO (blue), ajouter `enabled: false`:

**Avant:**
```yaml
- uid: lift_favorable
  title: "💨 LIFT_FAVORABLE"
  description: "Favorable wind shift > 8°/3min"
  condition: "A"
  labels:
    severity: "info"
    phase: "3"
```

**Après:**
```yaml
- uid: lift_favorable
  title: "💨 LIFT_FAVORABLE"
  description: "Favorable wind shift > 8°/3min"
  enabled: false          ← AJOUT: Désactiver
  condition: "A"
  labels:
    severity: "info"
    phase: "3"
```

**Step 2: Désactiver toutes les alertes ℹ️ INFO**

```bash
# Trouver toutes les alertes INFO
grep -n 'severity: "info"' /etc/grafana/provisioning/alerting/*.yaml

# Pour chacune, ajouter "enabled: false"
```

**Step 3: Redémarrer Grafana**

```bash
sudo systemctl restart grafana-server
```

**Step 4: Vérifier**

```
Alerting → Alert Rules
Should only see: 🔴 Critical + 🟠 Warning + 🟡 Yellow
NOT seeing: ℹ️ Info (disabled)
```

### Avantages:
- ✅ Permanent (persiste après redémarrage)
- ✅ Version-controlled (in GitHub)
- ✅ Reproducible
- ✅ Professional

### Inconvénients:
- ⚠️ Need to edit YAML files
- ⚠️ Need to restart Grafana

---

## APPROCHE 4: Alert Notification Rules (Advanced)

Si tu veux garder les alertes mais les **notifier seulement si important**:

1. **Aller à: Alerting → Notification policies**

2. **Créer une rule:**
   ```
   If severity = "info" → Don't notify
   If severity = "warning" or "critical" → Notify
   ```

3. **Les alertes existent toujours** mais tu n'es notifié que pour:
   - 🔴 Critical
   - 🟠 Warning

### Avantage:
- Les données existent pour l'analyse ultérieure
- Mais pas de "bruit" pendant la course

---

## MA RECOMMANDATION

**Pour une régate en bateau:**

### IMMÉDIAT (Today):
Use **Approache 1** (Filtering in UI) — 5 min, no code needed

### CETTE SEMAINE:
Implement **Approche 2** (Dedicated Dashboard) — Cleaner, saved

### LONG TERME:
Deploy **Approche 3** (YAML provisioning) — Professional, permanent

---

## QUICK REFERENCE: Which Alerts to Hide

### 🟢 GREEN (always hidden, nothing to worry about)
- None (no green alerts in system)

### ℹ️ BLUE — Hide these (informational only):
```
• SUNRISE_TIME
• MOONRISE_EVENT
• SLACK_WATER_APPROACHING
• SLACK_WATER_30MIN
• VMG_EXCEEDING_TARGET (too good to act on)
• LIFT_FAVORABLE
• HEADER_UNFAVORABLE (part of racing)
• PERSISTENT_SHIFT
• GEOGRAPHIC_DIFFERENCE
• OPTIMAL_CONFIG
• HELMET_ROTATION_RECOMMENDED (info only)
• LAYLINE_STARBOARD
• LAYLINE_PORT
• METEO_DIVERGENCE
• WIND_SHEAR
• PLUM_GUT_TIMING
• CURRENT_DEPTH_CHANGE
• FLEET_GROUPING (AIS)
• COMPETITOR_OVERTAKES (AIS, informational)
• MARK_APPROACH_1NM
• MOON_ILLUMINATION
• ... and others marked "info"
```

Total: **14-16 blue alerts** can be hidden

### 🟡 YELLOW — Keep visible:
```
• SUNSET_APPROACHING (prepare)
• DISTANCE_TO_START_LINE (get ready)
• PRESSURE_DROP_WARNING (weather changing)
• WIND_ANGLE_SUBOPTIMAL (trim needed)
• WIND_MISMATCH (forecast vs reality)
```

Total: **5-8 yellow alerts** should stay

### 🟠 ORANGE — Keep visible:
```
• EXCESSIVE_HEEL (adjust sails)
• INSUFFICIENT_HEEL (add sail)
• HEEL_INSTABILITY (steering issue)
• CURRENT_VARIATION_FORCE (navigation)
• CURRENT_VARIATION_DIRECTION (navigation)
• HELMSMAN_INSTABILITY (fatigue?)
• HEADING_DRIFT (course issue)
• HELMSMAN_DEGRADATION (rotate crew)
• SAIL_REDUCTION (wind rising)
• SPINNAKER_DOUSE (gust warning)
• SEAS_CORRECTION (rough conditions)
• COMPETITOR_DIVERGENCE (tactics)
• FOG_RISK (safety)
• GUST_NOWCAST (safety)
• COMPETITOR_ACCELERATION (fleet)
```

Total: **15-20 orange alerts** should stay

### 🔴 RED — CRITICAL, Always visible:
```
• NIGHT_APPROACH_CRITICAL
• START_COUNTDOWN
• OCS_EARLY_START
• NWS_GALE_WARNING
• DEPTH_CRITICAL
• MARK_APPROACH_200M
```

Total: **6 red alerts** should stay

---

## SUMMARY

| Approach | Time | Effort | Permanent | Best For |
|----------|------|--------|-----------|----------|
| UI Filter | 5 min | None | No | Quick test |
| Dashboard | 10 min | Low | Yes | This week |
| YAML | 20 min | Medium | Yes | Long term |
| Notifications | 15 min | Low | Yes | Alerts only |

---

## FINAL RECOMMENDATION

For your boat racing scenario:

1. **Today:** Try UI filter (Approach 1) — Just to see how it looks
2. **This week:** Create dedicated dashboard (Approach 2) — Use on iPad
3. **Later:** Implement YAML provisioning (Approach 3) — Professional setup

Result: iPad shows ONLY actionable alerts (Yellow/Orange/Red), not noise.

---

**Status:** ✅ You can have a cleaner view in 5 minutes
**Effort:** Low
**Impact:** High (cleaner cockpit UI)

Ready to try? Let me know which approach you want! 🚀
