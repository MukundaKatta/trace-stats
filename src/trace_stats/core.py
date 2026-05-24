"""Compute statistics on numeric fields in agent JSONL traces."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class TraceStatsError(Exception):
    """Base exception for trace-stats failures."""


@dataclass
class FieldStats:
    """Statistics for a single numeric field across a set of events.

    Attributes:
        field: the field name.
        count: number of events that had this field with a numeric value.
        total: sum of all values.
        mean: arithmetic mean.
        minimum: smallest value.
        maximum: largest value.
        p50: 50th percentile (median).
        p90: 90th percentile.
        p95: 95th percentile.
        p99: 99th percentile.
        stddev: sample standard deviation (0.0 when count <= 1).
    """

    field: str
    count: int
    total: float
    mean: float
    minimum: float
    maximum: float
    p50: float
    p90: float
    p95: float
    p99: float
    stddev: float

    def __str__(self) -> str:
        return (
            f"{self.field}: n={self.count} mean={self.mean:.3g} "
            f"p50={self.p50:.3g} p95={self.p95:.3g} p99={self.p99:.3g} "
            f"min={self.minimum:.3g} max={self.maximum:.3g}"
        )


def _percentile(sorted_vals: list[float], p: float) -> float:
    """Nearest-rank percentile, 0 < p <= 100. sorted_vals must be pre-sorted."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    # Nearest rank method (inclusive): rank = ceil(p/100 * n)
    rank = math.ceil(p / 100.0 * n)
    rank = max(1, min(rank, n))
    return sorted_vals[rank - 1]


def _extract_numeric(event: dict[str, Any], field: str) -> float | None:
    """Return float value of field from event, or None if missing/non-numeric."""
    v = event.get(field)
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def field_stats(
    events: Iterable[dict[str, Any]],
    field: str,
) -> FieldStats:
    """Compute statistics on a numeric field across events.

    Args:
        events: iterable of event dicts.
        field: the field name to analyse.

    Returns:
        FieldStats dataclass. If no events have the field, all numeric
        attributes are 0.0 and count is 0.

    Note:
        All values are collected into memory before computing percentiles.
        This is fine for typical agent trace files (thousands of events).
    """
    values: list[float] = []

    for ev in events:
        v = _extract_numeric(ev, field)
        if v is not None:
            values.append(v)

    if not values:
        return FieldStats(
            field=field, count=0, total=0.0, mean=0.0,
            minimum=0.0, maximum=0.0, p50=0.0, p90=0.0, p95=0.0, p99=0.0,
            stddev=0.0,
        )

    values.sort()
    n = len(values)
    total = sum(values)
    mean = total / n

    # Sample standard deviation (ddof=1), or 0 for single value.
    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0

    return FieldStats(
        field=field,
        count=n,
        total=total,
        mean=mean,
        minimum=values[0],
        maximum=values[-1],
        p50=_percentile(values, 50),
        p90=_percentile(values, 90),
        p95=_percentile(values, 95),
        p99=_percentile(values, 99),
        stddev=stddev,
    )


def multi_field_stats(
    events: Iterable[dict[str, Any]],
    fields: list[str],
) -> dict[str, FieldStats]:
    """Compute stats for multiple fields in one pass.

    Args:
        events: iterable of event dicts (consumed once).
        fields: list of field names.

    Returns:
        Dict mapping field name to FieldStats.
    """
    # Collect all events first so we can scan multiple fields.
    rows: list[dict[str, Any]] = list(events)
    return {f: field_stats(rows, f) for f in fields}


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSONL file into a list of event dicts. Blank lines skipped."""
    p = Path(path)
    if not p.exists():
        raise TraceStatsError(f"file does not exist: {p}")
    events: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise TraceStatsError(f"{p}:{lineno}: invalid JSON: {e.msg}") from e
            if not isinstance(obj, dict):
                raise TraceStatsError(
                    f"{p}:{lineno}: expected JSON object, got {type(obj).__name__}"
                )
            events.append(obj)
    return events
