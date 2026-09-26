// Contract logic: a line-for-line port of src/insurance.py.
//
// No page code here, so the same functions drive the explorer and the
// parity check (which confirms that, with the pipeline's own settings,
// these functions reproduce results/contract_metrics.csv).

// settings = {
//   tiers:         [[threshold, payout share of sum insured], ...], most severe first
//   sumInsured:    sum insured as a fraction of expected yield
//   lossThreshold: shortfall below trend that makes a "loss year"
//   windows:       end months of the SPI-3 windows used for the index
// }

/** Payout as a fraction of the sum insured (insurance.payout_fraction). */
export function tierPayout(index, tiers) {
  for (const [threshold, payout] of tiers) {   // tiers run most severe first
    if (index <= threshold) return payout;
  }
  return 0;
}

/** Index = lowest SPI-3 over the chosen windows (spi.growing_season_table). */
export function triggerIndex(row, windows) {
  let min = NaN;
  for (const m of windows) {
    const v = row.spi3[String(m)];
    if (v !== null && v !== undefined && !(v >= min)) min = v;
  }
  return min;
}

/** Apply a contract to every region-year (insurance.apply_contract). */
export function applyContract(rows, s) {
  return rows.map((r) => {
    const index = triggerIndex(r, s.windows);
    const tier = Number.isNaN(index) ? 0 : tierPayout(index, s.tiers);
    return {
      ...r,
      index,
      tier,
      payout: tier * s.sumInsured,
      paid: tier > 0,
      lossYear: r.loss_frac > s.lossThreshold,
    };
  });
}

function mean(xs) {
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

/** Pearson correlation; NaN when either series is constant (like numpy). */
function corr(x, y) {
  const mx = mean(x), my = mean(y);
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < x.length; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
    syy += (y[i] - my) ** 2;
  }
  return sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : NaN;
}

/** Skill scores for one group of region-years (insurance._metrics). */
export function metrics(rows) {
  let hits = 0, misses = 0, falseAlarms = 0, correctNeg = 0;
  for (const r of rows) {
    if (r.paid && r.lossYear) hits++;
    else if (!r.paid && r.lossYear) misses++;
    else if (r.paid) falseAlarms++;
    else correctNeg++;
  }
  const gap = rows.map((r) => r.payout - r.loss_frac);
  return {
    n_years: rows.length,
    loss_years: hits + misses,
    payouts: hits + falseAlarms,
    hits,
    misses,
    false_alarms: falseAlarms,
    correct_negatives: correctNeg,
    hit_rate: hits + misses ? hits / (hits + misses) : NaN,
    false_alarm_ratio: hits + falseAlarms ? falseAlarms / (hits + falseAlarms) : NaN,
    basis_risk_rmse: Math.sqrt(mean(gap.map((g) => g * g))),
    mean_abs_gap: mean(gap.map(Math.abs)),
    payout_loss_corr: corr(rows.map((r) => r.payout), rows.map((r) => r.loss_frac)),
    total_paid: rows.reduce((a, r) => a + r.payout, 0),
    total_loss: rows.reduce((a, r) => a + r.loss_frac, 0),
  };
}

/** Metrics per region and pooled (insurance.evaluate_contract). */
export function evaluate(contractRows, regions, pooledLabel) {
  const out = {};
  for (const region of regions) {
    out[region] = metrics(contractRows.filter((r) => r.region === region));
  }
  out[pooledLabel] = metrics(contractRows);
  return out;
}

/** "hit" | "false_alarm" | "miss" | "correct" for one region-year. */
export function outcome(r) {
  if (r.paid && r.lossYear) return "hit";
  if (r.paid) return "false_alarm";
  if (r.lossYear) return "miss";
  return "correct";
}

/**
 * Compare browser metrics with the pipeline's metrics.json.
 * Counts must match exactly; ratios to within the pipeline's 3-decimal rounding.
 * Returns a list of mismatch descriptions (empty = parity).
 */
const COUNT_KEYS = new Set(["n_years", "loss_years", "payouts", "hits",
  "misses", "false_alarms", "correct_negatives"]);

export function parityCheck(browser, pipelineRows) {
  const problems = [];
  for (const row of pipelineRows) {
    const mine = browser[row.region];
    if (!mine) { problems.push(`${row.region}: missing`); continue; }
    for (const [key, expected] of Object.entries(row)) {
      if (key === "region") continue;
      const got = mine[key];
      const bothMissing = expected === null && Number.isNaN(got);
      const ok = COUNT_KEYS.has(key)
        ? got === expected
        : bothMissing || Math.abs(got - expected) <= 0.0005 + 1e-9;
      if (!ok) problems.push(`${row.region} ${key}: pipeline ${expected}, browser ${got}`);
    }
  }
  return problems;
}
