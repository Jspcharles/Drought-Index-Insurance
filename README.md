# Drought-index insurance: a synthetic practice workflow

A small, reproducible project that runs a full drought-index insurance analysis on **synthetic** data:

1. Monthly rainfall, 1991–2023, for 5 fictional regions, with seasonality, persistence and deliberate multi-year dry spells
2. **SPI-3, SPI-6 and SPI-12**: gamma fit per calendar month, with proper handling of zero-rain months
3. **Drought events** by run theory (SPI-3 < −1): start, end, duration, severity, intensity
4. Annual **wheat yield** linked to growing-season (May–Oct) SPI, plus noise
5. A **3-tier index insurance contract** triggered on growing-season SPI-3, evaluated against yield losses (hit rate, false alarms, missed losses, basis risk)
6. Figures for each step

Everything is driven by a fixed random seed, so every run gives identical results.

## Setup (once)

Requires Python 3.10 or later. From the project folder, in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and then try again.

## Run

```powershell
python run_pipeline.py      # whole workflow: data -> SPI -> events -> yield -> contract -> figures
python -m pytest -q         # SPI sanity tests
jupyter lab                 # then open notebooks/walkthrough.ipynb
```

The pipeline takes a few seconds and prints a table of contract performance at the end.

## Project layout

```
run_pipeline.py            single entry point for the whole workflow
src/
  config.py                ALL settings: seed, regions, dry spells, thresholds, payout tiers
  generate_rainfall.py     step 1: synthetic rainfall
  spi.py                   step 2: SPI (any time scale) + growing-season summary
  drought_events.py        step 3: run theory
  generate_yield.py        step 4: synthetic yield
  insurance.py             step 5: contract payouts and skill metrics
  plotting.py              step 6: figures
tests/test_spi.py          checks that the SPI behaves as the method says it should
notebooks/walkthrough.ipynb  short guided tour of the results
docs/methods.md            equations, assumptions, limitations, references
data/raw/                  synthetic "observations" (rainfall, yield)       [generated]
data/processed/            SPI and growing-season index                    [generated]
results/                   drought events, payouts, contract metrics       [generated]
figures/                   PNG figures                                      [generated]
```

The folders marked "generated" are rebuilt by `run_pipeline.py` and are not tracked by git.

## Outputs

| File | Contents |
|---|---|
| `data/raw/rainfall_monthly.csv` | date, region, rain_mm |
| `data/raw/yield_annual.csv` | region, year, yield_t_ha |
| `data/processed/spi.csv` | date, region, spi_3, spi_6, spi_12 |
| `data/processed/growing_season_index.csv` | region, year, growing-season SPI, trigger index |
| `results/drought_events.csv` | one row per event: start, end, duration, severity, intensity, peak SPI |
| `results/payouts.csv` | one row per region-year: index, payout, yield, trend, loss, outcome flags |
| `results/contract_metrics.csv` | hit rate, false alarm ratio, basis risk, and more, per region and pooled |
| `figures/fig1_*` | rainfall and SPI time series, one per region |
| `figures/fig2a/b_*` | drought event timeline; event duration vs severity |
| `figures/fig3_*` | growing-season SPI vs yield anomaly |
| `figures/fig4a/b_*` | payouts vs losses (scatter, and year-by-year bars) |

## Experimenting

Every assumption is a named value in `src/config.py`. Change a value there and re-run the pipeline. Some ideas:

- `TRIGGER_WINDOW_END_MONTHS = [8]`: a single-window contract (SPI-3 for Jun–Aug only)
- `PAYOUT_TIERS`: stricter or looser trigger levels
- `YIELD_NOISE_SD`: how much of yield variability rainfall explains
- `SPI_CALIBRATION = (1991, 2020)`: calibrate on the WMO standard normal period
- `MIN_EVENT_DURATION = 2`: ignore one-month droughts

See [docs/methods.md](docs/methods.md) for the equations and the main limitations.
