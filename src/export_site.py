"""
Step 7: export what the website (site/) needs.

The pipeline outputs in data/, results/ and figures/ are git-ignored, so the
website cannot read them once hosted. This step writes small JSON files to
site/data/ and web-sized copies of the figures to site/assets/figures/; both
ARE committed. Every number shown on the website comes from these files, so
re-running the pipeline and committing site/ updates the site.

  config.json   : the settings from src/config.py that the text refers to,
                  plus a few values derived from them
  monthly.json  : rainfall and SPI per region, one array entry per month
  annual.json   : one row per region-year: growing-season SPI, the SPI-3 of
                  every candidate trigger window, yield, trend, loss, payout
  events.json   : drought events from run theory
  metrics.json  : contract skill metrics (the pipeline's contract_metrics.csv)
  figures.json  : which PNGs exist, grouped by figure

The contract explorer on the site recomputes payouts and metrics in the
browser from annual.json, and checks that with the pipeline's own settings
it reproduces metrics.json exactly.
"""

import json
import math
import re

from PIL import Image
from scipy import stats

from src import config
from src import spi as spi_module


def _clean(value, digits=None):
    """Make a value JSON-safe: numpy -> Python, NaN -> null, optional rounding."""
    if value is None:
        return None
    if hasattr(value, "item"):          # numpy scalar
        value = value.item()
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return round(value, digits) if digits is not None else value
    return value


def _write(name, obj, compact=False):
    path = config.SITE_DIR / "data" / name
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, separators=(",", ":"), allow_nan=False)
        else:
            json.dump(obj, f, indent=1, allow_nan=False)
        f.write("\n")
    return path


def candidate_windows():
    """End months of the SPI-3 windows that lie entirely inside the season.

    E.g. season May-Oct -> windows ending Jul, Aug, Sep, Oct. These are the
    windows the contract explorer lets the reader switch on and off.
    """
    start = config.GROWING_SEASON_END_MONTH - config.GROWING_SEASON_MONTHS + 1
    return list(range(start + 2, config.GROWING_SEASON_END_MONTH + 1))


def config_payload(metrics):
    start_month = (config.GROWING_SEASON_END_MONTH
                   - config.GROWING_SEASON_MONTHS + 1)
    return {
        "SEED": config.SEED,
        "START_YEAR": config.START_YEAR,
        "END_YEAR": config.END_YEAR,
        "REGIONS": config.REGIONS,
        "AR1_PHI": config.AR1_PHI,
        "AR1_SIGMA": config.AR1_SIGMA,
        "DRY_SPELLS": config.DRY_SPELLS,
        "SPI_SCALES": config.SPI_SCALES,
        "SPI_CALIBRATION": list(config.SPI_CALIBRATION),
        "DROUGHT_THRESHOLD": config.DROUGHT_THRESHOLD,
        "EVENT_SPI_SCALE": config.EVENT_SPI_SCALE,
        "MIN_EVENT_DURATION": config.MIN_EVENT_DURATION,
        "GROWING_SEASON_END_MONTH": config.GROWING_SEASON_END_MONTH,
        "GROWING_SEASON_MONTHS": config.GROWING_SEASON_MONTHS,
        "YIELD_TREND_PER_YEAR": config.YIELD_TREND_PER_YEAR,
        "YIELD_BETA_DRY": config.YIELD_BETA_DRY,
        "YIELD_BETA_WET": config.YIELD_BETA_WET,
        "YIELD_NOISE_SD": config.YIELD_NOISE_SD,
        "YIELD_EFFECT_FLOOR": config.YIELD_EFFECT_FLOOR,
        "TRIGGER_WINDOW_END_MONTHS": config.TRIGGER_WINDOW_END_MONTHS,
        "PAYOUT_TIERS": [list(t) for t in config.PAYOUT_TIERS],
        "SUM_INSURED_FRACTION": config.SUM_INSURED_FRACTION,
        "LOSS_THRESHOLD": config.LOSS_THRESHOLD,
        # Derived values, so the site never has to hard-code them
        "derived": {
            "n_years": config.END_YEAR - config.START_YEAR + 1,
            "season_start_month": start_month,
            "candidate_windows": candidate_windows(),
            "spi_prob_min": spi_module._P_MIN,
            "spi_cap": round(float(stats.norm.ppf(1 - spi_module._P_MIN)), 2),
            "pooled_label": str(metrics["region"].iloc[-1]),
        },
    }


