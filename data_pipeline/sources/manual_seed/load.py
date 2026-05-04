"""manual_seed source.

A small, hand-curated, publicly-sourced set of Venezuelan natural-gas pipelines
so the v1 app has data the moment you bring it up. Run automatically by the
backend container at startup; safe to re-run (idempotent).

Geometries are approximate two-point lines between named endpoints — fine for
v1's "where in Venezuela are these things" use case, NOT survey-grade. Each row
declares `properties.geometry_quality = "approximate_endpoints"` and cites the
public references behind its attributes.

Once you drop a real GEM file and run the GEM ingest, GEM rows will live
alongside these (different `external_ids` key) and you can hide manual_seed
from the map by status/source if you want.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

from shapely.geometry import LineString
from sqlalchemy.orm import Session

from app.db import SessionLocal
from data_pipeline.common.upsert import PipelineRecord, SourceRef, upsert_pipeline

logger = logging.getLogger("manual_seed")

SOURCE_NAME = "manual_seed"


@dataclass(frozen=True)
class Endpoint:
    name: str
    lat: float
    lon: float


# Approximate locations for trunk-line endpoints.
ANACO = Endpoint("Anaco gas hub", 9.43, -64.47)
CARACAS = Endpoint("Caracas", 10.48, -66.90)
PUERTO_ORDAZ = Endpoint("Puerto Ordaz / Ciudad Guayana", 8.36, -62.65)
BARQUISIMETO = Endpoint("Barquisimeto", 10.07, -69.32)
MARACAIBO = Endpoint("Maracaibo", 10.64, -71.61)
BALLENA_CO = Endpoint("Ballena, Colombia (La Guajira)", 11.95, -71.27)
PERLA_FIELD = Endpoint("Perla field (Cardón IV)", 12.10, -70.50)
PUNTO_FIJO = Endpoint("Punto Fijo / Falcón onshore", 11.70, -70.20)
DRAGON_FIELD = Endpoint("Dragon field (offshore VEN)", 10.95, -62.35)
HIBISCUS_TT = Endpoint("Hibiscus platform, Trinidad", 11.00, -61.95)


def _line(a: Endpoint, *waypoints: Endpoint, b: Endpoint) -> LineString:
    coords = [(a.lon, a.lat), *((w.lon, w.lat) for w in waypoints), (b.lon, b.lat)]
    return LineString(coords)


def _records() -> list[PipelineRecord]:
    now = datetime.now(UTC)

    return [
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-aco-caracas",
            name="Anaco–Caracas Gas Pipeline",
            name_es="Gasoducto Anaco–Caracas",
            aliases=["ACO"],
            status="operating",
            status_as_of=now,
            length_km=400,
            operator="PDVSA Gas",
            geometry=_line(ANACO, b=CARACAS),
            properties={
                "geometry_quality": "approximate_endpoints",
                "note": "Trunk line carrying gas from the Anaco processing complex "
                        "(Anzoátegui) westward into the Caracas demand region.",
            },
            sources=[
                SourceRef(
                    source_name="EIA",
                    note="Venezuela Country Analysis Brief — natural gas section",
                    url="https://www.eia.gov/international/analysis/country/VEN",
                    retrieved_at=now,
                ),
                SourceRef(
                    source_name="PDVSA Gas",
                    note="Operator filings / public communications",
                    url="https://www.pdvsa.com/",
                    retrieved_at=now,
                ),
            ],
        ),
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-aco-pzo",
            name="Anaco–Puerto Ordaz Gas Pipeline",
            name_es="Gasoducto Anaco–Puerto Ordaz",
            status="operating",
            status_as_of=now,
            length_km=210,
            operator="PDVSA Gas",
            geometry=_line(ANACO, b=PUERTO_ORDAZ),
            properties={
                "geometry_quality": "approximate_endpoints",
                "note": "Supplies industrial Guayana (steel, aluminum) from the Anaco hub.",
            },
            sources=[
                SourceRef(
                    source_name="EIA",
                    note="Venezuela Country Analysis Brief",
                    url="https://www.eia.gov/international/analysis/country/VEN",
                    retrieved_at=now,
                ),
            ],
        ),
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-ico-aco-bqto",
            name="Anaco–Barquisimeto Gas Pipeline (ICO)",
            name_es="Interconexión Centro Occidente (ICO)",
            aliases=["ICO"],
            status="operating",
            status_as_of=now,
            length_km=500,
            operator="PDVSA Gas",
            geometry=_line(ANACO, CARACAS, b=BARQUISIMETO),
            properties={
                "geometry_quality": "approximate_endpoints",
                "note": "Central-west interconnector linking eastern gas to the "
                        "Barquisimeto / Lara demand region.",
            },
            sources=[
                SourceRef(
                    source_name="EIA",
                    url="https://www.eia.gov/international/analysis/country/VEN",
                    retrieved_at=now,
                ),
                SourceRef(
                    source_name="PDVSA Gas",
                    url="https://www.pdvsa.com/",
                    retrieved_at=now,
                ),
            ],
        ),
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-co-antonio-ricaurte",
            name="Antonio Ricaurte Pipeline (Ballena–Maracaibo)",
            name_es="Gasoducto Antonio Ricaurte",
            aliases=["Ballena–Maracaibo", "Transcaribeño"],
            status="idle",
            status_as_of=now,
            length_km=225,
            diameter_in=26,
            capacity_mmcfd=500,
            operator="PDVSA Gas / Promigas",
            geometry=_line(BALLENA_CO, b=MARACAIBO),
            properties={
                "geometry_quality": "approximate_endpoints",
                "cross_border": ["VE", "CO"],
                "note": "Originally built for Colombia→Venezuela flow (2007). "
                        "Idle in recent years; multiple announcements about "
                        "reversing or restarting flow.",
            },
            sources=[
                SourceRef(
                    source_name="Reuters",
                    note="Coverage of Antonio Ricaurte status and reversal plans",
                    url="https://www.reuters.com/",
                    retrieved_at=now,
                ),
                SourceRef(
                    source_name="S&P Global Commodity Insights",
                    url="https://www.spglobal.com/commodityinsights",
                    retrieved_at=now,
                ),
            ],
        ),
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-perla-onshore",
            name="Perla Field Tie-In (Cardón IV)",
            name_es="Conexión Campo Perla (Cardón IV)",
            status="operating",
            status_as_of=now,
            length_km=30,
            operator="Cardón IV (Eni / Repsol)",
            geometry=_line(PERLA_FIELD, b=PUNTO_FIJO),
            properties={
                "geometry_quality": "approximate_endpoints",
                "note": "Offshore-to-onshore tie-in delivering Perla gas (Cardón IV "
                        "block) into the Falcón onshore system.",
            },
            sources=[
                SourceRef(
                    source_name="Eni",
                    url="https://www.eni.com/",
                    retrieved_at=now,
                ),
                SourceRef(
                    source_name="S&P Global Commodity Insights",
                    url="https://www.spglobal.com/commodityinsights",
                    retrieved_at=now,
                ),
            ],
        ),
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-tt-dragon-hibiscus",
            name="Dragon–Hibiscus Pipeline (proposed)",
            name_es="Gasoducto Dragon–Hibiscus (propuesto)",
            status="proposed",
            status_as_of=now,
            operator="Shell / NGC (proposed)",
            geometry=_line(DRAGON_FIELD, b=HIBISCUS_TT),
            properties={
                "geometry_quality": "approximate_endpoints",
                "cross_border": ["VE", "TT"],
                "note": "Proposed cross-border line carrying Dragon-field gas to "
                        "Trinidad's Hibiscus platform for processing and LNG export. "
                        "Subject to OFAC licensing.",
            },
            sources=[
                SourceRef(
                    source_name="Reuters",
                    note="Dragon field / OFAC license coverage",
                    url="https://www.reuters.com/",
                    retrieved_at=now,
                ),
                SourceRef(
                    source_name="S&P Global Commodity Insights",
                    url="https://www.spglobal.com/commodityinsights",
                    retrieved_at=now,
                ),
            ],
        ),
    ]


def run(db: Session) -> int:
    records = _records()
    for rec in records:
        upsert_pipeline(db, rec)
    db.commit()
    return len(records)


def main() -> int:
    db = SessionLocal()
    try:
        n = run(db)
    finally:
        db.close()
    logger.info("manual_seed: upserted %d pipelines", n)
    print(f"manual_seed: upserted {n} pipelines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
