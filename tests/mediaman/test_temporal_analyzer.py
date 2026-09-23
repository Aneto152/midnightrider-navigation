from mediaman.temporal_analyzer import analyze

def row(series, timestamp, value, source="N2K.35"):
    return {"series": series, "timestamp_utc": timestamp, "value": value, "source_id": source}

def test_temporal_analysis_is_bounded_and_llm_free():
    result = analyze([
        row("wind_true_speed", "2026-09-05T12:00:00Z", 5.0, "truewind.test"),
        row("wind_true_speed", "2026-09-05T12:01:00Z", 6.0, "truewind.test"),
        row("wind_true_angle", "2026-09-05T12:00:00Z", 359.0, "truewind.test"),
        row("wind_true_angle", "2026-09-05T12:01:00Z", 1.0, "truewind.test"),
        row("attitude_roll", "2026-09-05T12:00:00Z", 0.1),
        row("attitude_roll", "2026-09-05T12:01:00Z", 0.2),
    ], "2026-09-05T12:00:00Z", "2026-09-05T12:02:00Z", 60)
    assert result["success"] is True
    assert result["llm_status"] == "not_activated"
    assert result["interval"]["duration_seconds"] == 120
    assert result["statistics"]["wind_true_speed"]["sample_count"] == 2
    assert result["evidence"]["query_count"] == 1

def test_empty_series_remains_evidence_backed():
    result = analyze([], "2026-09-05T12:00:00Z", "2026-09-05T12:01:00Z", 60)
    assert result["patterns"] == []
    assert result["evidence"]["sample_counts"] == {}
