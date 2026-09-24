"""Deterministic, Vulcan-independent mark-passage geometry.

The detector accepts only ordered route snapshots and vessel positions as
primary evidence. VMG and plotter nextPoint values are intentionally absent
from this module: they are diagnostic observations, not acceptance signals.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import math
from typing import Any, Iterable, Mapping, Sequence


EARTH_RADIUS_NM = 3440.065
NM_PER_DEGREE = 60.0


@dataclass(frozen=True)
class Waypoint:
    """One named route waypoint with validated finite coordinates."""

    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteSnapshot:
    """One observed state of the plotter route, with unusable waypoints counted."""

    timestamp: datetime
    waypoints: tuple[Waypoint, ...]
    source: str = ""
    skipped_waypoints: int = 0


@dataclass(frozen=True)
class PositionSample:
    """One raw vessel position fix, attributed to its emitting source."""

    timestamp: datetime
    latitude: float
    longitude: float
    source: str = ""


@dataclass(frozen=True)
class MarkPassageEvent:
    """One accepted mark passage together with the geometry that justifies it."""

    mark_name: str
    mark_latitude: float
    mark_longitude: float
    passage_time_utc: str
    minimum_distance_nm: float
    distance_before_nm: float
    distance_after_nm: float
    closing_rate_before_kn: float
    closing_rate_after_kn: float
    geometric_closing_rate_sign_flip: bool
    route_progress_nm: float
    event_kind: str
    raw_candidates_in_cluster: int = 1
    cluster_window_seconds: float = 120.0
    speed_before_kn: float = 0.0
    speed_after_kn: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return the event as a plain JSON-serialisable mapping."""
        return asdict(self)


