"""
Step 1: generate synthetic monthly rainfall for the fictional regions.

For each region, each month's rainfall is built from four ingredients:
  1. Seasonal mean:   a smooth annual cycle peaking in the region's wet month.
  2. Persistence:     a slowly varying anomaly (AR(1) process), so that dry
                      months tend to cluster, as they do in real climates.
  3. Randomness:      the actual total is drawn from a gamma distribution
                      around that mean. Gamma is skewed like real rainfall:
                      many modest months and a few very wet ones.
  4. Dry spells:      during the multi-year spells in config.DRY_SPELLS,
                      rainfall is scaled down (e.g. to 50% of normal).
In the dry season a month can also be completely dry (0 mm).
"""

import numpy as np
import pandas as pd

from src import config


def seasonal_mean(months, annual_mm, peak_month, seasonality):
    """Mean rainfall (mm) for each calendar month: a cosine annual cycle.

    Averages to annual_mm / 12 over the year; `seasonality` sets how much
    wetter the peak month is than the average (0.6 = 60% wetter).
    """
    phase = 2 * np.pi * (months - peak_month) / 12
    return (annual_mm / 12) * (1 + seasonality * np.cos(phase))


def zero_rain_probability(months, peak_month, p_zero_max):
    """Chance of a completely dry month: zero in the wet half of the year,
    rising to p_zero_max in the driest month."""
    phase = 2 * np.pi * (months - peak_month) / 12
    return p_zero_max * np.clip(-np.cos(phase), 0, None)


def ar1_anomaly(n, phi, sigma, rng):
    """Multiplicative rainfall anomaly with month-to-month memory.

    z follows an AR(1) process with unit variance; the multiplier
    exp(sigma*z - sigma^2/2) averages to 1, so it changes the timing of
    wet/dry periods without changing long-term mean rainfall.
    """
    z = np.empty(n)
    z[0] = rng.standard_normal()
    innovation_sd = np.sqrt(1 - phi**2)
    for t in range(1, n):
        z[t] = phi * z[t - 1] + innovation_sd * rng.standard_normal()
    return np.exp(sigma * z - sigma**2 / 2)


def dry_spell_factor(dates, region):
    """Rainfall multiplier for each month: 1 normally, <1 inside a dry spell."""
    factor = np.ones(len(dates))
    for spell in config.DRY_SPELLS:
        if region in spell["regions"]:
            inside = (dates >= spell["start"]) & (
                dates <= pd.Period(spell["end"]).end_time)
            factor[inside] *= spell["factor"]
    return factor


def generate_rainfall(seed=config.SEED):
    """Return a tidy DataFrame: date, region, rain_mm (one row per month)."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(f"{config.START_YEAR}-01-01",
                          f"{config.END_YEAR}-12-01", freq="MS")
    months = dates.month.to_numpy()

    pieces = []
    for region, p in config.REGIONS.items():
        mean = seasonal_mean(months, p["annual_mm"], p["peak_month"],
                             p["seasonality"])
        mean = mean * ar1_anomaly(len(dates), config.AR1_PHI,
                                  config.AR1_SIGMA, rng)
        mean = mean * dry_spell_factor(dates, region)

        # Gamma with shape k and scale mean/k has exactly the desired mean.
        k = p["gamma_shape"]
        rain = rng.gamma(shape=k, scale=mean / k)

        # Some dry-season months receive no rain at all.
        p_zero = zero_rain_probability(months, p["peak_month"],
                                       p["p_zero_max"])
        rain[rng.random(len(dates)) < p_zero] = 0.0

        pieces.append(pd.DataFrame({"date": dates, "region": region,
                                    "rain_mm": rain.round(1)}))
    return pd.concat(pieces, ignore_index=True)


if __name__ == "__main__":
    df = generate_rainfall()
    print(df.groupby("region")["rain_mm"].describe())
