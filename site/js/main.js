// Page entry point: load the pipeline exports, fill in every number in the
// text, draw tables, figures and charts, and start the contract explorer.

import { applyContract } from "./contract.js";
import { drawSpiSeries, drawSpiVsYield } from "./charts.js";
import { initExplorer, pipelineSettings } from "./explorer.js";
import {
  MONTHS, afterMonth, inInjectedSpell, listJoin, loadData, num, pct, pearson,
  powerOfTen, wilson, windowLabel, ymLabel,
} from "./data.js";
import { CAPTIONS } from "./captions.js";

// ---------------------------------------------------------------------------
// Facts: every number the text quotes, computed from the exported data.
// In the HTML, <span data-bind="name"></span> is replaced by facts[name].
// ---------------------------------------------------------------------------
function computeFacts(data, contract) {
  const c = data.config, d = c.derived;
  const regions = Object.keys(c.REGIONS);
  const metrics = Object.fromEntries(data.metrics.map((m) => [m.region, m]));
  const pooled = metrics[d.pooled_label];
  const spells = c.DRY_SPELLS;

  const factors = spells.map((s) => s.factor);
  const tiers = c.PAYOUT_TIERS;
  const trigger = tiers[tiers.length - 1][0];

  // Drought events vs the injected "truth"
  const events = data.events.map((e) => ({ ...e,
    injected: inInjectedSpell(e.region, e.start, e.end, spells) }));
  const inSpell = events.filter((e) => e.injected);
  const pairs = spells.flatMap((s) => s.regions.map((r) => ({ r, s })));
  const detected = pairs.filter(({ r, s }) =>
    events.some((e) => e.region === r && e.start <= s.end && e.end >= s.start));
  const bySeverity = [...events].sort((a, b) => b.severity - a.severity);
  const topInSpell = bySeverity.findIndex((e) => !e.injected);
  const longest = [...events].sort((a, b) => b.duration - a.duration)[0];
  const oneMonth = events.filter((e) => e.duration === 1).length;

  // Share of months inside injected spells where SPI-3 / SPI-12 are in drought
  const inDrought = (scale) => {
    let hits = 0, total = 0;
    for (const s of spells) {
      for (const r of s.regions) {
        data.monthly.dates.forEach((ym, i) => {
          if (ym < s.start || ym > s.end) return;
          const v = data.monthly.regions[r][`spi_${scale}`][i];
          total++;
          if (v !== null && v < c.DROUGHT_THRESHOLD) hits++;
        });
      }
    }
    return hits / total;
  };
  const longScale = Math.max(...c.SPI_SCALES);

  // Yield vs growing-season SPI
  const rByRegion = regions.map((r) => {
    const rows = data.annual.filter((a) => a.region === r);
    return pearson(rows.map((a) => a.spi_gs), rows.map((a) => a.yield_t_ha / a.trend_t_ha - 1));
  });

  // Contract outcomes (pipeline contract)
  const hitsRows = contract.filter((r) => r.paid && r.lossYear);
  const faRows = contract.filter((r) => r.paid && !r.lossYear);
  const missRows = contract.filter((r) => !r.paid && r.lossYear);
  const meanOf = (rows, f) => rows.reduce((a, r) => a + f(r), 0) / rows.length;
  const payoutLevels = new Set(contract.filter((r) => r.paid).map((r) => r.payout.toFixed(6)));
  const [ciLo, ciHi] = wilson(pooled.hits, pooled.loss_years);
  const regionMetrics = data.metrics.filter((m) => m.region !== d.pooled_label);
  const best = regionMetrics.reduce((a, b) => (b.hit_rate > a.hit_rate ? b : a));
  const worst = regionMetrics.reduce((a, b) => (b.hit_rate < a.hit_rate ? b : a));

  // Loss years whose growing season overlaps an injected spell, vs the rest
  const seasonStart = String(d.season_start_month).padStart(2, "0");
  const seasonEnd = String(c.GROWING_SEASON_END_MONTH).padStart(2, "0");
  const duringSpell = (r) => inInjectedSpell(r.region, `${r.year}-${seasonStart}`,
    `${r.year}-${seasonEnd}`, spells);
  const spellLoss = contract.filter((r) => r.lossYear && duringSpell(r));
  const otherLoss = contract.filter((r) => r.lossYear && !duringSpell(r));

  const realisedAnnual = regions.map((r) =>
    data.monthly.regions[r].rain.reduce((a, b) => a + b, 0) / d.n_years);

  return {
    nRegions: regions.length,
    regionList: listJoin(regions),
    startYear: c.START_YEAR,
    endYear: c.END_YEAR,
    nYears: d.n_years,
    nMonths: data.monthly.dates.length,
    seed: c.SEED,
    seedYield: c.SEED + 1,
    ar1Phi: num(c.AR1_PHI, 2),
    ar1Sigma: num(c.AR1_SIGMA, 2),
    nSpells: spells.length,
    spellYears: listJoin(spells.map((s) => {
      const a = s.start.slice(0, 4), b = s.end.slice(0, 4);
      return a === b ? a : `${a}–${b.slice(2)}`;
    })),
    spellCutMin: pct(1 - Math.max(...factors)),
    spellCutMax: pct(1 - Math.min(...factors)),
    spellRegionsMin: Math.min(...spells.map((s) => s.regions.length)),
    spellRegionsMax: Math.max(...spells.map((s) => s.regions.length)),
    realisedMin: num(Math.min(...realisedAnnual), 0),
    realisedMax: num(Math.max(...realisedAnnual), 0),

    spiScales: listJoin(c.SPI_SCALES.map((s) => `SPI-${s}`)),
    calPeriod: `${c.SPI_CALIBRATION[0]}–${c.SPI_CALIBRATION[1]}`,
    spiCap: num(d.spi_cap, 2),
    pMin: powerOfTen(d.spi_prob_min),
    droughtThr: num(c.DROUGHT_THRESHOLD, 1),
    eventScale: `SPI-${c.EVENT_SPI_SCALE}`,
    minEventDur: c.MIN_EVENT_DURATION,

    season: `${MONTHS[d.season_start_month - 1]}–${MONTHS[c.GROWING_SEASON_END_MONTH - 1]}`,
    seasonEnd: MONTHS[c.GROWING_SEASON_END_MONTH - 1],
    gsIndex: `SPI-${c.GROWING_SEASON_MONTHS}`,
    trendPct: pct(c.YIELD_TREND_PER_YEAR, 1),
    betaDry: num(c.YIELD_BETA_DRY, 2),
    betaWet: num(c.YIELD_BETA_WET, 2),
    betaRatio: num(c.YIELD_BETA_DRY / c.YIELD_BETA_WET, 1),
    noiseSd: pct(c.YIELD_NOISE_SD),
    floor: num(c.YIELD_EFFECT_FLOOR, 1),
    floorPct: pct(-c.YIELD_EFFECT_FLOOR),

    windows: listJoin(c.TRIGGER_WINDOW_END_MONTHS.map(windowLabel)),
    windowEnds: listJoin(c.TRIGGER_WINDOW_END_MONTHS.map((m) => MONTHS[m - 1])),
    nWindows: c.TRIGGER_WINDOW_END_MONTHS.length,
    nCandidateWindows: d.candidate_windows.length,
    nTiers: tiers.length,
    triggerThr: num(trigger, 1),
    sumInsuredPct: pct(c.SUM_INSURED_FRACTION),
    lossThrPct: pct(c.LOSS_THRESHOLD),

    nEvents: events.length,
    eventsInSpells: inSpell.length,
    eventsInSpellsPct: pct(inSpell.length / events.length),
    spellPairs: pairs.length,
    spellPairsDetected: detected.length,
    topInSpell: topInSpell === -1 ? events.length : topInSpell,
    oneMonthEvents: oneMonth,
    oneMonthPct: pct(oneMonth / events.length),
    longestRegion: longest.region,
    longestStart: ymLabel(longest.start),
    longestDuration: longest.duration,
    shortScale: `SPI-${Math.min(...c.SPI_SCALES)}`,
    longScale: `SPI-${longScale}`,
    spellShortPct: pct(inDrought(Math.min(...c.SPI_SCALES))),
    spellLongPct: pct(inDrought(longScale)),

    rMin: num(Math.min(...rByRegion), 2),
    rMax: num(Math.max(...rByRegion), 2),

    nRegionYears: pooled.n_years,
    lossYears: pooled.loss_years,
    payouts: pooled.payouts,
    hits: pooled.hits,
    misses: pooled.misses,
    falseAlarms: pooled.false_alarms,
    hitRate: pct(pooled.hit_rate),
    hitRateLo: pct(ciLo),
    hitRateHi: pct(ciHi),
    far: pct(pooled.false_alarm_ratio),
    rmse: num(100 * pooled.basis_risk_rmse, 1),
    meanGap: num(100 * pooled.mean_abs_gap, 1),
    corr: num(pooled.payout_loss_corr, 2),
    paidToLoss: num(pooled.total_paid / pooled.total_loss, 2),
    bestRegion: best.region,
    bestHitRate: pct(best.hit_rate),
    worstRegion: worst.region,
    worstHitRate: pct(worst.hit_rate),
    bestLossYears: best.loss_years,
    worstLossYears: worst.loss_years,
    missesWetSeason: missRows.filter((r) => r.spi_gs >= 0).length,
    lossYearsWetSeason: contract.filter((r) => r.lossYear && r.spi_gs >= 0).length,
    spellLossYears: spellLoss.length,
    spellLossPaid: spellLoss.filter((r) => r.paid).length,
    otherLossYears: otherLoss.length,
    otherLossPaid: otherLoss.filter((r) => r.paid).length,
    missMeanIndex: num(meanOf(missRows, (r) => r.index), 2),
    nPayoutLevels: payoutLevels.size,
    faMeanGs: num(meanOf(faRows, (r) => r.spi_gs), 2),
    hitMeanGs: num(meanOf(hitsRows, (r) => r.spi_gs), 2),
    faMeanLoss: num(100 * meanOf(faRows, (r) => r.loss_frac), 1),
  };
}

