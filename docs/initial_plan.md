# Plan: Synthetic drought-index insurance practice project

## Context
You're a PhD student on drought / weather index insurance who wants a small, clean, reproducible practice project, built in an empty folder, that runs this chain: synthetic rainfall → SPI → drought events → synthetic wheat yield → a tiered index-insurance contract → an evaluation of basis risk → figures. The project should read like research code: short modules, comments explaining the *science*, one command to run everything, and a test for the SPI calculation.

**Environment found:** Python 3.14.6, pip, venv and git 2.55. Already installed globally: numpy 2.5.2, pandas 3.0.5, scipy 1.18.1. **Missing:** matplotlib, pytest, jupyter. Per your choice we'll use a project venv. These are the commands for you to run (I won't install anything):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install -r requirements.txt
```

**Your decisions:** project venv · trigger = minimum SPI-3 over the windows ending Jul–Oct · yield = technology trend + drought effect + noise, with a loss defined as yield more than 10% below the fitted trend · git init + initial commit once the tests pass.

## File structure
```
drought_practice/
├── run_pipeline.py          # THE single command: python run_pipeline.py
├── requirements.txt         # numpy, pandas, scipy, matplotlib, pytest, jupyter
├── README.md                # what, why, how to run, outputs, method summary
├── .gitignore               # .venv, __pycache__, .ipynb_checkpoints, generated outputs
├── src/
│   ├── __init__.py
│   ├── config.py            # ALL tunable settings in one place (seed, regions, dry spells, thresholds, tiers, paths)
│   ├── generate_rainfall.py # step 1
│   ├── spi.py               # step 2: SPI at any time scale (used for 3, 6, 12)
│   ├── drought_events.py    # step 3: run theory
│   ├── generate_yield.py    # step 4
│   ├── insurance.py         # step 5: contract, payouts, skill metrics
│   └── plotting.py          # step 6: all figures
├── tests/
│   └── test_spi.py          # SPI sanity checks (pytest)
├── notebooks/
│   └── walkthrough.ipynb    # short narrative; loads saved outputs, does not recompute
├── data/raw/                # rainfall_monthly.csv, yield_annual.csv (synthetic "observations")
├── data/processed/          # spi.csv, growing_season_index.csv
├── results/                 # drought_events.csv, payouts.csv, contract_metrics.csv
├── figures/                 # PNGs
└── docs/
    └── methods.md           # 1–2 page methods note (formulas, assumptions, limitations)
