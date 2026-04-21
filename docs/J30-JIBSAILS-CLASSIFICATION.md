# J/30 Jib Classification — J1, J2, J3, Storm Jib

**Date:** 2026-04-21  
**Question:** Denis — Sont les J1/J2/J3 intégrés dans le système de choix de voiles?  
**Status:** 🔄 À AMÉLIORER — Actuellement simplifié (GENOA/WORKING), besoin détail classe

---

## 📋 CONTEXTE ACTUEL

### What's in the System Now

```javascript
// Current simplification (signalk-sails-management.js):
jib: 'GENOA'      ← Large jib, light air
jib: 'WORKING'    ← Medium jib, standard
jib: 'OUT'        ← Poled downwind
```

**Problème:** Pas de distinction J1/J2/J3!

---

## ⛵ J/30 JIB TYPES — STANDARD CLASSIFICATION

### Luff Length Reference

Pour un **J/30 standard**, le paramètre **J = 11.50'** (3.51m) est la longueur de référence

**Jib Classification basée sur Luff:**

| Jib Type | Luff Length | % of J | Foot Length | Area (sq ft) | Usage |
|----------|-------------|--------|-------------|--------------|-------|
| **#1 Genoa** | 42-46' | 105-115% | 32-35' | 280-320 | Light air (<6kt) |
| **#2 Jib** (Working) | 37-40' | 90-100% | 26-28' | 200-230 | Medium (6-12kt) |
| **#3 Jib** | 35-38' | 87-95% | 24-26' | 170-200 | Strong (12-16kt) |
| **Storm Jib** | 30-35' | 75-87% | 18-22' | 80-120 | Gale (16kt+) |

### Common J/30 Sails in Racing Fleet

**Typical J/30 Inventory (IMS/ORC):**

```
Light Air Package:
  • #1 Genoa (300+ sq ft) — for windward racing <6kt
  • Uses roller furler or spare hank-on

Medium Wind Package:
  • #2 Working Jib (210 sq ft) — standard for most conditions
  • Usually hanks-on, stays up most of race

Heavy Weather Package:
  • #3 Jib (180 sq ft) — for conditions 12-16kt
  • Optional; many J/30s use #2 in all conditions
  • Helps reduce weather helm in strong wind

Storm Setup (Cruising/Heavy Weather):
  • Storm Jib (80-120 sq ft) — rare in J/30
  • Usually not on boat unless ocean cruising
  • Mostly for extreme conditions (>20kt sustained)
```

---

## 📊 CLASSIFICATION MATRIX FOR J/30 SAILS

### Option A: Simple (Current System)

```
GENOA    = #1 (light air)
WORKING  = #2 (standard, medium)
(No #3 or Storm Jib distinction)
```

**Pros:**
- Simple decision tree
- Most J/30s have #1 + #2 only
- Fewer configs to manage

**Cons:**
- Doesn't distinguish #3 (heavy weather jib)
- Doesn't account for sailors who carry #3
- Missing storm jib entirely

---

### Option B: Detailed (Recommended for Racing)

```
J1    = #1 Genoa (300+ sq ft)    — Light air (<6kt)
J2    = #2 Working Jib (210 sq ft) — Medium (6-12kt)
J3    = #3 Heavy Weather (180 sq ft) — Strong (12-16kt)
STORM = Storm Jib (100 sq ft)    — Gale (16kt+)
```

**Pros:**
- Complete classification
- Matches IMS/ORC standards
- Racing teams use this language
- Better recommendations for strong conditions

**Cons:**
- More configs (16x5 = 80 instead of 30)
- Assumes crew has #3 (many don't)
- More complexity

---

## 🎯 DETAILED JIB MATRIX FOR J/30

### BEATING (Au Près) — Jib Choices by Wind

```
             LIGHT   LIGHT_AIR  MEDIUM   FRESH   STRONG   GALE
             <4kt    4-6kt      7-12kt   13-15   16-18    >=19
MAIN         FULL    FULL       FULL     FULL    1REEF    2REEF
JIB          J1      J1         J2       J2      J3       STORM*
AREA         FULL    FULL       FULL     FULL    70%      45%
HEEL TGT     12°     14°        16°      18°     20°      22°

NOTES:
  J1 (Genoa) = +100 sq ft vs J2 (genoa = 300, j2 = 200)
  J2 (Working) = standard, most versatile
  J3 = optional, for crews that carry it
  STORM = rarely used on J/30 (use J2 in gale)
```

**Specific Guidance by Wind:**

**< 4kt (LIGHT):**
- Hoist J1 (Genoa) if available
- Every sq inch helps (300 sq ft vs 200 sq ft = 50% gain in area!)
- Loose outhaul, ease mainsheet
- Body weight forward for heel
- Goal: 12° heel for maximum VMG

**4-6kt (LIGHT_AIR):**
- Keep J1 (Genoa) up
- May start drifting, requires crew management
- J1 advantage is strongest here (+50% area)
- Target: 14° heel

