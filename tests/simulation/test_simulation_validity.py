from __future__ import annotations

from datetime import datetime
import os
import random
import statistics


def _run_sim_logs(
    seed: int,
    *,
    duration_hours: float = 0.02,
    timestep_seconds: float = 0.1,
    raw_material_batch_interval_seconds: float = 1.0,
    deterministic: bool = True,
):
    from src.simulation.simulator import Simulator
    from src.mock_up.config import SimulationConfig

    cfg = SimulationConfig(
        seed=seed,
        deterministic=bool(deterministic),
        assembly_use_stochastic_duration=not bool(deterministic),
        duration_hours=float(duration_hours),
        timestep_seconds=float(timestep_seconds),
        raw_material_batch_interval_seconds=float(raw_material_batch_interval_seconds),
    )
    sim = Simulator(cfg)
    sim.run()
    return sim.logger.get_logs()


def _summarize_logs(logs):
    perf = [l for l in logs if l.get("event_type") == "performance_metric"]
    latest = perf[-1].get("details", {}) if perf else {}
    sysm = latest.get("system_metrics", {})
    logm = latest.get("logistics_metrics", {})
    return {
        "log_lines": len(logs),
        "state_changes": len([l for l in logs if l.get("event_type") == "state_change"]),
        "raw_ingress": len(
            [
                l
                for l in logs
                if l.get("event_type") == "event"
                and l.get("component_id") == "ds_1"
                and l.get("name") == "raw_batch_ingress"
            ]
        ),
        "throughput_total_units": sysm.get("throughput_total_units"),
        "throughput_uph_window": sysm.get("throughput_uph_window"),
        "lead_time_avg_s": sysm.get("lead_time_avg_s"),
        "wip_current": sysm.get("wip_current"),
        "buffer_full_count": logm.get("buffer_full_count"),
        "resource_wait_avg_s": logm.get("resource_contention_wait_avg_s"),
    }


def _print_compact_report(label, rows):
    keys = [
        "log_lines",
        "state_changes",
        "raw_ingress",
        "throughput_total_units",
        "throughput_uph_window",
        "lead_time_avg_s",
        "wip_current",
        "buffer_full_count",
        "resource_wait_avg_s",
    ]
    print("=" * 88)
    print(f"[{label}] 整理后的测试报告 / Organized test report")
    print("-" * 88)
    for row in rows:
        prefix = row.get("tag", "run")
        metrics = ", ".join(f"{k}={row.get(k)}" for k in keys)
        seed = row.get("seed")
        seed_part = f" seed={seed}," if seed is not None else ""
        print(f"[{label}] {prefix}:{seed_part} {metrics}")
    print("-" * 88)
    print(f"[{label}] Conclusion")
    for key in keys:
        vals = [row.get(key) for row in rows if row.get(key) is not None]
        nums = [float(v) for v in vals if isinstance(v, (int, float))]
        if not nums:
            print(f"[{label}] {key}: 无有效样本 / no valid samples")
            continue
        if len(nums) == 1:
            print(f"[{label}] {key}: value={nums[0]:.6g}")
            continue
        print(
            f"[{label}] {key}: min={min(nums):.6g}, max={max(nums):.6g}, "
            f"mean={statistics.mean(nums):.6g}, stdev={statistics.stdev(nums):.6g}"
        )
    print("=" * 88)


def _multi_run_params(default_runs, default_hours):
    return (
        int(os.getenv("SIM_RUNS", str(default_runs))),
        float(os.getenv("SIM_HOURS", str(default_hours))),
    )


def _random_seed():
    return random.SystemRandom().randint(1, 2_147_483_647)


def _fingerprint(logs):
    return [
        (l.get("sim_time_s"), l.get("component_id"), l.get("name"), l.get("new_state"))
        for l in logs
        if (
            l.get("event_type") == "event"
            and l.get("name") in ("station_cycle_done", "mission_assigned")
        )
        or (
            l.get("event_type") == "state_change"
            and str(l.get("component_id", "")).startswith("ds_")
            and l.get("new_state") in ("processing", "sending", "init")
        )
    ]


def test_simulation_no_invalid_states():
    """Verify: state_change logs match actual component state at end."""
    from src.simulation.simulator import Simulator
    from src.mock_up.config import SimulationConfig

    config = SimulationConfig(duration_hours=0.05, deterministic=True, assembly_use_stochastic_duration=False)
    simulator = Simulator(config)
    simulator.run()

    logs = simulator.logger.get_logs()
    state_changes = [l for l in logs if l["event_type"] == "state_change"]
    assert state_changes, "No state_change logs captured"

    # Each component may transition multiple times; only the last logged new_state must match final state.
    last_by_component = {}
    for log in state_changes:
        last_by_component[log["component_id"]] = log
    for cid, log in last_by_component.items():
        comp = simulator.system.get_component(cid)
        assert comp is not None
        assert log["new_state"] == comp.state.value, f"{cid}: log says {log['new_state']!r}, component is {comp.state.value!r}"


