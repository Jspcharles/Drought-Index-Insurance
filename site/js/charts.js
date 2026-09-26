// Interactive charts (Plotly). Colours come from CSS variables so charts follow
// the page theme, and keep the same meaning as the pipeline's figures:
// blue = SPI-3 / payouts, orange = SPI-12 / losses, red = drought.

import { afterMonth, linearFit, num, pearson } from "./data.js";
import { outcome } from "./contract.js";

export const OUTCOMES = [
  { key: "hit", label: "Hit (loss, paid)", color: "blue", symbol: "circle" },
  { key: "false_alarm", label: "False alarm (paid, no loss)", color: "orange", symbol: "square" },
  { key: "miss", label: "Missed loss (loss, not paid)", color: "aqua", symbol: "triangle-up" },
  { key: "correct", label: "Correct no-payout", color: "neutral", symbol: "circle" },
];

export function theme() {
  const cs = getComputedStyle(document.documentElement);
  const v = (name) => cs.getPropertyValue(`--${name}`).trim();
  return {
    ink: v("ink"), ink2: v("ink-2"), muted: v("muted"), grid: v("grid"),
    line: v("line"), surface: v("surface"), blue: v("blue"), orange: v("orange"),
    aqua: v("aqua"), red: v("red"), band: v("band"), rain: v("rain"),
    neutral: v("neutral"), font: cs.getPropertyValue("font-family"),
  };
}

const PLOT_CONFIG = {
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"],
};

function axis(t, extra = {}) {
  return {
    gridcolor: t.grid, linecolor: t.line, zerolinecolor: t.line,
    tickfont: { color: t.ink2 }, title: { font: { color: t.ink2 } },
    automargin: true, ...extra,
  };
}

function baseLayout(t, extra = {}) {
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: t.font, size: 12, color: t.ink },
    margin: { l: 56, r: 16, t: 36, b: 48 },
    hoverlabel: { bgcolor: t.surface, bordercolor: t.line, font: { color: t.ink } },
    legend: { orientation: "h", x: 0, y: 1.12, font: { color: t.ink2 } },
    ...extra,
  };
}

function draw(el, traces, layout) {
  window.Plotly.react(el, traces, layout, PLOT_CONFIG);
}

// ---------------------------------------------------------------------------
// Rainfall + SPI time series for one region
// ---------------------------------------------------------------------------
export function drawSpiSeries(el, data, region) {
  const t = theme();
  const cfg = data.config;
  const series = data.monthly.regions[region];
  const x = data.monthly.dates;

  // 12-month running mean, centred as pandas rolling(12, center=True)
  const running = series.rain.map((_, i) => {
    const lo = i - 6, hi = i + 5;
    if (lo < 0 || hi >= series.rain.length) return null;
    let sum = 0;
    for (let j = lo; j <= hi; j++) sum += series.rain[j];
    return sum / 12;
  });

  const spiStyle = { 3: { color: t.blue, width: 1.2 }, 12: { color: t.orange, width: 2.2 } };
  const traces = [
    { type: "bar", x, y: series.rain, name: "Monthly rainfall", yaxis: "y",
      marker: { color: t.rain }, hovertemplate: "%{y:.0f} mm" },
    { type: "scatter", mode: "lines", x, y: running, name: "12-month mean", yaxis: "y",
      line: { color: t.ink2, width: 1.2 }, hovertemplate: "%{y:.0f} mm" },
    ...cfg.SPI_SCALES.map((s) => ({
      type: "scatter", mode: "lines", x, y: series[`spi_${s}`], name: `SPI-${s}`,
      yaxis: "y2", line: spiStyle[s] || { color: t.muted, width: 1.2 },
      visible: spiStyle[s] ? true : "legendonly",
      hovertemplate: "%{y:.2f}",
    })),
  ];

  const shapes = [];
  for (const spell of cfg.DRY_SPELLS) {
    if (!spell.regions.includes(region)) continue;
    shapes.push({ type: "rect", xref: "x", yref: "paper", layer: "below",
      x0: `${spell.start}-01`, x1: afterMonth(spell.end), y0: 0, y1: 1,
      fillcolor: t.band, line: { width: 0 } });
  }
  for (const e of data.events) {
    if (e.region !== region) continue;
    shapes.push({ type: "rect", xref: "x", yref: "y2 domain", layer: "below",
      x0: `${e.start}-01`, x1: afterMonth(e.end), y0: 0, y1: 1,
      fillcolor: t.red, opacity: 0.18, line: { width: 0 } });
  }
  shapes.push(
    { type: "line", xref: "paper", yref: "y2", x0: 0, x1: 1,
      y0: cfg.DROUGHT_THRESHOLD, y1: cfg.DROUGHT_THRESHOLD,
      line: { color: t.red, width: 1, dash: "dash" } },
    { type: "line", xref: "paper", yref: "y2", x0: 0, x1: 1, y0: 0, y1: 0,
      line: { color: t.line, width: 1 } },
  );

  draw(el, traces, baseLayout(t, {
    hovermode: "x unified",
    bargap: 0.1,
    shapes,
    xaxis: axis(t, { type: "date", anchor: "y2" }),
    yaxis: axis(t, { domain: [0.6, 1], title: { text: "Rain (mm)", font: { color: t.ink2 } }, rangemode: "tozero" }),
    yaxis2: axis(t, { domain: [0, 0.54], title: { text: "SPI", font: { color: t.ink2 } }, zeroline: false }),
  }));
}