function bindFacts(facts) {
  for (const node of document.querySelectorAll("[data-bind]")) {
    const key = node.dataset.bind;
    if (key in facts) {
      node.textContent = facts[key];
    } else {
      node.textContent = "?";
      node.classList.add("missing");
      console.error(`No fact named "${key}"`);
    }
  }
}

// ---------------------------------------------------------------------------
// Tables
// ---------------------------------------------------------------------------
function cell(tag, text, cls) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (cls) node.className = cls;
  return node;
}

function sparkline(values, t) {
  const w = 72, h = 22, max = Math.max(...values);
  const bw = w / values.length;
  const bars = values.map((v, i) => {
    const bh = (v / max) * (h - 2);
    return `<rect x="${(i * bw + 0.5).toFixed(1)}" y="${(h - bh).toFixed(1)}" width="${(bw - 1).toFixed(1)}" height="${bh.toFixed(1)}"/>`;
  }).join("");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${t}">${bars}</svg>`;
}

function renderRegionsTable(data) {
  const c = data.config;
  const body = document.querySelector("#regions-table tbody");
  for (const [region, p] of Object.entries(c.REGIONS)) {
    const rain = data.monthly.regions[region].rain;
    const clim = MONTHS.map((_, m) => {
      const vals = rain.filter((_, i) => i % 12 === m);
      return vals.reduce((a, b) => a + b, 0) / vals.length;
    });
    const realised = rain.reduce((a, b) => a + b, 0) / c.derived.n_years;
    const tr = document.createElement("tr");
    tr.append(
      cell("th", region),
      cell("td", `${p.annual_mm}`),
      cell("td", num(realised, 0)),
      cell("td", MONTHS[p.peak_month - 1]),
      cell("td", num(p.seasonality, 2)),
      cell("td", `${num(p.gamma_shape, 1)} (${num(1 / Math.sqrt(p.gamma_shape), 2)})`),
      cell("td", pct(p.p_zero_max)),
      cell("td", num(p.base_yield, 1)),
    );
    const spark = document.createElement("td");
    spark.innerHTML = sparkline(clim, `Mean monthly rainfall, ${region}`);
    tr.append(spark);
    body.append(tr);
  }
}

