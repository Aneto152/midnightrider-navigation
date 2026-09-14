#!/usr/bin/env python3
"""Lossless enrichment of regatta/competitors.json from the consolidated race database.

Context (2026-09-14). The 2026-09-13 enrichment (merge_version fleet-enrichment-v2)
applied the full merge to the 114 current competitors but left the 265 historical
competitors with a skeleton only: no skipper, no sail number, no ratings, no MMSI,
no yacht club, no home port, no class fleet sizes and no overall finisher counts.
This importer replays the source data over BOTH pools.

Policy - enrich only, never destroy:
  * no boat is ever removed
  * a non-null existing value is never overwritten by the source
  * an existing MMSI is never replaced; a divergent source MMSI is recorded in
    mmsi_conflict for human review
  * unknown keys already present on a boat are preserved untouched
  * the script is idempotent: running it twice yields the same file

Usage:
    python3 regatta/import_race_database.py [--dry-run] [--report PATH]
"""

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_CSV = os.path.join(REPO, 'regatta', 'sources', 'race_database_consolidated.csv')
TARGET_JSON = os.path.join(REPO, 'regatta', 'competitors.json')

FINISHED = 'FINISHED'


def norm(value):
    """Accent-folded, alphanumeric-only form of a boat name, for matching."""
    text = unicodedata.normalize('NFKD', str(value))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]', '', text.lower())


def clean(value):
    """Normalise a CSV cell to None or a stripped string."""
    if value is None:
        return None
    # Excel exports sometimes prefix text cells with an apostrophe ("'P39") and
    # earlier merges stored the literal string "none" instead of a null.
    text = str(value).strip().strip('\'"').strip()
    if text == '' or text.lower() in ('nan', 'none', 'nat', 'n/a', 'na', 'null', '-', 'unknown'):
        return None
    return text


