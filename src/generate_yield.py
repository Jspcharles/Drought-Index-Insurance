"""
Step 4: generate synthetic annual wheat yield linked to growing-season SPI.

    yield = trend(year) x (1 + drought_effect(SPI_gs)) x (1 + noise)

  trend           : base yield rising slowly over time (better varieties,
                    management). This is why losses must be measured
                    against a trend, not a flat long-term mean.
  drought_effect  : asymmetric response to growing-season SPI (May-Oct).
                    A dry season cuts yield strongly; a wet season helps
                    only a little (waterlogging, disease, nutrient limits).
  noise           : everything rainfall does not explain: frost, heat at
                    flowering, pests, prices affecting inputs, ...

Because of the noise, and because the insurance contract uses a *different*
rainfall index (the worst SPI-3 window) from the one driving yield (seasonal
SPI-6), the index will never capture losses perfectly. That gap is basis risk.
"""

import numpy as np
import pandas as pd

from src import config


def drought_effect(spi_gs):
    """Proportional yield change caused by growing-season SPI."""
    spi_gs = np.asarray(spi_gs, dtype=float)
    effect = np.where(spi_gs < 0,
                      config.YIELD_BETA_DRY * spi_gs,
                      config.YIELD_BETA_WET * spi_gs)
    return np.clip(effect, -0.8, None)  # a crop never loses more than 80% here


def generate_yield(season, seed=config.SEED):
    """
    Parameters
    ----------
    season : DataFrame with columns region, year, spi_gs
             (from spi.growing_season_table).

    Returns
    -------
    Tidy DataFrame: region, year, yield_t_ha.
    """
    # A separate random stream (seed + 1) so changing the yield model does
    # not alter the rainfall that was already generated.
    rng = np.random.default_rng(seed + 1)
    pieces = []
    for region, df in season.groupby("region", sort=False):
        df = df.sort_values("year")
        years_since_start = df["year"].to_numpy() - config.START_YEAR
        trend = config.REGIONS[region]["base_yield"] * (
            1 + config.YIELD_TREND_PER_YEAR * years_since_start)
        noise = rng.normal(0, config.YIELD_NOISE_SD, len(df))
        yld = trend * (1 + drought_effect(df["spi_gs"])) * (1 + noise)
        pieces.append(pd.DataFrame({"region": region,
                                    "year": df["year"].to_numpy(),
                                    "yield_t_ha": np.round(yld, 3)}))
    return pd.concat(pieces, ignore_index=True)
