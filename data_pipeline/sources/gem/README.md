# GEM — Global Gas Infrastructure Tracker

[Global Energy Monitor's GGIT](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/)
is the canonical open dataset of natural-gas pipeline projects worldwide.
It's distributed as an Excel workbook behind an email-gated download form.

## How to ingest

1. Register and download the latest GGIT workbook from GEM's site.
2. Drop the `.xlsx` into `data_pipeline/.data/` on your host. The directory is
   gitignored.
3. With the stack running, run:

   ```bash
   docker compose exec backend \
     python -m data_pipeline.sources.gem.load /data_pipeline/.data/<file>.xlsx
   ```

   Add `--dry-run` to parse and report without writing.

## What we filter

We keep rows where:

- a country column contains "Venezuela", **or**
- start or end country is Venezuela, **or**
- start/end form a VEN↔Colombia or VEN↔Trinidad cross-border pair.

## Geometry

If GEM's row has a usable WKT route column, we use it. Otherwise we build a
two-point line from start/end coordinates. Each row records its
`geometry_quality` in `properties`.

## Idempotency

We upsert by `external_ids["gem"] = <GEM project id>`. Running the loader
twice on the same file is a no-op aside from `updated_at`.

## Status normalization

GEM publishes statuses as: Operating, Construction, Proposed, Announced,
Pre-construction, Shelved, Mothballed, Cancelled, Retired, Idle (and
variants). We collapse these into our taxonomy: `operating`,
`construction`, `proposed`, `idle` (shelved/mothballed), `retired`
(cancelled/decommissioned), `unknown`. The original GEM string is preserved
in `properties.raw_status`.
