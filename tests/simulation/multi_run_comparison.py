#!/usr/bin/env python3
"""
多次运行基准仿真，汇总并比较指标，写入 XML（默认 data/logs），终端打印摘要。 / Run baseline simulation multiple times, aggregate/compare metrics, write XML (default `data/logs`), and print summary.

运行（仓库根目录）:: / Run from repository root::

    PYTHONPATH=. python3 tests/simulation/multi_run_comparison.py
    PYTHONPATH=. python3 tests/simulation/multi_run_comparison.py --runs 8 --hours 0.1 --output data/logs/my_compare.xml
"""

from __future__ import annotations

import argparse
import os
import statistics
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.mock_up.config import config_normal_operation
from src.simulation.simulator import Simulator


def _final_metrics_from_logs(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    perf = [e for e in logs if e.get("event_type") == "performance_metric"]
    if not perf:
        return {}
    return perf[-1].get("details") or {}


def _scalar_metrics(details: Dict[str, Any]) -> Dict[str, Optional[float]]:
    sysm = details.get("system_metrics") or {}
    logm = details.get("logistics_metrics") or {}
    out: Dict[str, Optional[float]] = {}

    def num(x: Any) -> Optional[float]:
        if x is None:
            return None
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    out["throughput_total_units"] = num(sysm.get("throughput_total_units"))
    out["throughput_uph_window"] = num(sysm.get("throughput_uph_window"))
    out["lead_time_avg_s"] = num(sysm.get("lead_time_avg_s"))
    out["lead_time_samples"] = num(sysm.get("lead_time_samples"))
    out["wip_current"] = num(sysm.get("wip_current"))
    out["wip_avg_sampled"] = num(sysm.get("wip_avg_sampled"))
    out["buffer_full_count"] = num(logm.get("buffer_full_count"))
    out["buffer_occupancy_avg"] = num(logm.get("buffer_occupancy_avg"))
    out["resource_wait_avg_s"] = num(logm.get("resource_contention_wait_avg_s"))
    out["resource_wait_total_s"] = num(logm.get("resource_contention_wait_total_s"))
    return out


def _event_counts(logs: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "log_lines": len(logs),
        "state_changes": len([e for e in logs if e.get("event_type") == "state_change"]),
        "performance_snapshots": len([e for e in logs if e.get("event_type") == "performance_metric"]),
        "ws6_station_cycle_done": len(
            [
                e
                for e in logs
                if e.get("event_type") == "event"
                and e.get("component_id") == "ds_6"
                and e.get("name") == "station_cycle_done"
            ]
        ),
        "raw_batch_ingress": len(
            [
                e
                for e in logs
                if e.get("event_type") == "event"
                and e.get("component_id") == "ds_1"
                and e.get("name") == "raw_batch_ingress"
            ]
        ),
    }


def run_single(
    *,
    duration_hours: float,
    timestep_seconds: float,
    seed: int,
    deterministic: bool,
    raw_interval: float,
    snapshot_interval: float,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    base = config_normal_operation()
    config = replace(
        base,
        duration_hours=float(duration_hours),
        timestep_seconds=float(timestep_seconds),
        seed=int(seed),
        deterministic=bool(deterministic),
        assembly_use_stochastic_duration=not bool(deterministic),
        raw_material_batch_interval_seconds=float(raw_interval),
        snapshot_interval_seconds=float(snapshot_interval),
    )
    sim = Simulator(config)
    sim.run()
    logs = sim.logger.get_logs()
    details = _final_metrics_from_logs(logs)
    scalars = _scalar_metrics(details)
    counts = _event_counts(logs)
    row: Dict[str, Any] = {
        "seed": seed,
        "deterministic": deterministic,
        "details": details,
        **scalars,
        **{f"count_{k}": float(v) for k, v in counts.items()},
    }
    return row, counts


def aggregate_numeric(rows: List[Dict[str, Any]], keys: List[str]) -> Dict[str, Dict[str, float]]:
    agg: Dict[str, Dict[str, float]] = {}
    for key in keys:
        vals = [rows[i][key] for i in range(len(rows)) if rows[i].get(key) is not None]
        nums = [float(v) for v in vals]
        if not nums:
            agg[key] = {"min": float("nan"), "max": float("nan"), "mean": float("nan"), "stdev": float("nan"), "n": 0.0}
            continue
        stdev = statistics.stdev(nums) if len(nums) > 1 else 0.0
        agg[key] = {
            "min": min(nums),
            "max": max(nums),
            "mean": statistics.mean(nums),
            "stdev": stdev,
            "n": float(len(nums)),
        }
    return agg


def build_xml(
    *,
    rows: List[Dict[str, Any]],
    aggregate: Dict[str, Dict[str, float]],
    meta: Dict[str, Any],
) -> str:
    root = ET.Element("multi_run_comparison")
    root.set("generated_at_utc", datetime.now(timezone.utc).isoformat())
    meta_el = ET.SubElement(root, "meta")
    for k, v in meta.items():
        meta_el.set(k, str(v))

    runs_el = ET.SubElement(root, "runs")
    metric_keys = [
        "throughput_total_units",
        "throughput_uph_window",
        "lead_time_avg_s",
        "wip_current",
        "buffer_full_count",
        "resource_wait_avg_s",
    ]
    count_keys: List[str] = []
    if rows:
        count_keys = sorted({k for r in rows for k in r if k.startswith("count_")})

    for i, row in enumerate(rows):
        run_el = ET.SubElement(runs_el, "run")
        run_el.set("index", str(i))
        run_el.set("seed", str(row.get("seed", "")))
        ET.SubElement(run_el, "deterministic").text = str(row.get("deterministic", ""))
        for mk in metric_keys:
            v = row.get(mk)
            child = ET.SubElement(run_el, mk)
            child.text = "" if v is None else f"{v:.6g}"
        for ck in sorted(count_keys):
            v = row.get(ck)
            child = ET.SubElement(run_el, ck)
            child.text = str(int(v)) if v is not None else ""

    agg_el = ET.SubElement(root, "aggregate")
    for key, stats in sorted(aggregate.items()):
        s_el = ET.SubElement(agg_el, "stat")
        s_el.set("metric", key)
        for sk, sv in stats.items():
            if sk == "n":
                s_el.set(sk, str(int(sv)))
            else:
                s_el.set(sk, f"{sv:.6g}" if sv == sv else "nan")  # NaN check

    # Pretty-print via minidom is optional; ElementTree tostring is enough
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def print_terminal_summary(rows: List[Dict[str, Any]], aggregate: Dict[str, Dict[str, float]]) -> None:
    print("=" * 72)
    print("多次运行比较 — 关键指标 / Multi-run comparison - key metrics")
    print("=" * 72)
    for i, row in enumerate(rows):
        print(
            f"  Run {i}: seed={row.get('seed')}  "
            f"throughput={row.get('throughput_total_units')}  "
            f"UPH≈{row.get('throughput_uph_window')}  "
            f"lead_avg_s={row.get('lead_time_avg_s')}  "
            f"raw_ingress={int(row.get('count_raw_batch_ingress') or 0)}"
        )
    print("-" * 72)
    print("  跨运行聚合 (min / max / mean / stdev) / Cross-run aggregate")
    for key in (
        "throughput_total_units",
        "throughput_uph_window",
        "lead_time_avg_s",
        "buffer_full_count",
        "resource_wait_avg_s",
    ):
        if key not in aggregate:
            continue
        a = aggregate[key]
        if int(a["n"]) == 0:
            print(f"  {key:28s}  (无有效样本 / no valid samples)")
            continue
        print(
            f"  {key:28s}  min={a['min']:.4g}  max={a['max']:.4g}  "
            f"mean={a['mean']:.4g}  stdev={a['stdev']:.4g}  (n={int(a['n'])})"
        )
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run simulator multiple times and compare metrics (XML report).")
    parser.add_argument("--runs", type=int, default=5, help="Number of simulation runs (default: 5)")
    parser.add_argument("--hours", type=float, default=0.08, help="Simulated hours per run (default: 0.08)")
    parser.add_argument("--timestep", type=float, default=0.1, help="Timestep seconds (default: 0.1)")
    parser.add_argument("--seed-base", type=int, default=1000, help="First seed; run i uses seed_base+i (default: 1000)")
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Deterministic assembly (all runs identical if same config)",
    )
    parser.add_argument("--raw-interval", type=float, default=120.0, help="Raw material batch interval (s)")
    parser.add_argument("--snapshot-interval", type=float, default=60.0, help="Metrics snapshot interval (s)")
    parser.add_argument(
        "--output",
        type=str,
        default="data/logs/multi_run_comparison.xml",
        help="Output XML path (default: data/logs/multi_run_comparison.xml)",
    )
    args = parser.parse_args()

    n = max(1, int(args.runs))
    rows: List[Dict[str, Any]] = []
    for i in range(n):
        seed = int(args.seed_base) + i
        row, _ = run_single(
            duration_hours=float(args.hours),
            timestep_seconds=float(args.timestep),
            seed=seed,
            deterministic=bool(args.deterministic),
            raw_interval=float(args.raw_interval),
            snapshot_interval=float(args.snapshot_interval),
        )
        rows.append(row)

    keys = [
        "throughput_total_units",
        "throughput_uph_window",
        "lead_time_avg_s",
        "wip_current",
        "buffer_full_count",
        "buffer_occupancy_avg",
        "resource_wait_avg_s",
        "count_raw_batch_ingress",
        "count_ws6_station_cycle_done",
    ]
    aggregate = aggregate_numeric(rows, keys)

    meta = {
        "runs": n,
        "duration_hours": args.hours,
        "timestep_seconds": args.timestep,
        "seed_base": args.seed_base,
        "deterministic": str(bool(args.deterministic)),
        "raw_interval_seconds": args.raw_interval,
        "snapshot_interval_seconds": args.snapshot_interval,
    }
    xml_text = build_xml(rows=rows, aggregate=aggregate, meta=meta)

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="utf-8"?>\n')
        fh.write(xml_text)
        fh.write("\n")

    print_terminal_summary(rows, aggregate)
    print(f"XML 报告已写入 / XML report written: {out_path}")


if __name__ == "__main__":
    main()
