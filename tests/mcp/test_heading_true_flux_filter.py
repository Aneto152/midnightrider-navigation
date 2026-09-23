from pathlib import Path


def test_heading_true_flux_regex_has_closing_delimiter():
    source = Path("mcp/servers/racing.js").read_text()

    assert r"r.source =~ /^signalk-heading-true-calculator\./)" in source
    assert r"r.source =~ /^signalk-heading-true-calculator\.)" not in source
