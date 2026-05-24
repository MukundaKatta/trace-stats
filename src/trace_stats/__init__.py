"""trace-stats: compute latency/cost/token percentile statistics from agent JSONL traces.

Public API:
    field_stats(events, field) -> FieldStats
    multi_field_stats(events, fields) -> dict[str, FieldStats]
    load_jsonl(path) -> list[dict]
    FieldStats    — dataclass: count, mean, p50, p95, p99, min, max, stddev
    TraceStatsError — base exception
"""

from .core import FieldStats, TraceStatsError, field_stats, load_jsonl, multi_field_stats

__all__ = ["field_stats", "multi_field_stats", "load_jsonl", "FieldStats", "TraceStatsError"]
__version__ = "0.1.0"
