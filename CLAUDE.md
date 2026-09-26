# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A small, reproducible research-practice project for drought-index insurance, run entirely on **synthetic** data: rainfall → SPI → drought events → wheat yield → tiered index-insurance contract → basis-risk evaluation → figures. It is written to read like research code: short modules whose comments explain the *science*, one command to run everything, and tests for the SPI. `docs/methods.md` has the equations, assumptions and limitations; `docs/initial_plan.md` records the original design decisions.

## Commands

Windows / PowerShell, with the project venv in `.venv` (Python 3.10+):

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

python run_pipeline.py                                       # full workflow, a few seconds
python -m pytest -q                                          # all tests (pytest.ini sets pythonpath=. and testpaths=tests)
python -m pytest tests/test_spi.py::test_zero_rain_months_handled -q   # single test
jupyter lab                                                  # notebooks/walkthrough.ipynb
```

There is no linter or build step.

## Architecture

- **`run_pipeline.py` is the only orchestrator.** It calls the step modules in order and writes every intermediate CSV. Step modules take and return pandas DataFrames and don't read files themselves; the notebook reads the saved outputs rather than recomputing.
- **`src/config.py` holds every tunable value** (seed, period, regions, dry spells, SPI scales/calibration, run-theory threshold, yield coefficients, trigger windows, payout tiers, loss threshold, output paths). Modules import it as `from src import config` and use config values as function defaults. New assumptions belong in config as named constants, not as literals inside modules.
- **Determinism:** everything derives from `config.SEED`, so identical runs give identical outputs. Keep all randomness going through a seeded `np.random.default_rng`.
- **Long-format tables keyed by `region`** (plus `date` for monthly data, `year` for annual data). Per-region logic uses `groupby("region", sort=False)` and then concatenates the pieces.
- **Two different SPI quantities, used on purpose** (`spi.growing_season_table`):
  - `spi_gs` = SPI-6 ending in October (May–Oct total). This **drives synthetic yield**.
  - `trigger_spi3` = the minimum SPI-3 over windows ending in `TRIGGER_WINDOW_END_MONTHS`. This is the **insurance index**.
  The mismatch between them, plus yield noise, is what produces basis risk. Don't "fix" it by making them the same.
- **SPI details (`src/spi.py`):** a gamma distribution is fitted separately for each calendar month over the calibration period. Zero totals use a mixed distribution with the Stagge et al. (2015) centre-of-mass probability for zeros. Probabilities are clipped so SPI stays within about ±4.75. The first `scale-1` months are NaN.
- **Losses are measured against a *fitted* linear trend** (`insurance.yield_losses`), not the true synthetic trend, just as a real analyst would do it. Payouts are `tier_payout × SUM_INSURED_FRACTION`, so payouts and losses are both in "fraction of expected yield" and can be compared directly.
- **Plotting** (`src/plotting.py`) uses the Agg backend and is imported lazily in step 6, so steps 1–5 still run without matplotlib. Style rules to keep: small multiples (one panel per region), no dual y-axes, and a fixed colour meaning (blue = SPI-3/payouts, orange = SPI-12/losses, red = drought).
- `data/raw`, `data/processed`, `results` and `figures` are generated and gitignored (only `.gitkeep` is tracked). Regenerate them with `run_pipeline.py` instead of editing them.
- The tests (`tests/test_spi.py`) check SPI properties on synthetic gamma rainfall: roughly standard normal, leading NaNs, zero-rain handling, monotonicity, and dry-spell detection. Other modules have no tests.
