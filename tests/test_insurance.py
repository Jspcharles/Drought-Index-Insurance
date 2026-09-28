"""
Checks on the insurance contract and its evaluation (src/insurance.py).

The payout tiers are passed explicitly, so these tests keep working when the
contract in config.py is changed. Run with:  python -m pytest -q
"""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.insurance import evaluate_contract, payout_fraction, yield_losses

TIERS = [(-2.0, 1.00), (-1.5, 0.50), (-1.0, 0.25)]


@pytest.mark.parametrize("index, expected", [
    (-2.5, 1.00),    # deeper than the most severe tier
    (-2.0, 1.00),    # thresholds are inclusive (index <= threshold)
    (-1.99, 0.50),
    (-1.5, 0.50),
    (-1.2, 0.25),
    (-1.0, 0.25),
    (-0.99, 0.0),    # above the trigger: no payout
    (1.0, 0.0),
])
def test_payout_tiers(index, expected):
    assert payout_fraction(index, TIERS) == expected


def test_loss_is_measured_against_fitted_trend():
    """Yields on a straight line except one bad year: only that year is a loss."""
    years = np.arange(2000, 2020)
    yields = 2.0 + 0.02 * (years - 2000)
    bad_year = 2010
    yields[years == bad_year] *= 1 - 3 * config.LOSS_THRESHOLD
    df = yield_losses(pd.DataFrame({"region": "A", "year": years,
                                    "yield_t_ha": yields}))

    bad = df[df["year"] == bad_year].iloc[0]
    assert bad["loss_year"]
    # The dip pulls the fitted trend down slightly, so every other year sits
    # above the trend: no loss, and never a negative loss.
    others = df[df["year"] != bad_year]
    assert (others["loss_frac"] == 0).all()
    assert not others["loss_year"].any()


def test_metrics_from_a_known_two_by_two_table():
    """One region-year of each outcome: hit, miss, false alarm, correct no."""
    contract = pd.DataFrame({
        "region":      ["A", "A", "A", "A"],
        "paid":        [True, False, True, False],
        "loss_year":   [True, True, False, False],
        "payout_frac": [0.25, 0.00, 0.125, 0.00],
        "loss_frac":   [0.20, 0.30, 0.05, 0.00],
    })
    metrics = evaluate_contract(contract)
    a = metrics[metrics["region"] == "A"].iloc[0]

    assert (a["hits"], a["misses"], a["false_alarms"], a["correct_negatives"]) == (1, 1, 1, 1)
    assert a["hit_rate"] == pytest.approx(0.5)
    assert a["false_alarm_ratio"] == pytest.approx(0.5)
    gaps = np.array([0.05, -0.30, 0.075, 0.0])
    assert a["basis_risk_rmse"] == pytest.approx(np.sqrt(np.mean(gaps**2)), abs=1e-3)
    assert a["mean_abs_gap"] == pytest.approx(np.mean(np.abs(gaps)), abs=1e-3)


def test_pooled_row_combines_regions():
    """The last row pools every region-year."""
    contract = pd.DataFrame({
        "region":      ["A", "A", "B", "B"],
        "paid":        [True, False, True, True],
        "loss_year":   [True, False, True, False],
        "payout_frac": [0.25, 0.0, 0.5, 0.125],
        "loss_frac":   [0.2, 0.0, 0.4, 0.0],
    })
    metrics = evaluate_contract(contract)
    assert list(metrics["region"]) == ["A", "B", "All regions"]
    pooled = metrics.iloc[-1]
    assert pooled["n_years"] == 4
    assert pooled["hits"] == 2
    assert pooled["false_alarms"] == 1
    assert pooled["hit_rate"] == pytest.approx(1.0)