function renderSpellTimeline(data) {
  const c = data.config;
  const box = document.querySelector("#spell-timeline");
  const t0 = c.START_YEAR, span = c.END_YEAR - c.START_YEAR + 1;
  const pos = (ym) => {
    const [y, m] = ym.split("-").map(Number);
    return ((y - t0) + (m - 1) / 12) / span * 100;
  };
  for (const region of Object.keys(c.REGIONS)) {
    const row = document.createElement("div");
    row.className = "tl-row";
    row.append(cell("div", region, "tl-label"));
    const track = document.createElement("div");
    track.className = "tl-track";
    for (const s of c.DRY_SPELLS.filter((sp) => sp.regions.includes(region))) {
      const bar = document.createElement("div");
      bar.className = "tl-bar";
      const [ey, em] = afterMonth(s.end).split("-");
      bar.style.left = `${pos(s.start)}%`;
      bar.style.width = `${pos(`${ey}-${em}`) - pos(s.start)}%`;
      bar.title = `${ymLabel(s.start)} – ${ymLabel(s.end)}: rainfall × ${s.factor}`;
      bar.textContent = `−${Math.round((1 - s.factor) * 100)}%`;
      track.append(bar);
    }
    row.append(track);
    box.append(row);
  }
  const axis = document.createElement("div");
  axis.className = "tl-row tl-axis";
  axis.append(cell("div", "", "tl-label"));
  const ticks = document.createElement("div");
  ticks.className = "tl-track";
  for (let y = Math.ceil(t0 / 5) * 5; y <= c.END_YEAR; y += 5) {
    const tick = cell("span", String(y), "tl-tick");
    tick.style.left = `${pos(`${y}-01`)}%`;
    ticks.append(tick);
  }
  axis.append(ticks);
  box.append(axis);
}

