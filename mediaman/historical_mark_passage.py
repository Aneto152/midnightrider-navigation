"""Wire the deterministic geometric mark-passage detector to historical rows.

Stage B consumes the Stage A historical transport contract exclusively:
normalized MCP rows carrying ``series``, ``source_id``, ``timestamp_utc`` and
``value``. Position tracks are grouped per emitting source and each source is
detected independently, so one source can never borrow another source's fixes.
Cross-source consensus is derived only after the independent results exist.

Acceptance is delegated to
:func:`mediaman.mark_passage_geometry.detect_mark_passage`, which uses route
geometry and raw position exclusively. Plotter-derived shortcuts and temporal
manoeuvre patterns such as a gybe or a sustained turn are never treated as
mark-passage evidence.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

try:  # pragma: no cover - import style depends on the caller's sys.path
    from mediaman.mark_passage_geometry import detect_mark_passage, normalize_route_snapshot
except ImportError:  # pragma: no cover
    from mark_passage_geometry import detect_mark_passage, normalize_route_snapshot

ROUTE_SERIES = "route_waypoints"
LATITUDE_SERIES = "latitude"
LONGITUDE_SERIES = "longitude"
DEFAULT_CONSENSUS_WINDOW_SECONDS = 120.0


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 instant into an aware UTC datetime, or return None."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def route_snapshots_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return raw route snapshots, preserving their emitting source and instant."""
    snapshots: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping) or row.get("series") != ROUTE_SERIES:
            continue
        snapshots.append({
            "timestamp": row.get("timestamp_utc"),
            "value": row.get("value"),
            "source": row.get("source_id", ""),
        })
    return snapshots


