# Tepuy Gas Intelligence — v1

The operational picture of Venezuela's natural gas system. v1 ships:

- A map of Venezuela (MapLibre + open basemap, fit to country bounds).
- A pipelines layer color-coded by status, click-to-detail.
- A FastAPI backend serving GeoJSON from PostGIS.
- An ingestion path for Global Energy Monitor's [Global Gas Infrastructure
  Tracker](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/),
  filtered to Venezuela + cross-border (Colombia, Trinidad).
- A small `manual_seed` source so the app has real, sourced data on first boot.

Public-facing, no auth. Same map serves as a reference picture for analysts,
researchers, and journalists.

## Run it

You need Docker (with the Compose plugin) and Node 20+.

```bash
cp .env.example .env
docker compose up --build
```

That brings up Postgres+PostGIS, runs Alembic migrations, seeds the database
from `manual_seed`, and starts the FastAPI backend on port 8000. In a second
terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Click any pipeline.

### What you should see on first boot

Six hand-curated, publicly-sourced Venezuelan pipelines appear on the map:
Anaco–Caracas, Anaco–Puerto Ordaz, Anaco–Barquisimeto (ICO), the Antonio
Ricaurte VEN↔CO interconnector, the Perla field tie-in, and the proposed
Dragon–Hibiscus VEN↔TT crossing. Each row carries source attribution and a
`geometry_quality: approximate_endpoints` flag — they're real entities, but
not survey-grade traces. They are placeholders until you ingest GEM.

## Ingest GEM (Global Gas Infrastructure Tracker)

GEM distributes the GGIT as an Excel workbook behind a free, email-gated form.

1. Download the latest GGIT workbook from
   [globalenergymonitor.org](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/).
2. Drop the `.xlsx` into `data_pipeline/.data/` (gitignored).
3. With the stack running:

   ```bash
   docker compose exec backend \
     python -m data_pipeline.sources.gem.load /data_pipeline/.data/<file>.xlsx
   ```

   Add `--dry-run` to parse-and-report without writing.

The loader filters to rows with Venezuela in their countries, plus VEN↔CO and
VEN↔TT cross-border pairs. Status values are normalized
(`Mothballed/Shelved → idle`, `Cancelled → retired`, etc.); the original GEM
status is preserved in `properties.raw_status`.

GEM rows live in their own database rows — keyed on `external_ids["gem"]` —
distinct from `manual_seed` rows. They do not auto-merge in v1; analysts can
see both and compare.

## Architecture

```
backend/
  app/
    main.py                 FastAPI app + CORS + healthz
    config.py               pydantic-settings
    db.py                   engine, SessionLocal
    models/
      base.py               EntityBase mixin (shared columns for the entity zoo)
      pipeline.py           Pipeline ORM model
    schemas/
      pipeline.py           Pydantic GeoJSON Feature/FeatureCollection
    api/
      pipelines.py          GET /api/pipelines, GET /api/pipelines/{id}
  alembic/                  migrations
  Dockerfile
  pyproject.toml

data_pipeline/
  common/
    upsert.py               PipelineRecord + idempotent upsert helper
  sources/
    manual_seed/            real, cited Venezuelan pipelines (auto-runs at boot)
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

docker-compose.yml          db + backend (frontend stays npm run dev)
.env.example
```

### Architectural principles

1. **Provenance is non-negotiable.** Every entity row has `sources` JSONB:
   `[{source_name, source_id, retrieved_at, url, note}]`. The frontend always
   shows attribution.
2. **Source decoupling.** Each ingestion source lives at
   `data_pipeline/sources/<name>/` and is purely additive.
3. **Idempotent ingestion.** Re-running an ingest upserts on
   `external_ids[<source>] = <stable id>`; never duplicates.
4. **Stable canonical IDs.** Internal UUID per row; external IDs in
   `external_ids` JSONB keyed by source name.
5. **Schema ready for the entity zoo.** `EntityBase` defines the shared
   columns. Adding a new entity type (fields, plants, terminals, flares,
   incidents, operators, licenses) = one model + one migration + one API
   route + one frontend layer config.
6. **GeoJSON over the wire.** Standard FeatureCollections; the
   `PipelineProperties` schema is documented in `schemas/pipeline.py` and
   `types/geojson.ts` (one source of truth per side).
7. **Pluggable frontend layers.** `LayerRegistry` holds layer configs; today
   it has one entry, tomorrow it has many.

## Adding a new data source

This is the path you'll walk most often. Suppose you want to add an `eia`
source for EIA pipeline data.

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

3. In `load.py`, mirror the GEM loader:

   ```python
   from app.db import SessionLocal
   from data_pipeline.common.upsert import upsert_pipeline
   from .transform import transform

   def main(argv):
       result = transform(Path(argv[0]))
       db = SessionLocal()
       try:
           for rec in result.records:
               upsert_pipeline(db, rec)
           db.commit()
       finally:
           db.close()
   ```

4. Document the source in `README.md` (URL, license, format, run command).

That's it. No code in the backend or frontend needs to change — the new rows
flow through the same API and render on the same layer, distinguished by
`external_ids` and `sources` in the detail panel.

## Adding a new entity type

Suppose you want a `processing_plants` layer.

1. **Model** — `backend/app/models/processing_plant.py`. Inherit `Base,
   EntityBase`; add a `Geometry("POINT", srid=4326)` column and the
   plant-specific columns. Register in `models/__init__.py`.
2. **Migration** — `alembic revision --autogenerate -m "processing_plants"`,
   review, commit.
3. **Schema** — `backend/app/schemas/processing_plant.py` with
   `ProcessingPlantFeature` / `ProcessingPlantFeatureCollection`.
4. **API** — `backend/app/api/processing_plants.py` with
   `GET /api/processing_plants`. Register in `main.py`.
5. **Frontend** — `frontend/src/map/layers/processing_plants.ts` with a
   `LayerConfig`. Append it to the layer list in `MapView.tsx`. Done.

The shared `EntityBase` columns guarantee that provenance, status, aliases,
and external IDs work the same way for every entity type.

## Notes & limitations (v1)

- **No auth, no multi-tenancy.** Public-facing. Add it later.
- **No live data.** No VIIRS flaring, no Sentinel-5P methane, no AIS
  shipping. The schema is sized for it; the wiring isn't here.
- **No tile server.** Pipelines ship as one GeoJSON. Will need vector tiles
  if/when the entity zoo grows past tens of thousands of features.
- **No automated GEM fetcher.** GEM downloads are gated; you drop the file.
- **No cross-source deduplication.** A pipeline appearing in both
  `manual_seed` and `gem` will show as two rows. Intentional in v1 — let the
  analyst see the disagreement, don't hide it.

## Hacking on the backend without Docker

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e .[ingest]
# Point DATABASE_URL at any Postgres+PostGIS you have running.
DATABASE_URL=postgresql+psycopg://... .venv/bin/alembic upgrade head
PYTHONPATH=backend:. .venv/bin/python -m data_pipeline.sources.manual_seed.load
.venv/bin/uvicorn app.main:app --reload
```

## Smoke test the GEM transform

No DB required:

```bash
cd backend && .venv/bin/python -m pip install pandas openpyxl
PYTHONPATH=backend:. .venv/bin/python -m data_pipeline.sources.gem.test_transform_smoke
```

Expected output: `OK: gem transform smoke passed`.
