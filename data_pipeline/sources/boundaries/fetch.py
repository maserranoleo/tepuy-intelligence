"""Fetch the Natural Earth admin-0 polygon for Venezuela.

Downloads the world admin-0 countries dataset from a public mirror,
extracts the Venezuela feature, and writes a single-feature GeoJSON to
`frontend/public/data/venezuela.geojson`. Overwrites the hand-traced
approximation that ships with the repo.

Natural Earth is public domain; the mirror at
github.com/martynafford/natural-earth-geojson is a community-maintained
GeoJSON conversion. The 1:50m scale strikes a good balance between
fidelity and file size for our country-mask use case (typically a few
hundred vertices for VEN).

Run:
    make fetch-boundaries

Or directly:
    PYTHONPATH=backend:. backend/.venv/bin/python \
        -m data_pipeline.sources.boundaries.fetch
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import httpx

logger = logging.getLogger("boundaries")
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

DEFAULT_URL = (
    "https://raw.githubusercontent.com/martynafford/natural-earth-geojson/"
    "master/50m/cultural/ne_50m_admin_0_countries.json"
)

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "data" / "venezuela.geojson"


def _find_venezuela(fc: dict) -> dict | None:
    """Search the FeatureCollection for the VEN feature, robust to
    Natural Earth's casing changes across versions."""
    keys = ("ADM0_A3", "ISO_A3", "iso_a3", "ADM0_ISO", "SOV_A3", "sov_a3")
    for f in fc.get("features", []):
        props = f.get("properties", {}) or {}
        for k in keys:
            if props.get(k) == "VEN":
                return f
    return None


def fetch(url: str = DEFAULT_URL) -> dict:
    logger.info("boundaries: GET %s", url)
    r = httpx.get(url, timeout=180.0, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def extract_polygon(feature: dict) -> dict:
    """Extract the Venezuelan mainland polygon. NE delivers a MultiPolygon
    when offshore islands are included; we keep the largest polygon (the
    mainland) and drop the others — they don't matter for the mask."""
    geom = feature.get("geometry", {})
    if geom.get("type") == "Polygon":
        return geom
    if geom.get("type") == "MultiPolygon":
        polygons = geom.get("coordinates", [])
        if not polygons:
            raise ValueError("MultiPolygon has no coordinates")
        # Pick the largest by outer-ring vertex count (proxy for area).
        biggest = max(polygons, key=lambda p: len(p[0]))
        return {"type": "Polygon", "coordinates": biggest}
    raise ValueError(f"unsupported geometry type: {geom.get('type')}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--url", default=DEFAULT_URL, help="GeoJSON source URL")
    p.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Path to write the single-feature GeoJSON",
    )
    args = p.parse_args(argv)

    fc = fetch(args.url)
    feature = _find_venezuela(fc)
    if feature is None:
        print(
            "ERROR: VEN feature not found in dataset. The source schema may "
            "have changed; inspect properties keys and update _find_venezuela.",
            file=sys.stderr,
        )
        return 2

    polygon = extract_polygon(feature)
    n_vertices = len(polygon["coordinates"][0])

    output_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "iso_a3": "VEN",
                    "name": "Venezuela",
                    "name_es": "República Bolivariana de Venezuela",
                    "fidelity": "natural-earth-50m",
                    "fidelity_note": (
                        f"Fetched from {args.url} ({n_vertices} vertices). "
                        "Replace via `make fetch-boundaries` if Natural Earth "
                        "publishes an updated version."
                    ),
                },
                "geometry": polygon,
            }
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output_fc, separators=(",", ":")))
    msg = f"boundaries: wrote {args.output} ({n_vertices} vertices)"
    logger.info(msg)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