**7-12kt (MEDIUM) — THE SWEET SPOT:**
- Drop J1, switch to J2 (Working Jib)
- J2 = standard config for most time on water
- Easier to handle than Genoa
- Good power balance with full main
- Target: 16-18° heel

**13-15kt (FRESH):**
- Keep J2 (Working Jib)
- Tighten outhaul progressively
- Consider 1-reef main if heel > 18°
- J2 power is good, no need to drop further yet
- Target: 18° heel

**16-18kt (STRONG):**
- Consider dropping to J3 (Heavy Weather Jib)
- If J3 not available, use J2 with 1-reef main
- J3 area ~180 sq ft = smaller, less power
- Better balance with 1-reef main (170-180 sq ft)
- Target: 20° heel

**>=19kt (GALE):**
- Use STORM jib (100 sq ft) if available
- Most J/30s don't carry storm jib
- Alternative: Furl J2 to 50% (if roller furler)
- Or run under main alone with J2 furled
- With 2-reef main (100-120 sq ft) + storm jib (100 sq ft) = balanced
- Target: 22° heel (absolute limit)

---

### REACHING (Largue) — Jib Choices

```
             LIGHT   LIGHT_AIR  MEDIUM   FRESH   STRONG   GALE
             <4kt    4-6kt      7-12kt   13-15   16-18    >=19
MAIN         FULL    FULL       FULL     FULL    1REEF    2REEF
JIB          J1      J1         J2       J2      J3       STORM
SPINNAKER    RDY     UP         RDY      DOWN    DOWN     DOWN
HEEL TGT     15°     16°        18°      20°     22°      20°

NOTES:
  On reach, power is less constrained (more room for heel)
  J1 = +2-3° heel OK (reaching forgiving)
  J3 = optional, for strong reach only
  Spinnaker dominates these angles
```

**Reaching Guidance:**

**Light (< 6kt):**
- J1 + Full Main is power mode
- Spinnaker can be UP (if crew ready)
- Heel 15-16° is good (slightly more than beating)
- Reaching is "forgiving" = can carry more heel

**Medium (7-12kt):**
- J2 + Full Main
- Spinnaker READY (prepare for hoist)
- If < 10kt, can hoist spinnaker
- If > 10kt, keep down (control)
- Heel 18° target

**Fresh (13-15kt):**
- J2 + Full Main
- Spinnaker DOWN (too much power)
- Could consider J3 if heel excessive
- Heel 20° (approaching limit)

