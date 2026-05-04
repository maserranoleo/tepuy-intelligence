"""Tiny smoke test for the GEM transform.

Runs without pytest: `python -m data_pipeline.sources.gem.test_transform_smoke`.
Builds a synthetic Excel matching GEM's general shape (header names are
substring-matched by transform()) and asserts filtering + normalization.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

from data_pipeline.sources.gem.transform import transform


def main() -> int:
    df = pd.DataFrame(
        [
            # Wholly inside Venezuela; should pass
            {
                "Pipeline ID": "GGIT-001",
                "Pipeline Name": "Anaco-Caracas",
                "Status": "Operating",
                "Countries": "Venezuela",
                "Start Country": "Venezuela",
                "End Country": "Venezuela",
                "Start Lat": 9.43, "Start Lon": -64.47,
                "End Lat": 10.48, "End Lon": -66.90,
                "Length (km)": 400,
                "Diameter": 30,
                "Capacity": 520,
                "Operator": "PDVSA Gas",
                "WKT": None,
            },
            # Cross-border VEN↔CO; should pass
            {
                "Pipeline ID": "GGIT-002",
                "Pipeline Name": "Antonio Ricaurte",
                "Status": "Mothballed",
                "Countries": "Venezuela; Colombia",
                "Start Country": "Colombia",
                "End Country": "Venezuela",
                "Start Lat": 11.95, "Start Lon": -71.27,
                "End Lat": 10.64, "End Lon": -71.61,
                "Length (km)": 225,
                "Diameter": 26,
                "Capacity": 500,
                "Operator": "Promigas",
                "WKT": None,
            },
            # Wholly Brazil; should be filtered out
            {
                "Pipeline ID": "GGIT-003",
                "Pipeline Name": "Bolivia-Brazil",
                "Status": "Operating",
                "Countries": "Brazil; Bolivia",
                "Start Country": "Bolivia",
                "End Country": "Brazil",
                "Start Lat": -17.78, "Start Lon": -63.18,
                "End Lat": -23.55, "End Lon": -46.63,
                "Length (km)": 3150,
                "Diameter": 32,
                "Capacity": 1100,
                "Operator": "TBG",
                "WKT": None,
            },
            # No geometry; should be skipped
            {
                "Pipeline ID": "GGIT-004",
                "Pipeline Name": "Phantom",
                "Status": "Proposed",
                "Countries": "Venezuela",
                "Start Country": "Venezuela",
                "End Country": "Venezuela",
                "Start Lat": None, "Start Lon": None,
                "End Lat": None, "End Lon": None,
                "Length (km)": None, "Diameter": None,
                "Capacity": None, "Operator": None, "WKT": None,
            },
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ggit-fixture.xlsx"
        with pd.ExcelWriter(path) as w:
            df.to_excel(w, sheet_name="Pipelines", index=False)
        result = transform(path)

    assert result.total_rows == 4, result
    assert len(result.records) == 2, [(r.external_id, r.name) for r in result.records]
    assert result.skipped_filter == 1, result
    assert result.skipped_no_geometry == 1, result

    by_id = {r.external_id: r for r in result.records}
    assert by_id["GGIT-001"].status == "operating"
    assert by_id["GGIT-002"].status == "idle"  # mothballed → idle
    assert by_id["GGIT-002"].diameter_in == 26
    print("OK: gem transform smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
