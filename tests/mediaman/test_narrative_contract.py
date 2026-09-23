"""Tests for the MediaMan narrative data contract."""

import pytest

from mediaman.narrative_contract import (
    FACT_SPECS,
    OPTIONAL_FACT_IDS,
    REQUIRED_FACT_IDS,
    FactQuality,
    NarrativeFact,
    NarrativeSnapshot,
    fact_spec,
)


def valid_required_facts():
    return (
        NarrativeFact("latitude", 41.0, "degrees", "N2K.1", "2026-09-05T12:00:00Z", "2026-09-05T12:00:01Z", FactQuality.VALID, "present"),
        NarrativeFact("longitude", -71.0, "degrees", "N2K.1", "2026-09-05T12:00:00Z", "2026-09-05T12:00:01Z", FactQuality.VALID, "present"),
        NarrativeFact("speed_over_ground", 2.5, "m_per_s", "N2K.1", "2026-09-05T12:00:00Z", "2026-09-05T12:00:01Z", FactQuality.VALID, "present"),
        NarrativeFact("course_over_ground", 81.2, "degrees_true", "N2K.1", "2026-09-05T12:00:00Z", "2026-09-05T12:00:01Z", FactQuality.VALID, "present"),
    )


def test_contract_has_four_required_semantic_facts_and_fifteen_optional_facts():
    assert REQUIRED_FACT_IDS == ("latitude", "longitude", "speed_over_ground", "course_over_ground")
    assert len(OPTIONAL_FACT_IDS) == 15
    assert len(FACT_SPECS) == 19


def test_snapshot_accepts_required_facts_without_optional_facts():
    snapshot = NarrativeSnapshot("2026-09-05T12:00:00Z", 3600, valid_required_facts())
    assert snapshot.fact("speed_over_ground").value == 2.5
    assert snapshot.as_dict()["collection_status"] == "complete"


def test_optional_missing_fact_is_explicit_and_non_blocking():
    missing = NarrativeFact("depth_below_transducer", None, "m", None, None, None, FactQuality.MISSING, "missing")
    snapshot = NarrativeSnapshot("2026-09-05T12:00:00Z", 60, valid_required_facts() + (missing,))
    assert snapshot.fact("depth_below_transducer").availability == "missing"


def test_unknown_fact_is_rejected():
    with pytest.raises(ValueError, match="unknown fact_id"):
        NarrativeFact("invented", 1.0, "unit", None, None, None, FactQuality.VALID, "present")


def test_unit_mismatch_is_rejected():
    with pytest.raises(ValueError, match="unit mismatch"):
        NarrativeFact("speed_over_ground", 2.0, "knots", None, None, None, FactQuality.VALID, "present")


def test_valid_fact_requires_numeric_value():
    with pytest.raises(ValueError, match="numeric value"):
        NarrativeFact("latitude", None, "degrees", None, None, None, FactQuality.VALID, "present")


def test_missing_fact_cannot_be_marked_present():
    with pytest.raises(ValueError, match="marked missing"):
        NarrativeFact("depth_below_transducer", None, "m", None, None, None, FactQuality.MISSING, "present")


def test_duplicate_fact_ids_are_rejected():
    facts = valid_required_facts()
    with pytest.raises(ValueError, match="duplicate"):
        NarrativeSnapshot("2026-09-05T12:00:00Z", 60, facts + (facts[0],))


def test_missing_required_fact_is_rejected():
    with pytest.raises(ValueError, match="missing required facts"):
        NarrativeSnapshot("2026-09-05T12:00:00Z", 60, valid_required_facts()[:-1])


def test_invalid_required_fact_is_rejected():
    facts = list(valid_required_facts())
    facts[0] = NarrativeFact("latitude", None, "degrees", None, None, None, FactQuality.MISSING, "missing")
    with pytest.raises(ValueError, match="invalid required facts"):
        NarrativeSnapshot("2026-09-05T12:00:00Z", 60, tuple(facts))


def test_window_is_bounded():
    with pytest.raises(ValueError, match="between 1 and 3600"):
        NarrativeSnapshot("2026-09-05T12:00:00Z", 3601, valid_required_facts())


def test_timestamp_must_be_utc_z():
    with pytest.raises(ValueError, match="end with Z"):
        NarrativeSnapshot("2026-09-05T12:00:00+00:00", 60, valid_required_facts())


def test_circular_specifications_are_marked():
    assert fact_spec("course_over_ground").circular is True
    assert fact_spec("wind_true_direction").circular is True
    assert fact_spec("speed_over_ground").circular is False


def test_source_paths_are_canonical_and_not_pgn_tables():
    assert fact_spec("water_temperature").source_paths == ("environment.water.temperature",)
    assert "environment.wind.speedTrue" in fact_spec("wind_true_speed").source_paths


def test_snapshot_serialization_preserves_provenance():
    snapshot = NarrativeSnapshot("2026-09-05T12:00:00Z", 60, valid_required_facts())
    serialized = snapshot.as_dict()
    assert serialized["facts"][0]["source"] == "N2K.1"
    assert serialized["facts"][0]["source_timestamp"].endswith("Z")
    assert serialized["facts"][0]["quality"] == "valid"
