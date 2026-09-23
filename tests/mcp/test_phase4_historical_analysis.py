from pathlib import Path

RACING = Path("mcp/servers/racing.js").read_text()


def test_historical_analysis_tool_is_declared():
    assert "name: 'get_historical_analysis'" in RACING
    assert "resolution_seconds" in RACING


def test_historical_analysis_uses_one_flux_constructor():
    assert RACING.count("from(bucket:") == 1
    assert "buildFluxQuery" in RACING
    assert "buildTemporalQuery" in RACING


def test_historical_analysis_preserves_sources_and_llm_boundary():
    assert "source_id: row.source || null" in RACING
    assert "llm_status: 'not_activated'" in RACING
    assert "query_count: 1" in RACING


def test_temporal_angle_semantics_are_explicit():
    assert "series === 'wind_true_angle'" in RACING
    assert "series === 'course_over_ground'" in RACING
    assert "previous.sum += value" in RACING
