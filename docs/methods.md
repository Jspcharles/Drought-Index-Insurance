# Methods note

All settings referred to below live in `src/config.py`.

## 1. Synthetic rainfall (`src/generate_rainfall.py`)

Monthly rainfall for region *r*, month *t* (calendar month *m*):

- Seasonal mean: μ(m) = (P_annual / 12) · [1 + a · cos(2π(m − m_peak)/12)]
- Persistent anomaly: z_t = φ z_{t−1} + √(1−φ²) ε_t, applied as the multiplier exp(σ z_t − σ²/2), which has mean 1
- Dry-spell multiplier d_t: 1 normally, and 0.45–0.60 inside the injected spells
- Rainfall: R_t ~ Gamma(k, θ = μ(m)·exp(…)·d_t / k); set to 0 with probability p₀(m), which is non-zero only in the dry half of the year

Four dry spells are injected (1994–95, 2002–03, 2006–09, 2018–19), each affecting 2–3 regions. They are the "known truth" for checking the SPI and event detection.

## 2. SPI (`src/spi.py`)

Following McKee et al. (1993) and the WMO SPI User Guide (2012):

1. X_t = sum of rainfall over the *k* months ending at *t* (k = 3, 6, 12)
2. For each calendar month separately, fit a two-parameter gamma distribution G (location fixed at 0, maximum likelihood) to the **non-zero** X values in the calibration period
3. Mixed distribution for zeros: H(x) = q + (1 − q) G(x), with q = m/(n+1) (m = number of zeros out of n). Zero totals receive the centre of the zero probability mass, (m+1)/(2(n+1)), as recommended by Stagge et al. (2015)
4. SPI = Φ⁻¹(H), where Φ is the standard normal CDF. H is clipped to [10⁻⁶, 1−10⁻⁶], which caps SPI at about ±4.75

The calibration period defaults to the full 1991–2023 record.

## 3. Drought events (`src/drought_events.py`)

Run theory (Yevjevich, 1967). An event is an unbroken run of months with SPI-3 < −1. For each event:

| Characteristic | Definition |
|---|---|
| Duration D | number of months in the run |
| Severity S | Σ (−SPI) over the run (McKee's "drought magnitude") |
| Intensity I | S / D |
| Peak | minimum SPI in the run |

`MIN_EVENT_DURATION` can be raised to filter out one-month events.

## 4. Synthetic yield (`src/generate_yield.py`)

Y = Y₀ (1 + g·t) · (1 + f(SPI_gs)) · (1 + ε), where ε ~ N(0, σ²)

- SPI_gs = SPI-6 ending in October (the May–October growing season)
- f(s) = β_dry · s for s < 0 and β_wet · s for s ≥ 0, with β_dry ≫ β_wet (dry seasons hurt more than wet seasons help); f is floored at −0.8 (`YIELD_EFFECT_FLOOR`)
- The growing-season length (`GROWING_SEASON_MONTHS`, 6) sets which SPI scale drives yield

## 5. Insurance contract (`src/insurance.py`)

- **Index:** I = min(SPI-3 ending Jul, Aug, Sep, Oct)
- **Payout (share of sum insured):** 1.00 if I ≤ −2.0; 0.50 if I ≤ −1.5; 0.25 if I ≤ −1.0; otherwise 0
- **Sum insured** = 50% of expected yield, so payout (% of expected yield) = tier × 0.5
- **Loss:** a linear trend is fitted to each region's yield. L = max(0, (trend − Y)/trend). A loss year has L > 10%

**Evaluation**, based on the 2×2 table of paid vs loss year:

- Hit rate = hits / (hits + misses)
- False alarm ratio = false alarms / (hits + false alarms)
- Basis risk: RMSE and mean |payout − loss|, and corr(payout, loss)

## 6. Website export (`src/export_site.py`)

Step 7 of the pipeline exports the results for the website in `site/`. It does not change any analysis:

- `site/data/*.json` holds the settings, monthly rainfall and SPI, one row per region-year (including the SPI-3 of every window inside the growing season), drought events and contract metrics
- `site/assets/figures/` holds the figures, downscaled to 1600 px wide and reduced to a 256-colour palette

The website's contract explorer recomputes the index, payouts and metrics in the browser from these files. `site/js/contract.js` repeats the logic of `src/insurance.py`. On load, the explorer runs the pipeline's own contract and checks that it reproduces `contract_metrics.csv`. Loss years are taken from the pipeline rather than recomputed, because the fitted trend does not depend on the contract.

## Limitations

- All data are synthetic. The strength of the rainfall–yield link is set by assumption, not estimated.
- SPI is calibrated and evaluated on the same 33 years, so it is in-sample by construction.
- Regions are generated independently, with no spatial correlation. Real droughts are spatially correlated, which matters for an insurer's portfolio risk.
- The yield trend is linear, and detrending with 33 points is itself uncertain, especially when a dry spell sits near the end of the record.
- Payout tiers are illustrative, not priced. There is no premium, loading or farmer-welfare analysis (e.g. certainty-equivalent income).

## References

- McKee, T.B., Doesken, N.J., Kleist, J. (1993). The relationship of drought frequency and duration to time scales. *8th Conf. on Applied Climatology*, AMS.
- Stagge, J.H., Tallaksen, L.M., Gudmundsson, L., Van Loon, A.F., Stahl, K. (2015). Candidate distributions for climatological drought indices (SPI and SPEI). *Int. J. Climatol.* 35, 4027–4040.
- WMO (2012). *Standardized Precipitation Index User Guide*. WMO-No. 1090.
- Yevjevich, V. (1967). An objective approach to definitions and investigations of continental hydrologic droughts. *Hydrology Paper 23*, Colorado State University.
