# FIRMS — NASA Fire Information for Resource Management System

[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) distributes daily VIIRS
and MODIS active-fire/thermal-anomaly detections globally, free.

This source ingests detections over Venezuela's bounding box (the FIRMS API
accepts `VEN` as a country shortcut). Detections include both **gas flares**
and **wildfires**; we don't classify here. The analyst-grade signal is
**persistence** — a thermal anomaly that shows up at the same coordinates
day after day is almost certainly a gas flare. Persistence is computed
downstream from the time series, not stored as a column.

## Get a MAP_KEY

1. Go to <https://firms.modaps.eosdis.nasa.gov/api/map_key/>.
2. Enter your email; the key arrives within a few seconds.
3. Add to `.env` at the repo root:

   ```
   NASA_FIRMS_MAP_KEY=your-key-here
   ```

## Run

```bash
make ingest-firms                  # default: VIIRS_SNPP_NRT, last 7 days
make ingest-firms DAYS=10
make ingest-firms SOURCE=VIIRS_NOAA20_NRT DAYS=5
```

`--dry-run`:

```bash
PYTHONPATH=backend:. backend/.venv/bin/python -m data_pipeline.sources.firms.load --dry-run
```

## Sources available

- `VIIRS_SNPP_NRT` — Suomi-NPP, 375 m, near-real-time (default).
- `VIIRS_NOAA20_NRT` — NOAA-20.
- `VIIRS_NOAA21_NRT` — NOAA-21.
- `MODIS_NRT` — MODIS, coarser (1 km), longer history.

VIIRS sources are preferred for gas-flare detection: 375 m resolution picks
up small flare stacks that MODIS misses.

## Idempotency

Each detection's `external_id` is a SHA1 of
`(satellite, acq_date, acq_time, lat, lon)`. Re-running on overlapping
windows is safe — duplicates are skipped silently.

## Limits

- FIRMS API caps a single call at 10 days. Default window is 7.
- The free key has a generous quota; for our daily-Venezuela volume you
  won't hit it.
