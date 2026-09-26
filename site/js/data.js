// Loading the pipeline's JSON exports, plus small formatting helpers.
// Every number on the page is derived from these files (see src/export_site.py).

const FILES = ["config", "monthly", "annual", "events", "metrics", "figures"];

export async function loadData() {
  const loaded = await Promise.all(FILES.map(async (name) => {
    const res = await fetch(`data/${name}.json`);
    if (!res.ok) throw new Error(`data/${name}.json: HTTP ${res.status}`);
    return res.json();
  }));
  return Object.fromEntries(FILES.map((name, i) => [name, loaded[i]]));
}

export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
  "Sep", "Oct", "Nov", "Dec"];

const MINUS = "−";
const isMissing = (x) => x === null || x === undefined || Number.isNaN(x);

/** Number with fixed decimals and a proper minus sign; "–" if missing. */
export function num(x, digits = 2) {
  if (isMissing(x)) return "–";
  return x.toFixed(digits).replace("-", MINUS);
}

/** Fraction as a percentage, e.g. 0.698 -> "70%". */
export function pct(x, digits = 0) {
  if (isMissing(x)) return "–";
  return `${num(x * 100, digits)}%`;
}

/** 1e-6 -> "10⁻⁶" (only for powers of ten). */
export function powerOfTen(x) {
  const sup = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵",
    6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
  const exponent = String(Math.round(Math.log10(x)));
  return `10${[...exponent].map((ch) => sup[ch]).join("")}`;
}

/** ["a", "b", "c"] -> "a, b and c" */
export function listJoin(items) {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** Label of the 3-month window ending in `endMonth`, e.g. 8 -> "Jun–Aug". */
export function windowLabel(endMonth) {
  const start = ((endMonth - 3 + 12) % 12) + 1;
  return `${MONTHS[start - 1]}–${MONTHS[endMonth - 1]}`;
}

/** "2006-12" -> "Dec 2006" */
export function ymLabel(ym) {
  const [y, m] = ym.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

/** First day of the month after "YYYY-MM" (used as the end of a shaded band). */
export function afterMonth(ym) {
  let [y, m] = ym.split("-").map(Number);
  m += 1;
  if (m === 13) { y += 1; m = 1; }
  return `${y}-${String(m).padStart(2, "0")}-01`;
}

/** Does the event (or any month range) overlap an injected dry spell for this region? */
export function inInjectedSpell(region, start, end, spells) {
  return spells.some((s) => s.regions.includes(region)
    && start <= s.end && end >= s.start);
}

/** Pearson correlation of two equal-length arrays. */
export function pearson(x, y) {
  const n = x.length;
  const mx = x.reduce((a, b) => a + b, 0) / n;
  const my = y.reduce((a, b) => a + b, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
    syy += (y[i] - my) ** 2;
  }
  return sxy / Math.sqrt(sxx * syy);
}

/** Least-squares line y = a + b x. */
export function linearFit(x, y) {
  const n = x.length;
  const mx = x.reduce((a, b) => a + b, 0) / n;
  const my = y.reduce((a, b) => a + b, 0) / n;
  let sxy = 0, sxx = 0;
  for (let i = 0; i < n; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
  }
  const b = sxy / sxx;
  return { a: my - b * mx, b };
}

/** 95% Wilson score interval for a proportion k/n. */
export function wilson(k, n, z = 1.96) {
  const p = k / n;
  const denom = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / denom;
  const half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / denom;
  return [centre - half, centre + half];
}
