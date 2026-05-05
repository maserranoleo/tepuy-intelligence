"""FIRMS — NASA Fire Information for Resource Management System.

Ingests VIIRS active-fire detections over Venezuela. Free API; you bring a
MAP_KEY (sign up: https://firms.modaps.eosdis.nasa.gov/api/map_key/).

Each row is a single thermal anomaly detection — candidate flare or fire.
We do not classify here; the analyst does that downstream by looking for
persistence (same coordinates day after day = likely flare).

Idempotency: each detection's external_id is a SHA1 of
(satellite, acq_date, acq_time, lat, lon). Re-running the loader on the
same window is a no-op.

Usage:
    NASA_FIRMS_MAP_KEY=...  python -m data_pipeline.sources.firms.load
    NASA_FIRMS_MAP_KEY=...  python -m data_pipeline.sources.firms.load --days 7
    NASA_FIRMS_MAP_KEY=...  python -m data_pipeline.sources.firms.load --source VIIRS_NOAA20_NRT
"""
from __future__ import annotations

import argparse
import hashlib
import io
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, time

import httpx
import pandas as pd
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.flare_event import FlareEvent

logger = logging.getLogger("firms")
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

SOURCE_NAME = "firms"
SOURCE_URL = "https://firms.modaps.eosdis.nasa.gov/api/"
ALLOWED_SOURCES = {
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT",
}
DEFAULT_AREA = "VEN"  # ISO-3 country code accepted by FIRMS
MAX_DAYS = 10  # FIRMS API hard limit


@dataclass
class FirmsConfig:
    map_key: str
    source: str = "VIIRS_SNPP_NRT"
    area: str = DEFAULT_AREA
    days: int = 7


def _build_url(cfg: FirmsConfig) -> str:
    return (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{cfg.map_key}/{cfg.source}/{cfg.area}/{cfg.days}"
    )


def _stable_id(row: dict) -> str:
    h = hashlib.sha1()
    h.update(
        "|".join(
            [
                str(row.get("satellite", "")),
                str(row.get("acq_date", "")),
                str(row.get("acq_time", "")),
                f"{float(row['latitude']):.5f}",
                f"{float(row['longitude']):.5f}",
            ]
        ).encode()
    )
    return h.hexdigest()


def _parse_acq(date_str: str, time_str: str | int) -> datetime:
    """FIRMS gives acq_time as 'HHMM' (sometimes as int 230 → 02:30)."""
    s = str(time_str).zfill(4)
    hh, mm = int(s[:2]), int(s[2:])
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return datetime.combine(d, time(hh, mm), tzinfo=UTC)


def fetch(cfg: FirmsConfig) -> pd.DataFrame:
    if cfg.source not in ALLOWED_SOURCES:
        raise ValueError(f"unknown source {cfg.source}; allowed: {sorted(ALLOWED_SOURCES)}")
    if not 1 <= cfg.days <= MAX_DAYS:
        raise ValueError(f"days must be 1..{MAX_DAYS}; got {cfg.days}")
    url = _build_url(cfg)
    logger.info("firms: GET %s/%s/%s/%d (key redacted)", "area/csv", cfg.source, cfg.area, cfg.days)
    r = httpx.get(url, timeout=60.0)
    r.raise_for_status()
    text = r.text
    # FIRMS returns plain text on errors (e.g. invalid key). Fail loud.
    if not text.lstrip().lower().startswith("latitude"):
        head = text[:200].replace("\n", " ")
        raise RuntimeError(f"FIRMS returned non-CSV (likely auth/quota error): {head}")
    return pd.read_csv(io.StringIO(text))


def upsert(db: Session, df: pd.DataFrame, cfg: FirmsConfig) -> int:
    now = datetime.now(UTC)
    inserted = 0
    skipped = 0
    for _, raw in df.iterrows():
        row = raw.to_dict()
        try:
            ext_id = _stable_id(row)
            acquired_at = _parse_acq(row["acq_date"], row.get("acq_time", 0))
        except (KeyError, ValueError) as e:  # malformed row — skip
            logger.debug("skip row: %s", e)
            skipped += 1
            continue

        existing = db.execute(
            select(FlareEvent).where(
                FlareEvent.source_name == SOURCE_NAME,
                FlareEvent.external_id == ext_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue  # already ingested, skip silently

        geom = from_shape(Point(float(row["longitude"]), float(row["latitude"])), srid=4326)
        ev = FlareEvent(
            geometry=geom,
            acquired_at=acquired_at,
            satellite=str(row.get("satellite") or "") or None,
            instrument=str(row.get("instrument") or "") or None,
            confidence=str(row.get("confidence") or "") or None,
            daynight=(str(row.get("daynight") or "") or None),
            brightness_ti4=float(row["bright_ti4"]) if pd.notna(row.get("bright_ti4")) else None,
            brightness_ti5=float(row["bright_ti5"]) if pd.notna(row.get("bright_ti5")) else None,
            frp=float(row["frp"]) if pd.notna(row.get("frp")) else None,
            source_name=SOURCE_NAME,
            external_id=ext_id,
            sources=[
                {
                    "source_name": "NASA FIRMS",
                    "source_id": ext_id,
                    "url": SOURCE_URL,
                    "note": f"{cfg.source} / area={cfg.area} / window={cfg.days}d",
                    "retrieved_at": now.isoformat(),
                }
            ],
        )
        db.add(ev)
        inserted += 1
    db.commit()
    if skipped:
        logger.info("firms: skipped %d malformed rows", skipped)
    return inserted


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Load FIRMS hotspots into Postgres.")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--source", default="VIIRS_SNPP_NRT", choices=sorted(ALLOWED_SOURCES))
    p.add_argument("--area", default=DEFAULT_AREA)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    map_key = os.environ.get("NASA_FIRMS_MAP_KEY", "").strip()
    if not map_key:
        print(
            "NASA_FIRMS_MAP_KEY is not set. Get a free key at "
            "https://firms.modaps.eosdis.nasa.gov/api/map_key/ and add to .env.",
            file=sys.stderr,
        )
        return 2

    cfg = FirmsConfig(map_key=map_key, source=args.source, area=args.area, days=args.days)
    df = fetch(cfg)
    logger.info("firms: fetched %d detections", len(df))

    if args.dry_run:
        print(df.head(10).to_string())
        return 0

    db = SessionLocal()
    try:
        n = upsert(db, df, cfg)
    finally:
        db.close()
    msg = f"firms: inserted {n} new flare_events ({len(df) - n} were duplicates)"
    logger.info(msg)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
