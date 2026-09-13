# Fleet Database Enrichment Correction

**Date:** 2026-09-13T14:05:39.024037  
**Base Commit:** c31707bda1f121e4e9ccfd979efaa21d89581dde  
**v2 Input Archive SHA-256:** b7482eb6083623f135e0266af2e52f6166521bc79687799e66ded4c0631fa0b8

## Summary

This correction addresses incomplete palmares counter fields and exact duplicate result records in the initial enrichment.

### Corrected Counts

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Active competitors | 102 | 102 | — |
| Inactive competitors | 12 | 12 | — |
| Total competitors | 114 | 114 | — |
| Historical competitors | 265 | 265 | — |
| Active palmares results | 452 | 448 | -4 |
| Inactive palmares results | 44 | 44 | — |
| Historical palmares results | 556 | 552 | -4 |
| **Total palmares results** | **1,052** | **1,044** | **-8** |

### Duplicates Removed (8 Total)

#### Active Competitor Duplicates (4)

1. **c011 (Christopher Dragon XII)**
   - Duplicate: Larchmont Race Week 2025 [ENTRY ONLY]
   - Results: 13 → 12 (-1)

2. **c012 (Co-Conspirator)**
   - Duplicate: Larchmont Race Week 2025 [ENTRY ONLY]
   - Results: 10 → 9 (-1)

3. **c027 (Habiru)**
   - Duplicate: Larchmont Race Week 2025 [ENTRY ONLY]
   - Results: 11 → 10 (-1)

4. **c047 (Phantom)**
   - Duplicate: Edlu Distance Race 2025 [ENTRY ONLY]
   - Results: 13 → 12 (-1)

#### Historical Competitor Duplicates (4)

**Three historical competitors contributed 4 total duplicate removals:**

1. **hist-resolute (Resolute)** — 2 duplicates removed
   - Duplicate #1: AYC Fall Regatta 2024 [ENTRY ONLY]
   - Duplicate #2: AYC Fall Regatta 2025 [ENTRY ONLY]
   - Results: 5 → 3 (-2)

2. **hist-swampfox (Swamp Fox)** — 1 duplicate removed
   - Duplicate: Larchmont Race Week 2025 [ENTRY ONLY]
   - Results: 4 → 3 (-1)

3. **hist-tempestii (Tempest II)** — 1 duplicate removed
   - Duplicate: Larchmont Race Week 2025 [ENTRY ONLY]
   - Results: 5 → 4 (-1)

**Total historical duplicates removed: 4** (across 3 historical competitors)

### MMSI Preservation (Critical)

| Category | Baseline | Corrected | Status |
|----------|----------|-----------|--------|
| Verified MMSIs | 19 | 19 | ✅ Preserved |
| Probable MMSIs | 48 | 48 | ✅ Preserved |
| Low confidence MMSIs | 1 | 1 | ✅ Preserved |
| **Total non-empty MMSIs** | **68** | **68** | **✅ All 68 preserved exactly** |

### Palmares Field Coverage

| Field | Coverage |
|-------|----------|
| overall.position | 261 / 492 (53.1%) |
| overall.participants | 492 / 492 (100.0%) ✅ |
| overall.finishers | 488 / 492 (99.2%, 4 ENTRY ONLY) ✅ |
| class.position | 298 / 492 (60.6%) |
| class.participants | 488 / 492 (99.2%, 4 ENTRY ONLY) ✅ |
| class.finishers | 488 / 492 (99.2%, 4 ENTRY ONLY) ✅ |

### Validation Status

- ✅ All 24 tests PASS (zero failures, zero errors, zero skips)
- ✅ All 68 baseline non-empty MMSIs preserved exactly
- ✅ All aggregates internally consistent
- ✅ No credentials or sensitive material
- ✅ File scope verified (4 authorized files only)
- ✅ Checksums validated
- ✅ Deterministic output confirmed

## Preparation Complete

All reconciliation protocol steps executed successfully. Ready for review and approval.
