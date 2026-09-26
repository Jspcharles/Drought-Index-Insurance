"""
Project settings: every number you might want to change lives here.

Changing a value here and re-running `python run_pipeline.py` regenerates
all data, results and figures consistently.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folders (resolved relative to the project root, so scripts work from anywhere)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"

# ---------------------------------------------------------------------------
# Reproducibility and study period
# ---------------------------------------------------------------------------
SEED = 42                 # fixed seed -> identical synthetic data on every run
START_YEAR = 1991
END_YEAR = 2023

# ---------------------------------------------------------------------------
# Fictional regions
# ---------------------------------------------------------------------------
# annual_mm     : mean annual rainfall (mm) in normal years; the realised
#                 1991-2023 average is lower because of dry spells and
#                 zero-rain months
# peak_month    : month (1-12) with the highest mean rainfall.
#                 6-7 = winter-dominant (like southern Australia);
#                 1-2 = summer-dominant (like northern Australia).
# seasonality   : 0 = flat year, 0.8 = very strong wet/dry season
# gamma_shape   : shape of month-to-month rainfall variability.
#                 Lower = more erratic (CV of a gamma = 1/sqrt(shape)).
# p_zero_max    : chance of a completely dry month in the driest part of year
# base_yield    : expected wheat yield in 1991 (t/ha)
REGIONS = {
    "Northvale": dict(annual_mm=520, peak_month=1, seasonality=0.60,
                      gamma_shape=1.8, p_zero_max=0.15, base_yield=1.9),
    "Eastbrook": dict(annual_mm=680, peak_month=2, seasonality=0.45,
                      gamma_shape=2.2, p_zero_max=0.08, base_yield=2.4),
    "Southmere": dict(annual_mm=450, peak_month=7, seasonality=0.55,
                      gamma_shape=2.0, p_zero_max=0.10, base_yield=2.1),
    "Westridge": dict(annual_mm=380, peak_month=6, seasonality=0.70,
                      gamma_shape=1.6, p_zero_max=0.20, base_yield=1.6),
    "Midland":   dict(annual_mm=600, peak_month=8, seasonality=0.35,
                      gamma_shape=2.5, p_zero_max=0.05, base_yield=2.8),
}

# Month-to-month persistence of rainfall anomalies (AR(1) process).
# Real climate has "memory": a dry month is more likely to be followed by
# another dry month (e.g. through ENSO, soil moisture feedback).
AR1_PHI = 0.5     # lag-1 autocorrelation of the anomaly
AR1_SIGMA = 0.25  # strength of the anomaly (log-scale standard deviation)

# ---------------------------------------------------------------------------
# Deliberate multi-year dry spells
# ---------------------------------------------------------------------------
# During a spell, rainfall is multiplied by `factor` (0.55 = 45% below normal).
# These are the "known truth" we expect SPI and run theory to recover.
DRY_SPELLS = [
    dict(start="1994-03", end="1995-08", factor=0.55,
         regions=["Westridge", "Southmere"]),
    dict(start="2002-01", end="2003-12", factor=0.50,
         regions=["Northvale", "Eastbrook", "Midland"]),
    dict(start="2006-01", end="2009-12", factor=0.60,
         regions=["Southmere", "Westridge", "Midland"]),
    dict(start="2018-01", end="2019-12", factor=0.45,
         regions=["Northvale", "Eastbrook"]),
]

# ---------------------------------------------------------------------------
# SPI settings
# ---------------------------------------------------------------------------
SPI_SCALES = [3, 6, 12]  # accumulation periods (months) to compute
# Years used to fit the gamma distributions. Using the full record is common
# when data are short; set to (1991, 2020) for the WMO standard normal period.
SPI_CALIBRATION = (START_YEAR, END_YEAR)

# ---------------------------------------------------------------------------
# Drought events (run theory)
# ---------------------------------------------------------------------------
DROUGHT_THRESHOLD = -1.0   # SPI below this = "in drought" (moderate or worse)
EVENT_SPI_SCALE = 3        # which SPI to apply run theory to
MIN_EVENT_DURATION = 1     # months; raise to 2-3 to ignore one-month blips

# ---------------------------------------------------------------------------
# Wheat yield model
# ---------------------------------------------------------------------------
# Growing season is May-October. The yield driver is SPI-6 ending in October,
# i.e. the standardised rainfall total for May-Oct.
GROWING_SEASON_END_MONTH = 10
YIELD_TREND_PER_YEAR = 0.010  # +1.0% of base yield per year (technology)
YIELD_BETA_DRY = 0.17         # yield change per unit of negative SPI
YIELD_BETA_WET = 0.03         # yield change per unit of positive SPI (small)
YIELD_NOISE_SD = 0.10        # non-rainfall shocks (pests, frost, heat, ...)

# ---------------------------------------------------------------------------
# Index insurance contract
# ---------------------------------------------------------------------------
# Index = the lowest SPI-3 in the season, over the windows ending Jul, Aug,
# Sep and Oct (i.e. May-Jul, Jun-Aug, Jul-Sep, Aug-Oct): all inside May-Oct.
TRIGGER_WINDOW_END_MONTHS = [7, 8, 9, 10]

# Payout tiers: (SPI-3 threshold, payout as a fraction of the sum insured).
# Listed from most to least severe; the first threshold met is paid.
PAYOUT_TIERS = [
    (-2.0, 1.00),   # extreme drought  -> full payout
    (-1.5, 0.50),   # severe drought   -> half
    (-1.0, 0.25),   # moderate drought -> quarter
]

# Sum insured as a fraction of expected (trend) yield value. With 0.5, a full
# payout compensates a 50% yield loss, so payouts and losses are on the same
# scale ("% of expected yield") and can be compared directly.
SUM_INSURED_FRACTION = 0.5

# A year counts as a "loss year" if yield is more than this far below trend.
LOSS_THRESHOLD = 0.10