function renderTierTable(data) {
  const c = data.config;
  const body = document.querySelector("#tier-table tbody");
  let upper = null;
  c.PAYOUT_TIERS.forEach(([thr, pay], i) => {
    const tr = document.createElement("tr");
    tr.append(
      cell("th", `Tier ${i + 1}`),
      cell("td", upper === null ? `I ≤ ${num(thr, 2)}` : `${num(upper, 2)} < I ≤ ${num(thr, 2)}`),
      cell("td", pct(pay)),
      cell("td", pct(pay * c.SUM_INSURED_FRACTION, 1)),
    );
    body.append(tr);
    upper = thr;
  });
  const tr = document.createElement("tr");
  tr.append(cell("th", "No payout"), cell("td", `I > ${num(upper, 2)}`), cell("td", "0%"), cell("td", "0%"));
  body.append(tr);
}

function renderMetricsTable(data) {
  const body = document.querySelector("#metrics-table tbody");
  for (const m of data.metrics) {
    const tr = document.createElement("tr");
    if (m.region === data.config.derived.pooled_label) tr.className = "total";
    tr.append(
      cell("th", m.region),
      cell("td", `${m.n_years}`),
      cell("td", `${m.loss_years}`),
      cell("td", `${m.payouts}`),
      cell("td", `${m.hits}`),
      cell("td", `${m.misses}`),
      cell("td", `${m.false_alarms}`),
      cell("td", pct(m.hit_rate)),
      cell("td", pct(m.false_alarm_ratio)),
      cell("td", num(100 * m.basis_risk_rmse, 1)),
      cell("td", num(100 * m.mean_abs_gap, 1)),
      cell("td", num(m.payout_loss_corr, 2)),
    );
    body.append(tr);
  }
}

function renderEventsTable(data, region) {
  const spells = data.config.DRY_SPELLS;
  const events = data.events.filter((e) => e.region === region)
    .sort((a, b) => b.severity - a.severity);
  const body = document.querySelector("#events-table tbody");
  body.replaceChildren(...events.map((e) => {
    const tr = document.createElement("tr");
    const injected = inInjectedSpell(e.region, e.start, e.end, spells);
    tr.append(
      cell("td", ymLabel(e.start)),
      cell("td", ymLabel(e.end)),
      cell("td", `${e.duration}`),
      cell("td", num(e.severity, 2)),
      cell("td", num(e.intensity, 2)),
      cell("td", num(e.peak_spi, 2)),
      cell("td", injected ? "yes" : "", injected ? "flag" : ""),
    );
    return tr;
  }));
  document.querySelector("#events-count").textContent =
    `${events.length} events in ${region}, most severe first`;
}

