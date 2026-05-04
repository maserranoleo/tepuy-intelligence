"""Transform GEM Global Gas Infrastructure Tracker rows → PipelineRecords.

GEM publishes the GGIT as an Excel workbook on a "Pipelines" sheet (name varies
slightly across releases). We read it defensively: pick the sheet by name match,
locate columns by best-guess header matching, build geometries from a WKT route
column when present, otherwise fall back to a two-point line from start/end
coordinates.

We filter to pipelines that:
  * have Venezuela as a country, OR
  * cross the VEN↔CO or VEN↔TT borders (start in one, end in the other).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.wkt import loads as wkt_loads

from data_pipeline.common.upsert import PipelineRecord, SourceRef

logger = logging.getLogger("gem.transform")

SOURCE_NAME = "gem"
SOURCE_URL = "https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/"

VEN_TOKENS = {"venezuela", "ven"}
CO_TOKENS = {"colombia", "col"}
TT_TOKENS = {"trinidad and tobago", "trinidad", "tt", "tto"}


def _norm(s: object) -> str:
    return str(s).strip().lower() if s is not None else ""


def _is_ven(s: object) -> bool:
    return _norm(s) in VEN_TOKENS


def _is_neighbor(s: object) -> bool:
    return _norm(s) in CO_TOKENS or _norm(s) in TT_TOKENS


# Best-effort column header → canonical key map. Match is case-insensitive
# substring; first match wins.
HEADER_PATTERNS: dict[str, list[str]] = {
    "id":         ["pipeline id", "ggit id", "project id", "id"],
    "name":       ["pipeline name", "project name", "name"],
    "status":     ["status"],
    "countries":  ["countries", "country"],
    "start_country": ["start country", "country start"],
    "end_country":   ["end country", "country end"],
    "start_lat":  ["start lat", "starting lat", "lat start"],
    "start_lon":  ["start lon", "start long", "starting lon", "lon start"],
    "end_lat":    ["end lat", "ending lat", "lat end"],
    "end_lon":    ["end lon", "end long", "ending lon", "lon end"],
    "length_km":  ["length", "length (km)", "length km"],
    "diameter":   ["diameter"],
    "capacity":   ["capacity"],
    "operator":   ["operator", "owner"],
    "wkt":        ["wkt", "route wkt", "geometry wkt", "linestring"],
}


def _resolve_columns(df: pd.DataFrame) -> dict[str, str | None]:
    headers = {c: _norm(c) for c in df.columns}
    resolved: dict[str, str | None] = {}
    for key, patterns in HEADER_PATTERNS.items():
        match: str | None = None
        for col, h in headers.items():
            if any(p in h for p in patterns):
                match = col
                break
        resolved[key] = match
    return resolved


def _pick_sheet(xl: pd.ExcelFile) -> str:
    for name in xl.sheet_names:
        if "pipeline" in name.lower():
            return name
    return xl.sheet_names[0]


def _to_float(v: object) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_geometry(row: dict[str, Any], cols: dict[str, str | None]) -> BaseGeometry | None:
    wkt_col = cols.get("wkt")
    if wkt_col and isinstance(row.get(wkt_col), str) and row[wkt_col].strip():
        try:
            geom = wkt_loads(row[wkt_col])
            if not geom.is_empty:
                return geom
        except Exception:  # noqa: BLE001
            logger.debug("invalid WKT for row, falling back to endpoints")

    sla, slo = cols.get("start_lat"), cols.get("start_lon")
    ela, elo = cols.get("end_lat"), cols.get("end_lon")
    if not (sla and slo and ela and elo):
        return None
    s_lat = _to_float(row.get(sla))
    s_lon = _to_float(row.get(slo))
    e_lat = _to_float(row.get(ela))
    e_lon = _to_float(row.get(elo))
    if None in (s_lat, s_lon, e_lat, e_lon):
        return None
    if (s_lat, s_lon) == (e_lat, e_lon):
        return None
    return LineString([(s_lon, s_lat), (e_lon, e_lat)])


# GEM uses several status vocabularies across releases; collapse to ours.
_STATUS_MAP = {
    "operating": "operating",
    "in service": "operating",
    "construction": "construction",
    "under construction": "construction",
    "proposed": "proposed",
    "announced": "proposed",
    "pre-construction": "proposed",
    "shelved": "idle",
    "mothballed": "idle",
    "idle": "idle",
    "cancelled": "retired",
    "canceled": "retired",
    "retired": "retired",
    "decommissioned": "retired",
}


def _normalize_status(raw: object) -> str:
    s = _norm(raw)
    if not s:
        return "unknown"
    return _STATUS_MAP.get(s, "unknown")


def _wants_row(row: dict[str, Any], cols: dict[str, str | None]) -> bool:
    countries = _norm(row.get(cols["countries"])) if cols.get("countries") else ""
    start_c = row.get(cols["start_country"]) if cols.get("start_country") else None
    end_c = row.get(cols["end_country"]) if cols.get("end_country") else None

    if "venezuela" in countries:
        return True
    if _is_ven(start_c) or _is_ven(end_c):
        return True
    # Cross-border with VEN as one endpoint
    if (_is_ven(start_c) and _is_neighbor(end_c)) or (
        _is_ven(end_c) and _is_neighbor(start_c)
    ):
        return True
    return False


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "row"


@dataclass
class TransformResult:
    records: list[PipelineRecord]
    skipped_no_geometry: int
    skipped_filter: int
    total_rows: int


def transform(path: Path) -> TransformResult:
    xl = pd.ExcelFile(path)
    sheet = _pick_sheet(xl)
    df = xl.parse(sheet)
    cols = _resolve_columns(df)
    logger.info("gem.transform: sheet=%s rows=%d columns=%s", sheet, len(df), cols)

    now = datetime.now(UTC)
    records: list[PipelineRecord] = []
    skipped_no_geom = 0
    skipped_filter = 0

    for _, raw in df.iterrows():
        row = raw.to_dict()
        if not _wants_row(row, cols):
            skipped_filter += 1
            continue

        geom = _build_geometry(row, cols)
        if geom is None:
            skipped_no_geom += 1
            continue

        ext_id_raw = row.get(cols["id"]) if cols.get("id") else None
        name = str(row.get(cols["name"]) if cols.get("name") else "").strip()
        if not name:
            name = "Unnamed pipeline"
        ext_id = str(ext_id_raw).strip() if ext_id_raw and not pd.isna(ext_id_raw) else f"derived-{_slugify(name)}"

        rec = PipelineRecord(
            source_name=SOURCE_NAME,
            external_id=ext_id,
            name=name,
            status=_normalize_status(row.get(cols["status"])) if cols.get("status") else "unknown",
            status_as_of=now,
            length_km=_to_float(row.get(cols["length_km"])) if cols.get("length_km") else None,
            diameter_in=_to_float(row.get(cols["diameter"])) if cols.get("diameter") else None,
            capacity_mmcfd=_to_float(row.get(cols["capacity"])) if cols.get("capacity") else None,
            operator=(str(row.get(cols["operator"])).strip()
                      if cols.get("operator") and row.get(cols["operator"]) else None),
            geometry=geom,
            properties={
                "geometry_quality": "wkt" if cols.get("wkt") and row.get(cols["wkt"]) else "approximate_endpoints",
                "raw_status": str(row.get(cols["status"])) if cols.get("status") else None,
            },
            sources=[
                SourceRef(
                    source_name="GEM-GGIT",
                    source_id=ext_id,
                    url=SOURCE_URL,
                    note=f"Imported from {path.name}",
                    retrieved_at=now,
                )
            ],
        )
        records.append(rec)

    return TransformResult(
        records=records,
        skipped_no_geometry=skipped_no_geom,
        skipped_filter=skipped_filter,
        total_rows=len(df),
    )
