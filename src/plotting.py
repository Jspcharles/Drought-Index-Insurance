"""
Step 6: figures.

All figures are saved as 300-dpi PNGs in figures/. Design choices:
  - One panel per region (small multiples) rather than five colours in one
    plot, so readers never have to match colours to regions.
  - Rainfall and SPI are drawn in separate panels (never two y-axes on one plot).
  - A consistent colour meaning throughout: blue = SPI-3 / payouts,
    orange = SPI-12 / yield losses, red shading = drought.
"""

import matplotlib

matplotlib.use("Agg")  # draw to files only; no display window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config

# --- Colour palette (colour-blind-safe order) and chart "ink" ----------------
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
RAIN_BAR = "#86b6ef"
DROUGHT = "#e34948"
GREY = "#898781"
INK, INK_2 = "#0b0b0b", "#52514e"

plt.rcParams.update({
    "figure.facecolor": "#fcfcfb",
    "axes.facecolor": "#fcfcfb",
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e1e0d9",
    "grid.linewidth": 0.6,
    "xtick.color": GREY,
    "ytick.color": GREY,
    "xtick.labelcolor": INK_2,
    "ytick.labelcolor": INK_2,
    "legend.frameon": False,
    "font.size": 9,
    "lines.linewidth": 1.5,
})


def _save(fig, name):
    path = config.FIGURES_DIR / name
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def _shade_dry_spells(ax, region):
    """Grey background bands where a dry spell was deliberately injected."""
    for spell in config.DRY_SPELLS:
        if region in spell["regions"]:
            ax.axvspan(pd.Timestamp(spell["start"]),
                       pd.Period(spell["end"]).end_time,
                       color=GREY, alpha=0.15, lw=0)


# -----------------------------------------------------------------------------
# Figure 1: rainfall and SPI time series, one file per region
# -----------------------------------------------------------------------------
def plot_rainfall_spi(rain, spi):
    paths = []
    for region in config.REGIONS:
        r = rain[rain["region"] == region].set_index("date")["rain_mm"]
        s = spi[spi["region"] == region].set_index("date")

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True,
                                       height_ratios=[1, 1.3])
        ax1.bar(r.index, r, width=25, color=RAIN_BAR, label="Monthly rainfall")
        ax1.plot(r.rolling(12, center=True).mean(), color=INK_2, lw=1.2,
                 label="12-month running mean")
        ax1.set_ylabel("Rainfall (mm/month)")
        ax1.set_title(f"{region}: monthly rainfall")
        ax1.legend(loc="upper right", ncols=2)
        _shade_dry_spells(ax1, region)

        ax2.plot(s.index, s["spi_3"], color=BLUE, lw=1, label="SPI-3")
        ax2.plot(s.index, s["spi_12"], color=ORANGE, lw=2, label="SPI-12")
        ax2.axhline(config.DROUGHT_THRESHOLD, color=DROUGHT, ls="--", lw=1,
                    label=f"Drought threshold (SPI = {config.DROUGHT_THRESHOLD:g})")
        ax2.axhline(0, color="#c3c2b7", lw=0.8)
        ax2.set_ylabel("SPI")
        ax2.set_ylim(-4, 5)   # headroom above +4 keeps the legend clear of data
        ax2.set_title("Standardized Precipitation Index "
                      "(grey bands = injected dry spells)")
        ax2.legend(loc="upper right", ncols=3)
        _shade_dry_spells(ax2, region)

        fig.tight_layout()
        paths.append(_save(fig, f"fig1_rainfall_spi_{region}.png"))
    return paths