// ---------------------------------------------------------------------------
// Growing-season SPI vs yield anomaly
// ---------------------------------------------------------------------------
export function drawSpiVsYield(el, data, contractRows, region) {
  const t = theme();
  const cfg = data.config;
  const rows = region ? contractRows.filter((r) => r.region === region) : contractRows;
  const anomaly = (r) => 100 * (r.yield_t_ha / r.trend_t_ha - 1);

  const traces = OUTCOMES.map((o) => {
    const d = rows.filter((r) => outcome(r) === o.key);
    return {
      type: "scatter", mode: "markers", name: o.label,
      x: d.map((r) => r.spi_gs), y: d.map(anomaly),
      marker: { color: t[o.color], symbol: o.symbol, size: 9, opacity: 0.9,
        line: { color: t.surface, width: 1 } },
      customdata: d.map((r) => [r.region, r.year, r.yield_t_ha, r.trend_t_ha,
        100 * r.loss_frac, r.index, 100 * r.payout]),
      hovertemplate: "<b>%{customdata[0]} %{customdata[1]}</b><br>"
        + "Growing-season SPI: %{x:.2f}<br>"
        + "Yield: %{customdata[2]:.2f} t/ha (trend %{customdata[3]:.2f})<br>"
        + "Anomaly: %{y:.1f}%  ·  loss: %{customdata[4]:.1f}%<br>"
        + "Index (min SPI-3): %{customdata[5]:.2f}  ·  payout: %{customdata[6]:.1f}%"
        + "<extra></extra>",
    };
  });

  const xs = rows.map((r) => r.spi_gs), ys = rows.map(anomaly);
  const lo = Math.min(...xs), hi = Math.max(...xs);
  const fit = linearFit(xs, ys);
  traces.push({
    type: "scatter", mode: "lines", name: "Least-squares fit", hoverinfo: "skip",
    x: [lo, hi], y: [fit.a + fit.b * lo, fit.a + fit.b * hi],
    line: { color: t.ink2, width: 1.5 },
  });
  // The response the synthetic yields were generated with (relative to the
  // true trend), for comparison with what the data show.
  const grid = Array.from({ length: 60 }, (_, i) => lo + ((hi - lo) * i) / 59);
  const f = (s) => Math.max(cfg.YIELD_EFFECT_FLOOR,
    s < 0 ? cfg.YIELD_BETA_DRY * s : cfg.YIELD_BETA_WET * s);
  traces.push({
    type: "scatter", mode: "lines", name: "Generating model f(SPI)", hoverinfo: "skip",
    x: grid, y: grid.map((s) => 100 * f(s)),
    line: { color: t.ink2, width: 1.5, dash: "dot" },
  });

  const r = pearson(xs, ys);
  draw(el, traces, baseLayout(t, {
    hovermode: "closest",
    legend: { orientation: "h", x: 0, y: -0.2, font: { color: t.ink2 } },
    margin: { l: 56, r: 16, t: 20, b: 20 },
    xaxis: axis(t, { title: { text: `Growing-season SPI (SPI-${cfg.GROWING_SEASON_MONTHS})`, font: { color: t.ink2 } } }),
    yaxis: axis(t, { title: { text: "Yield anomaly vs trend (%)", font: { color: t.ink2 } } }),
    shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1,
      y0: -100 * cfg.LOSS_THRESHOLD, y1: -100 * cfg.LOSS_THRESHOLD,
      line: { color: t.red, width: 1, dash: "dash" } }],
    annotations: [
      { xref: "paper", yref: "paper", x: 0.01, y: 0.99, showarrow: false,
        xanchor: "left", yanchor: "top", font: { color: t.ink, size: 13 },
        text: `r = ${num(r, 2)}  (n = ${rows.length})` },
      { xref: "paper", yref: "y", x: 0.99, y: -100 * cfg.LOSS_THRESHOLD,
        showarrow: false, xanchor: "right", yanchor: "top",
        font: { color: t.red, size: 11 }, text: "loss threshold" },
    ],
  }));
}

