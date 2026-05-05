"""manual_seed source.

A hand-curated baseline of Venezuela's documented natural-gas trunk system,
seeded so the app has a credible network the moment you bring it up.

PROVENANCE
==========
Every pipeline cites at least one of these public references:

  * Academia Nacional de la Ingeniería y el Hábitat (2009),
    "La Industria del Gas Natural en Venezuela" — the canonical academic
    reference for the seven national transmission systems, their parallel
    lines, capacities, and completion years. Long-form Spanish PDF.
    URL: https://www.acading.org.ve/wp-content/uploads/2023/02/LA_INDUSTRIA_DEL_GAS_NATURAL_EN_VENEZUELA.pdf

  * U.S. EIA — Venezuela Country Analysis Brief (Feb 2024). Table 4 lists
    operating gas pipelines with length and capacity.
    URL: https://www.eia.gov/international/analysis/country/VEN

  * Global Energy Monitor — Global Gas Infrastructure Tracker (GGIT) wiki.
    Per-asset pages with citations back to OPEC ASB and Academia Nacional.
    URL: https://www.gem.wiki/Special:Search?search=Venezuela+gas+pipeline

  * PDVSA Gas (operator page) — official names and system descriptions
    (note: not substantively updated since ~2017).
    URL: https://www.pdvsa.com/index.php?option=com_content&view=article&id=6530

GEOMETRY HONESTY
================
Routes pass through real, named intermediate cities and facilities (Anaco,
Altagracia de Orituco, Maracay, Morón, Yaritagua, Barquisimeto, Coro, Río
Seco, Punto Fijo, Ulé, José, Puerto La Cruz, etc.). They are NOT surveyed
pipe paths — every record is tagged `properties.geometry_quality =
"documented_route_approximate"` so the analyst sees the disclosure.

Upgrade path: the `gem` source ingests Global Energy Monitor's GGIT
shapefile (via `make ingest-gem FILE=...`); GGIT contains higher-fidelity
route geometry. GGIT rows live in distinct database rows
(`external_ids.gem` vs `external_ids.manual_seed`) and do not auto-merge.

IDEMPOTENCY
===========
Upserts by `external_ids.manual_seed = <slug>`. Re-running this loader on
the same database is safe — rows are updated in place; nothing duplicates.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from shapely.geometry import LineString, Point
from sqlalchemy.orm import Session

from app.db import SessionLocal
from data_pipeline.common.upsert import (
    GasFieldRecord,
    PipelineRecord,
    ProcessingPlantRecord,
    SourceRef,
    upsert_gas_field,
    upsert_pipeline,
    upsert_processing_plant,
)

logger = logging.getLogger("manual_seed")

SOURCE_NAME = "manual_seed"


@dataclass(frozen=True)
class Endpoint:
    name: str
    lat: float
    lon: float


# Documented intermediate nodes for Venezuela's gas trunk system.
# Coordinates are real city/facility locations; routes through these nodes
# approximate the documented topology (NOT surveyed pipe paths).
# Sources: Academia Nacional de la Ingeniería 2009, EIA Venezuela Country
# Analysis Brief, GEM GGIT wiki pages.

# --- Anaco hub & east-trunk corridor ---
ANACO = Endpoint("Anaco gas hub", 9.43, -64.47)
ALTAGRACIA = Endpoint("Altagracia de Orituco", 9.87, -66.38)
MARACAY = Endpoint("Maracay", 10.25, -67.60)
MORON = Endpoint("Morón (Carabobo coast)", 10.49, -68.21)

# --- West / Centro-Occidente ---
YARITAGUA = Endpoint("Yaritagua", 10.08, -69.13)
BARQUISIMETO = Endpoint("Barquisimeto", 10.07, -69.32)
ACARIGUA = Endpoint("Acarigua", 9.55, -69.20)
GUANARE = Endpoint("Guanare", 9.04, -69.74)
BARINAS = Endpoint("Barinas", 8.62, -70.20)
YUCAL_PLACER = Endpoint("Yucal-Placer field (Guárico)", 9.27, -67.30)

# --- Caracas / capital corridor ---
CARACAS = Endpoint("Caracas", 10.48, -66.90)

# --- Falcón coast / Paraguaná refining complex ---
CORO = Endpoint("Coro", 11.40, -69.67)
RIO_SECO = Endpoint("Río Seco (Falcón coast)", 11.42, -69.93)
PUNTO_FIJO = Endpoint("Punto Fijo / Paraguaná", 11.69, -70.21)
AMUAY = Endpoint("Amuay refinery (CRP)", 11.75, -70.21)

# --- Lake Maracaibo basin ---
ULE = Endpoint("Ulé gas processing complex", 10.45, -71.65)
MARACAIBO = Endpoint("Maracaibo", 10.64, -71.61)
BACHAQUERO = Endpoint("Bachaquero / TJL (lake east shore)", 9.92, -71.13)

# --- East coast / Anzoátegui industrial corridor ---
JOSE = Endpoint("José cryogenic complex", 10.18, -64.78)
PUERTO_LA_CRUZ = Endpoint("Puerto La Cruz", 10.21, -64.69)
BARBACOAS = Endpoint("Barbacoas (Anzoátegui)", 9.78, -64.21)

# --- South / Orinoco belt ---
SOTO = Endpoint("Soto (Anzoátegui)", 9.00, -64.20)
SANTA_BARBARA = Endpoint("Santa Bárbara de Monagas", 9.66, -63.59)
PUERTO_ORDAZ = Endpoint("Puerto Ordaz / Ciudad Guayana", 8.36, -62.65)

# --- Sucre / Paria peninsula (Mariscal Sucre offshore) ---
GUIRIA = Endpoint("Güiria (CIGMA onshore landing)", 10.57, -62.30)
NORTE_PARIA = Endpoint("Norte Paria offshore (Patao/Mejillones)", 10.95, -62.60)

# --- Cross-border ---
BALLENA_CO = Endpoint("Ballena, Colombia (La Guajira)", 11.95, -71.27)
DRAGON_FIELD = Endpoint("Dragon field (offshore VEN)", 10.95, -62.35)
HIBISCUS_TT = Endpoint("Hibiscus platform, Trinidad", 11.00, -61.95)
PERLA_FIELD = Endpoint("Perla field (Cardón IV)", 12.10, -70.50)


def _line(a: Endpoint, *waypoints: Endpoint, b: Endpoint) -> LineString:
    coords = [(a.lon, a.lat), *((w.lon, w.lat) for w in waypoints), (b.lon, b.lat)]
    return LineString(coords)


# --- Reusable source citations (kept DRY; reference document URLs) ---

ACADEMIA_NACIONAL_2009 = "https://www.acading.org.ve/wp-content/uploads/2023/02/LA_INDUSTRIA_DEL_GAS_NATURAL_EN_VENEZUELA.pdf"
EIA_VEN_BRIEF = "https://www.eia.gov/international/analysis/country/VEN"
PDVSA_GAS_SYSTEMS = "https://www.pdvsa.com/index.php?option=com_content&view=article&id=6530"
PDVSA_GAS_PROJECTS = "https://www.pdvsa.com/index.php?option=com_content&view=article&id=9039"
GEM_WIKI_BASE = "https://www.gem.wiki/"
UCV_THESIS = "https://saber.ucv.ve/bitstream/10872/3497/1/TEG.pdf"


def _src_academia(now: datetime, page_hint: str | None = None) -> SourceRef:
    return SourceRef(
        source_name="Academia Nacional de la Ingeniería (2009)",
        note=("La Industria del Gas Natural en Venezuela — canonical reference"
              + (f" ({page_hint})" if page_hint else "")),
        url=ACADEMIA_NACIONAL_2009,
        retrieved_at=now,
    )


def _src_eia(now: datetime) -> SourceRef:
    return SourceRef(
        source_name="EIA",
        note="Venezuela Country Analysis Brief — natural gas section (Feb 2024)",
        url=EIA_VEN_BRIEF,
        retrieved_at=now,
    )


def _src_gem(now: datetime, slug: str) -> SourceRef:
    return SourceRef(
        source_name="GEM-GGIT (wiki)",
        note=f"Global Energy Monitor wiki — {slug.replace('_', ' ')}",
        url=f"{GEM_WIKI_BASE}{slug}",
        retrieved_at=now,
    )


def _src_pdvsa(now: datetime, projects: bool = False) -> SourceRef:
    return SourceRef(
        source_name="PDVSA Gas",
        note="Operator page (note: not substantively updated since ~2017)",
        url=PDVSA_GAS_PROJECTS if projects else PDVSA_GAS_SYSTEMS,
        retrieved_at=now,
    )


def _pipeline_records() -> list[PipelineRecord]:
    """Documented Venezuelan gas trunk system.

    Topology and naming follow the Academia Nacional de la Ingeniería (2009)
    classification of "the seven national gas transmission systems" plus
    cross-border and offshore tie-in projects.
    """
    now = datetime.now(UTC)
    GQ = "documented_route_approximate"

    return [
        # ---------------------------------------------------------------
        # 1. ANACO–CARACAS (eastern trunk → capital)
        # ---------------------------------------------------------------
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
            geometry=_line(ANACO, ALTAGRACIA, b=CARACAS),
            properties={
                "geometry_quality": GQ,
                "intermediate_nodes": ["Altagracia de Orituco"],
                "note": "Trunk line from the Anaco processing complex (Anzoátegui) "
                        "westward through Altagracia de Orituco into the Caracas "
                        "demand region.",
            },
            sources=[_src_academia(now, "Sistema Anaco–Caracas"),
                     _src_eia(now), _src_pdvsa(now)],
        ),

        # ---------------------------------------------------------------
        # 2. ANACO–PUERTO ORDAZ (south to industrial Guayana)
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-aco-pzo",
            name="Anaco–Puerto Ordaz Gas Pipeline",
            name_es="Gasoducto Anaco–Puerto Ordaz",
            status="operating",
            status_as_of=now,
            length_km=210,
            operator="PDVSA Gas",
            geometry=_line(ANACO, SOTO, SANTA_BARBARA, b=PUERTO_ORDAZ),
            properties={
                "geometry_quality": GQ,
                "intermediate_nodes": ["Soto", "Santa Bárbara de Monagas"],
                "note": "Supplies industrial Guayana (steel, aluminum, electricity) "
                        "from the Anaco hub via the Orinoco belt corridor.",
            },
            sources=[_src_academia(now, "Sistema Anaco–Puerto Ordaz"),
                     _src_eia(now), _src_pdvsa(now, projects=True)],
        ),

        # ---------------------------------------------------------------
        # 3. ANACO–BARQUISIMETO–RÍO SECO (ABRS) — east trunk
        #    Canonical major east-west trunk; Academia Nacional 2009 lists
        #    4 parallel lines, ~2,210 km cumulative, 970 MMcf/d, completed 1991.
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-abrs-east-trunk",
            name="Sistema Anaco–Barquisimeto (ABRS, east trunk)",
            name_es="Sistema Anaco–Barquisimeto–Río Seco — tramo oriental",
            aliases=["ABRS", "ICO", "Sistema Anaco-Barquisimeto"],
            status="operating",
            status_as_of=now,
            length_km=550,
            diameter_in=36,
            capacity_mmcfd=970,
            operator="PDVSA Gas",
            geometry=_line(ANACO, ALTAGRACIA, MARACAY, MORON, YARITAGUA,
                           b=BARQUISIMETO),
            properties={
                "geometry_quality": GQ,
                "parallel_lines": 4,
                "intermediate_nodes": ["Altagracia de Orituco", "Maracay",
                                       "Morón (Carabobo)", "Yaritagua"],
                "completed_year": 1991,
                "note": "Major east-west trunk: four parallel ~36-inch lines, "
                        "~2,210 km cumulative, ~970 MMcf/d aggregate capacity. "
                        "Carries Anaco and Yucal-Placer gas to the Centro-Occidente "
                        "demand region (Lara, Yaracuy) via Maracay and Morón.",
            },
            sources=[_src_academia(now, "Sistema Anaco-Barquisimeto-Río Seco"),
                     _src_gem(now, "Anaco-Barquisimeto_Gas_Pipeline"),
                     _src_eia(now)],
        ),

        # ---------------------------------------------------------------
        # 4. ABRS NORTH BRANCH — Morón → Coro → Río Seco (Falcón coast)
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-abrs-norte-rio-seco",
            name="ABRS — Falcón Coastal Branch (Morón–Río Seco)",
            name_es="Tramo Norte ABRS — Morón–Coro–Río Seco",
            status="operating",
            status_as_of=now,
            length_km=180,
            operator="PDVSA Gas",
            geometry=_line(MORON, CORO, b=RIO_SECO),
            properties={
                "geometry_quality": GQ,
                "intermediate_nodes": ["Coro"],
                "note": "Northern branch of the ABRS system carrying gas from "
                        "Morón along the Falcón coast to Río Seco — the upstream "
                        "feed for the Ulé–Amuay Paraguaná extension.",
            },
            sources=[_src_academia(now, "extensión norte ABRS"),
                     _src_pdvsa(now, projects=True)],
        ),

        # ---------------------------------------------------------------
        # 5. ANACO–JOSE–PUERTO LA CRUZ
        #    Connects Anaco to the José cryogenic complex and Puerto La Cruz
        #    industrial coast.
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-aco-jose-plc",
            name="Anaco–Jose–Puerto La Cruz Pipeline",
            name_es="Gasoducto Anaco–Jose–Puerto La Cruz",
            status="operating",
            status_as_of=now,
            length_km=140,
            operator="PDVSA Gas",
            geometry=_line(ANACO, BARBACOAS, JOSE, b=PUERTO_LA_CRUZ),
            properties={
                "geometry_quality": GQ,
                "intermediate_nodes": ["Barbacoas (Anzoátegui)",
                                       "José cryogenic complex"],
                "note": "Eastern Anaco trunk feeding the José cryogenic complex "
                        "(NGL fractionation) and the Puerto La Cruz coastal "
                        "industrial / refining cluster.",
            },
            sources=[_src_academia(now, "Sistema Anaco–Jose–Puerto La Cruz"),
                     _src_pdvsa(now, projects=True)],
        ),

        # ---------------------------------------------------------------
        # 6. SISTEMA ULÉ–AMUAY (Lake Maracaibo basin → Paraguaná refining)
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-ule-amuay",
            name="Sistema Ulé–Amuay (Paraguaná extension)",
            name_es="Sistema Ulé–Amuay",
            aliases=["Ulé-Amuay"],
            status="operating",
            status_as_of=now,
            length_km=230,
            operator="PDVSA Gas",
            geometry=_line(ULE, MARACAIBO, b=AMUAY),
            properties={
                "geometry_quality": GQ,
                "intermediate_nodes": ["Maracaibo"],
                "note": "Western trunk taking gas from the Ulé processing complex "
                        "(east shore of Lake Maracaibo) up to the Paraguaná "
                        "refining complex (Amuay + Cardón = CRP). Backbone of "
                        "the Zulia/Falcón industrial corridor.",
            },
            sources=[_src_academia(now, "Sistema Ulé–Amuay"),
                     _src_pdvsa(now)],
        ),

        # ---------------------------------------------------------------
        # 7. YUCAL-PLACER FEEDER (Guárico field → ABRS)
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-yucal-placer-feeder",
            name="Yucal-Placer Feeder",
            name_es="Gasoducto Yucal-Placer–ABRS",
            status="operating",
            status_as_of=now,
            length_km=80,
            operator="Repsol / PDVSA Gas",
            geometry=_line(YUCAL_PLACER, b=ALTAGRACIA),
            properties={
                "geometry_quality": GQ,
                "note": "Feeder from the Yucal-Placer non-associated gas field "
                        "(Guárico) into the ABRS trunk at Altagracia de Orituco. "
                        "Significant central-Venezuela gas source independent "
                        "of the Anaco hub.",
            },
            sources=[_src_academia(now, "Yucal-Placer"),
                     _src_eia(now)],
        ),

        # ---------------------------------------------------------------
        # 8. CENTRO-SUR EXTENSION (Barquisimeto → Acarigua → Guanare → Barinas)
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-centro-sur-bqto-barinas",
            name="Centro-Sur Extension (Barquisimeto–Barinas)",
            name_es="Extensión Centro-Sur — Barquisimeto–Acarigua–Guanare–Barinas",
            status="operating",
            status_as_of=now,
            length_km=210,
            operator="PDVSA Gas",
            geometry=_line(BARQUISIMETO, ACARIGUA, GUANARE, b=BARINAS),
            properties={
                "geometry_quality": GQ,
                "intermediate_nodes": ["Acarigua", "Guanare"],
                "note": "Southward extension of the ABRS system into the Llanos: "
                        "Barquisimeto → Acarigua → Guanare → Barinas. Serves "
                        "Portuguesa and Barinas demand.",
            },
            sources=[_src_academia(now, "extensión Centro-Sur"),
                     _src_pdvsa(now, projects=True)],
        ),

        # ---------------------------------------------------------------
        # 9. MARISCAL SUCRE — Norte Paria offshore tie-in (Dragon → Güiria)
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-mariscal-sucre-onshore",
            name="Mariscal Sucre Offshore Tie-In (Dragon → Güiria)",
            name_es="Conexión Mariscal Sucre — Dragón–Güiria",
            status="proposed",
            status_as_of=now,
            length_km=80,
            operator="PDVSA / partners (license-dependent)",
            geometry=_line(DRAGON_FIELD, NORTE_PARIA, b=GUIRIA),
            properties={
                "geometry_quality": GQ,
                "intermediate_nodes": ["Norte Paria offshore"],
                "note": "Planned onshore landing at Güiria (CIGMA complex) for the "
                        "four Mariscal Sucre offshore fields (Dragon, Patao, "
                        "Mejillones, Río Caribe). Subject to OFAC licensing for "
                        "Western counterparties; alternative monetization route to "
                        "Trinidad LNG via the Dragon–Hibiscus link.",
            },
            sources=[_src_academia(now, "Proyecto Mariscal Sucre"),
                     _src_pdvsa(now, projects=True),
                     SourceRef(
                         source_name="UCV thesis (Recursos y Reservas)",
                         note="Saber UCV — Mariscal Sucre / Plataforma Deltana",
                         url=UCV_THESIS,
                         retrieved_at=now,
                     )],
        ),

        # ---------------------------------------------------------------
        # 10. MARACAIBO LAKE FEEDER (Bachaquero/TJL → Ulé)
        #     Representative of the dense subsea network (LAMARGAS / UNIGAS /
        #     CEUTAGAS systems) feeding the Ulé processing complex.
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-lago-bachaquero-ule",
            name="Maracaibo Lake Feeder (Bachaquero/TJL → Ulé)",
            name_es="Gasoducto del Lago — Bachaquero/TJL–Ulé",
            aliases=["LAMARGAS feeder", "UNIGAS feeder"],
            status="operating",
            status_as_of=now,
            length_km=80,
            operator="PDVSA Gas (lake operations)",
            geometry=_line(BACHAQUERO, b=ULE),
            properties={
                "geometry_quality": GQ,
                "note": "Representative trunk feeder from the lake-east-shore "
                        "production area (Bachaquero / TJL) to the Ulé "
                        "processing complex. Stands in for a denser subsea "
                        "network (LAMARGAS, UNIGAS, CEUTAGAS) — single line "
                        "shown for v1 readability.",
                "representative_of": "lake subsea gas-gathering network",
            },
            sources=[_src_academia(now, "Sistema del Lago"),
                     _src_pdvsa(now)],
        ),

        # ---------------------------------------------------------------
        # 11. ANTONIO RICAURTE (cross-border Colombia ↔ Venezuela, idle)
        # ---------------------------------------------------------------
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
                "geometry_quality": GQ,
                "cross_border": ["VE", "CO"],
                "note": "Originally built for Colombia→Venezuela flow (2007); "
                        "idle in recent years. Multiple announcements about "
                        "reversing or restarting flow are tracked via news "
                        "OSINT (out of scope for v1 manual_seed).",
            },
            sources=[
                _src_academia(now, "interconexiones internacionales"),
                SourceRef(
                    source_name="Reuters",
                    note="Antonio Ricaurte status / reversal coverage",
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

        # ---------------------------------------------------------------
        # 12. PERLA / CARDÓN IV — onshore tie-in
        # ---------------------------------------------------------------
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
                "geometry_quality": GQ,
                "note": "Offshore-to-onshore tie-in delivering Perla gas (Cardón "
                        "IV block) into the Falcón onshore system at Punto Fijo. "
                        "Feeds into the Ulé–Amuay backbone.",
            },
            sources=[
                SourceRef(
                    source_name="Eni",
                    note="Operator press releases on Perla / Cardón IV",
                    url="https://www.eni.com/",
                    retrieved_at=now,
                ),
                _src_academia(now, "Proyecto Rafael Urdaneta — Cardón IV"),
                SourceRef(
                    source_name="S&P Global Commodity Insights",
                    url="https://www.spglobal.com/commodityinsights",
                    retrieved_at=now,
                ),
            ],
        ),

        # ---------------------------------------------------------------
        # 13. DRAGON–HIBISCUS (cross-border Trinidad, proposed)
        # ---------------------------------------------------------------
        PipelineRecord(
            source_name=SOURCE_NAME,
            external_id="ven-tt-dragon-hibiscus",
            name="Dragon–Hibiscus Pipeline (proposed)",
            name_es="Gasoducto Dragon–Hibiscus (propuesto)",
            status="proposed",
            status_as_of=now,
            operator="Shell / NGC (proposed, OFAC license)",
            geometry=_line(DRAGON_FIELD, b=HIBISCUS_TT),
            properties={
                "geometry_quality": GQ,
                "cross_border": ["VE", "TT"],
                "note": "Proposed cross-border line carrying Dragon-field gas to "
                        "Trinidad's Hibiscus platform for processing and LNG "
                        "export. Subject to OFAC licensing.",
            },
            sources=[
                _src_academia(now, "Plataforma Deltana / monetización"),
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


def _gas_field_records() -> list[GasFieldRecord]:
    """Three real, publicly-sourced Venezuelan gas fields, chosen to span
    offshore (Perla), proposed/dev (Dragon), and cross-border (Loran-Manatee)."""
    now = datetime.now(UTC)
    return [
        GasFieldRecord(
            source_name=SOURCE_NAME,
            external_id="ven-perla-cardon-iv",
            name="Perla Field (Cardón IV block)",
            name_es="Campo Perla (Bloque Cardón IV)",
            aliases=["Cardón IV"],
            status="operating",
            status_as_of=now,
            operator="Eni / Repsol (Cardón IV consortium)",
            geometry=Point(-70.50, 12.10),
            properties={
                "geometry_quality": "approximate_centroid",
                "basin": "Gulf of Venezuela (offshore Falcón)",
                "reservoir_type": "non-associated gas",
                "reserves_estimate": "~17 Tcf gas in place (largest non-associated gas discovery in LatAm)",
                "note": "Producing offshore gas field tied into the Falcón onshore "
                        "system. Plateau ~800 mmcfd target.",
            },
            sources=[
                SourceRef(
                    source_name="Eni",
                    note="Operator press releases on Perla / Cardón IV",
                    url="https://www.eni.com/",
                    retrieved_at=now,
                ),
                SourceRef(
                    source_name="EIA",
                    note="Venezuela Country Analysis Brief — natural gas section",
                    url="https://www.eia.gov/international/analysis/country/VEN",
                    retrieved_at=now,
                ),
            ],
        ),
        GasFieldRecord(
            source_name=SOURCE_NAME,
            external_id="ven-dragon-mariscal-sucre",
            name="Dragon Field (Mariscal Sucre Project)",
            name_es="Campo Dragón (Proyecto Mariscal Sucre)",
            aliases=["Mariscal Sucre — Dragon"],
            status="proposed",
            status_as_of=now,
            operator="PDVSA / Shell / NGC (under OFAC license)",
            geometry=Point(-62.35, 10.95),
            properties={
                "geometry_quality": "approximate_centroid",
                "basin": "Gulf of Paria (offshore Sucre)",
                "reservoir_type": "non-associated gas",
                "reserves_estimate": "~4 Tcf recoverable",
                "note": "Largest of the four Mariscal Sucre fields (Dragon, Patao, "
                        "Mejillones, Río Caribe). Subject to OFAC licensing for the "
                        "Dragon-to-Hibiscus monetization route via Trinidad LNG.",
            },
            sources=[
                SourceRef(
                    source_name="Reuters",
                    note="Coverage of Dragon field and OFAC license modifications",
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
        GasFieldRecord(
            source_name=SOURCE_NAME,
            external_id="ven-loran-manatee",
            name="Loran-Manatee Field (Plataforma Deltana)",
            name_es="Campo Loran-Manatee (Plataforma Deltana)",
            aliases=["Loran", "Manatee"],
            status="idle",
            status_as_of=now,
            operator="Historical: Chevron / Shell (cross-border unitization)",
            geometry=Point(-61.40, 10.40),
            properties={
                "geometry_quality": "approximate_centroid",
                "cross_border": ["VE", "TT"],
                "basin": "Plataforma Deltana / East Coast Marine Area",
                "reservoir_type": "non-associated gas",
                "reserves_estimate": "~10 Tcf recoverable (combined Loran + Manatee)",
                "note": "Cross-border gas accumulation straddling the VE↔TT maritime "
                        "boundary; subject to a 2010 unitization framework, "
                        "development paused.",
            },
            sources=[
                SourceRef(
                    source_name="S&P Global Commodity Insights",
                    url="https://www.spglobal.com/commodityinsights",
                    retrieved_at=now,
                ),
                SourceRef(
                    source_name="Reuters",
                    url="https://www.reuters.com/",
                    retrieved_at=now,
                ),
            ],
        ),
    ]


def _processing_plant_records() -> list[ProcessingPlantRecord]:
    """Documented Venezuelan gas processing & compression plants.

    Coverage spans the four sub-types we care about for v1:
      - processing  (gas treatment / NGL recovery)
      - cryogenic   (deep NGL fractionation)
      - compression (transmission boosters along the trunk lines)
      - refinery_gas_treatment (refinery off-gas / fuel-gas systems)

    plant_type lives in `properties` JSONB so adding a new sub-type later
    (LNG terminal, city gate, metering station) doesn't require a migration.
    """
    now = datetime.now(UTC)

    def _plant(
        external_id: str,
        name: str,
        name_es: str,
        plant_type: str,
        coords: tuple[float, float],
        operator: str,
        status: str = "operating",
        note: str = "",
        extra_props: dict[str, Any] | None = None,
        sources: list[SourceRef] | None = None,
    ) -> ProcessingPlantRecord:
        props: dict[str, Any] = {
            "plant_type": plant_type,
            "geometry_quality": "approximate_centroid",
            "note": note,
        }
        if extra_props:
            props.update(extra_props)
        return ProcessingPlantRecord(
            source_name=SOURCE_NAME,
            external_id=external_id,
            name=name,
            name_es=name_es,
            geometry=Point(coords[1], coords[0]),  # (lat, lon) → Point(lon, lat)
            operator=operator,
            status=status,
            status_as_of=now,
            properties=props,
            sources=sources or [
                _src_academia(now),
                _src_pdvsa(now, projects=True),
            ],
        )

    return [
        _plant(
            "ven-cgp-anaco",
            name="Anaco Gas Processing Complex",
            name_es="Complejo de Procesamiento de Gas Anaco",
            plant_type="processing",
            coords=(9.45, -64.45),
            operator="PDVSA Gas",
            note=(
                "Anchor processing complex for the eastern (Anzoátegui) gas "
                "fields; feeds the ABRS, Anaco–Caracas, Anaco–PZO and "
                "Anaco–Jose trunk lines."
            ),
            extra_props={"role": "eastern hub"},
        ),
        _plant(
            "ven-cgp-san-joaquin",
            name="San Joaquín Gas Processing",
            name_es="Procesamiento de Gas San Joaquín",
            plant_type="processing",
            coords=(9.95, -64.43),
            operator="PDVSA Gas",
            note=(
                "Northern Anzoátegui processing satellite of the Anaco hub; "
                "treats associated and non-associated gas from local fields."
            ),
        ),
        _plant(
            "ven-cgp-jose",
            name="José Cryogenic Complex",
            name_es="Complejo Criogénico de José",
            plant_type="cryogenic",
            coords=(10.18, -64.78),
            operator="PDVSA Gas",
            note=(
                "Major NGL fractionation complex on the Anzoátegui coast; "
                "outputs ethane, propane, butane and natural gasoline. "
                "Anchor demand point on the Anaco–Jose trunk."
            ),
            extra_props={"capacity_note": "fractionation ~200 Mb/d (per OPEC ASB)"},
        ),
        _plant(
            "ven-cmp-santa-barbara",
            name="Santa Bárbara Compression",
            name_es="Planta de Compresión Santa Bárbara",
            plant_type="compression",
            coords=(9.66, -63.59),
            operator="PDVSA Gas",
            note=(
                "Compression along the Anaco–Puerto Ordaz corridor; "
                "Monagas state. World Bank GGFR identifies Santa Bárbara as "
                "a major flaring node — useful ground-truth signal for "
                "downstream VIIRS validation."
            ),
            extra_props={"ggfr_top_flaring_site": True},
            sources=[
                _src_academia(now),
                SourceRef(
                    source_name="World Bank GGFR",
                    note="Global Gas Flaring Reduction Partnership — facility-level annual data",
                    url="https://www.worldbank.org/en/programs/gasflaringreduction",
                    retrieved_at=now,
                ),
            ],
        ),
        _plant(
            "ven-cmp-altagracia",
            name="Altagracia Compression",
            name_es="Planta de Compresión Altagracia",
            plant_type="compression",
            coords=(9.87, -66.38),
            operator="PDVSA Gas",
            note=(
                "Mid-trunk compression on the ABRS east trunk + the Anaco–"
                "Caracas branch; intersection with the Yucal-Placer feeder."
            ),
        ),
        _plant(
            "ven-cmp-maracay",
            name="Maracay Compression",
            name_es="Planta de Compresión Maracay",
            plant_type="compression",
            coords=(10.25, -67.60),
            operator="PDVSA Gas",
            note="Aragua-state booster on the ABRS east trunk between Altagracia and Morón.",
        ),
        _plant(
            "ven-cmp-moron",
            name="Morón Compression",
            name_es="Planta de Compresión Morón",
            plant_type="compression",
            coords=(10.49, -68.21),
            operator="PDVSA Gas",
            note=(
                "Major ABRS junction on the Carabobo coast; splits flow north "
                "(Falcón coastal branch → Río Seco / CRP) and west (Yaritagua "
                "→ Barquisimeto)."
            ),
            extra_props={"role": "ABRS junction"},
        ),
        _plant(
            "ven-cgp-ule",
            name="Ulé Gas Processing Complex",
            name_es="Complejo de Procesamiento de Gas Ulé",
            plant_type="processing",
            coords=(10.45, -71.65),
            operator="PDVSA Gas",
            note=(
                "Anchor processing complex for the Lake Maracaibo basin; "
                "head-end of the Ulé–Amuay trunk to the Paraguaná refining "
                "complex (CRP). Receives subsea gathering from LAMARGAS / "
                "UNIGAS / CEUTAGAS systems."
            ),
            extra_props={"role": "western hub"},
        ),
        _plant(
            "ven-rgt-amuay",
            name="Amuay Refinery Gas Treatment (CRP)",
            name_es="Tratamiento de Gas Refinería Amuay (CRP)",
            plant_type="refinery_gas_treatment",
            coords=(11.75, -70.21),
            operator="PDVSA Refinación",
            note=(
                "Fuel-gas and off-gas treatment within the Amuay leg of the "
                "Centro Refinador Paraguaná (CRP). Terminal demand point on "
                "the Ulé–Amuay system."
            ),
        ),
        _plant(
            "ven-cgp-cigma-guiria",
            name="CIGMA / Güiria Onshore Complex",
            name_es="Complejo CIGMA — Güiria",
            plant_type="processing",
            coords=(10.57, -62.30),
            operator="PDVSA / partners (license-dependent)",
            status="proposed",
            note=(
                "Planned onshore processing complex at Güiria (CIGMA, "
                "Complejo Industrial Gran Mariscal de Ayacucho) for the four "
                "Mariscal Sucre offshore fields (Dragon, Patao, Mejillones, "
                "Río Caribe). Includes a planned LNG monetization branch; "
                "subject to OFAC licensing."
            ),
            sources=[
                _src_academia(now, "Proyecto Mariscal Sucre / CIGMA"),
                _src_pdvsa(now, projects=True),
                SourceRef(
                    source_name="UCV thesis (Recursos y Reservas)",
                    note="Saber UCV — Mariscal Sucre / Plataforma Deltana",
                    url=UCV_THESIS,
                    retrieved_at=now,
                ),
            ],
        ),
    ]


def run(db: Session) -> tuple[int, int, int]:
    pipelines = _pipeline_records()
    for rec in pipelines:
        upsert_pipeline(db, rec)
    fields = _gas_field_records()
    for rec in fields:
        upsert_gas_field(db, rec)
    plants = _processing_plant_records()
    for rec in plants:
        upsert_processing_plant(db, rec)
    db.commit()
    return len(pipelines), len(fields), len(plants)


def main() -> int:
    db = SessionLocal()
    try:
        n_pipes, n_fields, n_plants = run(db)
    finally:
        db.close()
    msg = (
        f"manual_seed: upserted {n_pipes} pipelines, {n_fields} gas fields, "
        f"{n_plants} processing/compression plants"
    )
    logger.info(msg)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