// ---------------------------------------------------------------------------
// Figures from the pipeline
// ---------------------------------------------------------------------------
function renderFigures(data, facts) {
  const box = document.querySelector("#figure-gallery");
  const groups = [];
  for (const f of data.figures) {
    let g = groups.find((x) => x.id === f.id);
    if (!g) groups.push(g = { id: f.id, files: [] });
    g.files.push(f);
  }
  for (const g of groups) {
    const caption = CAPTIONS[g.id];
    const fig = document.createElement("figure");
    fig.className = "pipeline-fig";
    fig.id = `figure-${g.id}`;

    const link = document.createElement("a");
    const img = document.createElement("img");
    img.loading = "lazy";
    link.append(img);
    const show = (f) => {
      link.href = f.file;
      img.src = f.file;
      img.width = f.width;
      img.height = f.height;
      img.alt = caption ? caption.alt(f.region) : f.file;
    };

    if (g.files.length > 1) {        // one file per region: add region tabs
      const tabs = document.createElement("div");
      tabs.className = "tabs";
      tabs.setAttribute("role", "tablist");
      g.files.forEach((f, i) => {
        const b = cell("button", f.region || f.file);
        b.type = "button";
        b.setAttribute("role", "tab");
        b.setAttribute("aria-selected", i === 0);
        b.addEventListener("click", () => {
          tabs.querySelectorAll("button").forEach((x) => x.setAttribute("aria-selected", x === b));
          show(f);
        });
        tabs.append(b);
      });
      fig.append(tabs);
    }
    show(g.files[0]);
    fig.append(link);

    const cap = document.createElement("figcaption");
    const fileNames = g.files.length > 1
      ? `${g.id}_*.png` : g.files[0].file.split("/").pop();
    cap.innerHTML = caption
      ? `<strong>${caption.title}</strong> ${caption.text(facts)} <span class="file">${fileNames}</span>`
      : fileNames;
    fig.append(cap);
    box.append(fig);
  }
}

// ---------------------------------------------------------------------------
// Page chrome: equations, navigation, theme changes
// ---------------------------------------------------------------------------
function renderMath() {
  if (!window.katex) return;   // CDN unavailable: the TeX source stays readable
  for (const node of document.querySelectorAll(".eq, .m")) {
    window.katex.render(node.textContent, node, {
      displayMode: node.classList.contains("eq"), throwOnError: false,
    });
  }
}

function initNav() {
  const links = [...document.querySelectorAll(".site-nav a[href^='#']")];
  const sections = links.map((a) => document.querySelector(a.getAttribute("href")));
  const strip = document.querySelector(".site-nav ul");
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const i = sections.indexOf(entry.target);
      links.forEach((a, j) => a.classList.toggle("active", i === j));
      // On phones the menu scrolls sideways: keep the current item in view
      if (strip.scrollWidth > strip.clientWidth) {
        strip.scrollTo({ left: links[i].offsetLeft - 16, behavior: "smooth" });
      }
    }
  }, { rootMargin: "-45% 0px -50% 0px" });
  sections.forEach((s) => observer.observe(s));
}

function regionSelect(id, regions, extraLabel) {
  const sel = document.getElementById(id);
  if (extraLabel) sel.append(new Option(extraLabel, ""));
  for (const r of regions) sel.append(new Option(r, r));
  return sel;
}

async function main() {
  initNav();
  let data;
  try {
    data = await loadData();
  } catch (err) {
    document.body.classList.add("load-failed");
    document.querySelector("#load-error").hidden = false;
    console.error(err);
    return;
  }

  const regions = Object.keys(data.config.REGIONS);
  const contract = applyContract(data.annual, pipelineSettings(data.config));
  const facts = computeFacts(data, contract);

  bindFacts(facts);
  renderRegionsTable(data);
  renderSpellTimeline(data);
  renderTierTable(data);
  renderMetricsTable(data);
  renderFigures(data, facts);
  renderMath();

  const spiSel = regionSelect("spi-region", regions);
  const yieldSel = regionSelect("yield-region", regions, data.config.derived.pooled_label);
  renderEventsTable(data, spiSel.value);
  spiSel.addEventListener("change", () => renderEventsTable(data, spiSel.value));

  const explorer = initExplorer(document.querySelector("#explorer"), data);

  if (!window.Plotly) {
    for (const node of document.querySelectorAll(".chart")) {
      node.textContent = "Interactive chart unavailable: the charting library (Plotly, loaded from a CDN) could not be loaded.";
      node.classList.add("chart-missing");
    }
    return;
  }
  const drawSpi = () => drawSpiSeries(document.querySelector("#spi-chart"), data, spiSel.value);
  const drawYield = () => drawSpiVsYield(document.querySelector("#yield-chart"), data, contract,
    yieldSel.value || null);
  spiSel.addEventListener("change", drawSpi);
  yieldSel.addEventListener("change", drawYield);
  drawSpi();
  drawYield();

  // Redraw charts with the new colours when the system theme changes
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    drawSpi(); drawYield(); explorer.redraw();
  });
  document.body.dataset.ready = "true";
}

main();
