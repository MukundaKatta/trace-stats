"""Tests for trace_stats."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import math
import pytest
from trace_stats import FieldStats, TraceStatsError, field_stats, load_jsonl, multi_field_stats


# ---------------------------------------------------------------------------
# field_stats — basic
# ---------------------------------------------------------------------------

def test_empty_events():
    s = field_stats([], "duration_ms")
    assert s.count == 0
    assert s.mean == 0.0


def test_single_event():
    s = field_stats([{"duration_ms": 100.0}], "duration_ms")
    assert s.count == 1
    assert s.mean == 100.0
    assert s.minimum == 100.0
    assert s.maximum == 100.0
    assert s.stddev == 0.0


def test_two_values():
    events = [{"duration_ms": 100.0}, {"duration_ms": 200.0}]
    s = field_stats(events, "duration_ms")
    assert s.count == 2
    assert s.mean == 150.0
    assert s.minimum == 100.0
    assert s.maximum == 200.0


def test_total():
    events = [{"cost_usd": 0.01}, {"cost_usd": 0.02}, {"cost_usd": 0.03}]
    s = field_stats(events, "cost_usd")
    assert abs(s.total - 0.06) < 1e-9


def test_missing_field_skipped():
    events = [{"duration_ms": 100}, {"other": 200}, {"duration_ms": 300}]
    s = field_stats(events, "duration_ms")
    assert s.count == 2
    assert s.mean == 200.0


def test_bool_skipped():
    events = [{"duration_ms": True}, {"duration_ms": 100.0}]
    s = field_stats(events, "duration_ms")
    assert s.count == 1
    assert s.mean == 100.0


def test_string_numeric():
    events = [{"duration_ms": "150.5"}, {"duration_ms": 50.5}]
    s = field_stats(events, "duration_ms")
    assert s.count == 2
    assert abs(s.mean - 100.5) < 1e-9


def test_string_non_numeric_skipped():
    events = [{"duration_ms": "not a number"}, {"duration_ms": 100.0}]
    s = field_stats(events, "duration_ms")
    assert s.count == 1


# ---------------------------------------------------------------------------
# Percentiles
# ---------------------------------------------------------------------------

def test_p50_odd():
    # 1,2,3,4,5 → median is 3
    events = [{"v": x} for x in [3, 1, 5, 2, 4]]
    s = field_stats(events, "v")
    assert s.p50 == 3.0


def test_p50_even():
    # 1,2,3,4 → nearest rank p50 = 2 (rank = ceil(50/100*4) = 2)
    events = [{"v": x} for x in [2, 4, 1, 3]]
    s = field_stats(events, "v")
    assert s.p50 == 2.0


def test_p95_single():
    s = field_stats([{"v": 42.0}], "v")
    assert s.p95 == 42.0


def test_p99_large():
    # 100 values 1..100. p99 = ceil(99) = 99th element = 99
    events = [{"v": float(i)} for i in range(1, 101)]
    s = field_stats(events, "v")
    assert s.p99 == 99.0


def test_p90_ten_values():
    # 10 values 10,20,...,100. p90 = ceil(90/100*10)=9th = 90
    events = [{"v": float(i * 10)} for i in range(1, 11)]
    s = field_stats(events, "v")
    assert s.p90 == 90.0


# ---------------------------------------------------------------------------
# Standard deviation
# ---------------------------------------------------------------------------

def test_stddev_known():
    # values: 2, 4, 6 → mean=4, sum_sq_dev=8, sample stddev=sqrt(8/2)=2
    events = [{"v": float(x)} for x in [2, 4, 6]]
    s = field_stats(events, "v")
    assert abs(s.stddev - 2.0) < 1e-9


def test_stddev_single_is_zero():
    s = field_stats([{"v": 7.0}], "v")
    assert s.stddev == 0.0


# ---------------------------------------------------------------------------
# multi_field_stats
# ---------------------------------------------------------------------------

def test_multi_field_stats():
    events = [
        {"duration_ms": 100.0, "cost_usd": 0.01},
        {"duration_ms": 200.0, "cost_usd": 0.02},
    ]
    result = multi_field_stats(events, ["duration_ms", "cost_usd"])
    assert result["duration_ms"].count == 2
    assert result["cost_usd"].count == 2
    assert abs(result["duration_ms"].mean - 150.0) < 1e-9


def test_multi_field_stats_missing_field():
    events = [{"duration_ms": 100.0}]
    result = multi_field_stats(events, ["duration_ms", "nonexistent"])
    assert result["nonexistent"].count == 0


# ---------------------------------------------------------------------------
# FieldStats.__str__
# ---------------------------------------------------------------------------

def test_str_format():
    s = field_stats([{"v": 1.0}, {"v": 2.0}, {"v": 3.0}], "v")
    text = str(s)
    assert "v" in text
    assert "n=3" in text
    assert "p50" in text


# ---------------------------------------------------------------------------
# load_jsonl
# ---------------------------------------------------------------------------

def test_load_jsonl_missing():
    with pytest.raises(TraceStatsError, match="does not exist"):
        load_jsonl("/tmp/__trace_stats_no_such_file__.jsonl")
