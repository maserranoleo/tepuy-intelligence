"""FIRMS proximity classifier.

For each point-geometry asset (gas field, processing plant, …) we count
VIIRS flare detections within a fixed radius over a recent window. The
intent — straight from the strategy paper's "VIIRS as operational
reality layer" claim — is that a thermal anomaly that recurs in the
same place day after day is almost certainly a gas flare, which means
the asset is *actually operating* regardless of what the official
record says.

Proximity radius: 5 km. Wide enough to capture an asset's centroid +
its immediate associated infrastructure (treaters, separators, well
pads); narrow enough that hits aren't shared across distinct assets in
sparse gas regions.

Window: 30 days. Long enough for daily-batch persistence to emerge,
short enough that an asset shut down last quarter has fallen out.

Computation lives in SQL (PostGIS `ST_DWithin` on geography casts +
GROUP BY the asset's primary key). The matcher reads the join's
aggregates: total count, latest acquisition time, peak FRP. Persistence
itself (e.g., "detected on N distinct days in the window") is a richer
signal we'll add in a follow-up — for v1 the count + last-seen carries
80% of the value.
"""

PROXIMITY_M: float = 5_000.0
WINDOW_DAYS: int = 30