def _timestamp(value: Any) -> datetime:
    """Parse an ISO-8601 instant or datetime into an aware UTC datetime."""
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        result = datetime.fromisoformat(text)
    else:
        raise ValueError("timestamp must be ISO-8601 text or datetime")
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    """Render a datetime as millisecond-precision ISO-8601 with a Z suffix."""
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _number(value: Any, name: str) -> float:
    """Coerce a raw value to a finite float.

    Real route snapshots published by the plotter carry waypoints whose
    coordinates are null. Those must surface as ValueError so that callers
    can skip one waypoint instead of losing the whole snapshot to a
    TypeError raised from inside float().
    """
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name} is missing")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} is not a number") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _position_dict(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    """Unwrap the Signal K position envelope, which nests coordinates under value."""
    position = raw.get("position", raw)
    if not isinstance(position, Mapping):
        raise ValueError("position must be an object")
    value = position.get("value")
    if isinstance(value, Mapping):
        position = value
    return position


def normalize_waypoint(raw: Mapping[str, Any]) -> Waypoint:
    """Validate one raw waypoint, raising ValueError when it is unusable."""
    if not isinstance(raw, Mapping):
        raise ValueError("waypoint must be an object")
    position = _position_dict(raw)
    latitude = _number(position.get("latitude", position.get("lat")), "latitude")
    longitude = _number(position.get("longitude", position.get("lon")), "longitude")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude outside [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude outside [-180, 180]")
    name = str(raw.get("name") or raw.get("id") or "").strip()
    if not name:
        raise ValueError("waypoint name is required")
    return Waypoint(name, latitude, longitude)


def normalize_route_snapshot(raw: Mapping[str, Any]) -> RouteSnapshot:
    """Validate one route snapshot, skipping unusable waypoints but counting them.

    A snapshot survives as long as two usable waypoints remain, because real
    plotter routes publish waypoints with null coordinates. The number of
    skipped waypoints is preserved so nothing is dropped silently.
    """
    value = raw.get("value", raw.get("waypoints", raw))
    if isinstance(value, Mapping) and isinstance(value.get("value"), str):
        value = value["value"]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("route snapshot must contain a waypoint list")
    usable: list[Waypoint] = []
    skipped = 0
    for item in value:
        try:
            usable.append(normalize_waypoint(item))
        except ValueError:
            skipped += 1
    if len(usable) < 2:
        raise ValueError(
            "route snapshot requires at least two usable waypoints "
            f"({len(usable)} usable, {skipped} skipped)")
    return RouteSnapshot(
        _timestamp(raw.get("timestamp", raw.get("_time"))),
        tuple(usable),
        str(raw.get("source", "")),
        skipped,
    )


def normalize_position(raw: Mapping[str, Any]) -> PositionSample:
    """Validate one raw position fix into a PositionSample."""
    position = _position_dict(raw)
    latitude = _number(position.get("latitude", position.get("lat")), "latitude")
    longitude = _number(position.get("longitude", position.get("lon")), "longitude")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude outside [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude outside [-180, 180]")
    return PositionSample(_timestamp(raw.get("timestamp", raw.get("_time"))), latitude, longitude, str(raw.get("source", "")))


def distance_nm(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    """Return the great-circle distance between two points, in nautical miles."""
    p1 = math.radians(a_lat)
    p2 = math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * EARTH_RADIUS_NM * math.asin(min(1.0, math.sqrt(h)))


def _project_to_route(sample: PositionSample, route: RouteSnapshot) -> tuple[float, float, int]:
    """Project a fix onto the route, returning chainage, cross-track and leg index."""
    """Return cumulative chainage, cross-track distance and nearest leg."""
    best: tuple[float, float, int] | None = None
    chainage = 0.0
    for leg_index, (a, b) in enumerate(zip(route.waypoints, route.waypoints[1:])):
        midpoint_lat = math.radians((a.latitude + b.latitude) / 2.0)
        scale = math.cos(midpoint_lat)
        bx = (b.longitude - a.longitude) * NM_PER_DEGREE * scale
        by = (b.latitude - a.latitude) * NM_PER_DEGREE
        px = (sample.longitude - a.longitude) * NM_PER_DEGREE * scale
        py = (sample.latitude - a.latitude) * NM_PER_DEGREE
        length2 = bx * bx + by * by
        ratio = 0.0 if length2 == 0 else max(0.0, min(1.0, (px * bx + py * by) / length2))
        cross_track = math.hypot(px - ratio * bx, py - ratio * by)
        leg_length = distance_nm(a.latitude, a.longitude, b.latitude, b.longitude)
        candidate = (chainage + ratio * leg_length, cross_track, leg_index)
        if best is None or candidate[1] < best[1]:
            best = candidate
        chainage += leg_length
    if best is None:
        raise ValueError("route has no leg")
    return best


def _route_chainages(route: RouteSnapshot) -> list[float]:
    """Return the cumulative along-route distance of each waypoint."""
    values = [0.0]
    for a, b in zip(route.waypoints, route.waypoints[1:]):
        values.append(values[-1] + distance_nm(a.latitude, a.longitude, b.latitude, b.longitude))
    return values


def _representative_route(
    snapshots: Sequence[RouteSnapshot],
    reference_time: datetime | None = None,
) -> tuple[RouteSnapshot, str]:
    """Pick the latest snapshot at or before reference_time and classify topology.

    A route that changes while sharing at least one waypoint is a normal
    plotter advance and yields TRANSITION_OBSERVED; disjoint route sets
    yield UNCERTAIN.
    """
    if not snapshots:
        raise ValueError("at least one route snapshot is required")
    ordered = sorted(snapshots, key=lambda snapshot: snapshot.timestamp)
    eligible = [snapshot for snapshot in ordered if reference_time is None or snapshot.timestamp <= reference_time]
    route = (eligible or ordered)[-1]
    name_groups = {tuple(w.name for w in snapshot.waypoints) for snapshot in snapshots}
    transition = "STABLE"
    if len(name_groups) > 1:
        transition = "TRANSITION_OBSERVED" if any(
            set(left) & set(right)
            for left in name_groups
            for right in name_groups
            if left != right
        ) else "UNCERTAIN"
    return route, transition


def _cluster(events: Sequence[MarkPassageEvent], window_seconds: float) -> list[MarkPassageEvent]:
    """Collapse repeated candidates for the same mark into one physical event.

    The representative is the minimum-distance candidate. Note that the
    minimum distance is rounded to four decimals, so ties are broken by the
    earliest timestamp; the representative instant therefore carries an
    uncertainty of about one sampling interval.
    """
    ordered = sorted(events, key=lambda event: (event.mark_name, event.passage_time_utc))
    groups: list[list[MarkPassageEvent]] = []
    for event in ordered:
        if groups:
            previous = groups[-1][-1]
            delta = abs((_timestamp(event.passage_time_utc) - _timestamp(previous.passage_time_utc)).total_seconds())
            if event.mark_name == previous.mark_name and delta <= window_seconds:
                groups[-1].append(event)
                continue
        groups.append([event])
    result: list[MarkPassageEvent] = []
    for group in groups:
        representative = min(group, key=lambda event: (event.minimum_distance_nm, event.passage_time_utc))
        result.append(MarkPassageEvent(**{
            **representative.to_dict(),
            "raw_candidates_in_cluster": len(group),
            "cluster_window_seconds": window_seconds,
        }))
    return result


def detect_mark_passage(
    route_snapshots: Iterable[Mapping[str, Any] | RouteSnapshot],
    positions: Iterable[Mapping[str, Any] | PositionSample],
    *,
    radius_nm: float = 0.10,
    edge_seconds: float = 90.0,
    event_cluster_seconds: float = 120.0,
    max_plausible_speed_kn: float = 15.0,
    acceptance_start: Any | None = None,
    acceptance_end: Any | None = None,
) -> dict[str, Any]:
    """Detect named route-waypoint passages from route geometry and track only.

    Acceptance uses route geometry and raw position exclusively. VMG and the
    plotter nextPoint are never consulted.

    ``max_plausible_speed_kn`` rejects a candidate whose supporting samples
    imply an average speed the vessel cannot reach. It exists to discard
    position outliers, which were measured on source N2K.0 on 2026-09-05
    (a 15.6 nm displacement across 90 s, i.e. 624 kn). It is an outlier
    filter, not a performance model of the vessel, and it is deliberately
    exposed as a parameter so it can be revised against multi-day data.
    """
    if radius_nm <= 0 or edge_seconds <= 0 or event_cluster_seconds <= 0:
        raise ValueError("radius and time parameters must be positive")
    if max_plausible_speed_kn <= 0:
        raise ValueError("max_plausible_speed_kn must be positive")
    routes = [item if isinstance(item, RouteSnapshot) else normalize_route_snapshot(item) for item in route_snapshots]
    track = [item if isinstance(item, PositionSample) else normalize_position(item) for item in positions]
    track.sort(key=lambda item: item.timestamp)
    reference_time = _timestamp(acceptance_end) if acceptance_end is not None else None
    route, topology_status = _representative_route(routes, reference_time)
    chainages = _route_chainages(route)
    projected = [(sample, *_project_to_route(sample, route)) for sample in track]
    start = _timestamp(acceptance_start) if acceptance_start is not None else None
    end = _timestamp(acceptance_end) if acceptance_end is not None else None
    raw_events: list[MarkPassageEvent] = []
    implausible_candidates = 0

    for index, waypoint in enumerate(route.waypoints):
        inside = [i for i, (sample, *_rest) in enumerate(projected)
                  if distance_nm(sample.latitude, sample.longitude, waypoint.latitude, waypoint.longitude) <= radius_nm]
        if not inside:
            continue
        runs: list[list[int]] = [[inside[0]]]
        for item in inside[1:]:
            if item == runs[-1][-1] + 1:
                runs[-1].append(item)
            else:
                runs.append([item])
        for run in runs:
            minimum_index = min(run, key=lambda i: distance_nm(
                projected[i][0].latitude, projected[i][0].longitude, waypoint.latitude, waypoint.longitude))
            before_index = min(range(len(projected)), key=lambda i: abs(
                (projected[i][0].timestamp - projected[minimum_index][0].timestamp).total_seconds() + edge_seconds))
            after_index = min(range(len(projected)), key=lambda i: abs(
                (projected[i][0].timestamp - projected[minimum_index][0].timestamp).total_seconds() - edge_seconds))
            if before_index >= minimum_index or after_index <= minimum_index:
                continue
            before = projected[before_index][0]
            minimum = projected[minimum_index][0]
            after = projected[after_index][0]
            d_before = distance_nm(before.latitude, before.longitude, waypoint.latitude, waypoint.longitude)
            d_minimum = distance_nm(minimum.latitude, minimum.longitude, waypoint.latitude, waypoint.longitude)
            d_after = distance_nm(after.latitude, after.longitude, waypoint.latitude, waypoint.longitude)
            dt_before = (minimum.timestamp - before.timestamp).total_seconds()
            dt_after = (after.timestamp - minimum.timestamp).total_seconds()
            if dt_before <= 0 or dt_after <= 0:
                continue
            closing_before = (d_before - d_minimum) / (dt_before / 3600.0)
            closing_after = (d_minimum - d_after) / (dt_after / 3600.0)
            if not (d_before > d_minimum and d_after > d_minimum and closing_before > 0 > closing_after):
                continue
            passage_time = minimum.timestamp
            if start is not None and passage_time < start:
                continue
            if end is not None and passage_time > end:
                continue
            progress = projected[after_index][1] - projected[before_index][1]
            event_kind = "ROUTE_START_ENDPOINT_CANDIDATE" if index == 0 else (
                "ROUTE_END_ENDPOINT_CANDIDATE" if index == len(route.waypoints) - 1 else "INTERIOR_WAYPOINT_CANDIDATE"
            )
            leg_before_nm = distance_nm(
                before.latitude, before.longitude, minimum.latitude, minimum.longitude)
            leg_after_nm = distance_nm(
                minimum.latitude, minimum.longitude, after.latitude, after.longitude)
            speed_before_kn = leg_before_nm / (dt_before / 3600.0)
            speed_after_kn = leg_after_nm / (dt_after / 3600.0)
            if max(speed_before_kn, speed_after_kn) > max_plausible_speed_kn:
                implausible_candidates += 1
                continue
            raw_events.append(MarkPassageEvent(
                mark_name=waypoint.name,
                mark_latitude=waypoint.latitude,
                mark_longitude=waypoint.longitude,
                passage_time_utc=_iso(passage_time),
                minimum_distance_nm=round(d_minimum, 4),
                distance_before_nm=round(d_before, 4),
                distance_after_nm=round(d_after, 4),
                closing_rate_before_kn=round(closing_before, 3),
                closing_rate_after_kn=round(closing_after, 3),
                geometric_closing_rate_sign_flip=True,
                route_progress_nm=round(progress, 4),
                event_kind=event_kind,
                speed_before_kn=round(speed_before_kn, 3),
                speed_after_kn=round(speed_after_kn, 3),
            ))

    events = _cluster(raw_events, event_cluster_seconds)
    return {
        "detector": "course_geometry",
        "route_topology_status": topology_status,
        "route_waypoints": [asdict(item) for item in route.waypoints],
        "route_waypoints_skipped": route.skipped_waypoints,
        "raw_candidate_count": len(raw_events),
        "implausible_candidate_count": implausible_candidates,
        "max_plausible_speed_kn": max_plausible_speed_kn,
        "event_count": len(events),
        "events": [event.to_dict() for event in events],
        "vmg_used_for_acceptance": False,
        "next_point_used_for_acceptance": False,
        "course_geometry_used_for_acceptance": True,
    }