def as_int(value):
    text = clean(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def as_float(value):
    text = clean(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def length_ft(value):
    """'44 Ft' -> 44.0"""
    text = clean(value)
    if text is None:
        return None
    match = re.search(r'[\d.]+', text)
    return float(match.group(0)) if match else None


def force(target, key, value, changes, label):
    """Overwrite unconditionally: the source is authoritative for this field.

    Reserved for values that are mechanically derived from the race database and
    cannot be locally curated (ranks, fleet sizes, finisher counts, times,
    per-event ratings). The 2026-09-13 merge had written
    overall.finishers = overall.participants on 488 results, which is false as
    soon as a single boat fails to finish; preserving such a value would
    preserve the error.
    """
    if value is None:
        return False
    if target.get(key) != value:
        target[key] = value
        changes[label] += 1
        return True
    return False


def fill(target, key, value, changes, label):
    """Set target[key] only when it is currently empty. Returns True if written."""
    if value is None:
        return False
    current = target.get(key)
    if isinstance(current, str):
        current = clean(current)
    if current not in (None, '', [], {}):
        return False
    target[key] = value
    changes[label] += 1
    return True


def load_rows(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def index_source(rows):
    """Group source rows by Boat Key and derive class fleet sizes."""
    by_boat = defaultdict(list)
    by_class = defaultdict(list)
    for row in rows:
        by_boat[clean(row['Boat Key'])].append(row)
        division = clean(row.get('Class / Division'))
        if division:
            by_class[(clean(row.get('Event ID')), division)].append(row)
    class_sizes = {}
    for key, members in by_class.items():
        entrants = len({clean(r['Boat Key']) for r in members})
        finishers = len({clean(r['Boat Key']) for r in members
                         if (clean(r.get('Result Status')) or '').upper() == FINISHED})
        class_sizes[key] = (entrants, finishers)
    return by_boat, class_sizes


def build_result(row, class_sizes):
    """Full result record for one source row."""
    division = clean(row.get('Class / Division'))
    entrants, finishers = class_sizes.get((clean(row.get('Event ID')), division), (None, None))
    return {
        'regatta_id': clean(row.get('Event ID')),
        'regatta': clean(row.get('Event')),
        'year': as_int(row.get('Year')),
        'event_dates': clean(row.get('Event Dates')),
        'status': clean(row.get('Result Status')),
        'overall': {
            'position': as_int(row.get('Overall Fleet Rank')),
            'participants': as_int(row.get('Overall Fleet Size')),
            'finishers': as_int(row.get('Overall Fleet Finishers')),
        },
        'class': {
            'name': division,
            'position': as_int(row.get('Class Rank')),
            'participants': entrants,
            'finishers': finishers,
        },
        'rating_system': clean(row.get('Rating System')),
        'rating_metric': clean(row.get('Rating Metric')),
        'rating_division': clean(row.get('Rating Division')),
        'published_rating': as_float(row.get('Published Rating')),
        'latest_rating': as_float(row.get('Latest Rating')),
        'racing_circle': clean(row.get('Racing Circle')),
        'fleet_group': clean(row.get('Overall Fleet Group')),
        'times': {
            'corrected': clean(row.get('Corrected Time')),
            'elapsed': clean(row.get('Elapsed Time')),
            'finish': clean(row.get('Finish Time')),
        },
        'source_urls': {
            k: clean(row.get(k)) for k in (
                'YachtScoring Result Detail',
                'YachtScoring Scratch Sheet',
                'YachtScoring Boat Detail',
            ) if clean(row.get(k))
        },
    }


def merge_result(existing, fresh, changes):
    """Deep-fill one result record without overwriting existing values."""
    for key in ('event_dates', 'status', 'rating_system', 'rating_metric',
                'rating_division', 'published_rating', 'latest_rating',
                'racing_circle', 'fleet_group', 'year', 'regatta'):
        force(existing, key, fresh[key], changes, 'result.' + key)
    for group in ('overall', 'class'):
        existing.setdefault(group, {})
        for key, value in fresh[group].items():
            force(existing[group], key, value, changes, '{}.{}'.format(group, key))
    existing.setdefault('times', {})
    for key, value in fresh['times'].items():
        force(existing['times'], key, value, changes, 'times.' + key)
    existing.setdefault('source_urls', {})
    for key, value in fresh['source_urls'].items():
        fill(existing['source_urls'], key, value, changes, 'source_urls')


def ais_block(rows):
    """AIS metadata for the boat, taken from the most recent row that carries it."""
    carriers = [r for r in rows if clean(r.get('AIS MMSI'))]
    if not carriers:
        return None
    row = sorted(carriers, key=lambda r: as_int(r.get('Year')) or 0)[-1]
    block = {
        'mmsi': clean(row.get('AIS MMSI')),
        'name': clean(row.get('AIS Name')),
        'ais_class': clean(row.get('AIS Class')),
        'ship_type': clean(row.get('AIS Ship Type')),
        'reported_length': as_float(row.get('AIS Reported Length')),
        'reported_beam': as_float(row.get('AIS Reported Beam')),
        'reported_draft': as_float(row.get('AIS Reported Draft')),
        'callsign': clean(row.get('AIS Callsign')),
        'first_seen_utc': clean(row.get('AIS First Seen UTC')),
        'last_seen_utc': clean(row.get('AIS Last Seen UTC')),
        'observation_count': as_int(row.get('AIS Observation Count')),
        'match_confidence': clean(row.get('AIS Match Confidence')),
        'match_basis': clean(row.get('AIS Match Basis')),
        'source': clean(row.get('AIS Source')),
    }
    return {k: v for k, v in block.items() if v is not None} or None


def enrich_boat(boat, rows, class_sizes, changes, conflicts):
    """Apply every source field available for this boat."""
    ordered = sorted(rows, key=lambda r: as_int(r.get('Year')) or 0)
    latest = ordered[-1]

    def newest(column):
        """Most recent non-empty value for a column: the latest row is often blank."""
        for row in reversed(ordered):
            value = clean(row.get(column))
            if value is not None:
                return value
        return None

    fill(boat, 'skipper', newest('Owner / Skipper'), changes, 'boat.skipper')
    fill(boat, 'yacht_club', newest('Yacht Club'), changes, 'boat.yacht_club')
    fill(boat, 'home_port', newest('Home Port'), changes, 'boat.home_port')

    sail_numbers = sorted({clean(r.get('Sail Number')) for r in rows if clean(r.get('Sail Number'))})
    fill(boat, 'sail_number', newest('Sail Number'), changes, 'boat.sail_number')
    if sail_numbers:
        fill(boat, 'sail_numbers', sail_numbers, changes, 'boat.sail_numbers')

    vessel = boat.setdefault('vessel', {})
    fill(vessel, 'model', newest('Boat Type'), changes, 'vessel.model')
    fill(vessel, 'length_ft', length_ft(newest('Length')), changes, 'vessel.length_ft')

    circles = sorted({clean(r.get('Racing Circle')) for r in rows if clean(r.get('Racing Circle'))})
    groups = sorted({clean(r.get('Overall Fleet Group')) for r in rows if clean(r.get('Overall Fleet Group'))})
    if circles:
        fill(boat, 'racing_circles', circles, changes, 'boat.racing_circles')
    if groups:
        fill(boat, 'fleet_groups', groups, changes, 'boat.fleet_groups')

    # --- ratings -------------------------------------------------------
    ratings = boat.setdefault('ratings', {})
    phrf_rows = [r for r in rows if 'PHRF' in (clean(r.get('Rating System')) or '').upper()]
    rated = [r for r in phrf_rows
             if as_float(r.get('Latest Rating')) is not None
             or as_float(r.get('Published Rating')) is not None]
    if rated:
        # Take the most recent row that actually carries a rating: the newest
        # entry is sometimes blank, which previously produced an empty PHRF.
        newest = sorted(rated, key=lambda r: as_int(r.get('Year')) or 0)[-1]
        value = as_float(newest.get('Latest Rating'))
        if value is None:
            value = as_float(newest.get('Published Rating'))
        fill(ratings, 'PHRF_LIS', value, changes, 'ratings.PHRF_LIS')
    history = [
        {
            'year': as_int(r.get('Year')),
            'event': clean(r.get('Event')),
            'system': clean(r.get('Rating System')),
            'metric': clean(r.get('Rating Metric')),
            'division': clean(r.get('Rating Division')),
            'published': as_float(r.get('Published Rating')),
            'latest': as_float(r.get('Latest Rating')),
            'latest_year': as_int(r.get('Latest Rating Year')),
        }
        for r in sorted(rows, key=lambda r: as_int(r.get('Year')) or 0)
        if as_float(r.get('Published Rating')) is not None or as_float(r.get('Latest Rating')) is not None
    ]
    if history:
        fill(boat, 'phrf_history', history, changes, 'boat.phrf_history')

    # --- MMSI: fill only, never overwrite ------------------------------
    # A source cell may carry several MMSIs separated by ';'. Auto-filling then
    # amounts to guessing, so we only fill when the source is unambiguous.
    raw_mmsi = clean(latest.get('Best Available MMSI')) or clean(latest.get('AIS MMSI'))
    candidates = [c.strip() for c in re.split(r'[;,]', raw_mmsi) if c.strip()] if raw_mmsi else []
    if candidates:
        fill(boat, 'mmsi_candidates', candidates, changes, 'boat.mmsi_candidates')
        current = clean(boat.get('mmsi'))
        if not current and len(candidates) == 1:
            boat['mmsi'] = candidates[0]
            changes['boat.mmsi'] += 1
            # confidence is coupled to the value: it must be rewritten with it,
            # otherwise a freshly matched MMSI keeps a stale 'unverified' tag.
            boat['mmsi_confidence'] = clean(latest.get('AIS Match Confidence')) or 'ais_matched'
            changes['boat.mmsi_confidence'] += 1
        elif not current and len(candidates) > 1:
            boat['mmsi_review'] = {'reason': 'several MMSI in source', 'candidates': candidates}
            conflicts.append((boat.get('id'), boat.get('boat_name'), '(empty)', ' | '.join(candidates)))
        elif current and current not in candidates:
            boat['mmsi_conflict'] = {'kept': current, 'source': candidates,
                                     'source_basis': clean(latest.get('AIS Match Basis'))}
            conflicts.append((boat.get('id'), boat.get('boat_name'), current, ' | '.join(candidates)))

    ais = ais_block(rows)
    if ais:
        fill(boat, 'ais', ais, changes, 'boat.ais')

    # --- palmares ------------------------------------------------------
    palmares = boat.setdefault('palmares', {})
    results = palmares.setdefault('results', [])
    # A boat can be entered in TWO divisions of the same event (10 such rows in
    # the source, e.g. Resolute at event 16314 in both J/44 and Coastal PHRF 5).
    # Keying results by regatta_id alone silently dropped one of them, so the
    # key is (regatta_id, class name).
    by_key = {}
    for item in results:
        by_key.setdefault((str(item.get('regatta_id')), (item.get('class') or {}).get('name')), item)
    for row in sorted(rows, key=lambda r: as_int(r.get('Year')) or 0):
        fresh = build_result(row, class_sizes)
        key = (str(fresh['regatta_id']), fresh['class']['name'])
        existing = by_key.get(key)
        if existing is None:
            # fall back on a record stored before divisions were tracked
            legacy_key = (str(fresh['regatta_id']), None)
            existing = by_key.pop(legacy_key, None)
        if existing is None:
            results.append(fresh)
            by_key[key] = fresh
            changes['result.added'] += 1
        else:
            merge_result(existing, fresh, changes)
            by_key[key] = existing
    results.sort(key=lambda r: (r.get('year') or 0, r.get('regatta') or ''))

    # Aggregates describe the results actually stored, so they are derived from
    # the deduplicated results array and never from the raw source rows. The
    # source holds duplicate (event, division) rows for a few boats (deviation,
    # valiant at event 50796), which merge into a single result. Counting rows
    # made participations exceed len(results) and broke the legitimate invariant
    # asserted by tests/regatta/test_fleet_enrichment_merge.py::test_16.
    statuses = [(clean(r.get('status')) or '').upper() for r in results]
    overall_ranks = [(r.get('overall') or {}).get('position') for r in results]
    overall_ranks = [v for v in overall_ranks if isinstance(v, int)]
    class_ranks = [(r.get('class') or {}).get('position') for r in results]
    class_ranks = [v for v in class_ranks if isinstance(v, int)]
    computed = {
        'participations': len(results),
        'finished': statuses.count(FINISHED),
        'retired': statuses.count('RET'),
        'did_not_finish_or_start': sum(statuses.count(s) for s in ('DNF', 'DNS', 'DNC', 'NSC', 'SCP')),
        'wins_overall': sum(1 for v in overall_ranks if v == 1),
        'podiums_overall': sum(1 for v in overall_ranks if v <= 3),
        'best_overall_rank': min(overall_ranks) if overall_ranks else None,
        'best_class_rank': min(class_ranks) if class_ranks else None,
    }
    for key, value in computed.items():
        force(palmares, key, value, changes, 'palmares.' + key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='report without writing')
    parser.add_argument('--report', help='write the change report to this path')
    parser.add_argument('--source', default=SOURCE_CSV)
    parser.add_argument('--target', default=TARGET_JSON)
    args = parser.parse_args()

    rows = load_rows(args.source)
    by_boat, class_sizes = index_source(rows)
    with open(args.target, encoding='utf-8') as handle:
        data = json.load(handle)

    # --- unify the two pools into a single fleet -----------------------
    # Until schema_version 3 the file carried `competitors` (114) and
    # `historical_competitors` (265) as separate arrays. That split had no
    # functional meaning - both are boats in the same fleet listing - and it
    # produced two divergent code paths, one of which never received the
    # 2026-09-13 enrichment. There is now a single `competitors` array.
    unified = list(data.get('competitors', []))
    legacy = data.pop('historical_competitors', [])
    for boat in legacy:
        boat.pop('source_status', None)
        unified.append(boat)
    for boat in unified:
        boat.pop('source_status', None)
    data['competitors'] = unified
    data['schema_version'] = 3

    index = {}
    for boat in unified:
        boat_id = str(boat.get('id', ''))
        if boat_id.startswith('hist-'):
            index.setdefault(boat_id[5:], []).append(('competitors', boat))
        index.setdefault(norm(boat.get('boat_name')), []).append(('competitors', boat))

    changes = defaultdict(int)
    conflicts = []
    matched, unmatched, duplicated = 0, [], []
    for boat_key, boat_rows in sorted(by_boat.items()):
        targets = index.get(boat_key) or index.get(norm(boat_rows[0].get('Boat Name'))) or []
        seen, unique = set(), []
        for pool_name, boat in targets:
            marker = id(boat)
            if marker not in seen:
                seen.add(marker)
                unique.append((pool_name, boat))
        if not unique:
            unmatched.append(boat_key)
            continue
        if len(unique) > 1:
            duplicated.append((boat_key, [b.get('id') for _, b in unique]))
        for _, boat in unique:
            enrich_boat(boat, boat_rows, class_sizes, changes, conflicts)
            matched += 1

    data.setdefault('metadata', {}).update({
        'last_enrichment_source': os.path.basename(args.source),
        'last_enrichment_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source_rows': len(rows),
        'source_unique_boats': len(by_boat),
        'merge_version': 'fleet-enrichment-v3-lossless',
    })

    lines = ['UNIFIED FLEET          {} boats in a single competitors array'.format(len(unified)),
             '  from legacy split      {} current + {} historical'.format(
                 len(unified) - len(legacy), len(legacy)),
             'SOURCE ROWS            {}'.format(len(rows)),
             'SOURCE BOATS           {}'.format(len(by_boat)),
             'BOAT RECORDS ENRICHED  {}'.format(matched),
             'SOURCE KEYS UNMATCHED  {} {}'.format(len(unmatched), unmatched),
             'DUPLICATE TARGETS      {} {}'.format(len(duplicated), duplicated),
             'MMSI CONFLICTS         {}'.format(len(conflicts)),
             '']
    for boat_id, name, kept, src in conflicts:
        lines.append('  conflict {} {}: kept {}, source {}'.format(boat_id, name, kept, src))
    lines.append('')
    lines.append('FIELDS WRITTEN (empty -> value):')
    for key in sorted(changes):
        lines.append('  {:32} {}'.format(key, changes[key]))
    report = '\n'.join(lines)
    print(report)
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as handle:
            handle.write(report + '\n')

    if args.dry_run:
        print('\nDRY RUN - nothing written')
        return 0

    with open(args.target, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print('\nWRITTEN {}'.format(args.target))
    return 0


if __name__ == '__main__':
    sys.exit(main())
