"""
Checks on the website export (src/export_site.py).

The site's contract explorer recomputes the insurance index in the browser
from the exported SPI-3 windows, so the export must let it reproduce the
pipeline's index exactly. Run with:  python -m pytest -q
"""

import json

import numpy as np
import pytest

from src import config
from src.drought_events import find_events_all_regions
from src.export_site import (annual_payload, candidate_windows, config_payload,
                             events_payload, metrics_payload, monthly_payload)
from src.generate_rainfall import generate_rainfall
from src.generate_yield import generate_yield
from src.insurance import apply_contract, evaluate_contract
from src.spi import compute_spi_table, growing_season_table


@pytest.fixture(scope="module")
def pipeline():
    """Steps 1-5 of run_pipeline.py, in memory (no files, no figures)."""
    rain = generate_rainfall()
    spi = compute_spi_table(rain, config.SPI_SCALES, config.SPI_CALIBRATION)
    season = growing_season_table(spi, config.GROWING_SEASON_END_MONTH,
                                  config.TRIGGER_WINDOW_END_MONTHS,
                                  config.GROWING_SEASON_MONTHS)
    events = find_events_all_regions(spi)
    contract = apply_contract(season, generate_yield(season))
    return dict(rain=rain, spi=spi, events=events, contract=contract,
                metrics=evaluate_contract(contract))


def test_payloads_are_strict_json(pipeline):
    """NaN is not valid JSON; browsers would refuse to parse the file."""
    p = pipeline
    for payload in (config_payload(p["metrics"]),
                    monthly_payload(p["rain"], p["spi"]),
                    annual_payload(p["spi"], p["contract"]),
                    events_payload(p["events"]),
                    metrics_payload(p["metrics"])):
        json.dumps(payload, allow_nan=False)


def test_candidate_windows_cover_the_contract():
    """The explorer can only switch on windows that were exported."""
    assert set(config.TRIGGER_WINDOW_END_MONTHS) <= set(candidate_windows())


def test_exported_windows_reproduce_the_index(pipeline):
    """min(SPI-3 over the contract's windows) must equal the pipeline's index."""
    rows = annual_payload(pipeline["spi"], pipeline["contract"])
    assert len(rows) == len(config.REGIONS) * (config.END_YEAR - config.START_YEAR + 1)
    for r in rows:
        index = min(r["spi3"][str(m)] for m in config.TRIGGER_WINDOW_END_MONTHS)
        assert index == pytest.approx(r["trigger_spi3"], abs=1e-6)


def test_monthly_series_align(pipeline):
    """Every region's series has one value per month of the study period."""
    monthly = monthly_payload(pipeline["rain"], pipeline["spi"])
    n = len(monthly["dates"])
    assert n == 12 * (config.END_YEAR - config.START_YEAR + 1)
    for series in monthly["regions"].values():
        assert all(len(v) == n for v in series.values())
        # the first months of SPI-12 cannot be computed and must be null
        assert series["spi_12"][:11] == [None] * 11
        assert np.isfinite(series["spi_12"][11])
