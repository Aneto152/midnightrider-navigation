"""Single implementation of the InfluxDB record routing rules.

The chunked export path used to carry its own, much simpler, copy of this
logic. That copy passed the raw Signal K measurement name straight to the
normalizer as a CSV field name and never called the field mapper, so:

  * every aggregate column was written empty, because keys such as
    ``navigation.speedOverGround`` are absent from the 22-column schema and
    ``CSVWriter`` silently substitutes an empty cell for a missing key;
  * no unit conversion happened, so angles would have stayed in radians and
    speeds in metres per second;
  * ``navigation.position`` raised ``ValueError`` on ``float()`` and was
    swallowed by a bare ``except``, discarding roughly 2174 rows per minute.

Routing now lives here so the two export paths cannot diverge again, and
every discarded record is counted instead of being silently dropped.
"""

import logging
import math
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Nominal 12 V bank: 0 % -> 9.6 V, 100 % -> 14.4 V
BATTERY_PERCENT_MEASUREMENT = "electrical.batteries.calypso.percent"
BATTERY_MIN_VOLTS = 9.6
BATTERY_SPAN_VOLTS = 4.8

POSITION_MEASUREMENT = "navigation.position"
LATITUDE_FIELDS = ("lat", "latitude")
LONGITUDE_FIELDS = ("lon", "longitude")


class RecordRouter:
    """Classify one InfluxDB record and route it to the right output.

    Counters are plain attributes so callers can persist them verbatim:

    ``source_rows``
        records received from the stream.
    ``ais_rows``
        records written to the raw AIS output.
    ``midnight_rider_rows``
        records classified as onboard data, mapped or not.
    ``mapped_points``
        values actually handed to the normalizer. This is the only counter
        that reflects data reaching the aggregates.
    ``unmapped_rows``
        onboard records whose measurement has no schema column.
    ``unparsable_rows``
        onboard records whose value was not a finite number.
    ``unclassified_rows``
        records the classifier assigned to neither family.
    """

    def __init__(self, classifier, field_mapper, ais_writer, normalizer):
        self.classifier = classifier
        self.field_mapper = field_mapper
        self.ais_writer = ais_writer
        self.normalizer = normalizer

        self.source_rows = 0
        self.ais_rows = 0
        self.midnight_rider_rows = 0
        self.mapped_points = 0
        self.unmapped_rows = 0
        self.unparsable_rows = 0
        self.unclassified_rows = 0

    # ------------------------------------------------------------------ API

    def route(self, record: Any) -> Optional[str]:
        """Route one record. Returns its classification, or None if ignored."""
        if not isinstance(record, dict):
            return None

        self.source_rows += 1
        classification = self.classifier.classify(record)

        if classification == "ais":
            self.ais_writer.write_row(record)
            self.ais_rows += 1
            return classification

        if classification == "midnight_rider":
            self.midnight_rider_rows += 1
            self._route_onboard(record)
            return classification

        self.unclassified_rows += 1
        return classification

    def counters(self) -> Dict[str, int]:
        """Return every counter as a plain dict, for checkpoint persistence."""
        return {
            "source_rows": self.source_rows,
            "ais_rows": self.ais_rows,
            "midnight_rider_rows": self.midnight_rider_rows,
            "mapped_points": self.mapped_points,
            "unmapped_rows": self.unmapped_rows,
            "unparsable_rows": self.unparsable_rows,
            "unclassified_rows": self.unclassified_rows,
        }

    # -------------------------------------------------------------- interns

    def _route_onboard(self, record: Dict[str, Any]) -> None:
        timestamp = record.get("_time")
        measurement = record.get("_measurement")
        field_raw = record.get("_field")
        value_str = record.get("_value")

        if not timestamp or value_str is None or value_str == "":
            self.unparsable_rows += 1
            return

        # Position is stored as two separate _field attributes, so float() on
        # the measurement alone would fail.
        if measurement == POSITION_MEASUREMENT:
            if field_raw in LATITUDE_FIELDS:
                self._add("latitude", timestamp, value_str)
            elif field_raw in LONGITUDE_FIELDS:
                self._add("longitude", timestamp, value_str)
            else:
                self.unmapped_rows += 1
            return

        if measurement == BATTERY_PERCENT_MEASUREMENT:
            percent = self._to_float(value_str)
            if percent is None:
                self.unparsable_rows += 1
                return
            volts = BATTERY_MIN_VOLTS + (percent * BATTERY_SPAN_VOLTS / 100.0)
            self._emit("battery_voltage", timestamp, volts)
            return

        # map_and_convert returns None both for an unknown measurement and
        # for a value that would not parse, so the mapper's own counter is
        # the only way to attribute the loss correctly.
        invalid_before = getattr(self.field_mapper, "invalid_numeric_count", 0)
        mapped = self.field_mapper.map_and_convert(measurement, value_str)
        if not mapped:
            invalid_after = getattr(self.field_mapper, "invalid_numeric_count", 0)
            if invalid_after > invalid_before:
                self.unparsable_rows += 1
            else:
                self.unmapped_rows += 1
            return

        target_field, converted = mapped
        self._emit(target_field, timestamp, converted)

    def _add(self, field_name: str, timestamp: str, value_str: str) -> None:
        value = self._to_float(value_str)
        if value is None:
            self.unparsable_rows += 1
            return
        self._emit(field_name, timestamp, value)

    def _emit(self, field_name: str, timestamp: str, value: float) -> None:
        if not math.isfinite(value):
            self.unparsable_rows += 1
            return
        self.normalizer.add_point(
            timestamp_utc=timestamp,
            field_name=field_name,
            value=value,
        )
        self.mapped_points += 1

    @staticmethod
    def _to_float(value_str: Any) -> Optional[float]:
        try:
            value = float(value_str)
        except (ValueError, TypeError):
            return None
        return value if math.isfinite(value) else None