def test_simulation_timing_constraints_rfid_and_motor_ramp():
    """Verify: nominal RFID delay and motor ramp timing."""
    from src.simulation.simulator import Simulator
    from src.mock_up.config import SimulationConfig

    config = SimulationConfig(
        duration_hours=0.01,
        timestep_seconds=0.1,
        deterministic=True,
        assembly_use_stochastic_duration=False,
        rfid_detection_delay=0.5,
        conveyor_ramp_time=2.0,
        # 仿真总时长 0.01h=36s；间隔须 <36s 才会触发入线/Mission3 与 RFID / Total duration is 0.01h=36s; interval must be <36s to trigger ingress/Mission3 and RFID
        raw_material_batch_interval_seconds=5.0,
    )
    sim = Simulator(config)
    sim.run()
    logs = sim.logger.get_logs()

    # Motor ramp: first RAMP_UP -> RUNNING transition should be ~2.0s
    motor_changes = [
        l for l in logs if l["event_type"] == "state_change" and l["component_id"] == "conveyor_motor"
    ]
    # find first ramp_up and next running
    ramp_start = next((l for l in motor_changes if l.get("new_state") == "ramp_up"), None)
    ramp_end = None
    if ramp_start:
        for l in motor_changes:
            if l["sim_time_s"] >= ramp_start["sim_time_s"] and l.get("new_state") == "running":
                ramp_end = l
                break
    assert ramp_start and ramp_end, "Did not observe motor ramp_up -> running"
    accel = ramp_end["sim_time_s"] - ramp_start["sim_time_s"]
    assert 1.9 <= accel <= 2.1

    # RFID delay: rfid_queue idle -> identified should not happen earlier than 0.5s after detect
    detects = [l for l in logs if l["event_type"] == "event" and l["component_id"] == "rfid_queue" and l.get("name") == "rfid_queue_detect"]
    assert detects, "No RFID detect events"
    first_detect = detects[0]
    # find when rfid_queue becomes identified after that
    rfid_changes = [l for l in logs if l["event_type"] == "state_change" and l["component_id"] == "rfid_queue"]
    identified = next(
        (l for l in rfid_changes if l["sim_time_s"] >= first_detect["sim_time_s"] and l.get("new_state") == "identified"),
        None,
    )
    assert identified, "RFID never reached IDENTIFIED"
    delay = identified["sim_time_s"] - first_detect["sim_time_s"]
    assert delay >= 0.5 - 1e-6


def test_simulation_determinism_fixed_mode():
    """Verify: deterministic mode produces identical logs."""
    logs1 = _run_sim_logs(seed=42)
    logs2 = _run_sim_logs(seed=42)
    assert len(logs1) == len(logs2)
    for a, b in zip(logs1, logs2):
        # timestamps are virtual and should match
        assert a["timestamp"] == b["timestamp"]
        assert a["event_type"] == b["event_type"]
        assert a["component_id"] == b["component_id"]
        # compare key fields if present
        for k in ("old_state", "new_state", "name"):
            if k in a or k in b:
                assert a.get(k) == b.get(k)


def test_simulation_repeatability_across_multiple_runs():
    """多次运行随机 seed 仿真；仅自定义 runs / hours，并输出整理报告。 / Run random-seed simulation multiple times; customize only runs/hours and print organized report."""
    runs, hours = _multi_run_params(default_runs=6, default_hours=0.5)
    report_rows = []
    fingerprints = []
    for i in range(max(runs, 1)):
        seed = _random_seed()
        logs = _run_sim_logs(
            seed=seed,
            duration_hours=hours,
            deterministic=False,
        )
        stats = _summarize_logs(logs)
        report_rows.append({"tag": f"run={i}", "seed": seed, **stats})
        fingerprints.append(_fingerprint(logs))
        assert logs, f"run={i} produced no logs"
        assert stats["state_changes"] > 0, f"run={i} produced no state changes"
    _print_compact_report(f"random-seed-runs runs={runs} hours={hours}", report_rows)
    if len(fingerprints) > 1:
        assert len({tuple(fp) for fp in fingerprints}) >= 2


def test_simulation_repeatability_long_horizon_like_basic():
    """
    多次长时运行（对齐 basic_simulation 的小时级场景）。 / Multiple long-horizon runs aligned with hour-scale `basic_simulation` scenario.

    仅支持两个自定义参数： / Only two custom parameters are supported:
    - SIM_RUNS
    - SIM_HOURS

    每次运行 seed 自动随机。 / Seed is randomized automatically for each run.
    """
    runs, hours = _multi_run_params(default_runs=3, default_hours=8.0)
    report_rows = []
    for i in range(max(runs, 1)):
        seed = _random_seed()
        logs = _run_sim_logs(
            seed=seed,
            duration_hours=hours,
            deterministic=False,
        )
        stats = _summarize_logs(logs)
        report_rows.append({"tag": f"run={i}", "seed": seed, **stats})
        assert logs, f"run={i} produced no logs"
        assert stats["state_changes"] > 0, f"run={i} produced no state changes"
    _print_compact_report(
        f"long-random-seed-runs runs={runs} hours={hours}",
        report_rows,
    )

