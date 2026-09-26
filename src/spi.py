"""
Standardized Precipitation Index (SPI).

Method (McKee et al., 1993; WMO, 2012):
  1. Sum rainfall over the chosen time scale (e.g. 3 months).
  2. For each calendar month separately, fit a gamma distribution to those
     sums. This removes seasonality: a January total is only compared with
     other January totals.
  3. Convert each value to its cumulative probability under the fitted
     distribution.
  4. Map that probability onto a standard normal distribution. The result
     is the SPI: 0 = median conditions, -1 = roughly a 1-in-6 dry event,
     -2 = roughly a 1-in-44 dry event.

Zero rainfall: the gamma distribution is only defined for values > 0, so
totals of exactly zero get special treatment. We use a "mixed" distribution:
    H(x) = q + (1 - q) * G(x)
where q is the probability of a zero total and G is the gamma CDF fitted to
the non-zero totals. For the zeros themselves, we use the "centre of mass"
of the zero probability (Stagge et al., 2015) instead of q itself. Otherwise
a region where most months are dry would give zero-rain months a *positive*
SPI, which makes no physical sense.
"""

import numpy as np
import pandas as pd
from scipy import stats

# Probabilities are kept within these bounds so the normal transform never
# returns +/- infinity. This caps SPI at about +/-4.75.
_P_MIN, _P_MAX = 1e-6, 1 - 1e-6


def fit_gamma_with_zeros(values):
    """
    Fit the mixed zero/gamma distribution to one calendar month's totals.

    Returns a dict with:
      alpha, beta : gamma shape and scale (fitted to non-zero values only)
      p_zero      : probability of a zero total, using the Weibull plotting
                    position m / (n + 1) as in Stagge et al. (2015)
      p_zero_mid  : probability assigned to a zero total (centre of the zero
                    mass), (m + 1) / (2 * (n + 1))
    """
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    n = len(values)
    m = int(np.sum(values == 0))
    nonzero = values[values > 0]

    if len(nonzero) < 3:
        # Too few wet values to fit a distribution reliably.
        return None

    # floc=0 fixes the gamma location at zero: the standard two-parameter
    # gamma used for rainfall.
    alpha, _, beta = stats.gamma.fit(nonzero, floc=0)
    return dict(
        alpha=alpha,
        beta=beta,
        p_zero=m / (n + 1),
        p_zero_mid=(m + 1) / (2 * (n + 1)),
    )


def _to_spi(values, params):
    """Convert rainfall totals to SPI using one month's fitted parameters."""
    values = np.asarray(values, dtype=float)
    q = params["p_zero"]
    prob = q + (1 - q) * stats.gamma.cdf(values, params["alpha"],
                                         scale=params["beta"])
    prob = np.where(values == 0, params["p_zero_mid"], prob)
    prob = np.clip(prob, _P_MIN, _P_MAX)
    spi = stats.norm.ppf(prob)
    return np.where(np.isnan(values), np.nan, spi)


def compute_spi(precip, scale, calibration=None):
    """
    Compute SPI at a given time scale for one monthly rainfall series.

    Parameters
    ----------
    precip : pandas Series of monthly rainfall (mm) with a monthly
             DatetimeIndex (one value per month, no gaps).
    scale : accumulation period in months (e.g. 3 for SPI-3).
    calibration : optional (first_year, last_year) used to fit the
                  distributions. Defaults to the whole record.

    Returns
    -------
    pandas Series of SPI values, same index as `precip`. The first
    `scale - 1` months are NaN because a full window is not yet available.
    """
    if scale < 1:
        raise ValueError("scale must be at least 1 month")

    # Step 1: rolling sum over `scale` months, labelled by the window's END
    # month. E.g. SPI-3 for August covers June + July + August.
    totals = precip.rolling(window=scale, min_periods=scale).sum()

    years = totals.index.year
    if calibration is None:
        in_calibration = np.ones(len(totals), dtype=bool)
    else:
        in_calibration = (years >= calibration[0]) & (years <= calibration[1])

    spi = pd.Series(np.nan, index=totals.index, name=f"spi_{scale}")

    # Steps 2-4, done separately for each calendar month.
    for month in range(1, 13):
        is_month = totals.index.month == month
        params = fit_gamma_with_zeros(totals[is_month & in_calibration])
        if params is None:
            continue  # leave NaN: not enough data to fit this month
        spi[is_month] = _to_spi(totals[is_month].to_numpy(), params)

    return spi


def compute_spi_table(rain, scales, calibration=None):
    """
    Compute several SPI scales for every region.

    Parameters
    ----------
    rain : tidy DataFrame with columns date, region, rain_mm.
    scales : list of time scales, e.g. [3, 6, 12].

    Returns
    -------
    Tidy DataFrame with columns date, region, spi_3, spi_6, ...
    """
    pieces = []
    for region, df in rain.groupby("region", sort=False):
        series = df.set_index("date")["rain_mm"]
        out = pd.DataFrame({"date": series.index, "region": region})
        for s in scales:
            out[f"spi_{s}"] = compute_spi(series, s, calibration).to_numpy()
        pieces.append(out)
    return pd.concat(pieces, ignore_index=True)


def growing_season_table(spi_table, season_end_month, trigger_end_months,
                         season_months=6):
    """
    Summarise the monthly SPI into one row per region and year.

    Columns:
      spi_gs        : SPI-`season_months` ending in `season_end_month`
                      (SPI-6 ending Oct -> May-Oct), the growing-season
                      rainfall that drives yield.
      trigger_spi3  : the lowest SPI-3 among the windows ending in
                      `trigger_end_months`. This is the insurance index.
      trigger_month : which window gave that lowest value (useful for
                      seeing *when* in the season droughts hit).
    """
    df = spi_table.assign(year=spi_table["date"].dt.year,
                          month=spi_table["date"].dt.month)

    gs = (df[df["month"] == season_end_month]
          .loc[:, ["region", "year", f"spi_{season_months}"]]
          .rename(columns={f"spi_{season_months}": "spi_gs"}))

    window = df[df["month"].isin(trigger_end_months)]
    worst = window.loc[window.groupby(["region", "year"])["spi_3"].idxmin(),
                       ["region", "year", "spi_3", "month"]]
    worst = worst.rename(columns={"spi_3": "trigger_spi3",
                                  "month": "trigger_month"})

    return gs.merge(worst, on=["region", "year"]).reset_index(drop=True)
