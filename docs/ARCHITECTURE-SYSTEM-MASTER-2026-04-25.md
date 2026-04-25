# ARCHITECTURE SYSTEM — MIDNIGHT RIDER (J/30)
**Version:** 1.0-MASTER  
**Date:** 2026-04-25  
**Status:** ✅ PRODUCTION-READY for Block Island Race (May 22, 2026)

---

# ⚠️ DOCUMENT VIVANT — RÈGLE ABSOLUE

## CE DOCUMENT EST LA SINGLE SOURCE OF TRUTH

```
RÈGLE 1: TOUJOURS À JOUR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVANT toute modification du système → Lire ce document
APRÈS toute modification → Mettre à jour ce document IMMÉDIATEMENT

Un document obsolète est PIRE qu'aucun document.

CHECKLIST MISE À JOUR OBLIGATOIRE:
 □ Modèle matériel vérifié → TIER 2 HARDWARE (remplacer [À VÉRIFIER])
 □ Nouveau capteur connecté → TIER 2 + TIER 3 INTEGRATION
 □ Nouveau plugin Signal K → TIER 4 SOFTWARE
 □ Nouveau script créé → TIER 4 SOFTWARE
 □ Nouveau MCP déployé → TIER 5 MCP
 □ Architecture cloud modifiée → TIER 4 SOFTWARE
 □ Changement priorité source → TIER 2 HARDWARE
 □ Nouveau PGN vers Vulcan → TIER 3 INTEGRATION

FORMAT CORRECTION OBLIGATOIRE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CORRIGÉ LE JJ/MM/YYYY] ancienne valeur → nouvelle valeur réelle

EXEMPLE:
  Avant: "modèle : NANO-HED10L [À VÉRIFIER]"
  Après: "[CORRIGÉ LE 25/04/2026] NANO-HED10L → [MODÈLE RÉEL]"
```

---

# ⚠️ DIRECTIVE OC — VÉRIFICATION SYSTÉMATIQUE OBLIGATOIRE

```
CE DOCUMENT EST NOTRE MEILLEURE VUE À DATE DE L'ARCHITECTURE.
IL PEUT CONTENIR DES ERREURS, APPROXIMATIONS OU ÉLÉMENTS OBSOLÈTES.

RÈGLE ABSOLUE POUR OC — À APPLIQUER À CHAQUE SESSION:

1. VÉRIFIER AVANT D'AGIR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Avant d'utiliser une information comme hypothèse de travail,
vérifier par rapport à la réalité observée sur le RPi:

# Plugins Signal K réellement installés
cd ~/.signalk && npm list --depth=0 2>/dev/null | grep signalk

# Services systemd actifs
systemctl list-units --state=active | grep -E "signalk|influx|grafana|qtvlm"

# Scripts Python actifs
ls -la /home/aneto/*.py /home/aneto/*.sh /home/aneto/*.py /home/aneto/*.sh 2>/dev/null

# Ports série (GPS exact device name)
ls -la /dev/ttyUSB* /dev/ttyACM* /dev/gnss* 2>/dev/null
dmesg | grep -i usb | tail -20
udevadm info -a -p $(udevadm trigger -p /dev/ttyUSB0 -d -n 2>/dev/null | head -1) 2>/dev/null

# Paths Signal K réellement alimentés
curl -s http://localhost:3000/signalk/v1/api/vessels/self 2>/dev/null | \
  python3 -c "import json,sys; d=json.load(sys.stdin); \
  [print(f'{k}: {d[k]}') for k in sorted(d.keys())]" 2>/dev/null

# Vérifier InfluxDB et Grafana
curl -s http://localhost:8086/api/v2/health 2>/dev/null
curl -s http://localhost:3001/api/health 2>/dev/null

2. CORRIGER ET METTRE À JOUR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Si une information vérifiée diffère de ce document:
  → Corriger IMMÉDIATEMENT dans ce fichier
  → Format: [CORRIGÉ LE JJ/MM/YYYY] ancienne → nouvelle
  → Ne JAMAIS laisser une erreur connue sans corriger

3. COMPLÉTER LES [À VÉRIFIER] ET [À COMPLÉTER]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dès qu'une information manquante devient connue:
  → La remplir dans ce document
  → Changer le statut: 🔴 / 🟡 / ✅
  → Ajouter annotation [CORRIGÉ LE ...]

4. SINGLE SOURCE OF TRUTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ce document est la référence ABSOLUE de l'architecture Midnight Rider.
Tout ce qui n'y est pas documenté n'existe pas pour OC.

Toute décision d'architecture doit:
  1. Se baser sur ce document
  2. Être exécutée
  3. Mettre à jour ce document IMMÉDIATEMENT après
```