def usable_route_snapshots(
    snapshots: Iterable[Mapping[str, Any]],
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Normalize route snapshots and isolate null/invalid plotter snapshots.

    The plotter can publish a transient route containing a placeholder waypoint
    with null coordinates. Such a snapshot is not a detector error when other
    route snapshots are usable; it is excluded individually and recorded with
    its source, timestamp and sanitized validation message.
    """
    usable: list[Any] = []
    rejected: list[dict[str, Any]] = []
    for raw in snapshots:
        try:
            usable.append(normalize_route_snapshot(raw))
        except ValueError as error:
            rejected.append({
                "source": str(raw.get("source", "")),
                "timestamp": raw.get("timestamp"),
                "error": str(error),
            })
    return usable, rejected


def _route_signature(route: Any) -> tuple[tuple[str, float, float], ...]:
    """Return a stable topology/coordinate signature for one route snapshot."""
    return tuple((item.name, round(item.latitude, 7), round(item.longitude, 7))
                 for item in route.waypoints)


def route_snapshots_by_source(
    snapshots: Iterable[Mapping[str, Any]],
) -> dict[str, list[Any]]:
    """Group already-normalized route snapshots by their emitting source."""
    grouped: dict[str, list[Any]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[str(snapshot.get("source", ""))].append(snapshot)
    return grouped


def _dedupe_events(events: Iterable[Mapping[str, Any]], window_seconds: float) -> list[dict[str, Any]]:
    """Collapse replay duplicates while retaining the closest geometric event."""
    ordered = []
    for event in events:
        instant = _parse_timestamp(event.get("passage_time_utc"))
        if instant is not None:
            ordered.append((str(event.get("mark_name", "")), instant, dict(event)))
    ordered.sort(key=lambda item: (item[0], item[1]))
    groups: list[list[tuple[str, datetime, dict[str, Any]]]] = []
    for item in ordered:
        if groups:
            previous = groups[-1][-1]
            if item[0] == previous[0] and abs((item[1] - previous[1]).total_seconds()) <= window_seconds:
                groups[-1].append(item)
                continue
        groups.append([item])
    result = []
    for group in groups:
        representative = min(
            group,
            key=lambda item: (float(item[2].get("minimum_distance_nm", float("inf"))), item[1]),
        )[2]
        representative["raw_candidates_in_cluster"] = len(group)
        representative["cluster_window_seconds"] = window_seconds
        result.append(representative)
    return result


def _historical_route_detection(
    route_groups: Mapping[str, Sequence[Any]],
    track: Sequence[Mapping[str, Any]],
    acceptance_start: Any | None,
    acceptance_end: Any | None,
    consensus_window_seconds: float,
) -> dict[str, Any]:
    """Replay each route topology that existed before the historical passage.

    The geometry detector intentionally selects the latest route at its
    reference time. For historical analysis, that would incorrectly replace
    the pre-passage ``THE RACE -> BUZZARD`` route with the post-passage
    ``BUZZARD -> BLOCK ISLAND EAST`` route. This wrapper replays only topology
    change points per route source, then deduplicates the resulting events.
    """
    all_events: list[dict[str, Any]] = []
    raw_candidates = 0
    implausible_candidates = 0
    route_results: dict[str, list[dict[str, Any]]] = {}
    latest_waypoints: list[dict[str, Any]] = []

    for route_source, routes in sorted(route_groups.items()):
        ordered = sorted(routes, key=lambda route: route.timestamp)
        prefixes: list[list[Any]] = []
        previous_signature = None
        for index, route in enumerate(ordered):
            signature = _route_signature(route)
            if signature != previous_signature:
                prefixes.append(ordered[: index + 1])
                previous_signature = signature
        route_results[route_source] = []
        for prefix in prefixes:
            outcome = detect_mark_passage(
                prefix,
                track,
                acceptance_start=acceptance_start,
                acceptance_end=acceptance_end,
            )
            raw_candidates += int(outcome.get("raw_candidate_count", 0))
            implausible_candidates += int(outcome.get("implausible_candidate_count", 0))
            route_results[route_source].append({
                "route_topology_status": outcome.get("route_topology_status"),
                "route_waypoints": outcome.get("route_waypoints", []),
                "raw_candidate_count": outcome.get("raw_candidate_count", 0),
                "implausible_candidate_count": outcome.get("implausible_candidate_count", 0),
                "event_count": outcome.get("event_count", 0),
            })
            latest_waypoints = outcome.get("route_waypoints", latest_waypoints)
            for event in outcome.get("events", []):
                enriched = dict(event)
                enriched["route_source"] = route_source
                all_events.append(enriched)

    events = _dedupe_events(all_events, consensus_window_seconds)
    return {
        "detector": "course_geometry_historical_route_replay",
        "route_topology_status": "HISTORICAL_ROUTE_REPLAY",
        "route_waypoints": latest_waypoints,
        "route_waypoints_skipped": 0,
        "raw_candidate_count": raw_candidates,
        "implausible_candidate_count": implausible_candidates,
        "max_plausible_speed_kn": 15.0,
        "event_count": len(events),
        "events": events,
        "route_source_results": route_results,
        "vmg_used_for_acceptance": False,
        "next_point_used_for_acceptance": False,
        "course_geometry_used_for_acceptance": True,
    }


def position_tracks_by_source(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group latitude/longitude rows into one independent track per source.

    A fix is emitted only when the same source published both coordinates for
    the same instant, so a track never mixes coordinates across sources.
    """
    pending: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        series = row.get("series")
        if series not in (LATITUDE_SERIES, LONGITUDE_SERIES):
            continue
        timestamp = row.get("timestamp_utc")
        if not isinstance(timestamp, str) or not timestamp:
            continue
        value = row.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        source = str(row.get("source_id", ""))
        pending[source].setdefault(timestamp, {})[series] = float(value)

    tracks: dict[str, list[dict[str, Any]]] = {}
    for source, instants in pending.items():
        track = [
            {
                "timestamp": timestamp,
                "latitude": coordinates[LATITUDE_SERIES],
                "longitude": coordinates[LONGITUDE_SERIES],
                "source": source,
            }
            for timestamp, coordinates in instants.items()
            if LATITUDE_SERIES in coordinates and LONGITUDE_SERIES in coordinates
        ]
        if track:
            track.sort(key=lambda item: item["timestamp"])
            tracks[source] = track
    return tracks


def _consensus(
    results_by_source: Mapping[str, Mapping[str, Any]],
    window_seconds: float,
) -> list[dict[str, Any]]:
    """Cluster already-independent per-source events by mark name and instant."""
    observations: list[tuple[str, str, datetime, Mapping[str, Any]]] = []
    for source, result in results_by_source.items():
        for event in result.get("events", []):
            instant = _parse_timestamp(event.get("passage_time_utc"))
            if instant is None:
                continue
            observations.append((str(event.get("mark_name", "")), source, instant, event))
    observations.sort(key=lambda item: (item[0], item[2]))

    consensus: list[dict[str, Any]] = []
    for mark_name, source, instant, event in observations:
        for existing in consensus:
            if existing["mark_name"] != mark_name:
                continue
            reference = _parse_timestamp(existing["passage_time_utc"])
            if reference is None:
                continue
            if abs((instant - reference).total_seconds()) <= window_seconds:
                existing["sources"] = sorted({*existing["sources"], source})
                existing["source_count"] = len(existing["sources"])
                break
        else:
            consensus.append({
                "mark_name": mark_name,
                "passage_time_utc": event.get("passage_time_utc"),
                "event_kind": event.get("event_kind"),
                "sources": [source],
                "source_count": 1,
            })
    return consensus


def detect_mark_passage_by_source(
    rows: Sequence[Mapping[str, Any]],
    acceptance_start: Any | None = None,
    acceptance_end: Any | None = None,
    consensus_window_seconds: float = DEFAULT_CONSENSUS_WINDOW_SECONDS,
) -> dict[str, Any]:
    """Detect independently per position source using historical route topology."""
    raw_route_snapshots = route_snapshots_from_rows(rows)
    usable, route_rejections = usable_route_snapshots(raw_route_snapshots)
    route_groups = route_snapshots_by_source([
        {
            "timestamp": snapshot.timestamp,
            "value": [
                {"name": item.name, "position": {"value": {
                    "latitude": item.latitude, "longitude": item.longitude}}}
                for item in snapshot.waypoints
            ],
            "source": snapshot.source,
        }
        for snapshot in usable
    ])
    # Re-normalize through the geometry contract so the grouped values remain
    # RouteSnapshot instances while keeping this module independent of its
    # concrete dataclass implementation.
    normalized_route_groups: dict[str, list[Any]] = defaultdict(list)
    for source, snapshots in route_groups.items():
        for raw in snapshots:
            normalized_route_groups[source].append(normalize_route_snapshot(raw))

    tracks = position_tracks_by_source(rows)
    results_by_source: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for source, track in sorted(tracks.items()):
        if not normalized_route_groups:
            errors[source] = "no usable route snapshot available"
            continue
        try:
            results_by_source[source] = _historical_route_detection(
                normalized_route_groups,
                track,
                acceptance_start,
                acceptance_end,
                consensus_window_seconds,
            )
        except ValueError as error:
            errors[source] = str(error)

    consensus = _consensus(results_by_source, consensus_window_seconds)
    return {
        "detector": "course_geometry_historical_route_replay",
        "route_snapshot_count": len(raw_route_snapshots),
        "route_snapshot_usable_count": len(usable),
        "route_snapshot_rejected_count": len(route_rejections),
        "route_snapshot_rejections": route_rejections,
        "route_source_count": len(normalized_route_groups),
        "route_snapshots_by_source": {
            source: len(snapshots) for source, snapshots in sorted(normalized_route_groups.items())
        },
        "position_source_count": len(tracks),
        "position_rows_by_source": {source: len(track) for source, track in sorted(tracks.items())},
        "results_by_source": results_by_source,
        "event_count_by_source": {
            source: result.get("event_count", 0) for source, result in sorted(results_by_source.items())
        },
        "consensus_events": consensus,
        "consensus_event_count": len(consensus),
        "errors_by_source": errors,
        "vmg_used_for_acceptance": False,
        "next_point_used_for_acceptance": False,
        "temporal_patterns_used_for_acceptance": False,
        "course_geometry_used_for_acceptance": True,
    }

