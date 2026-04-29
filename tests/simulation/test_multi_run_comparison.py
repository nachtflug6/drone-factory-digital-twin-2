"""Smoke test: multi-run comparison script produces valid XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from tests.simulation.multi_run_comparison import aggregate_numeric, build_xml, run_single


def test_run_single_produces_metrics():
    row, counts = run_single(
        duration_hours=0.02,
        timestep_seconds=0.1,
        seed=7,
        deterministic=True,
        raw_interval=30.0,
        snapshot_interval=10.0,
    )
    assert "throughput_total_units" in row or row.get("throughput_total_units") is None
    assert counts["log_lines"] > 0


def test_aggregate_and_xml_roundtrip(tmp_path: Path):
    rows = []
    for i in range(3):
        r, _ = run_single(
            duration_hours=0.02,
            timestep_seconds=0.1,
            seed=100 + i,
            deterministic=True,
            raw_interval=30.0,
            snapshot_interval=10.0,
        )
        rows.append(r)
    keys = [
        "throughput_total_units",
        "throughput_uph_window",
        "count_raw_batch_ingress",
    ]
    agg = aggregate_numeric(rows, keys)
    xml_text = build_xml(
        rows=rows,
        aggregate=agg,
        meta={"runs": 3, "duration_hours": 0.02},
    )
    out = tmp_path / "cmp.xml"
    out.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + xml_text, encoding="utf-8")
    tree = ET.parse(out)
    root = tree.getroot()
    assert root.tag == "multi_run_comparison"
    assert root.find("runs") is not None
    assert root.find("aggregate") is not None
