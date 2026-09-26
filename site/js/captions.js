// Captions for the pipeline's PNG figures, keyed by figure id (fig1, fig2a, ...).
// Numbers come from `f` (the facts computed in main.js), never typed here.

export const CAPTIONS = {
  fig1: {
    title: "Rainfall and SPI, one region at a time.",
    alt: (region) => `Monthly rainfall and SPI time series for ${region}`,
    text: (f) => `Top: monthly rainfall with its 12-month running mean. Bottom: ${f.shortScale} (blue)
      and ${f.longScale} (orange), with the drought threshold (SPI = ${f.droughtThr}, dashed red).
      Grey bands are the injected dry spells. <em>Notice</em> how the two time scales behave differently
      inside the spells: ${f.longScale} sinks and stays down (below the threshold in ${f.spellLongPct}
      of spell months across all regions), while ${f.shortScale} flickers in and out
      (${f.spellShortPct} of spell months). ${f.longScale} also stays low for months after a spell ends,
      because its window still contains the dry months. Short-scale dips outside the grey bands are
      genuine dry anomalies arising from the random rainfall process, not errors.`,
  },
  fig2a: {
    title: "Drought events found by run theory.",
    alt: () => "SPI-3 time series for every region with drought months filled in red",
    text: (f) => `Months with ${f.eventScale} below ${f.droughtThr} are filled red; each unbroken run is
      one event (${f.nEvents} in total). <em>Notice</em> that ${f.spellPairsDetected} of the ${f.spellPairs}
      region–spell combinations contain at least one detected event, yet only ${f.eventsInSpells} of
      the ${f.nEvents} events (${f.eventsInSpellsPct}) overlap an injected spell; the others are natural
      dry periods produced by the random rainfall process. Inside a long spell, a brief recovery above the threshold splits the drought into
      several events, which is a known weakness of simple run theory without pooling.`,
  },
  fig2b: {
    title: "Event duration against severity.",
    alt: () => "Scatter plot of drought event duration against severity",
    text: (f) => `Each point is one event; marker size shows intensity (severity ÷ duration).
      <em>Notice</em> that severity grows almost linearly with duration, so long events dominate: the
      ${f.topInSpell} most severe events all lie inside injected dry spells, while
      ${f.oneMonthEvents} events (${f.oneMonthPct}) last a single month. The longest event is
      ${f.longestRegion} from ${f.longestStart} (${f.longestDuration} months).`,
  },
  fig3: {
    title: "Growing-season SPI against yield anomaly.",
    alt: () => "Scatter plots of growing-season SPI against yield anomaly, one panel per region",
    text: (f) => `Yield anomaly is the departure from each region's fitted linear trend; the dashed
      red line marks the loss threshold (−${f.lossThrPct}). <em>Notice</em> the clear but imperfect
      relationship (r from ${f.rMin} to ${f.rMax} across regions): the scatter around the line is
      the non-rainfall noise in the yield model. Points fall away more steeply on the dry side,
      because the model gives a dry season ${f.betaRatio}× the effect of an equally wet one.`,
  },
  fig4a: {
    title: "Index payouts against actual losses, all region-years.",
    alt: () => "Scatter plot of index payouts against yield losses, coloured by outcome",
    text: (f) => `Points on the dotted diagonal would be perfectly compensated. <em>Notice</em> the
      horizontal rows: the contract can only pay ${f.nPayoutLevels} distinct amounts, while losses are
      continuous, so some basis risk is built into any tiered design. Missed losses (green) sit on the
      x-axis to the right of the loss threshold; false alarms (orange) sit to its left, above zero.
      The distance of points from the diagonal is what the basis-risk RMSE
      (${f.rmse} percentage points) summarises.`,
  },
  fig4b: {
    title: "Losses and payouts year by year.",
    alt: () => "Bar charts of yield losses and index payouts by year for each region",
    text: (f) => `Orange bars are yield losses, blue bars are payouts; “M” marks a missed loss and
      “FA” a false alarm. <em>Notice</em> the contrast between drought and non-drought losses:
      ${f.spellLossPaid} of the ${f.spellLossYears} loss years during injected dry spells received a
      payout, against ${f.otherLossPaid} of ${f.otherLossYears} at other times. Of the
      ${f.lossYearsWetSeason} loss years with an above-median growing season (SPI ≥ 0),
      ${f.missesWetSeason} were missed: those losses came from something other than rainfall, which
      no rainfall index can see.`,
  },
};
