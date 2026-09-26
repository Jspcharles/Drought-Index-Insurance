"""
Run the whole workflow, from synthetic data to figures:

    python run_pipeline.py

Steps
  1. Generate synthetic monthly rainfall         -> data/raw/rainfall_monthly.csv
  2. Compute SPI-3, SPI-6, SPI-12                -> data/processed/spi.csv
     and the growing-season summary              -> data/processed/growing_season_index.csv
  3. Find drought events (run theory)            -> results/drought_events.csv
  4. Generate synthetic wheat yield              -> data/raw/yield_annual.csv
  5. Apply and evaluate the insurance contract   -> results/payouts.csv, contract_metrics.csv
  6. Draw figures                                -> figures/*.png
  7. Export data and figures for the website     -> site/data/*.json,
                                                    site/assets/figures/*.png
"""

import pandas as pd

from src import config
from src.drought_events import find_events_all_regions
from src.export_site import export_site
from src.generate_rainfall import generate_rainfall
from src.generate_yield import generate_yield
from src.insurance import apply_contract, evaluate_contract
from src.spi import compute_spi_table, growing_season_table


def main():
    for folder in (config.RAW_DIR, config.PROCESSED_DIR, config.RESULTS_DIR,
                   config.FIGURES_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    print("1/7  Generating synthetic rainfall ...")
    rain = generate_rainfall()
    rain.to_csv(config.RAW_DIR / "rainfall_monthly.csv", index=False)

    print("2/7  Computing SPI ...")
    spi = compute_spi_table(rain, config.SPI_SCALES, config.SPI_CALIBRATION)
    spi.to_csv(config.PROCESSED_DIR / "spi.csv", index=False,
               float_format="%.3f")
    season = growing_season_table(spi, config.GROWING_SEASON_END_MONTH,
                                  config.TRIGGER_WINDOW_END_MONTHS,
                                  config.GROWING_SEASON_MONTHS)
    season.round(3).to_csv(config.PROCESSED_DIR / "growing_season_index.csv",
                           index=False)

    print("3/7  Identifying drought events ...")
    events = find_events_all_regions(spi)
    events.to_csv(config.RESULTS_DIR / "drought_events.csv", index=False)

    print("4/7  Generating synthetic wheat yield ...")
    yields = generate_yield(season)
    yields.to_csv(config.RAW_DIR / "yield_annual.csv", index=False)

    print("5/7  Evaluating the insurance contract ...")
    contract = apply_contract(season, yields)
    contract.round(4).to_csv(config.RESULTS_DIR / "payouts.csv", index=False)
    metrics = evaluate_contract(contract)
    metrics.to_csv(config.RESULTS_DIR / "contract_metrics.csv", index=False)

    print("6/7  Drawing figures ...")
    # Imported here so steps 1-5 still run if matplotlib is not installed.
    from src import plotting
    figures = (plotting.plot_rainfall_spi(rain, spi)
               + plotting.plot_drought_events(spi, events)
               + plotting.plot_spi_vs_yield(contract)
               + plotting.plot_payouts_vs_losses(contract))

    print("7/7  Exporting website data ...")
    export_site(rain, spi, events, contract, metrics, figures)

    print(f"\nDone: {len(events)} drought events, {len(figures)} figures.\n")
    print("Contract performance (payout and loss amounts in % of expected yield):")
    cols = ["region", "loss_years", "payouts", "hits", "misses",
            "false_alarms", "hit_rate", "false_alarm_ratio",
            "basis_risk_rmse", "payout_loss_corr"]
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(metrics[cols].to_string(index=False))


if __name__ == "__main__":
    main()
