#!/usr/bin/env python3
"""
Basic simulation smoke test for current project state.

Run:
    PYTHONPATH=. python3 examples/basic_simulation.py
    PYTHONPATH=. python3 examples/basic_simulation.py --hours 0.5 --raw-interval 60 --deterministic
    PYTHONPATH=. python3 examples/basic_simulation.py --seed 12345
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from dataclasses import replace
from typing import Any, Dict

from src.mock_up.config import config_normal_operation
from src.simulation.simulator import Simulator


def _format_event(event: Dict[str, Any]) -> str:
    sim_time_s = float(event.get("sim_time_s", 0.0))
    h = int(sim_time_s // 3600)
    m = int((sim_time_s % 3600) // 60)
    s = int(sim_time_s % 60)
    prefix = f"[SIM {h:02d}:{m:02d}:{s:02d}] [{event.get('event_type')}] [{event.get('component_id')}]"
    if event.get("event_type") == "state_change":
        return f"{prefix} {event.get('old_state')} -> {event.get('new_state')}"
    if event.get("event_type") == "performance_metric":
        details = event.get("details", {})
        sysm = details.get("system_metrics", {})
        return (
            f"{prefix} metrics "
            f"throughput={sysm.get('throughput_total_units')} "
            f"lead_avg_s={sysm.get('lead_time_avg_s')} "
            f"wip={sysm.get('wip_current')}"
        )
    name = event.get("name")
    if name:
        return f"{prefix} {name}"
    return prefix


def main() -> None:
    parser = argparse.ArgumentParser(description="Run current baseline simulator with configurable horizon.")
    parser.add_argument("--hours", type=float, default=8.0, help="Simulation horizon in hours (default: 8.0)")
    parser.add_argument("--timestep", type=float, default=0.1, help="Simulation timestep in seconds")
    parser.add_argument("--raw-interval", type=float, default=600.0, help="Raw material batch interval (seconds)")
    parser.add_argument("--snapshot-interval", type=float, default=60.0, help="Metric snapshot interval (seconds)")
    parser.add_argument("--deterministic", action="store_true", help="Use deterministic assembly duration")
    parser.add_argument(
        "--assembly-dist",
        type=str,
        default="truncated_exponential",
        choices=["truncated_exponential", "uniform", "deterministic"],
        help="Assembly duration distribution",
    )
    parser.add_argument("--assembly-min", type=float, default=120.0, help="Assembly duration min seconds")
    parser.add_argument("--assembly-max", type=float, default=900.0, help="Assembly duration max seconds")
    parser.add_argument(
        "--assembly-exp-scale",
        type=float,
        default=180.0,
        help="Assembly exponential scale seconds (for truncated_exponential)",
    )
    parser.add_argument("--worker-efficiency", type=float, default=1.0, help="Constant worker efficiency in this run")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Simulation RNG seed (default: random each run). Use with --deterministic for reproducible runs.",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="data/logs/basic_simulation.jsonl",
        help="Output JSONL log file path",
    )
    args = parser.parse_args()

    base = config_normal_operation()
    run_seed = int(args.seed) if args.seed is not None else secrets.randbelow(2_147_483_647) + 1
    config = replace(
        base,
        seed=run_seed,
        duration_hours=float(args.hours),
        timestep_seconds=float(args.timestep),
        deterministic=bool(args.deterministic),
        assembly_use_stochastic_duration=not bool(args.deterministic),
        assembly_duration_distribution=str(args.assembly_dist),
        assembly_time_min_seconds=float(args.assembly_min),
        assembly_time_max_seconds=float(args.assembly_max),
        assembly_exponential_scale_seconds=float(args.assembly_exp_scale),
        worker_efficiency_base=float(args.worker_efficiency),
        raw_material_batch_interval_seconds=float(args.raw_interval),
        snapshot_interval_seconds=float(args.snapshot_interval),
        log_file=str(args.log_file),
    )

    sim = Simulator(config)
    base_log = sim.logger.log

    def _tee_log(payload: Dict[str, Any]) -> None:
        base_log(payload)
        print(_format_event(payload))

    sim.logger.log = _tee_log
    sim.run()
    logs = sim.logger.get_logs()
    os.makedirs(os.path.dirname(config.log_file) or ".", exist_ok=True)
    with open(config.log_file, "w", encoding="utf-8") as fh:
        for event in logs:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    print("=" * 80)
    print("BASIC SIMULATION RESULT")
    print(f"Simulation seed: {config.seed}")
    print(f"Sim duration (h): {config.duration_hours}")
    print(f"Timestep (s): {config.timestep_seconds}")
    print(f"Total logs: {len(logs)}")
    print(f"Log file: {config.log_file}")

    state_changes = [e for e in logs if e.get("event_type") == "state_change"]
    perf = [e for e in logs if e.get("event_type") == "performance_metric"]
    completed = [e for e in logs if e.get("name") == "station_cycle_done" and e.get("component_id") == "ds_6"]
    iface_clear = [e for e in logs if e.get("component_id") == "align_ds_6" and e.get("name") == "iface_window" and e.get("sensor_bits") == [0, 0]]

    print(f"State changes: {len(state_changes)}")
    print(f"Performance metric snapshots: {len(perf)}")
    print(f"WS6 station_cycle_done events: {len(completed)}")
    print(f"WS6 interface clear events (lead-time endpoint): {len(iface_clear)}")

    if perf:
        m = perf[-1]["details"]
        sysm = m.get("system_metrics", {})
        logm = m.get("logistics_metrics", {})
        stn = m.get("station_metrics", {})
        print("-" * 80)
        print("Latest metrics snapshot")
        print(f"Throughput total units: {sysm.get('throughput_total_units')}")
        print(f"Throughput UPH window: {sysm.get('throughput_uph_window')}")
        print(f"Lead time avg (s): {sysm.get('lead_time_avg_s')}")
        print(f"WIP current: {sysm.get('wip_current')}")
        print(f"Buffer full count: {logm.get('buffer_full_count')}")
        print(f"Resource contention wait avg (s): {logm.get('resource_contention_wait_avg_s')}")
        print("-" * 80)
        print("Per-station starvation (avg seconds per episode, cumulative / sim time)")
        for key in sorted(stn.keys(), key=lambda k: int(k.split("_")[1]) if k.startswith("ds_") else 0):
            d = stn.get(key) or {}
            avg = d.get("starvation_avg_s")
            frac = d.get("starvation_fraction_of_sim")
            tot = d.get("starvation_time_s")
            n = d.get("starvation_episodes")
            if avg is None:
                extra = f"  frac_of_sim={frac:.3f}" if isinstance(frac, (int, float)) else ""
                print(f"  {key}: avg_starvation_s=n/a  episodes={n}  total_s={tot}{extra}")
            else:
                if isinstance(frac, (int, float)):
                    print(
                        f"  {key}: avg_starvation_s={avg:.2f}  episodes={n}  "
                        f"total_s={float(tot or 0):.1f}  frac_of_sim={frac:.3f}"
                    )
                else:
                    print(
                        f"  {key}: avg_starvation_s={avg:.2f}  episodes={n}  total_s={float(tot or 0):.1f}"
                    )

    print("=" * 80)


if __name__ == "__main__":
    main()
