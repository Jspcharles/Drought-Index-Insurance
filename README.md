# Drought-index insurance: a synthetic practice workflow

**Website:** [https://YOUR-USERNAME.github.io/YOUR-REPO/](https://YOUR-USERNAME.github.io/YOUR-REPO/) *(placeholder until GitHub Pages is enabled)*

A small, reproducible project that runs a full drought-index insurance analysis on **synthetic** data:

1. Monthly rainfall, 1991–2023, for 5 fictional regions, with seasonality, persistence and deliberate multi-year dry spells
2. **SPI-3, SPI-6 and SPI-12**: gamma fit per calendar month, with proper handling of zero-rain months
3. **Drought events** by run theory (SPI-3 < −1): start, end, duration, severity, intensity
4. Annual **wheat yield** linked to growing-season (May–Oct) SPI, plus noise
5. A **3-tier index insurance contract** triggered on growing-season SPI-3, evaluated against yield losses (hit rate, false alarms, missed losses, basis risk)
6. Figures for each step
7. An interactive **website** (`site/`) that walks through the question, methods, results and limitations, with a contract explorer that recomputes payouts and skill metrics in the browser

Everything is driven by a fixed random seed, so every run gives identical results. **All data are synthetic**: the regions are fictional, and nothing describes a real place.

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
python run_pipeline.py      # whole workflow: data -> SPI -> events -> yield -> contract -> figures -> website data
python -m pytest -q         # SPI and website-export tests
python -m pytest tests/test_spi.py::test_zero_rain_months_handled -q   # a single test
jupyter lab                 # then open notebooks/walkthrough.ipynb
```

The pipeline takes a few seconds and prints a table of contract performance at the end.

## The website

`site/` is a static website (plain HTML, CSS and JavaScript; Plotly and KaTeX load from a CDN). It needs no build step.

**View it locally.** Browsers refuse to load the JSON data from a page opened straight from disk, so serve the folder:

```powershell
python -m http.server -d site     # then open http://localhost:8000
```

**Where its numbers come from.** Step 7 of `run_pipeline.py` (`src/export_site.py`) writes the data the site needs to `site/data/*.json` and web-sized copies of the figures to `site/assets/figures/`. Unlike `data/`, `results/` and `figures/`, these files **are committed**, so the hosted site works without running Python. No number is typed into the page: every value in the text, tables and captions is computed from those JSON files. After changing `src/config.py`, re-run the pipeline and commit `site/` to update the site.

**Contract explorer.** The site's explorer ports `src/insurance.py` to JavaScript (`site/js/contract.js`) and recomputes payouts and metrics as you move the sliders. On load it runs the pipeline's own contract and checks the result against `contract_metrics.csv`; a green badge confirms that the two agree.

**Publishing (GitHub Pages).** `.github/workflows/pages.yml` publishes `site/` on every push to `main`. One-time setup: on GitHub, open *Settings → Pages* and set *Source* to **GitHub Actions**. The repository must be public on a free GitHub plan. The site then appears at `https://<username>.github.io/<repository>/`; put that link at the top of this README.

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
  export_site.py           step 7: JSON data and figure copies for the website
tests/
  test_spi.py              checks that the SPI behaves as the method says it should
  test_export_site.py      checks that the website export reproduces the pipeline's index
notebooks/walkthrough.ipynb  short guided tour of the results
docs/methods.md            equations, assumptions, limitations, references
site/                      the website (committed, including its generated data)
  index.html               the single page: overview, data, methods, results, explorer, limitations
  css/style.css            layout and light/dark theme
  js/                      main.js (page), charts.js (Plotly), explorer.js + contract.js (explorer),
                           captions.js (figure captions), data.js (loading and formatting)
  data/*.json              pipeline outputs for the site                    [generated, committed]
  assets/figures/*.png     web-sized copies of figures/                     [generated, committed]
.github/workflows/pages.yml  publishes site/ to GitHub Pages
data/raw/                  synthetic "observations" (rainfall, yield)       [generated]
data/processed/            SPI and growing-season index                    [generated]
results/                   drought events, payouts, contract metrics       [generated]
figures/                   PNG figures                                      [generated]
```

The folders marked "generated" are rebuilt by `run_pipeline.py`. Those outside `site/` are not tracked by git.

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
| `site/data/*.json` | config, monthly rain and SPI, region-year contract data, events, metrics, figure list |
| `site/assets/figures/*.png` | the figures above, downscaled for the web |

## Experimenting

Every assumption is a named value in `src/config.py`. Change a value there and re-run the pipeline (the website updates too). Many contract changes can also be tried live in the website's contract explorer. Some ideas:

- `TRIGGER_WINDOW_END_MONTHS = [8]`: a single-window contract (SPI-3 for Jun–Aug only)
- `PAYOUT_TIERS`: stricter or looser trigger levels
- `YIELD_NOISE_SD`: how much of yield variability rainfall explains
- `SPI_CALIBRATION = (1991, 2020)`: calibrate on the WMO standard normal period
- `MIN_EVENT_DURATION = 2`: ignore one-month droughts

See [docs/methods.md](docs/methods.md) for the equations and the main limitations.