```
All data are tidy CSVs (one row per region-month or region-year), so they're easy to open in Excel or R.

## What each file does

**config.py**: holds the seed (e.g. 42), the 1991–2023 period, and 5 fictional regions (e.g. Northvale, Eastbrook, Southmere, Westridge, Midland). Each region has an annual rainfall total, a seasonal shape (a mix of winter-dominant and summer-dominant regions), a variability level and a baseline yield. It also holds the dry-spell definitions (region, years, rainfall reduction factor), the SPI calibration period, the drought threshold (−1), the loss threshold (10%), the payout tiers and the sum insured.

**generate_rainfall.py**: builds monthly rainfall for each region as follows:
- **Seasonal mean:** a sinusoid, with the peak month set per region.
- **Monthly totals:** gamma-distributed around that mean, since rainfall is skewed.
- **Zero months:** a probability of a zero-rain month that is higher in the dry season, so SPI's zero-handling actually gets exercised.
- **Persistence:** an AR(1) multiplicative anomaly, so wet and dry months cluster the way real climate does.
- **Dry spells:** 2–4 deliberate multi-year dry spells, e.g. 2002–03, 2006–09 and 2018–19, each applied to some regions with a 35–60% rainfall reduction.

Output: `data/raw/rainfall_monthly.csv`.

**spi.py**: implements `compute_spi(series, scale)`, following McKee et al. (1993) and the WMO guide:
1. Take the rolling `scale`-month sum. The first `scale−1` months are NaN.
2. Fit a separate gamma distribution for each calendar month (ending month), using `scipy.stats.gamma.fit(..., floc=0)` on the non-zero values only.
3. **Handle zeros** with the mixed distribution H(x) = q + (1−q)·G(x), where q is the fraction of zeros for that calendar month.
4. Transform to a standard normal with `norm.ppf(H)`, clipping H to avoid ±∞.

The calibration period is a config parameter (default: the full 1991–2023 record). The function is used for SPI-3 and SPI-12, and also for SPI-6 ending in October, which serves as the "growing-season SPI (May–Oct)" that drives yield. Output: `data/processed/spi.csv`.

**drought_events.py**: run theory on SPI (default SPI-3, but the scale is a parameter). An event is a consecutive run of months with SPI < −1. For each event it records start, end, duration (months), severity (the sum of |SPI| over the run) and intensity (severity ÷ duration, plus the minimum SPI). There's an optional parameter for a minimum duration, or for pooling runs separated by one month; the default is off, so behaviour stays textbook. Output: `results/drought_events.csv`.

**generate_yield.py**: yield = baseline × (1 + technology trend·t) × (1 + β·f(growing-season SPI)) + noise. f() is asymmetric: dry years hurt much more than wet years help, which mirrors real crops. The noise (pests, frost, management) is sized so the correlation between SPI and yield is roughly 0.6–0.75: realistic but imperfect. The yield depends on SPI-6 (May–Oct) while the contract uses min SPI-3; this mismatch is a deliberate, realistic source of basis risk. Output: `data/raw/yield_annual.csv`.

**insurance.py**: covers the contract and its evaluation.
- **Detrending:** fit a linear trend to each region's yield. Loss % = max(0, (trend − yield)/trend). A "loss year" is one with loss above 10%.
- **Index:** the minimum SPI-3 over the windows ending Jul, Aug, Sep and Oct, all of which fall inside May–Oct.
- **3 payout tiers:** SPI-3 ≤ −1.0 pays 25%, ≤ −1.5 pays 50%, and ≤ −2.0 pays 100% of the sum insured.
- **Metrics per region and pooled:**
  - hit rate = paid loss years ÷ all loss years
  - false-alarm ratio = payouts in non-loss years ÷ all payouts
  - missed losses = count of loss years with no payout
  - basis risk = RMSE and mean absolute gap between payout % and loss %, plus the correlation between them
  - a 2×2 contingency table

Outputs: `results/payouts.csv` and `results/contract_metrics.csv`.

**plotting.py**: produces these figures, all saved as 300-dpi PNGs:
1. Rainfall + SPI-3/SPI-12 time series for each region, with the dry spells shaded.
2. The drought events: an SPI-3 time series with the events shaded, plus a duration-vs-severity scatter.
3. Growing-season SPI vs yield anomaly for each region, with a fitted line and r.
4. Payout % vs loss % (a scatter with the 1:1 line), plus a year-by-year bar chart for each region.
5. Optional: a heatmap of the contract metrics by region.

**run_pipeline.py**: calls steps 1–6 in order, prints a short progress log and a summary table of the contract metrics, and finishes in a few seconds.

**tests/test_spi.py**:
- (a) On a long synthetic gamma sample, SPI has mean ≈ 0 and SD ≈ 1.
- (b) A series with many zeros gives finite SPI values (no NaN or inf after warm-up).
- (c) Within the same calendar month, more rain always gives a higher SPI (monotonic).
- (d) The first `scale−1` values are NaN.
- (e) An injected dry spell produces SPI < −1.

**notebooks/walkthrough.ipynb**: about 8–10 cells covering the objective, a look at the rainfall, the SPI, the events table, SPI vs yield, the contract table, the metrics, and a short "what drives basis risk" discussion. It loads the CSVs and PNGs made by the pipeline.

**docs/methods.md**: equations, parameter choices and limitations. The limitations include: synthetic data, SPI calibrated on the same period it's evaluated on, no spatial correlation between regions, and a linear yield trend.

## Build order
1. Scaffolding: folders, `.gitignore`, `requirements.txt`, `config.py`. **You then create the venv and install.**
2. `spi.py` + `tests/test_spi.py`. The core method, tested first against simple synthetic inputs.
3. `generate_rainfall.py`, then a quick check of the seasonality and dry spells in the SPI.
4. `drought_events.py`
5. `generate_yield.py`, then a check that the SPI–yield correlation lands in the target range and adjusting the noise if it doesn't.
6. `insurance.py`
7. `plotting.py`
8. `run_pipeline.py`, run end to end.
9. Notebook, `docs/methods.md`, README.
10. `git init` + initial commit.

## Smaller defaults I'll use unless you say otherwise
- SPI calibration: the full 1991–2023 record (a 30-year WMO normal of 1991–2020 is one config change away).
- Generated data/results/figures are **git-ignored** (placeholder `.gitkeep` files keep the folders). They regenerate in seconds, so the repo holds only code and docs.
- Sum insured is expressed as a % of expected (trend) revenue, so payouts and losses are directly comparable.
- Plain Python script as the single command (no Makefile, which is awkward on Windows).

## Verification
- `python -m pytest -q`: all SPI tests pass.
- `python run_pipeline.py`: all CSVs and PNGs appear, and the console shows the metrics table.
- Sanity checks: SPI-3 mean ≈ 0 and SD ≈ 1 per region; the injected dry spells appear as drought events; SPI–yield r is roughly 0.6–0.75; the hit rate is high but not 100%, with some false alarms and misses.
- Execute the notebook end to end (`jupyter nbconvert --to notebook --execute`) to confirm it runs cleanly.
- Look over each figure by eye.
