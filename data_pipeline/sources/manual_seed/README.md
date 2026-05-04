# manual_seed

A small, hand-curated set of well-known Venezuelan natural-gas pipelines used
to seed the database on first boot so the v1 app shows real, sourced data
before any external file is dropped.

**Geometry quality:** approximate two-point lines between named endpoints. Each
row sets `properties.geometry_quality = "approximate_endpoints"`.

**Provenance:** each row attributes one or more public secondary sources
(EIA, Reuters, S&P Global, operator press releases). Treat these as starting
points for analyst review, not as primary data.

**Idempotency:** runs on every backend container start. Upserts by
`external_ids["manual_seed"] = <slug>`. Safe to re-run.

**Override path:** when a pipeline appears in a higher-fidelity source (e.g.
GEM), that source ingests under its own `external_ids[<source>] = <id>` key
into a separate row. We do not auto-merge across sources in v1 — the analyst
sees both and can compare.