**Strong (16-18kt):**
- J3 (if available)
- Main staying full (reaching doesn't need reef yet)
- Spinnaker definitely DOWN
- Heel 22° (getting critical)

**Gale (>=19kt):**
- STORM jib (if available)
- Consider dropping main to 1-reef
- No spinnaker
- Heel monitor critical

---

### RUNNING (Vent Arrière) — Jib Choices

```
             LIGHT   LIGHT_AIR  MEDIUM   FRESH   STRONG   GALE
             <4kt    4-6kt      7-12kt   13-15   16-18    >=19
MAIN         FULL    FULL       FULL     FULL    1REEF    2REEF
JIB          OUT     OUT        OUT      OUT     POLED    POLED
SPINNAKER    UP      UP         RDY      DOWN    DOWN     DOWN
HEEL TGT     12°     13°        15°      16°     18°      14°

NOTES:
  Running: Jib poled OUT for stability (wing-on-wing)
  J1 vs J2 doesn't matter much (both poled)
  Spinnaker is KING (704 sq ft!)
  Heel lower on run (stability important)
```

**Running Guidance:**

**Light (< 6kt):**
- Jib OUT (poled)
- Spinnaker UP (main + spinnaker + poled jib = maximum)
- Very stable configuration
- Heel 12-13° (balanced)

**Medium (7-12kt):**
- Jib OUT (poled)
- Spinnaker UP (excellent conditions)
- Large area, good speed
- Heel 15° target

**Fresh (13-15kt):**
- Jib OUT (poled)
- Spinnaker DOWN (too much power)
- Consider main + jib only
- Heel 16° OK

**Strong (16-18kt):**
- Jib POLED (harder to handle)
- Main + jib only (spinnaker down)
- Heel 18° target

**Gale (>=19kt):**
- Under bare poles (main down, jib down)
- Or minimal sails (just jib)
- Heel 14-16° (lower for stability)
- Survival mode

---

## 🔄 INTEGRATION INTO PLUGIN

### Current Code (Simplified)

```javascript
const SAIL_MATRIX = {
  'BEATING': {
    'LIGHT': { main: 'FULL', jib: 'GENOA', ... },
    'MEDIUM': { main: 'FULL', jib: 'WORKING', ... },
    'STRONG': { main: '1REEF', jib: 'WORKING', ... },
  },
  // ...
};
```

### Proposed Enhancement

```javascript
const SAIL_MATRIX_V2 = {
  'BEATING': {
    'LIGHT': { main: 'FULL', jib: 'J1', area: 'FULL', ... },      // Genoa
    'LIGHT_AIR': { main: 'FULL', jib: 'J1', area: 'FULL', ... },  // Genoa
    'MEDIUM': { main: 'FULL', jib: 'J2', area: 'FULL', ... },     // Working
    'FRESH': { main: 'FULL', jib: 'J2', area: 'FULL', ... },      // Working
    'STRONG': { main: '1REEF', jib: 'J3', area: 'FULL', ... },    // Heavy weather
    'GALE': { main: '2REEF', jib: 'STORM', area: 'FULL', ... },   // Storm (if available)
  },
  'REACHING': {
    // Similar with J1/J2/J3/STORM
  },
  'RUNNING': {
    // Jib POLED (which J doesn't matter), focus on spinnaker
  }
};
```

---

## 💾 DATA STRUCTURE PROPOSAL

### New Signal K Paths (Optional)

```
navigation.sails.jib.type = 'J1' | 'J2' | 'J3' | 'STORM' | 'FURLED'
navigation.sails.jib.recommendedType = 'J1' | 'J2' | 'J3' | 'STORM'
navigation.sails.jib.area = 300 | 210 | 180 | 100  (sq ft)
navigation.sails.jib.recommendation = "Switch to J2 (heel > 18°)"
```

### Grafana Display

**Option 1: Simple Text Box**
```
Current Jib: J2 (Working, 210 sq ft)
Recommended: J3 (Heavy, 180 sq ft)
Reason: Heel 20.5°, sustaining fresh wind
```

**Option 2: Matrix Visual**
```
Wind Speed: 15kt
Heel Angle: 20.5°
Current: J2 + Full Main
↓
Recommendation: Switch to J3 (reduce jib power)
```

---

## 🎯 YOUR J/30 CONFIGURATION

### Question for Denis:

1. **What jibs do you carry?**
   - J1 Genoa? (for light air)
   - J2 Working? (standard)
   - J3 Heavy? (for strong wind)
   - Storm Jib? (for extreme)

2. **How do you currently choose?**
   - By wind speed?
   - By heel angle?
   - By crew preference?
   - By manual experience?

3. **What would be useful?**
   - System recommends J1/J2/J3 by wind?
   - Alert when time to switch?
   - Log which jib for performance analysis?
   - Integration with Grafana?

---

## ✅ RECOMMENDED NEXT STEP

### For Your System:

**Option A: Keep Simple (Current)**
- GENOA = J1
- WORKING = J2
- No J3 or STORM distinction
- Pro: Simple, works for most J/30s
- Con: Missing heavy weather options

**Option B: Add J1/J2/J3 Detail**
- Update plugin matrix to use J1/J2/J3/STORM names
- Set triggers by wind + heel (example: J2→J3 at 16kt + 20° heel)
- Add Signal K paths for jib type recommendations
- Update Grafana to show current vs recommended jib
- Test with your actual boat performance

**Option C: Hybrid (Recommended)**
- Keep GENOA/WORKING for simplicity (most of time)
- Add J3/STORM as alternatives in strong wind
- Only recommend switch if jib available + heel > 20°
- Document in dashboard what sails you have

---

## 📋 IMPLEMENTATION CHECKLIST

To add J1/J2/J3 support:

- [ ] Determine which jibs you actually have
- [ ] Update SAIL_MATRIX to use J1/J2/J3 names
- [ ] Set wind + heel thresholds for jib switches
- [ ] Add Signal K output paths (navigation.sails.jib.recommended)
- [ ] Create Grafana alert: "Recommend jib change"
- [ ] Test recommendations against real sailing data
- [ ] Document which configurations work for your boat

---

## 📚 REFERENCES

### Standard Jib Definitions

- **#1 Genoa:** 100-115% J, largest, light air only
- **#2 Jib (Working):** 90-100% J, standard workhorse
- **#3 Jib:** 85-95% J, strong wind jib (optional)
- **Storm Jib:** 75-85% J, extreme conditions (rarely used on J/30)

### J/30-Specific Sources

- J/30 Class Association: j30.us
- North Sails J/30 tuning guide
- Official IMS/ORC specifications
- Racing fleet practice (Stamford area?)

---

## 🚀 NEXT CONVERSATION

Denis, let me know:

1. **Which jibs do you have on your J/30?**
   - Just J1 + J2?
   - Also carry J3?
   - Ever use storm jib?

2. **How would you like the system to recommend?**
   - By wind speed only?
   - By heel angle?
   - By wind + heel combination?
   - Manual override option?

3. **Integration preference?**
   - Show in Grafana dashboard?
   - Alert when time to switch?
   - Log for post-race analysis?

Based on your answers, I can update the plugin to add full J1/J2/J3 support! 🚀⛵

---

**Created:** 2026-04-21  
**Status:** 📝 Ready for your input to finalize
