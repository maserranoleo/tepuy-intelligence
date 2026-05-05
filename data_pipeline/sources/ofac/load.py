"""OFAC SDN list ingestion.

Fetches the U.S. Treasury OFAC Specially Designated Nationals (SDN) list
and upserts it into `sanctions_entries`. The matcher in
`app/sanctions/matcher.py` reads from this table.

The SDN.CSV format is no-headers with a fixed column order documented at
https://ofac.treasury.gov/recent-actions :

    1.  ent_num            (entity number, integer key)
    2.  SDN_Name           (e.g. "PETROLEOS DE VENEZUELA, S.A.")
    3.  SDN_Type           (Individual / Entity / Vessel / Aircraft)
    4.  Program            (semicolon- or comma-separated programs)
    5.  Title
    6.  Call_Sign          (vessel)
    7.  Vess_type
    8.  Tonnage
    9.  GRT
    10. Vess_flag
    11. Vess_owner
    12. Remarks

OFAC uses the literal string "-0-" for null values.

For Tepuy v1 we keep all entries (not just Venezuela-program) because
operators of Venezuelan assets may include subsidiaries listed under
non-Venezuela programs (e.g. CITGO under VENEZUELA, but also vessel
designations under other regimes that touch Venezuelan trade).

Re-run is idempotent — keyed on `ent_num`. Run weekly or after major
OFAC actions: `make ingest-ofac`.
"""
from __future__ import annotations

import argparse
import csv
import io
import logging
import re
import sys
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.sanctions_entry import SanctionsEntry

logger = logging.getLogger("ofac")
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

DEFAULT_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"
LEGACY_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"

OFAC_NULL = "-0-"


def _normalize_name(s: str) -> str:
    """Normalize a name for substring matching: uppercase, strip
    punctuation, collapse whitespace."""
    s = s.upper()
    s = re.sub(r"[^\w\s]", " ", s)  # strip punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    if v == "" or v == OFAC_NULL:
        return None
    return v


def _split_programs(s: str | None) -> list[str]:
    if not s:
        return []
    # OFAC uses semicolons or commas; both forms appear in the wild.
    parts = re.split(r"[;,]", s)
    return [p.strip() for p in parts if p.strip()]


def fetch(url: str) -> str:
    logger.info("ofac: GET %s", url)
    r = httpx.get(url, timeout=120.0, follow_redirects=True)
    r.raise_for_status()
    text = r.text
    if len(text) < 1024:
        # OFAC returns small error pages on bad URLs; flag.
        raise RuntimeError(
            f"OFAC response suspiciously small ({len(text)} bytes); first 200: "
            f"{text[:200]!r}"
        )
    return text


# OFAC SDN.CSV column order (1-indexed in their docs, 0-indexed below).
COL_ENT_NUM = 0
COL_SDN_NAME = 1
COL_SDN_TYPE = 2
COL_PROGRAM = 3
COL_TITLE = 4
COL_REMARKS = 11


def parse(csv_text: str) -> list[dict]:
    """Parse SDN.CSV. Returns dict rows ready for upsert."""
    reader = csv.reader(io.StringIO(csv_text))
    rows: list[dict] = []
    for raw in reader:
        if len(raw) < 5:
            continue  # malformed
        try:
            ent_num = int(raw[COL_ENT_NUM])
        except ValueError:
            continue
        sdn_name = _clean(raw[COL_SDN_NAME])
        if not sdn_name:
            continue
        rows.append(
            {
                "ent_num": ent_num,
                "sdn_name": sdn_name,
                "sdn_name_normalized": _normalize_name(sdn_name),
                "sdn_type": _clean(raw[COL_SDN_TYPE]),
                "programs": _split_programs(_clean(raw[COL_PROGRAM])),
                "title": _clean(raw[COL_TITLE]),
                "remarks": _clean(raw[COL_REMARKS]) if len(raw) > COL_REMARKS else None,
                "raw": {f"col_{i}": v for i, v in enumerate(raw)},
            }
        )
    return rows


def upsert(db: Session, rows: list[dict], source_url: str) -> tuple[int, int]:
    now = datetime.now(UTC)
    inserted = 0
    updated = 0

    # Single SELECT to check existence; cheaper than per-row roundtrips.
    existing_ents = {
        row.ent_num: row
        for row in db.execute(select(SanctionsEntry)).scalars().all()
    }

    for r in rows:
        existing = existing_ents.get(r["ent_num"])
        if existing is None:
            db.add(
                SanctionsEntry(
                    ent_num=r["ent_num"],
                    sdn_name=r["sdn_name"],
                    sdn_name_normalized=r["sdn_name_normalized"],
                    sdn_type=r["sdn_type"],
                    programs=r["programs"],
                    title=r["title"],
                    remarks=r["remarks"],
                    source_url=source_url,
                    retrieved_at=now,
                    raw=r["raw"],
                )
            )
            inserted += 1
        else:
            existing.sdn_name = r["sdn_name"]
            existing.sdn_name_normalized = r["sdn_name_normalized"]
            existing.sdn_type = r["sdn_type"]
            existing.programs = r["programs"]
            existing.title = r["title"]
            existing.remarks = r["remarks"]
            existing.source_url = source_url
            existing.retrieved_at = now
            existing.raw = r["raw"]
            updated += 1

    db.commit()
    return inserted, updated


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Load OFAC SDN list into Postgres.")
    p.add_argument(
        "--url",
        default=DEFAULT_SDN_URL,
        help="SDN.CSV URL. Falls back to legacy URL on 404.",
    )
    p.add_argument(
        "--file",
        type=str,
        default=None,
        help="Local SDN.CSV file path (skips network).",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.file:
        with open(args.file) as fh:
            text = fh.read()
        source_url = f"file://{args.file}"
    else:
        try:
            text = fetch(args.url)
            source_url = args.url
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 and args.url == DEFAULT_SDN_URL:
                logger.warning("ofac: primary URL 404, trying legacy URL")
                text = fetch(LEGACY_SDN_URL)
                source_url = LEGACY_SDN_URL
            else:
                raise

    rows = parse(text)
    logger.info("ofac: parsed %d entries from %s", len(rows), source_url)

    if args.dry_run:
        # Show a sample of Venezuela-program entries.
        ven = [r for r in rows if any("VENEZUELA" in p for p in r["programs"])]
        logger.info("ofac: %d entries on Venezuela-related programs", len(ven))
        for r in ven[:10]:
            logger.info(
                "  ent_num=%d  programs=%s  name=%s",
                r["ent_num"],
                ",".join(r["programs"]),
                r["sdn_name"],
            )
        return 0

    db = SessionLocal()
    try:
        ins, upd = upsert(db, rows, source_url)
    finally:
        db.close()
    msg = f"ofac: inserted {ins}, updated {upd} ({len(rows)} total)"
    logger.info(msg)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
