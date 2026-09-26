// Contract explorer: sliders -> contract.js -> metrics, table and charts.

import { applyContract, evaluate, parityCheck } from "./contract.js";
import { drawPayoutScatter, drawYearBars } from "./charts.js";
import { MONTHS, num, pct, windowLabel } from "./data.js";

const STEP = 0.01;           // threshold step (SPI units)
const THRESHOLD_RANGE = [-3, -0.25];

/** The pipeline's own contract, from config.json. */
export function pipelineSettings(cfg) {
  return {
    tiers: cfg.PAYOUT_TIERS.map(([thr, pay]) => [thr, pay]),
    sumInsured: cfg.SUM_INSURED_FRACTION,
    lossThreshold: cfg.LOSS_THRESHOLD,
    windows: [...cfg.TRIGGER_WINDOW_END_MONTHS],
  };
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c);
  return node;
}

function slider({ id, label, min, max, step, value, format }) {
  const input = el("input", { type: "range", id, min, max, step, value });
  const out = el("output", { for: id, text: format(value) });
  const wrap = el("div", { class: "slider" }, [
    el("label", { for: id }, [el("span", { text: label }), out]), input]);
  return { wrap, input, out, format };
}

export function initExplorer(root, data) {
  const cfg = data.config;
  const regions = Object.keys(cfg.REGIONS);
  const pooled = cfg.derived.pooled_label;
  const defaults = pipelineSettings(cfg);
  const baseline = evaluate(applyContract(data.annual, defaults), regions, pooled);

  // ---- Parity: browser port vs pipeline, with the pipeline's own settings
  const problems = parityCheck(baseline, data.metrics);
  const badge = root.querySelector("#parity");
  if (problems.length === 0) {
    badge.className = "badge ok";
    badge.textContent = "✓ With the pipeline's settings, this explorer reproduces contract_metrics.csv exactly";
  } else {
    badge.className = "badge warn";
    badge.textContent = `⚠ Browser and pipeline disagree (${problems.length} values) — see console`;
    console.warn("Parity check failed:", problems);
  }

  let state = structuredClone(defaults);
  let view = "";   // "" = pooled

  // ---- Controls ------------------------------------------------------------
  const tierBox = root.querySelector("#tier-controls");
  const tierSliders = state.tiers.map(([thr, pay], i) => {
    const n = state.tiers.length;
    const name = i === 0 ? "most severe" : i === n - 1 ? "trigger" : "";
    const tThr = slider({ id: `tier${i}-thr`, label: "Index ≤", step: STEP,
      min: Math.min(THRESHOLD_RANGE[0], thr), max: Math.max(THRESHOLD_RANGE[1], thr),
      value: thr, format: (v) => num(+v, 2) });
    const tPay = slider({ id: `tier${i}-pay`, label: "Pays", min: 0, max: 100, step: 1,
      value: Math.round(pay * 100), format: (v) => `${v}% of sum insured` });
    tierBox.append(el("fieldset", { class: "tier" }, [
      el("legend", { text: `Tier ${i + 1}${name ? ` (${name})` : ""}` }), tThr.wrap, tPay.wrap]));
    return { tThr, tPay };
  });

  const sumSlider = slider({ id: "sum-insured", label: "Sum insured", min: 5, max: 100,
    step: 1, value: Math.round(state.sumInsured * 100), format: (v) => `${v}% of expected yield` });
  const lossSlider = slider({ id: "loss-thr", label: "Loss year if shortfall >", min: 0,
    max: 40, step: 0.5, value: state.lossThreshold * 100, format: (v) => `${num(+v, 1)}%` });
  root.querySelector("#other-controls").append(sumSlider.wrap, lossSlider.wrap);

  const winBox = root.querySelector("#window-controls");
  const winInputs = cfg.derived.candidate_windows.map((m) => {
    const input = el("input", { type: "checkbox", value: m, id: `win-${m}` });
    input.checked = state.windows.includes(m);
    winBox.append(el("label", { class: "check", for: `win-${m}` },
      [input, el("span", { text: windowLabel(m) })]));
    return input;
  });

  const regionSelect = root.querySelector("#explorer-region");
  regionSelect.append(el("option", { value: "", text: pooled }));
  for (const r of regions) regionSelect.append(el("option", { value: r, text: r }));

  // Keep tiers ordered: thresholds rise and payouts fall from tier 1 to tier n.
  function enforceOrder(changed, kind) {
    const tiers = state.tiers;
    const n = tiers.length;
    if (kind === "thr") {
      for (let j = changed - 1; j >= 0; j--) tiers[j][0] = Math.min(tiers[j][0], tiers[j + 1][0] - STEP);
      for (let j = changed + 1; j < n; j++) tiers[j][0] = Math.max(tiers[j][0], tiers[j - 1][0] + STEP);
      tiers.forEach((t) => { t[0] = Math.round(t[0] / STEP) * STEP; });
    } else {
      for (let j = changed - 1; j >= 0; j--) tiers[j][1] = Math.max(tiers[j][1], tiers[j + 1][1]);
      for (let j = changed + 1; j < n; j++) tiers[j][1] = Math.min(tiers[j][1], tiers[j - 1][1]);
    }
  }

  function syncInputs() {
    state.tiers.forEach(([thr, pay], i) => {
      const { tThr, tPay } = tierSliders[i];
      tThr.input.value = thr; tThr.out.textContent = tThr.format(thr);
      tPay.input.value = Math.round(pay * 100); tPay.out.textContent = tPay.format(Math.round(pay * 100));
    });
    sumSlider.input.value = Math.round(state.sumInsured * 100);
    sumSlider.out.textContent = sumSlider.format(sumSlider.input.value);
    lossSlider.input.value = state.lossThreshold * 100;
    lossSlider.out.textContent = lossSlider.format(lossSlider.input.value);
    winInputs.forEach((w) => { w.checked = state.windows.includes(+w.value); });
  }

  tierSliders.forEach(({ tThr, tPay }, i) => {
    tThr.input.addEventListener("input", () => {
      state.tiers[i][0] = +tThr.input.value; enforceOrder(i, "thr"); update();
    });
    tPay.input.addEventListener("input", () => {
      state.tiers[i][1] = +tPay.input.value / 100; enforceOrder(i, "pay"); update();
    });
  });
  sumSlider.input.addEventListener("input", () => { state.sumInsured = +sumSlider.input.value / 100; update(); });
  lossSlider.input.addEventListener("input", () => { state.lossThreshold = +lossSlider.input.value / 100; update(); });
  winInputs.forEach((w) => w.addEventListener("change", () => {
    const chosen = winInputs.filter((x) => x.checked).map((x) => +x.value);
    if (chosen.length === 0) { w.checked = true; return; }   // need at least one window
    state.windows = chosen; update();
  }));
  regionSelect.addEventListener("change", () => { view = regionSelect.value; update(); });
  root.querySelector("#explorer-reset").addEventListener("click", () => {
    state = structuredClone(defaults); update();
  });

  // ---- Outputs -------------------------------------------------------------
  // Each tile: how to show the value, how to show a change, and which
  // direction is better (+1 higher, -1 lower, 0 neither).
  const pp = (d, digits) => `${num(100 * Math.abs(d), digits)} pp`;
  const TILES = [
    { key: "hit_rate", label: "Hit rate", fmt: (v) => pct(v), dfmt: (d) => pp(d, 0), better: +1,
      help: "Share of loss years that received a payout" },
    { key: "false_alarm_ratio", label: "False alarm ratio", fmt: (v) => pct(v), dfmt: (d) => pp(d, 0), better: -1,
      help: "Share of payouts made in years without a loss" },
    { key: "misses", label: "Missed losses", fmt: String, dfmt: (d) => String(Math.abs(d)), better: -1,
      help: "Loss years with no payout" },
    { key: "false_alarms", label: "False alarms", fmt: String, dfmt: (d) => String(Math.abs(d)), better: -1,
      help: "Payouts in years without a loss" },
    { key: "basis_risk_rmse", label: "Basis risk (RMSE)", fmt: (v) => `${num(100 * v, 1)} pp`,
      dfmt: (d) => pp(d, 1), better: -1,
      help: "Root-mean-square gap between payout and loss, in percentage points of expected yield" },
    { key: "payout_loss_corr", label: "Payout–loss correlation", fmt: (v) => num(v, 2),
      dfmt: (d) => num(Math.abs(d), 2), better: +1,
      help: "Pearson correlation of payout and loss amounts" },
    { key: "paid_to_loss", label: "Total paid ÷ total loss", fmt: (v) => num(v, 2),
      dfmt: (d) => num(Math.abs(d), 2), better: 0,
      help: "Above 1: the contract pays out more in total than the losses it is meant to cover" },
  ];
  const tileBox = root.querySelector("#explorer-tiles");
  const tileEls = TILES.map((tile) => {
    const value = el("div", { class: "tile-value" });
    const delta = el("div", { class: "tile-delta" });
    tileBox.append(el("div", { class: "tile", title: tile.help },
      [el("div", { class: "tile-label", text: tile.label }), value, delta]));
    return { value, delta };
  });

  const withRatio = (m) => ({ ...m, paid_to_loss: m.total_loss ? m.total_paid / m.total_loss : NaN });

  function deltaText(tile, now, base) {
    if (Number.isNaN(now) || Number.isNaN(base)) return ["", ""];
    const d = now - base;
    if (Math.abs(d) < 1e-9) return ["same as pipeline contract", ""];
    const cls = tile.better === 0 ? "" : d * tile.better > 0 ? "better" : "worse";
    return [`${d > 0 ? "+" : "−"}${tile.dfmt(d)} vs pipeline contract`, cls];
  }

  const summary = root.querySelector("#explorer-summary");
  const tableBody = root.querySelector("#explorer-table tbody");

  function update() {
    syncInputs();
    const rows = applyContract(data.annual, state);
    const all = evaluate(rows, regions, pooled);
    const key = view || pooled;
    const m = withRatio(all[key]);
    const b = withRatio(baseline[key]);

    TILES.forEach((tile, i) => {
      tileEls[i].value.textContent = tile.fmt(m[tile.key]);
      const [text, cls] = deltaText(tile, m[tile.key], b[tile.key]);
      tileEls[i].delta.textContent = text;
      tileEls[i].delta.className = `tile-delta ${cls}`;
    });

    const active = state.tiers.filter(([, p]) => p > 0);
    const trigger = active.length ? active[active.length - 1][0] : null;
    summary.textContent = trigger === null
      ? "No tier pays anything: the contract never pays."
      : `Index = lowest SPI-3 over ${state.windows.map(windowLabel).join(", ")}. `
        + `Pays when the index is ≤ ${num(trigger, 2)}. `
        + `${key}: ${m.loss_years} loss years, ${m.payouts} payouts in ${m.n_years} region-years.`;

    tableBody.replaceChildren(...[...regions, pooled].map((r) => {
      const x = all[r];
      return el("tr", r === key ? { class: "current" } : {}, [
        el("th", { scope: "row", text: r }),
        el("td", { text: `${x.loss_years}` }),
        el("td", { text: `${x.payouts}` }),
        el("td", { text: `${x.hits}` }),
        el("td", { text: `${x.misses}` }),
        el("td", { text: `${x.false_alarms}` }),
        el("td", { text: pct(x.hit_rate) }),
        el("td", { text: pct(x.false_alarm_ratio) }),
        el("td", { text: num(100 * x.basis_risk_rmse, 1) }),
        el("td", { text: num(x.payout_loss_corr, 2) }),
      ]);
    }));

    if (window.Plotly) {
      const shown = view ? rows.filter((r) => r.region === view) : rows;
      drawPayoutScatter(root.querySelector("#explorer-scatter"), shown, state.lossThreshold);
      drawYearBars(root.querySelector("#explorer-years"), rows, view || null);
    }
  }

  update();
  return { redraw: update };
}