// ---------------------------------------------------------------------------
// Contract explorer: payouts vs losses
// ---------------------------------------------------------------------------
export function drawPayoutScatter(el, rows, lossThreshold) {
  const t = theme();
  const traces = OUTCOMES.map((o) => {
    const d = rows.filter((r) => outcome(r) === o.key);
    return {
      type: "scatter", mode: "markers", name: `${o.label} (${d.length})`,
      x: d.map((r) => 100 * r.loss_frac), y: d.map((r) => 100 * r.payout),
      marker: { color: t[o.color], symbol: o.symbol, size: 9, opacity: 0.85,
        line: { color: t.surface, width: 1 } },
      customdata: d.map((r) => [r.region, r.year, r.index]),
      hovertemplate: "<b>%{customdata[0]} %{customdata[1]}</b><br>"
        + "Loss: %{x:.1f}%  ·  payout: %{y:.1f}%<br>Index: %{customdata[2]:.2f}<extra></extra>",
    };
  });
  const top = Math.max(5, ...rows.map((r) => 100 * Math.max(r.loss_frac, r.payout))) + 3;
  traces.push({ type: "scatter", mode: "lines", name: "payout = loss", hoverinfo: "skip",
    x: [0, top], y: [0, top], line: { color: t.muted, width: 1, dash: "dot" } });

  draw(el, traces, baseLayout(t, {
    hovermode: "closest",
    legend: { orientation: "h", x: 0, y: -0.22, font: { color: t.ink2 } },
    margin: { l: 56, r: 16, t: 12, b: 20 },
    xaxis: axis(t, { range: [-2, top], title: { text: "Yield loss (% of trend yield)", font: { color: t.ink2 } } }),
    yaxis: axis(t, { range: [-2, top], title: { text: "Payout (% of expected yield)", font: { color: t.ink2 } } }),
    shapes: [{ type: "line", yref: "paper", y0: 0, y1: 1,
      x0: 100 * lossThreshold, x1: 100 * lossThreshold,
      line: { color: t.red, width: 1, dash: "dash" } }],
  }));
}

/** Year-by-year view: bars for one region, or outcome counts when pooled. */
export function drawYearBars(el, rows, region) {
  const t = theme();
  let traces, yTitle;
  if (region) {
    const d = rows.filter((r) => r.region === region);
    const label = { hit: "hit", false_alarm: "false alarm", miss: "missed loss", correct: "no loss, no payout" };
    const common = { type: "bar", x: d.map((r) => r.year), customdata: d.map((r) => label[outcome(r)]) };
    traces = [
      { ...common, name: "Yield loss", y: d.map((r) => 100 * r.loss_frac),
        marker: { color: t.orange }, hovertemplate: "Loss %{y:.1f}% (%{customdata})<extra></extra>" },
      { ...common, name: "Index payout", y: d.map((r) => 100 * r.payout),
        marker: { color: t.blue }, hovertemplate: "Payout %{y:.1f}%<extra></extra>" },
    ];
    yTitle = "% of expected yield";
  } else {
    const years = [...new Set(rows.map((r) => r.year))].sort((a, b) => a - b);
    traces = OUTCOMES.filter((o) => o.key !== "correct").map((o) => ({
      type: "bar", name: o.label, x: years,
      y: years.map((y) => rows.filter((r) => r.year === y && outcome(r) === o.key).length),
      marker: { color: t[o.color] },
      hovertemplate: `%{y} ${o.key.replace("_", " ")}(s)<extra></extra>`,
    }));
    yTitle = "Regions";
  }
  draw(el, traces, baseLayout(t, {
    barmode: region ? "group" : "stack",
    bargap: 0.25,
    hovermode: "x unified",
    margin: { l: 56, r: 16, t: 36, b: 36 },
    xaxis: axis(t, { dtick: 5 }),
    yaxis: axis(t, { title: { text: yTitle, font: { color: t.ink2 } }, rangemode: "tozero" }),
  }));
}
