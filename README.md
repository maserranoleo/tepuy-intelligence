# Tepuy Gas Intelligence — v1

The operational picture of Venezuela's natural gas system. v1 ships:

- A map of Venezuela (MapLibre + open basemap, fit to country bounds).
- Three pluggable layers, each toggleable:
  - **Gas Pipelines** — color-coded by status, click-to-detail, source attribution.
  - **Gas Fields** — point markers for fields like Perla, Dragon, Loran-Manatee.
  - **Flare Detections (VIIRS, last 14 days)** — heatmap + clickable points
    fed by NASA FIRMS satellite hotspots.
- A FastAPI backend serving GeoJSON from PostGIS.
- Three ingestion paths:
  - `manual_seed` — real, cited Venezuelan pipelines + gas fields (auto-runs).
  - `gem` — Global Energy Monitor's [Global Gas Infrastructure Tracker](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/) (manual file drop).
  - `firms` — NASA FIRMS daily VIIRS active-fire detections (free API).

Public-facing, no auth.

## Run it

You need:

- **Python 3.12** (`python3.12 --version`)
- **Node 20+** (`node --version`)
- A free **Supabase** project with PostGIS enabled — see
  [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) for the 5-minute walkthrough.

Then, from the repo root:

```bash
cp .env.example .env       # paste your Supabase connection string
make install               # one-time: venv + Python deps + npm deps
make migrate               # one-time: create the schema
make seed                  # one-time: load the 6 manual_seed pipelines
make api                   # runs FastAPI with auto-reload on :8000
```

In a second terminal:

```bash
cd frontend
cp .env.example .env       # one-time
npm run dev                # opens on :5173
```

