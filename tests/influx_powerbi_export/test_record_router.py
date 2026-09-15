"""Tests for RecordRouter — the routing rules shared by both export paths.

These cover the defect that made every aggregate column empty: the chunked
path passed the raw Signal K measurement name to the normalizer instead of
the mapped schema field, and discarded navigation.position outright.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.influx_powerbi_export.classifier import Classifier
from tools.influx_powerbi_export.field_mapper import SignalKFieldMapper
from tools.influx_powerbi_export.record_router import RecordRouter
from tools.influx_powerbi_export.schema import get_midnight_rider_headers


class FakeAISWriter:
    def __init__(self):
        self.rows = []

    def write_row(self, record):
        self.rows.append(record)


class FakeNormalizer:
    def __init__(self):
        self.points = []

    def add_point(self, timestamp_utc, field_name, value):
        self.points.append((timestamp_utc, field_name, value))


def build():
    ais = FakeAISWriter()
    norm = FakeNormalizer()
    router = RecordRouter(Classifier(), SignalKFieldMapper(), ais, norm)
    return router, ais, norm


def rec(measurement, value, field="value", context="vessels.self", source="n2k.0"):
    return {
        "_time": "2026-09-04T16:00:03Z",
        "_measurement": measurement,
        "_field": field,
        "_value": value,
        "context": context,
        "source": source,
    }


def test_ais_record_goes_to_ais_writer():
    router, ais, norm = build()
    router.route(rec("sensors.ais.target", "A",
                     context="vessels.urn:mrn:imo:mmsi:000000000"))
    assert len(ais.rows) == 1
    assert norm.points == []
    assert router.ais_rows == 1
    assert router.midnight_rider_rows == 0


def test_position_latitude_and_longitude_are_kept():
    """navigation.position used to be dropped by float() on a JSON payload."""
    router, ais, norm = build()
    router.route(rec("navigation.position", "44.6", field="lat"))
    router.route(rec("navigation.position", "-63.5", field="lon"))
    fields = [p[1] for p in norm.points]
    assert fields == ["latitude", "longitude"]
    assert norm.points[0][2] == 44.6
    assert norm.points[1][2] == -63.5
    assert router.unparsable_rows == 0
    assert router.unmapped_rows == 0


def test_measurement_name_is_never_used_as_field_name():
    """The core regression: raw Signal K paths must never reach the CSV."""
    router, ais, norm = build()
    router.route(rec("navigation.speedOverGround", "5.0"))
    assert norm.points, "the point was dropped entirely"
    field = norm.points[0][1]
    assert field in get_midnight_rider_headers(), field
    assert not field.startswith("navigation."), field
    assert field == "sog_knots"


def test_units_are_converted():
    """Radians in, degrees out; metres per second in, knots out."""
    router, ais, norm = build()
    router.route(rec("environment.wind.angleApparent", str(math.pi / 2)))
    router.route(rec("environment.wind.speedApparent", "10.0"))
    by_field = {p[1]: p[2] for p in norm.points}
    assert abs(by_field["awa_deg"] - 90.0) < 0.001
    assert abs(by_field["aws_knots"] - 19.4384) < 0.01


def test_roll_keeps_its_sign():
    router, ais, norm = build()
    router.route(rec("navigation.attitude.roll", str(-math.pi / 6)))
    value = norm.points[0][2]
    assert -31.0 < value < -29.0, value


def test_battery_percent_becomes_voltage():
    router, ais, norm = build()
    router.route(rec("electrical.batteries.calypso.percent", "50"))
    assert norm.points[0][1] == "battery_voltage"
    assert abs(norm.points[0][2] - 12.0) < 0.001


def test_water_temperature_now_has_a_home():
    """environment.water.temperature was mapped but had no column until the
    22-column schema added water_temp_c."""
    router, ais, norm = build()
    router.route(rec("environment.water.temperature", "288.15"))
    assert norm.points, "water temperature still discarded"
    assert norm.points[0][1] == "water_temp_c"
    assert abs(norm.points[0][2] - 15.0) < 0.01


def test_unmapped_measurement_is_counted_not_silent():
    router, ais, norm = build()
    router.route(rec("navigation.acceleration.x", "0.1"))
    assert norm.points == []
    assert router.unmapped_rows == 1
    assert router.midnight_rider_rows == 1


def test_non_numeric_value_is_counted():
    router, ais, norm = build()
    router.route(rec("navigation.speedOverGround", "not-a-number"))
    assert norm.points == []
    assert router.unparsable_rows == 1


def test_non_finite_value_is_rejected():
    router, ais, norm = build()
    router.route(rec("navigation.speedOverGround", "NaN"))
    router.route(rec("navigation.speedOverGround", "inf"))
    assert norm.points == []
    assert router.unparsable_rows == 2


def test_non_dict_records_are_ignored():
    router, ais, norm = build()
    assert router.route("annotation line") is None
    assert router.route(None) is None
    assert router.source_rows == 0


def test_counters_expose_every_field():
    router, ais, norm = build()
    router.route(rec("navigation.speedOverGround", "5.0"))
    c = router.counters()
    assert set(c) == {
        "source_rows", "ais_rows", "midnight_rider_rows", "mapped_points",
        "unmapped_rows", "unparsable_rows", "unclassified_rows",
    }
    assert c["source_rows"] == 1
    assert c["mapped_points"] == 1


def test_every_mapped_target_exists_in_the_schema():
    """No mapping may point at a column the CSV does not have. This is what
    silently discarded water temperature for weeks.

    "position" is the one documented exception: navigation.position is a
    compound measurement split into latitude and longitude by the router,
    so its mapping target is never written as a column.
    """
    headers = set(get_midnight_rider_headers())
    targets = {m[0] for m in SignalKFieldMapper.MEASUREMENT_MAPPINGS.values()}
    orphans = sorted(t for t in targets if t not in headers)
    assert orphans == ["position"], f"mappings with no CSV column: {orphans}"
