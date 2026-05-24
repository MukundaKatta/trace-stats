"""CLI: print statistics for numeric fields in a JSONL trace.

Usage:
    python3 -m trace_stats PATH FIELD [FIELD ...]
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="trace-stats",
        description="Compute statistics on numeric fields in an agent JSONL trace.",
    )
    parser.add_argument("path", help="JSONL file to analyse")
    parser.add_argument(
        "fields",
        nargs="+",
        help="one or more field names (e.g. duration_ms cost_usd tokens_in)",
    )
    args = parser.parse_args(argv)

    from . import TraceStatsError, load_jsonl, multi_field_stats

    try:
        events = load_jsonl(args.path)
    except TraceStatsError as e:
        print(f"trace-stats: {e}", file=sys.stderr)
        sys.exit(1)

    stats_map = multi_field_stats(events, args.fields)

    for fname, s in stats_map.items():
        if s.count == 0:
            print(f"{fname}: no values found")
            continue
        print(f"{fname}:")
        print(f"  n={s.count} total={s.total:.4g}")
        print(f"  mean={s.mean:.4g} stddev={s.stddev:.4g}")
        print(f"  min={s.minimum:.4g} p50={s.p50:.4g} p90={s.p90:.4g} p95={s.p95:.4g} p99={s.p99:.4g} max={s.maximum:.4g}")


if __name__ == "__main__":
    main()