Open [http://localhost:5173](http://localhost:5173) and click any pipeline.

### What you'll see on first boot

Six hand-curated, publicly-sourced Venezuelan pipelines: Anaco–Caracas,
Anaco–Puerto Ordaz, Anaco–Barquisimeto (ICO), the Antonio Ricaurte VEN↔CO
interconnector, the Perla field tie-in, and the proposed Dragon–Hibiscus
VEN↔TT crossing. Each row carries source attribution and a
`geometry_quality: approximate_endpoints` flag — they are real entities, not
survey-grade traces.

## Ingest FIRMS (NASA satellite hotspots)

Free, fast, no file drop required. One-time setup:

1. Get a MAP_KEY (free, email-gated, arrives in seconds):
   <https://firms.modaps.eosdis.nasa.gov/api/map_key/>
2. Add to `.env`: `NASA_FIRMS_MAP_KEY=<your-key>`
3. Pull the last 7 days of VIIRS detections over Venezuela:

   ```bash
   make ingest-firms              # default: VIIRS_SNPP_NRT, last 7 days
   make ingest-firms DAYS=10
   make ingest-firms SOURCE=VIIRS_NOAA20_NRT DAYS=5
   ```

Each detection is one satellite hotspot — could be a gas flare or a wildfire.
The analyst-grade signal is **persistence**: a thermal anomaly that shows up
at the same coordinates day after day is almost certainly a gas flare. The
heatmap surfaces this density at country zoom; individual points become
clickable above zoom 6.

Idempotent — re-running on overlapping windows is safe (deduplicated by a
SHA1 of `(satellite, date, time, lat, lon)`).

See [`data_pipeline/sources/firms/README.md`](data_pipeline/sources/firms/README.md)
for full details.

## Ingest GEM (Global Gas Infrastructure Tracker)

GEM distributes the GGIT as an Excel workbook behind a free, email-gated form.

1. Download the latest GGIT workbook from
   [globalenergymonitor.org](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/).
2. Drop the `.xlsx` into `data_pipeline/.data/` (gitignored).
3. Run:

   ```bash
   make ingest-gem FILE=data_pipeline/.data/<your-file>.xlsx
   ```

   Add `--dry-run` for parse-and-report:

   ```bash
   PYTHONPATH=backend:. backend/.venv/bin/python -m data_pipeline.sources.gem.load \
     data_pipeline/.data/<your-file>.xlsx --dry-run
   ```

The loader filters to rows with Venezuela in their countries, plus VEN↔CO and
VEN↔TT cross-border pairs. Status values are normalized
(`Mothballed/Shelved → idle`, `Cancelled → retired`, etc.); the original GEM
status is preserved in `properties.raw_status`.

GEM rows live in their own database rows — keyed on `external_ids["gem"]` —
distinct from `manual_seed` rows. They do not auto-merge in v1; analysts can
see both and compare.

## Project layout

```
backend/
  app/
    main.py                 FastAPI app + CORS + healthz
    config.py               pydantic-settings (reads root .env)
    db.py                   engine, SessionLocal
    models/
      base.py               EntityBase mixin (shared columns for the entity zoo)
      pipeline.py           Pipeline ORM model
    schemas/
      pipeline.py           Pydantic GeoJSON Feature/FeatureCollection
    api/
      pipelines.py          GET /api/pipelines, GET /api/pipelines/{id}
  alembic/                  migrations
  pyproject.toml

data_pipeline/
  common/upsert.py          PipelineRecord + idempotent upsert helper
  sources/
    manual_seed/            real, cited Venezuelan pipelines (one-time seed)
    gem/                    GEM GGIT loader (manual file drop)
  .data/                    gitignored — drop ingestion inputs here

frontend/
  src/
    App.tsx                 layout + Legend
    map/
      MapView.tsx           MapLibre instance, fit to VEN
      LayerRegistry.ts      pluggable layer registry
      layers/pipelines.ts   pipelines layer config
    components/
      DetailPanel.tsx       click-to-detail with source attribution
    api/                    fetch helpers + TanStack Query hooks
    types/geojson.ts        documented properties schema
  index.html, vite.config.ts, tailwind.config.js

Makefile                    one-command tasks: install, migrate, seed, api, ingest-gem
.env.example                root env (DATABASE_URL, CORS_ORIGINS)
SUPABASE_SETUP.md           one-time database walkthrough
```

## Architectural principles

1. **Provenance is non-negotiable.** Every entity row has `sources` JSONB:
   `[{source_name, source_id, retrieved_at, url, note}]`. The frontend always
   shows attribution.
2. **Source decoupling.** Each ingestion source lives at
   `data_pipeline/sources/<name>/` and is purely additive.
3. **Idempotent ingestion.** Re-running an ingest upserts on
   `external_ids[<source>] = <stable id>`; never duplicates.
4. **Stable canonical IDs.** Internal UUID per row; external IDs in
   `external_ids` JSONB keyed by source name.
5. **Schema ready for the entity zoo.** `EntityBase` defines shared columns.
   Adding a new entity type (fields, plants, terminals, flares, incidents,
   operators, licenses) = one model + one migration + one API route + one
   frontend layer config.
6. **GeoJSON over the wire.** Standard FeatureCollections; the
   `PipelineProperties` schema is documented in `schemas/pipeline.py` and
   `types/geojson.ts` (one source of truth per side).
7. **Pluggable frontend layers.** `LayerRegistry` holds layer configs; today
   it has one entry, tomorrow it has many.

## Adding a new data source

This is the path you'll walk most often. Suppose you want to add an `eia`
source.

1. Create the source folder and three files:

   ```
   data_pipeline/sources/eia/
     __init__.py
     transform.py      # raw input → list[PipelineRecord]
     load.py           # CLI that calls transform() then upsert_pipeline()
     README.md         # source URL, license, columns, caveats
   ```

2. In `transform.py`, return `PipelineRecord` objects with:
   - `source_name = "eia"` and a stable `external_id` per row.
   - `geometry` as a Shapely `LineString` or `MultiLineString` (EPSG:4326).
   - One or more `SourceRef`s in `sources=[...]`.

3. In `load.py`, mirror the GEM loader: read input, call `transform()`,
   `upsert_pipeline()` per record, `db.commit()`.

4. Document the source in `README.md`.

That's it. No backend or frontend code changes — the new rows flow through
the same API and render on the same layer, distinguished by `external_ids`
and `sources` in the detail panel.

## Adding a new entity type

`gas_fields` is the worked example. Use it as a template — every file in the
list below has a matching pipeline-side and gas-field-side. To add e.g.
`processing_plants` next, copy the gas-field files and rename:

1. **Model** — `backend/app/models/<entity>.py` (cf. `gas_field.py`). Inherit
   `Base, EntityBase`; add a `Geometry(<TYPE>, srid=4326, spatial_index=False)`
   column and any entity-specific columns. Register in
   `backend/app/models/__init__.py`.
2. **Migration** — copy `backend/alembic/versions/0002_gas_fields.py`,
   bump the revision id, list the columns. Don't re-emit
   `CREATE EXTENSION postgis` — it's already in 0001.
3. **Schema** — `backend/app/schemas/<entity>.py` mirroring `gas_field.py`.
4. **API** — `backend/app/api/<entity>s.py` mirroring `gas_fields.py`.
   Register in `app/main.py`.
5. **Upsert helper** — add `<Entity>Record` + `upsert_<entity>` siblings in
   `data_pipeline/common/upsert.py`.
6. **Seed (optional)** — extend `data_pipeline/sources/manual_seed/load.py`
   with a `_<entity>_records()` and a loop in `run()`.
7. **Frontend types** — extend `frontend/src/types/geojson.ts`: add the
   `<Entity>Properties`/`Feature`/`FeatureCollection` types and a new arm to
   the `SelectedEntity` discriminated union.
8. **Frontend api** — `frontend/src/api/<entity>s.ts` with `fetch<Entity>s()`.
9. **Frontend layer** — `frontend/src/map/layers/<entity>s.ts` mirroring
   `gas-fields.ts`; declare its `layerIds: string[]` so visibility toggling
   works.
10. **Wire** — append the layer to the registry array in
    `frontend/src/map/MapView.tsx` and add a `LayerToggleRow` for it in
    `frontend/src/App.tsx`.
11. **DetailPanel** — add a `<Entity>Fields` subcomponent in
    `frontend/src/components/DetailPanel.tsx` and a new branch in the
    `kind` switch.

The shared `EntityBase` columns guarantee provenance, status, aliases, and
external IDs work the same way for every entity type. Entity-specific
attributes that don't deserve a column (reservoir type, basin, reserves)
go in the `properties` JSONB.

## Useful Make targets

```
make help            # list all targets
make install         # one-time: backend venv + deps + frontend deps
make migrate         # alembic upgrade head
make seed            # load manual_seed pipelines
make api             # uvicorn with --reload
make ingest-gem FILE=path/to/ggit.xlsx
make typecheck-front
make build-front
make clean           # nuke venv + node_modules
```

## Notes & limitations (v1)

- **No auth, no multi-tenancy.** Public-facing. Add it later — Supabase Auth
  + RLS is the natural path.
- **No live data.** No VIIRS flaring, no Sentinel-5P methane, no AIS
  shipping. The schema is sized for it; the wiring isn't here.
- **No tile server.** Pipelines ship as one GeoJSON. Will need vector tiles
  if/when the entity zoo grows past tens of thousands of features.
- **No automated GEM fetcher.** GEM downloads are gated; you drop the file.
- **No cross-source deduplication.** A pipeline appearing in both
  `manual_seed` and `gem` will show as two rows. Intentional in v1 — let the
  analyst see the disagreement, don't hide it.

## Smoke-test the GEM transform without a database

```bash
PYTHONPATH=backend:. backend/.venv/bin/python \
  -m data_pipeline.sources.gem.test_transform_smoke
```

Expected output: `OK: gem transform smoke passed`.
