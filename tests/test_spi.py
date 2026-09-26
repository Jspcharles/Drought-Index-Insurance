"""
Sanity checks for the SPI calculation.

These don't prove the SPI is "correct" in every detail. They check that it
behaves the way the method says it should. Run with:  python -m pytest -q
"""

import numpy as np
import pandas as pd
import pytest

from src.spi import compute_spi


def monthly_series(values, start="1900-01"):
    """Wrap an array of monthly values in a Series with a monthly date index."""
    index = pd.date_range(start, periods=len(values), freq="MS")
    return pd.Series(values, index=index)


@pytest.fixture
def gamma_rain():
    """200 years of random monthly rain with a seasonal cycle."""
    rng = np.random.default_rng(0)
    n = 200 * 12
    seasonal_mean = 50 + 30 * np.cos(2 * np.pi * np.arange(n) / 12)
    return monthly_series(rng.gamma(shape=2.0, scale=seasonal_mean / 2.0))


@pytest.mark.parametrize("scale", [1, 3, 12])
def test_spi_is_standard_normal(gamma_rain, scale):
    """By construction, SPI over the calibration period has mean ~0, SD ~1."""
    spi = compute_spi(gamma_rain, scale).dropna()
    assert abs(spi.mean()) < 0.05
    assert abs(spi.std() - 1) < 0.05


def test_first_months_are_nan(gamma_rain):
    """SPI-12 needs 12 months of data, so the first 11 values must be NaN."""
    spi = compute_spi(gamma_rain, 12)
    assert spi.iloc[:11].isna().all()
    assert spi.iloc[11:].notna().all()


def test_zero_rain_months_handled():
    """A very dry climate (40% zero months) must give finite SPI values,
    and zero-rain months must never be scored as wetter than normal."""
    rng = np.random.default_rng(1)
    rain = rng.gamma(shape=1.5, scale=20, size=100 * 12)
    rain[rng.random(rain.size) < 0.4] = 0.0
    series = monthly_series(rain)

    spi = compute_spi(series, 1)
    assert np.isfinite(spi).all()
    assert (spi[series == 0] < 0).all()


def test_more_rain_means_higher_spi(gamma_rain):
    """Within one calendar month, SPI must increase with rainfall."""
    spi = compute_spi(gamma_rain, 1)
    january = gamma_rain.index.month == 1
    order = np.argsort(gamma_rain[january].to_numpy())
    assert np.all(np.diff(spi[january].to_numpy()[order]) > 0)


def test_dry_spell_is_detected(gamma_rain):
    """Halving rainfall for two years should push SPI-12 well below -1."""
    rain = gamma_rain.copy()
    spell = (rain.index >= "1950-01-01") & (rain.index <= "1951-12-01")
    rain[spell] *= 0.5
    spi = compute_spi(rain, 12)
    assert spi["1951-01-01":"1951-12-01"].mean() < -1.0
