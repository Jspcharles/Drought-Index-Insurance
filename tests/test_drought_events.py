"""
Checks on run theory (src/drought_events.py).

Each test builds a short SPI series whose drought events can be worked out
by hand, so the expected start, end, duration and severity are known exactly.
Run with:  python -m pytest -q
"""

import numpy as np
import pandas as pd
import pytest

from src.drought_events import find_events


def monthly_spi(values, start="2000-01"):
    """Wrap SPI values in a Series with a monthly date index."""
    index = pd.date_range(start, periods=len(values), freq="MS")
    return pd.Series(values, index=index, dtype=float)


def test_two_runs_are_found_with_correct_characteristics():
    """Months 2-3 and month 5 are below -1: two events."""
    spi = monthly_spi([0.3, -1.5, -2.0, 0.1, -1.2, 0.4])
    events = find_events(spi, threshold=-1.0, min_duration=1)

    assert len(events) == 2
    first, second = events.iloc[0], events.iloc[1]
    assert first["start"] == pd.Timestamp("2000-02-01")
    assert first["end"] == pd.Timestamp("2000-03-01")
    assert first["duration"] == 2
    assert first["severity"] == pytest.approx(3.5)     # 1.5 + 2.0
    assert first["intensity"] == pytest.approx(1.75)   # 3.5 / 2
    assert first["peak_spi"] == pytest.approx(-2.0)
    assert second["duration"] == 1
    assert second["severity"] == pytest.approx(1.2)


def test_threshold_is_strict():
    """SPI exactly at the threshold is not "below" it, so it is not drought."""
    spi = monthly_spi([0.0, -1.0, 0.0])
    assert find_events(spi, threshold=-1.0, min_duration=1).empty


def test_run_still_open_at_the_end_is_closed():
    """A drought continuing into the final month must still be recorded."""
    spi = monthly_spi([0.5, 0.2, -1.1, -1.3])
    events = find_events(spi, threshold=-1.0, min_duration=1)
    assert len(events) == 1
    assert events.iloc[0]["end"] == pd.Timestamp("2000-04-01")
    assert events.iloc[0]["duration"] == 2


def test_nan_months_break_a_run():
    """NaN (e.g. SPI warm-up months) counts as "not in drought"."""
    spi = monthly_spi([-1.5, np.nan, -1.5])
    events = find_events(spi, threshold=-1.0, min_duration=1)
    assert list(events["duration"]) == [1, 1]


def test_min_duration_filters_short_events():
    """With a minimum of 2 months, the one-month event is dropped."""
    spi = monthly_spi([-1.5, 0.0, -1.2, -1.4, 0.0])
    events = find_events(spi, threshold=-1.0, min_duration=2)
    assert len(events) == 1
    assert events.iloc[0]["duration"] == 2


def test_no_drought_gives_empty_table_with_columns():
    """An empty result still has the expected columns, so later steps work."""
    events = find_events(monthly_spi([0.5, 1.0, -0.5]), threshold=-1.0)
    assert events.empty
    assert list(events.columns) == ["start", "end", "duration", "severity",
                                    "intensity", "peak_spi"]
