"""
Step 5: a simple tiered drought-index insurance contract and its evaluation.

Contract
  Index  : lowest growing-season SPI-3 (windows ending Jul-Oct).
  Payout : tiered, e.g. SPI-3 <= -1.0 -> 25%, <= -1.5 -> 50%, <= -2.0 -> 100%
           of the sum insured. The sum insured is a fixed share of expected
           yield, so payouts are expressed as "% of expected yield".

"Actual" loss
  We fit a linear trend to each region's yield (as an analyst would, without
  knowing the true synthetic trend). Loss = shortfall below trend, as a
  fraction of trend yield. A "loss year" has a shortfall above
  config.LOSS_THRESHOLD (10%).

Evaluation: a 2x2 table of "paid?" vs "loss year?"
                      loss year       no loss year
      payout          hit             false alarm
      no payout       miss            correct negative
  hit rate          = hits / loss years       (share of losses compensated)
  false alarm ratio = false alarms / payouts  (share of payouts not needed)
  basis risk        = mismatch between payout and loss *amounts*, reported as
                      RMSE and mean absolute gap (both in % of expected
                      yield), plus the payout-loss correlation.
"""

import numpy as np
import pandas as pd

from src import config


def payout_fraction(index_value, tiers=config.PAYOUT_TIERS):
    """Payout as a fraction of the sum insured for one index value."""
    for threshold, payout in tiers:        # tiers run most severe first
        if index_value <= threshold:
            return payout
    return 0.0


def yield_losses(yields):
    """Add detrended yield and loss columns to a region/year yield table."""
    pieces = []
    for region, df in yields.groupby("region", sort=False):
        df = df.sort_values("year").copy()
        slope, intercept = np.polyfit(df["year"], df["yield_t_ha"], deg=1)
        df["trend_t_ha"] = intercept + slope * df["year"]
        shortfall = (df["trend_t_ha"] - df["yield_t_ha"]) / df["trend_t_ha"]
        df["loss_frac"] = shortfall.clip(lower=0)
        df["loss_year"] = df["loss_frac"] > config.LOSS_THRESHOLD
        pieces.append(df)
    return pd.concat(pieces, ignore_index=True)


def apply_contract(season, yields):
    """
    Combine the insurance index with yield losses, one row per region-year.

    Returns columns: region, year, trigger_spi3, tier_payout (fraction of sum
    insured), payout_frac (fraction of expected yield), paid, loss_frac,
    loss_year, plus the yield columns.
    """
    df = season.merge(yield_losses(yields), on=["region", "year"])
    df["tier_payout"] = df["trigger_spi3"].apply(payout_fraction)
    df["payout_frac"] = df["tier_payout"] * config.SUM_INSURED_FRACTION
    df["paid"] = df["tier_payout"] > 0
    return df


def _metrics(df):
    """Skill scores for one group of region-years."""
    hits = int((df["paid"] & df["loss_year"]).sum())
    misses = int((~df["paid"] & df["loss_year"]).sum())
    false_alarms = int((df["paid"] & ~df["loss_year"]).sum())
    correct_neg = int((~df["paid"] & ~df["loss_year"]).sum())
    gap = df["payout_frac"] - df["loss_frac"]
    return {
        "n_years": len(df),
        "loss_years": hits + misses,
        "payouts": hits + false_alarms,
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "correct_negatives": correct_neg,
        "hit_rate": hits / (hits + misses) if hits + misses else np.nan,
        "false_alarm_ratio": (false_alarms / (hits + false_alarms)
                              if hits + false_alarms else np.nan),
        "basis_risk_rmse": float(np.sqrt(np.mean(gap**2))),
        "mean_abs_gap": float(np.mean(np.abs(gap))),
        "payout_loss_corr": float(np.corrcoef(df["payout_frac"],
                                              df["loss_frac"])[0, 1]),
        "total_paid": float(df["payout_frac"].sum()),
        "total_loss": float(df["loss_frac"].sum()),
    }


def evaluate_contract(contract):
    """Skill metrics for each region and for all regions pooled."""
    rows = [{"region": region, **_metrics(df)}
            for region, df in contract.groupby("region", sort=False)]
    rows.append({"region": "All regions", **_metrics(contract)})
    return pd.DataFrame(rows).round(3)
