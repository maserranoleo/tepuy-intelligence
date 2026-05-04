"""GEM Global Gas Infrastructure Tracker — load.

Usage (inside the running stack):
    docker compose exec backend python -m data_pipeline.sources.gem.load \\
        /data_pipeline/.data/gem-ggit-2025-Q1.xlsx

Or from the host with the backend container running:
    docker compose run --rm backend python -m data_pipeline.sources.gem.load \\
        /data_pipeline/.data/<your-file>.xlsx

Drop your GEM workbook into `data_pipeline/.data/` (gitignored). No fetcher;
GEM downloads are email-gated, so you supply the file manually.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.db import SessionLocal
from data_pipeline.common.upsert import upsert_pipeline
from data_pipeline.sources.gem.transform import transform

logger = logging.getLogger("gem.load")
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Load GEM GGIT into Postgres.")
    p.add_argument("path", type=Path, help="Path to the GEM .xlsx file")
    p.add_argument("--dry-run", action="store_true", help="Transform only; don't write")
    args = p.parse_args(argv)

    if not args.path.exists():
        logger.error("file not found: %s", args.path)
        return 2

    result = transform(args.path)
    logger.info(
        "gem: parsed %d rows; %d kept, %d filtered (non-VEN), %d skipped (no geometry)",
        result.total_rows,
        len(result.records),
        result.skipped_filter,
        result.skipped_no_geometry,
    )

    if args.dry_run:
        for r in result.records[:10]:
            logger.info("  - %s [%s] %s", r.external_id, r.status, r.name)
        return 0

    db = SessionLocal()
    try:
        for rec in result.records:
            upsert_pipeline(db, rec)
        db.commit()
    finally:
        db.close()
    logger.info("gem: upserted %d pipelines", len(result.records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
