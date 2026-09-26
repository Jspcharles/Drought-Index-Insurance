"""
Step 3: identify drought events with run theory (Yevjevich, 1967).

A drought event is an unbroken "run" of months with SPI below a threshold
(here -1). For each run we record:
  start, end  : first and last month below the threshold
  duration    : number of months in the run
  severity    : accumulated deficit, the sum of -SPI over the run
                (McKee et al., 1993, call this "drought magnitude")
  intensity   : severity / duration, i.e. the average SPI deficit per month
  peak_spi    : the lowest SPI reached during the event

Note: some studies measure severity as the deficit below the threshold,
sum(threshold - SPI), instead. Both rank events the same way; this one is
easier to relate back to SPI values.
"""

import numpy as np
import pandas as pd

from src import config


def find_events(spi, threshold=config.DROUGHT_THRESHOLD,
                min_duration=config.MIN_EVENT_DURATION):
    """
    Find drought events in one SPI series.

    Parameters
    ----------
    spi : pandas Series of SPI with a monthly DatetimeIndex. NaN values
          (e.g. the warm-up months) count as "not in drought".
    threshold : SPI value below which a month is in drought.
    min_duration : shortest run (in months) that counts as an event.

    Returns
    -------
    DataFrame with one row per event.
    """
    in_drought = (spi < threshold).to_numpy()   # NaN < x is False
    values = spi.to_numpy()
    dates = spi.index

    events = []
    start = None
    # Scan month by month; one extra step at the end closes a run that is
    # still open in the final month.
    for i in range(len(values) + 1):
        dry = i < len(values) and in_drought[i]
        if dry and start is None:
            start = i                              # a run begins
        elif not dry and start is not None:
            run = values[start:i]                  # the run just ended
            if len(run) >= min_duration:
                severity = float(np.sum(-run))
                events.append(dict(
                    start=dates[start],
                    end=dates[i - 1],
                    duration=len(run),
                    severity=round(severity, 3),
                    intensity=round(severity / len(run), 3),
                    peak_spi=round(float(run.min()), 3),
                ))
            start = None

    return pd.DataFrame(events, columns=["start", "end", "duration",
                                         "severity", "intensity", "peak_spi"])


def find_events_all_regions(spi_table, scale=config.EVENT_SPI_SCALE):
    """Run find_events for every region in a tidy SPI table."""
    pieces = []
    for region, df in spi_table.groupby("region", sort=False):
        events = find_events(df.set_index("date")[f"spi_{scale}"])
        events.insert(0, "region", region)
        events.insert(1, "spi_scale", scale)
        pieces.append(events)
    return pd.concat(pieces, ignore_index=True)