def monthly_payload(rain, spi):
    df = rain.merge(spi, on=["date", "region"])
    out = {"dates": None, "regions": {}}
    for region, d in df.groupby("region", sort=False):
        d = d.sort_values("date")
        if out["dates"] is None:
            out["dates"] = d["date"].dt.strftime("%Y-%m").tolist()
        series = {"rain": [_clean(v, 1) for v in d["rain_mm"]]}
        for s in config.SPI_SCALES:
            series[f"spi_{s}"] = [_clean(v, 3) for v in d[f"spi_{s}"]]
        out["regions"][region] = series
    return out


def annual_payload(spi, contract):
    """One row per region-year, with the SPI-3 of every candidate window."""
    windows = candidate_windows()
    s3 = spi.assign(year=spi["date"].dt.year, month=spi["date"].dt.month)
    s3 = s3[s3["month"].isin(windows)]
    spi3 = {(r.region, r.year, r.month): r.spi_3 for r in s3.itertuples()}

    rows = []
    for r in contract.itertuples():
        rows.append({
            "region": r.region,
            "year": int(r.year),
            "spi_gs": _clean(r.spi_gs, 6),
            "spi3": {str(m): _clean(spi3[(r.region, r.year, m)], 6)
                     for m in windows},
            "trigger_spi3": _clean(r.trigger_spi3, 6),
            "trigger_month": int(r.trigger_month),
            "yield_t_ha": _clean(r.yield_t_ha, 3),
            "trend_t_ha": _clean(r.trend_t_ha, 6),
            "loss_frac": _clean(r.loss_frac, 8),
            "loss_year": bool(r.loss_year),
            "tier_payout": _clean(r.tier_payout, 6),
            "payout_frac": _clean(r.payout_frac, 6),
            "paid": bool(r.paid),
        })
    return rows


def events_payload(events):
    return [{
        "region": e.region,
        "start": e.start.strftime("%Y-%m"),
        "end": e.end.strftime("%Y-%m"),
        "duration": int(e.duration),
        "severity": _clean(e.severity, 3),
        "intensity": _clean(e.intensity, 3),
        "peak_spi": _clean(e.peak_spi, 3),
    } for e in events.itertuples()]


def metrics_payload(metrics):
    return [{k: _clean(v) for k, v in row.items()}
            for row in metrics.to_dict(orient="records")]


def export_figures(figure_paths):
    """Copy web-sized versions of the figures; describe them in figures.json."""
    out_dir = config.SITE_DIR / "assets" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):     # drop figures that no longer exist
        old.unlink()

    entries = []
    for path in figure_paths:
        with Image.open(path) as img:
            img = img.convert("RGB")      # figures have opaque backgrounds
            if img.width > config.SITE_FIGURE_WIDTH:
                height = round(img.height * config.SITE_FIGURE_WIDTH / img.width)
                img = img.resize((config.SITE_FIGURE_WIDTH, height),
                                 Image.LANCZOS)
            # Charts use few colours, so a 256-colour palette looks the same
            # and makes the committed files less than half the size.
            img = img.quantize(256, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE)
            img.save(out_dir / path.name, optimize=True)
            width, height = img.size
        group = re.match(r"(fig\d+[a-z]?)_", path.name).group(1)
        region = next((r for r in config.REGIONS
                       if path.stem.endswith(f"_{r}")), None)
        entries.append({"id": group, "region": region,
                        "file": f"assets/figures/{path.name}",
                        "width": width, "height": height})
    return entries


def export_site(rain, spi, events, contract, metrics, figure_paths):
    """Write everything the website needs. Returns the list of files written."""
    (config.SITE_DIR / "data").mkdir(parents=True, exist_ok=True)
    return [
        _write("config.json", config_payload(metrics)),
        _write("monthly.json", monthly_payload(rain, spi), compact=True),
        _write("annual.json", annual_payload(spi, contract), compact=True),
        _write("events.json", events_payload(events)),
        _write("metrics.json", metrics_payload(metrics)),
        _write("figures.json", export_figures(figure_paths)),
    ]