---

# 📊 ARCHITECTURE OVERVIEW

```
╔═══════════════════════════════════════════════════════════════════════╗
║                        MIDNIGHT RIDER SYSTEM                         ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  SENSORS (Boat)          PROCESSING (RPi4)      DISPLAY & OUTPUT    ║
║  ───────────────         ──────────────────     ─────────────────   ║
║                                                                       ║
║  GPS UM982              Signal K v2.25          Vulcan 7 FS (MFD)   ║
║  └─ Position    ────→   ├─ Hub + API           └─ NMEA 2000       ║
║  └─ Heading             ├─ 5 Custom Plugins                        ║
║  └─ Speed               ├─ InfluxDB → Grafana → iPad Dashboard    ║
║                         ├─ qtVLM (routing)                         ║
║  WIT IMU                └─ 7 MCP Servers (Claude AI)               ║
║  └─ Roll/Pitch   ────→                                             ║
║  └─ Acceleration        (NMEA 2000 via YDNU-02 Gateway)           ║
║                                                                       ║
║  Calypso UP10           (Optional: InfluxDB Cloud + Grafana Cloud)  ║
║  └─ Wind    ────→                                                   ║
║  └─ Temp                                                             ║
║                                                                       ║
║  NMEA 2000 Backbone                                                 ║
║  └─ Loch, AIS, Baro     ──→                                         ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

# 📚 DOCUMENTATION STRUCTURE (7 TIERS)

## TIER 0: MASTER (This File)
- ✅ **ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md** ← You are here
  - Living document rules
  - OC verification directives
  - System overview
  - Documentation index

---

## TIER 1: SYSTEM OVERVIEW
- 📄 **SYSTEM-SUMMARY.md** (1-page quick reference)
- 📄 **SYSTEM-CHECKLIST.md** (pre-race + race-day actions)

---

## TIER 2: HARDWARE DATASHEETS
Located: `/docs/HARDWARE/`

| Equipment | File | Purpose |
|-----------|------|---------|
| **Vulcan 7 FS** | VULCAN-7-FS-DATASHEET.md | B&G MFD specs + NMEA 2000 |
| **UM982 GNSS** | UM982-GNSS-DATASHEET.md | Unicore GPS specs + sentences |
| **WIT WT901BLECL** | WIT-WT901BLECL-DATASHEET.md | IMU specs + BLE protocol |
| **Calypso UP10** | CALYPSO-UP10-DATASHEET.md | Anemometer specs |
| **YDNU-02** | YDNU-02-GATEWAY-DATASHEET.md | NMEA 2000 gateway specs |
| **Raspberry Pi 4** | RASPBERRY-PI4-DATASHEET.md | Computer specs |

---

## TIER 3: INTEGRATION GUIDES
Located: `/docs/INTEGRATION/`

| Integration | File | Purpose |
|-------------|------|---------|
| **Vulcan ↔ Signal K** | VULCAN-SIGNALK-INTEGRATION.md | PGN mapping + config |
| **UM982 GPS** | UM982-INTEGRATION-GUIDE.md | Serial setup + plugin |
| **WIT IMU** | WIT-INTEGRATION-GUIDE.md | BLE setup + bleak driver |
| **Calypso Wind** | CALYPSO-INTEGRATION-GUIDE.md | BLE setup + plugin |
| **YDNU-02** | YDNU-02-INTEGRATION-GUIDE.md | NMEA 2000 gateway |

---

## TIER 4: SOFTWARE DOCUMENTATION
Located: `/docs/SOFTWARE/`

| Software | File | Purpose |
|----------|------|---------|
| **Signal K v2.25** | SIGNAL-K-CONFIGURATION.md | Setup + plugins |
| **Plugins Catalog** | PLUGINS-CATALOG.md | 5 custom plugins details |
| **Wave Analyzer v1.1** | WAVE-ANALYZER-V1.1-GUIDE.md | Heel correction algorithm |
| **Grafana** | GRAFANA-DASHBOARDS.md | 4 pre-built dashboards |
| **InfluxDB** | INFLUXDB-SETUP.md | Time-series database |

---

## TIER 5: AI INTEGRATION (MCP)
Located: `/docs/MCP/`

| Server | File | Purpose |
|--------|------|---------|
| **7 MCP Servers** | MCP-SERVERS-RECAP.md | Claude AI integration |

---

## TIER 6: OPERATIONS
Located: `/docs/OPERATIONS/`

| Checklist | File | Purpose |
|-----------|------|---------|
| **Pre-Race** | ACTION-ITEMS-2026-04-25.md | Immediate actions |
| **Field Test** | FIELD-TEST-CHECKLIST-2026-05-19.md | May 19-20 validation |
| **Race Day** | RACE-DAY-CHECKLIST-2026-05-22.md | May 22 procedures |
| **Troubleshooting** | TROUBLESHOOTING.md | Common issues + fixes |

---

## TIER 7: KNOWLEDGE BASE
Located: `/docs/MEMORY/`

| Knowledge | File | Purpose |
|-----------|------|---------|
| **Lessons Learned** | MEMORY.md | Critical insights |
| **Daily Notes** | memory/YYYY-MM-DD.md | Session logs |

---

# 🔗 QUICK LINKS

**For quick reference, see:**
- 1-page overview → `SYSTEM-SUMMARY.md`
- Pre-race checklist → `ACTION-ITEMS-2026-04-25.md`
- Hardware specs → `/docs/HARDWARE/*.md`
- Integration setup → `/docs/INTEGRATION/*.md`
- Software config → `/docs/SOFTWARE/*.md`
- Race procedures → `/docs/OPERATIONS/RACE-DAY-CHECKLIST-2026-05-22.md`

---

# ✅ STATUS

| Layer | Status | Files |
|-------|--------|-------|
| TIER 0 (Master) | ✅ Ready | 1 |
| TIER 1 (Overview) | ⏳ Creating | 2 |
| TIER 2 (Hardware) | ⏳ Creating | 6 |
| TIER 3 (Integration) | ⏳ Creating | 5 |
| TIER 4 (Software) | ⏳ Creating | 5 |
| TIER 5 (MCP) | ✅ Ready | 1 |
| TIER 6 (Operations) | ⏳ Creating | 4 |
| TIER 7 (Knowledge) | ✅ Ready | 1+ |

**Total docs:** 25+ structured files

---

# 🎯 HOW TO USE THIS STRUCTURE

1. **Quick Reference?** → Read `SYSTEM-SUMMARY.md`
2. **Before modifications?** → Check relevant TIER files
3. **Need datasheets?** → Go to `/docs/HARDWARE/`
4. **Integration issues?** → Go to `/docs/INTEGRATION/`
5. **Software config?** → Go to `/docs/SOFTWARE/`
6. **Pre-race prep?** → Go to `/docs/OPERATIONS/`
7. **Something failed?** → Check `TROUBLESHOOTING.md`

---

# 📝 MAINTENANCE LOG

| Date | Change | Who | Status |
|------|--------|-----|--------|
| 2026-04-25 | Created TIER 0 (this file) + structure | AI | ✅ DONE |
| 2026-04-25 | Creating TIER 1-7 documents | AI | ⏳ IN PROGRESS |

---

# ✍️ NEXT ACTIONS (IN PROGRESS)

- [ ] Create TIER 1: SYSTEM-SUMMARY.md + SYSTEM-CHECKLIST.md
- [ ] Create TIER 2: 6 hardware datasheets with specs
- [ ] Create TIER 3: 5 integration guides
- [ ] Create TIER 4: 5 software documentation files
- [ ] Create TIER 6: 4 operations checklists
- [ ] Verify all links work
- [ ] Final review + validation

---

**MIDNIGHT RIDER DOCUMENTATION — PROFESSIONAL STRUCTURE READY** ⛵

---

*Last updated: 2026-04-25 10:05 EDT*  
*Next review: Post-restructuring completion*