# -----------------------------------------------------------------------------
# Figure 2: drought events from run theory
# -----------------------------------------------------------------------------
def plot_drought_events(spi, events, scale=config.EVENT_SPI_SCALE):
    col = f"spi_{scale}"
    regions = list(config.REGIONS)

    # 2a: SPI with the months inside detected events filled in red
    fig, axes = plt.subplots(len(regions), 1, figsize=(10, 9), sharex=True,
                             sharey=True)
    for ax, region in zip(axes, regions):
        s = spi[spi["region"] == region].set_index("date")[col]
        ax.plot(s.index, s, color=BLUE, lw=0.8)
        ax.fill_between(s.index, config.DROUGHT_THRESHOLD, s,
                        where=s < config.DROUGHT_THRESHOLD, color=DROUGHT,
                        alpha=0.6, lw=0, interpolate=True)
        ax.axhline(config.DROUGHT_THRESHOLD, color=DROUGHT, ls="--", lw=0.8)
        _shade_dry_spells(ax, region)
        n = (events["region"] == region).sum()
        ax.set_title(f"{region}  ({n} events)", fontsize=10)
        ax.set_ylim(-3.5, 3.5)
        ax.set_ylabel(f"SPI-{scale}")
    fig.suptitle(f"Drought events (SPI-{scale} < {config.DROUGHT_THRESHOLD}) "
                 "found by run theory; grey = injected dry spells",
                 x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout()
    path_a = _save(fig, "fig2a_drought_events_timeline.png")

    # 2b: duration vs severity for every event; the largest are labelled
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.scatter(events["duration"], events["severity"], s=20 + 12 * events["intensity"] ** 2,
               color=BLUE, alpha=0.7, edgecolor="#fcfcfb", lw=1)
    for _, e in events.nlargest(5, "severity").iterrows():
        ax.annotate(f"{e['region']} {e['start']:%Y}",
                    (e["duration"], e["severity"]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8,
                    color=INK_2)
    ax.set_xlabel("Duration (months)")
    ax.set_ylabel("Severity (sum of -SPI over event)")
    ax.set_title("Drought events: longer droughts accumulate more severity")
    ax.text(0.99, 0.02, "marker size = intensity", transform=ax.transAxes,
            ha="right", color=GREY, fontsize=8)
    fig.tight_layout()
    path_b = _save(fig, "fig2b_event_duration_severity.png")
    return [path_a, path_b]


# -----------------------------------------------------------------------------
# Figure 3: growing-season SPI vs yield anomaly
# -----------------------------------------------------------------------------
def plot_spi_vs_yield(contract):
    regions = list(config.REGIONS)
    fig, axes = plt.subplots(1, len(regions), figsize=(13, 3.4), sharey=True)
    for ax, region in zip(axes, regions):
        d = contract[contract["region"] == region]
        anomaly = 100 * (d["yield_t_ha"] / d["trend_t_ha"] - 1)
        ax.scatter(d["spi_gs"], anomaly, color=BLUE, s=22, alpha=0.8,
                   edgecolor="#fcfcfb", lw=1)
        slope, intercept = np.polyfit(d["spi_gs"], anomaly, 1)
        x = np.linspace(d["spi_gs"].min(), d["spi_gs"].max(), 50)
        ax.plot(x, intercept + slope * x, color=INK_2, lw=1.2)
        ax.axhline(-100 * config.LOSS_THRESHOLD, color=DROUGHT, ls="--", lw=0.8)
        r = np.corrcoef(d["spi_gs"], anomaly)[0, 1]
        ax.set_title(region, fontsize=10)
        ax.text(0.04, 0.95, f"r = {r:.2f}", transform=ax.transAxes, va="top",
                color=INK)
        ax.set_xlabel("Growing-season SPI\n(SPI-6, May-Oct)")
    axes[0].set_ylabel("Yield anomaly vs trend (%)")
    axes[0].text(0.04, 0.12, "loss threshold (-10%)", transform=axes[0].transAxes,
                 color=INK_2, fontsize=7.5)
    fig.suptitle("Drier seasons give lower yields, but not perfectly",
                 x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout()
    return [_save(fig, "fig3_spi_vs_yield.png")]


# -----------------------------------------------------------------------------
# Figure 4: payouts vs losses
# -----------------------------------------------------------------------------
def _outcome(row):
    if row["paid"] and row["loss_year"]:
        return "Hit (loss, paid)"
    if row["paid"]:
        return "False alarm (paid, no loss)"
    if row["loss_year"]:
        return "Missed loss (loss, not paid)"
    return "Correct no-payout"


OUTCOME_STYLE = {
    "Hit (loss, paid)": dict(color=BLUE, marker="o"),
    "False alarm (paid, no loss)": dict(color=ORANGE, marker="s"),
    "Missed loss (loss, not paid)": dict(color=AQUA, marker="^"),
    "Correct no-payout": dict(color="#c3c2b7", marker="o"),
}


def plot_payouts_vs_losses(contract):
    df = contract.assign(outcome=contract.apply(_outcome, axis=1))

    # 4a: pooled scatter of payout vs loss, all region-years
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for label, style in OUTCOME_STYLE.items():
        d = df[df["outcome"] == label]
        ax.scatter(100 * d["loss_frac"], 100 * d["payout_frac"], s=36,
                   alpha=0.85, edgecolor="#fcfcfb", lw=1,
                   label=f"{label}  (n={len(d)})", **style)
    lim = 100 * max(df["loss_frac"].max(), df["payout_frac"].max()) + 3
    ax.plot([0, lim], [0, lim], color=GREY, ls=":", lw=1)
    ax.text(lim * 0.72, lim * 0.78, "payout = loss", color=GREY, rotation=38,
            fontsize=8)
    ax.axvline(100 * config.LOSS_THRESHOLD, color=DROUGHT, ls="--", lw=0.8)
    ax.set_xlim(-2, lim)
    ax.set_ylim(-2, lim)
    ax.set_xlabel("Yield loss (% of trend yield)")
    ax.set_ylabel("Payout (% of expected yield)")
    ax.set_title("Index payouts vs actual losses (all regions, 1991-2023)")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 0.06), fontsize=8)
    fig.tight_layout()
    path_a = _save(fig, "fig4a_payout_vs_loss_scatter.png")

    # 4b: year-by-year bars per region
    regions = list(config.REGIONS)
    fig, axes = plt.subplots(len(regions), 1, figsize=(10, 10), sharex=True,
                             sharey=True)
    w = 0.4
    for ax, region in zip(axes, regions):
        d = df[df["region"] == region]
        ax.bar(d["year"] - w / 2, 100 * d["loss_frac"], width=w, color=ORANGE,
               label="Yield loss")
        ax.bar(d["year"] + w / 2, 100 * d["payout_frac"], width=w, color=BLUE,
               label="Index payout")
        ax.axhline(100 * config.LOSS_THRESHOLD, color=DROUGHT, ls="--", lw=0.8)
        # Mark misses and false alarms so mismatches stand out
        for _, row in d.iterrows():
            if row["outcome"].startswith(("False", "Missed")):
                ax.text(row["year"], -9, "FA" if row["paid"] else "M",
                        ha="center", fontsize=7, color=INK_2)
        ax.set_title(region, fontsize=10)
        ax.set_ylabel("% of expected")
        ax.set_ylim(-13, None)
    axes[0].legend(loc="upper right", ncols=2)
    axes[-1].set_xlabel("Year   (M = missed loss, FA = false alarm)")
    fig.suptitle("Yield losses and index payouts by year",
                 x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout()
    path_b = _save(fig, "fig4b_payout_loss_by_year.png")
    return [path_a, path_b]
