"""Tests for the final merge: AIS deduplication and the MR header contract.

The AIS deduplication key used to read `timestamp_utc` and `mmsi`, columns
the raw AIS output does not have. Every row therefore produced the key "_",
a whole chunk collapsed into a single event, and the loss was logged as
"52100 duplicates removed".
"""

import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.influx_powerbi_export.merge import AISEventsMerger, FinalMerger
from tools.influx_powerbi_export.schema import get_midnight_rider_headers

AIS_COLUMNS = ["_time", "_measurement", "_field", "_value", "context", "source"]


def row(time, measurement="sensors.ais.class", field="value", value="A",
        context="vessels.urn:mrn:imo:mmsi:000000000", source="n2k.1"):
    return {
        "_time": time, "_measurement": measurement, "_field": field,
        "_value": value, "context": context, "source": source,
    }


def write_chunk(directory, rows, name="AIS_EVENTS_RAW.csv"):
    path = Path(directory) / name
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AIS_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return path


def test_distinct_events_survive():
    """The regression: 52101 rows must not become 1."""
    merger = AISEventsMerger()
    for i in range(50):
        merger.add_event(row(f"2026-09-04T16:00:{i:02d}Z"))
    merged = merger.get_merged_events()
    assert len(merged) == 50, len(merged)
    assert merger.dedup_count == 0


def test_same_instant_different_series_are_distinct():
    """Two vessels reporting at the same instant are two events."""
    merger = AISEventsMerger()
    merger.add_event(row("2026-09-04T16:00:00Z", context="vessels.a"))
    merger.add_event(row("2026-09-04T16:00:00Z", context="vessels.b"))
    merger.add_event(row("2026-09-04T16:00:00Z", context="vessels.a",
                         measurement="navigation.position"))
    merger.add_event(row("2026-09-04T16:00:00Z", context="vessels.a",
                         field="lat"))
    assert len(merger.get_merged_events()) == 4
    assert merger.dedup_count == 0


def test_a_true_duplicate_is_removed():
    merger = AISEventsMerger()
    merger.add_event(row("2026-09-04T16:00:00Z"))
    merger.add_event(row("2026-09-04T16:00:00Z"))
    assert len(merger.get_merged_events()) == 1
    assert merger.dedup_count == 1


def test_incomplete_key_fails_closed():
    """A missing key column must raise, never silently collapse rows."""
    merger = AISEventsMerger()
    try:
        merger.add_event({"timestamp_utc": "x", "mmsi": "y"})
    except ValueError as exc:
        assert "deduplication" in str(exc)
        return
    raise AssertionError("an incomplete dedup key was accepted")


def test_ordering_is_deterministic():
    forward = AISEventsMerger()
    backward = AISEventsMerger()
    times = [f"2026-09-04T16:00:{i:02d}Z" for i in range(10)]
    for t in times:
        forward.add_event(row(t))
    for t in reversed(times):
        backward.add_event(row(t))
    a = [e["_time"] for e in forward.get_merged_events()]
    b = [e["_time"] for e in backward.get_merged_events()]
    assert a == b == times


def test_merge_chunk_files_keeps_every_row():
    with tempfile.TemporaryDirectory() as tmp:
        write_chunk(tmp, [row(f"2026-09-04T16:00:{i:02d}Z") for i in range(30)])
        merger = AISEventsMerger()
        merged = merger.merge_chunk_files([Path(tmp) / "AIS_EVENTS_RAW.csv"])
        assert len(merged) == 30
        assert merger.dedup_count == 0


def test_final_mr_header_comes_from_the_schema():
    """One source for the column list, so the merged header cannot drift."""
    with tempfile.TemporaryDirectory() as tmp:
        merger = FinalMerger(output_dir=Path(tmp), chunk_count=1)
        merger._write_final_mr_csv([])
        path = Path(tmp) / "MIDNIGHT_RIDER_10S_AGGREGATES.csv"
        header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert header == get_midnight_rider_headers(), header
