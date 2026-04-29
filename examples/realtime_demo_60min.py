#!/usr/bin/env python3
"""
墙钟实时演示：默认连续运行 **60 分钟真实时间**，仿真时间与墙钟 **1:1**（每步
``time.sleep(timestep_seconds)`` 后再推进 ``sim_time``）。

逻辑与 ``ws_conveyor_simulation.py`` 一致（原材料批次、名义 RFID 0.5s、DS1 流水线、
升降机编排、Buffer 满载停输送带等）。JSONL 日志默认写入单独文件，避免覆盖短时仿真日志。

运行（仓库根目录）::

    PYTHONPATH=. python3 examples/realtime_demo_60min.py

快速自检（不睡眠、仅验证能跑若干步）::

    PYTHONPATH=. python3 examples/realtime_demo_60min.py --minutes 0 --max-steps 500 --no-realtime-sleep
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import deque
from dataclasses import replace
from datetime import datetime, timedelta

from src.mock_up.config import config_normal_operation
from src.mock_up.logic import (
    RawMaterialIngressScheduler,
    build_station_processing_route,
    count_pallets_on_line,
)
from src.mock_up.components import (
    create_ws_conveyor_system,
    ConveyorMotorState,
    ElevatorPosition,
    TransferDirection,
    BufferState,
    DockingStationState,
    PneumaticState,
    RFIDState,
)


def _to_enum_value(v):
    if hasattr(v, "value"):
        return v.value
    return v


def run_realtime_demo(
    wall_minutes: float = 60.0,
    timestep_seconds: float = 0.1,
    realtime_sleep: bool = True,
    max_steps: int | None = None,
    deterministic: bool = False,
) -> None:
    dt = float(timestep_seconds)
    if dt <= 0:
        raise ValueError("timestep_seconds must be > 0")

    wm = float(wall_minutes)
    if wm <= 0:
        if max_steps is None:
            raise SystemExit("当 --minutes <= 0 时必须指定 --max-steps（用于快速自检）")
        wall_seconds = float("inf")
    else:
        wall_seconds = wm * 60.0

    base = config_normal_operation()
    config = replace(
        base,
        timestep_seconds=dt,
        log_file="data/logs/realtime_60min_demo.jsonl",
        rfid_detection_delay=0.5,
        deterministic=deterministic,
    )

    components = create_ws_conveyor_system(config)

    log_enabled = getattr(config, "log_state_changes", True)
    log_file = getattr(config, "log_file", "data/logs/realtime_60min_demo.jsonl")
    if log_enabled:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    log_fh = open(log_file, "a", encoding="utf-8") if log_enabled else None
    log_seq = 0

    sim_time = 0.0
    step = 0
    events: deque[tuple[float, str, str]] = deque(maxlen=400)
    sim_start_dt = datetime.now()

    did_start = False
    did_conveyor_started = False
    did_request_up = False
    did_request_down = False
    did_elevator_receive_ping = False
    transfer_to_ws_started_at: float | None = None
    transfer_from_ws_started_at: float | None = None
    did_transfer_to_ws = False
    did_transfer_from_ws = False
    station_order = build_station_processing_route(config)
    next_station_idx = 0
    active_station_id: int | None = None
    active_pallet_id: str | None = None

    conveyor = components["conveyor_motor"]
    elevator = components["elevator"]
    buffer = components["buffer"]
    stations = {i: components[f"ds_{i}"] for i in range(1, 7)}
    pneumatic = components["pneumatic"]
    rfid_queue = components["rfid_queue"]
    rfid_elevator = components["rfid_elevator"]

    ingress = RawMaterialIngressScheduler(
        interval_seconds=config.raw_material_batch_interval_seconds,
        pallets_per_batch=config.raw_material_pallets_per_batch,
    )

    def log_state_change(component: str, old_state, new_state, details: dict, event: str = "state_change"):
        nonlocal log_seq
        if not log_enabled or log_fh is None:
            return
        payload = {
            "timestamp": (sim_start_dt + timedelta(seconds=sim_time)).isoformat(timespec="milliseconds") + "Z",
            "wall_clock": datetime.now().isoformat(timespec="milliseconds"),
            "component": component,
            "event": event,
            "old_state": _to_enum_value(old_state),
            "new_state": _to_enum_value(new_state),
            "details": details,
            "sim_time_s": sim_time,
            "seq": log_seq,
        }
        log_seq += 1
        log_fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    prev = {
        "conveyor_motor": conveyor.state,
        "elevator_position": elevator.position,
        "buffer_state": buffer.state,
        "pneumatic_state": pneumatic.state,
        "rfid_queue_state": rfid_queue.state,
        "rfid_elevator_state": rfid_elevator.state,
    }
    for i, st in stations.items():
        prev[f"ds_{i}_state"] = st.state

    def _line_pallet_count() -> int:
        return count_pallets_on_line(components, [], config.station_numbers)

    def elapsed_from(ts):
        if isinstance(ts, datetime):
            return max((sim_start_dt + timedelta(seconds=sim_time) - ts).total_seconds(), 0.0)
        return 0.0

    wall_start = time.monotonic()
    last_status_wall = wall_start

    print("=" * 80)
    print("WS CONVEYOR — 墙钟实时演示 (REALTIME 1:1)")
    print("=" * 80)
    _wall_disp = "∞" if wall_seconds == float("inf") else f"{wall_seconds:.0f} s"
    print(f"墙钟时长:     {wall_minutes:.1f} min ({_wall_disp})")
    print(f"仿真步长:     {dt} s（与 sleep 一致 → 1:1 实时）")
    print(f"名义 RFID:    {config.rfid_detection_delay} s")
    print(f"原材料批次:   每 {config.raw_material_batch_interval_seconds:.0f} s × {config.raw_material_pallets_per_batch} 托盘")
    print(
        f"装配:         {config.assembly_time_min_seconds:.0f}–{config.assembly_time_max_seconds:.0f} s "
        f"({'随机' if config.assembly_use_stochastic_duration and not config.deterministic else '中点'})"
    )
    print(f"状态 JSONL:   {log_file}")
    print(f"实时睡眠:     {realtime_sleep}")
    print(f"工位路线:     WS{config.ws_ingress_station}(ingress) -> {station_order} -> WS{config.ws_egress_station}(egress)")
    print(f"托盘长度:     {config.pallet_length_m:.2f} m")
    print("=" * 80)
    print()

    try:
        while True:
            if max_steps is not None and step >= max_steps:
                break
            wall_now = time.monotonic()
            if wall_seconds != float("inf") and wall_now - wall_start >= wall_seconds:
                break

            step += 1

            for rid in ingress.tick(
                sim_time,
                stations[1],
                max_pallets_on_line=config.max_pallets_on_line,
                get_pallet_count=_line_pallet_count,
            ):
                events.append((sim_time, "RAW_BATCH_INGRESS", f"Mission 3 accepted for {rid}"))

            if (
                buffer.pallet_at_queue
                and buffer.pallet_rfid_at_queue
                and rfid_queue.state == RFIDState.IDLE
            ):
                if rfid_queue.detect(buffer.pallet_rfid_at_queue):
                    events.append(
                        (sim_time, "RFID_QUEUE_DETECT", f"tag={buffer.pallet_rfid_at_queue}"),
                    )

            if not did_start and sim_time >= 0.0:
                events.append((sim_time, "SIM_START", "Simulation begins"))
                pneumatic.enable()
                events.append((sim_time, "PNEUMATIC_ENABLE", "Air supply activated"))
                did_start = True

            if (
                sim_time >= 3.0
                and conveyor.state == ConveyorMotorState.IDLE
                and not did_conveyor_started
            ):
                conveyor.start(speed_percent=50.0)
                events.append((sim_time, "CONVEYOR_START", "Conveyor started at 50% speed"))
                did_conveyor_started = True

            # Buffer 出队后轮流分配到当前产线组装工位（WS2/3/5/6）。
            if (
                active_station_id is None
                and buffer.pallet_at_queue
                and rfid_queue.state.value == "identified"
            ):
                target_station_id = station_order[next_station_idx]
                target_station = stations[target_station_id]
                if target_station.state == DockingStationState.INIT:
                    rid = buffer.pallet_rfid_at_queue
                    buffer.pallet_leaves()
                    target_station.pallet_arrived(rid)
                    rfid_queue.clear()
                    rfid_elevator.detect(rid)
                    mission = "2"
                    if target_station.accept_mission(mission):
                        active_station_id = target_station_id
                        active_pallet_id = rid
                        next_station_idx = (next_station_idx + 1) % len(station_order)
                        events.append(
                            (
                                sim_time,
                                "MISSION_ASSIGNED",
                                f"{rid} → DS{target_station_id} Mission {mission}",
                            ),
                        )
                    else:
                        events.append(
                            (
                                sim_time,
                                "MISSION_ASSIGN_FAILED",
                                f"{rid} failed at DS{target_station_id} Mission {mission}",
                            ),
                        )

            active_station = stations.get(active_station_id) if active_station_id is not None else None
            if (
                active_station is not None
                and not did_elevator_receive_ping
                and active_station.state == DockingStationState.RECEIVING
                and elevator.position == ElevatorPosition.DOWN
            ):
                elevator.request_down()
                events.append(
                    (
                        sim_time,
                        "ELEVATOR_DOWN",
                        f"Elevator at lower position (receive DS{active_station_id})",
                    ),
                )
                did_elevator_receive_ping = True

            if (
                active_station is not None
                and not did_request_up
                and elevator.position == ElevatorPosition.DOWN
                and active_station.state == DockingStationState.PROCESSING
            ):
                # 防止上/下行锁存互冲
                elevator.up_requested = False
                elevator.down_requested = False
                elevator.request_up()
                events.append((sim_time, "ELEVATOR_UP", f"Elevator moving to UP for DS{active_station_id}"))
                did_request_up = True

            if (
                active_station is not None
                and active_station.state == DockingStationState.PROCESSING
                and elevator.position == ElevatorPosition.UP
                and not elevator.transfer_running
                and transfer_to_ws_started_at is None
                and not did_transfer_to_ws
            ):
                if elevator.start_transfer(TransferDirection.TO_WS):
                    transfer_to_ws_started_at = sim_time
                    events.append((sim_time, "ELEVATOR_XFER_TO_WS_START", f"DS{active_station_id}"))

            if (
                transfer_to_ws_started_at is not None
                and elevator.transfer_running
                and sim_time - transfer_to_ws_started_at >= elevator.transfer_time
            ):
                elevator.stop_transfer()
                events.append((sim_time, "ELEVATOR_XFER_TO_WS_STOP", f"elapsed={elevator.transfer_time:.1f}s"))
                transfer_to_ws_started_at = None
                did_transfer_to_ws = True

            if (
                active_station is not None
                and not did_request_down
                and elevator.position == ElevatorPosition.UP
                and active_station.state in (
                    DockingStationState.SENDING,
                    DockingStationState.CLEANUP,
                    DockingStationState.INIT,
                )
                and did_transfer_to_ws
            ):
                elevator.up_requested = False
                elevator.down_requested = False
                elevator.request_down()
                events.append(
                    (
                        sim_time,
                        "ELEVATOR_DOWN",
                        f"Elevator returning DOWN for DS{active_station_id}",
                    ),
                )
                did_request_down = True

            if (
                active_station is not None
                and active_station.state == DockingStationState.SENDING
                and elevator.position == ElevatorPosition.DOWN
                and not elevator.transfer_running
                and transfer_from_ws_started_at is None
                and not did_transfer_from_ws
            ):
                if elevator.start_transfer(TransferDirection.FROM_WS):
                    transfer_from_ws_started_at = sim_time
                    events.append((sim_time, "ELEVATOR_XFER_FROM_WS_START", f"DS{active_station_id}"))

            if (
                transfer_from_ws_started_at is not None
                and elevator.transfer_running
                and sim_time - transfer_from_ws_started_at >= elevator.transfer_time
            ):
                elevator.stop_transfer()
                events.append(
                    (sim_time, "ELEVATOR_XFER_FROM_WS_STOP", f"elapsed={elevator.transfer_time:.1f}s"),
                )
                transfer_from_ws_started_at = None
                did_transfer_from_ws = True

            conveyor.update(elapsed_from(conveyor.transition_start_time))
            elevator.update(elapsed_from(elevator.transition_start_time))
            buffer.update(elapsed_from(buffer.transition_start_time))
            pneumatic.update(elapsed_from(pneumatic.transition_start_time))
            rfid_queue.update(elapsed_from(rfid_queue.detect_start_time))
            rfid_elevator.update(elapsed_from(rfid_elevator.detect_start_time))
            for station in stations.values():
                station.update(elapsed_from(station.transition_start_time))

            # 当前活跃工位完成一个完整循环后，释放占用并准备下一托盘。
            if active_station_id is not None:
                finished_station = stations[active_station_id]
                if (
                    finished_station.state == DockingStationState.INIT
                    and not finished_station.pallet_present
                    and not finished_station.pallet_at_ws
                ):
                    events.append(
                        (
                            sim_time,
                            "STATION_CYCLE_DONE",
                            f"DS{active_station_id} finished pallet {active_pallet_id}",
                        ),
                    )
                    if active_pallet_id is not None and rfid_elevator.tag_detected == active_pallet_id:
                        rfid_elevator.clear()
                    active_station_id = None
                    active_pallet_id = None
                    did_request_up = False
                    did_request_down = False
                    did_elevator_receive_ping = False
                    transfer_to_ws_started_at = None
                    transfer_from_ws_started_at = None
                    did_transfer_to_ws = False
                    did_transfer_from_ws = False

            if log_enabled:
                if prev["conveyor_motor"] != conveyor.state:
                    log_state_change(
                        "conveyor_motor",
                        prev["conveyor_motor"],
                        conveyor.state,
                        {
                            "current_speed_percent": conveyor.current_speed_percent,
                            "is_malfunctioning": getattr(conveyor, "is_malfunctioning", False),
                        },
                    )
                    prev["conveyor_motor"] = conveyor.state

                if prev["elevator_position"] != elevator.position:
                    log_state_change(
                        "elevator",
                        prev["elevator_position"],
                        elevator.position,
                        {
                            "transfer_running": elevator.transfer_running,
                            "transfer_direction": _to_enum_value(elevator.transfer_direction),
                        },
                    )
                    prev["elevator_position"] = elevator.position

                if prev["buffer_state"] != buffer.state:
                    log_state_change(
                        "buffer",
                        prev["buffer_state"],
                        buffer.state,
                        {
                            "pallet_count": buffer.pallet_count,
                            "pallet_at_queue": buffer.pallet_at_queue,
                            "pallet_rfid_at_queue": buffer.pallet_rfid_at_queue,
                            "is_transferring": buffer.is_transferring,
                            "transfer_direction": buffer.transfer_direction,
                        },
                    )
                    prev["buffer_state"] = buffer.state

                if prev["pneumatic_state"] != pneumatic.state:
                    log_state_change(
                        "pneumatic_system",
                        prev["pneumatic_state"],
                        pneumatic.state,
                        {
                            "current_pressure_bar": pneumatic.current_pressure_bar,
                            "current_flow_nm3h": pneumatic.current_flow_nm3h,
                            "is_enabled": pneumatic.is_enabled,
                        },
                    )
                    prev["pneumatic_state"] = pneumatic.state

                if prev["rfid_queue_state"] != rfid_queue.state:
                    log_state_change(
                        "rfid_queue",
                        prev["rfid_queue_state"],
                        rfid_queue.state,
                        {"tag_detected": rfid_queue.tag_detected},
                    )
                    prev["rfid_queue_state"] = rfid_queue.state

                if prev["rfid_elevator_state"] != rfid_elevator.state:
                    log_state_change(
                        "rfid_elevator",
                        prev["rfid_elevator_state"],
                        rfid_elevator.state,
                        {"tag_detected": rfid_elevator.tag_detected},
                    )
                    prev["rfid_elevator_state"] = rfid_elevator.state

                for i, st in stations.items():
                    key = f"ds_{i}_state"
                    if prev.get(key) != st.state:
                        log_state_change(
                            f"ds_{i}",
                            prev.get(key),
                            st.state,
                            {
                                "pallet_present": st.pallet_present,
                                "pallet_at_ws": st.pallet_at_ws,
                                "pallet_rfid": st.pallet_rfid,
                                "current_mission": st.current_mission,
                            },
                        )
                        prev[key] = st.state

            if pneumatic.current_pressure_bar > pneumatic.max_pressure_bar:
                events.append(
                    (
                        sim_time,
                        "PRESSURE_HIGH",
                        f"Pressure {pneumatic.current_pressure_bar:.1f} bar",
                    ),
                )

            if buffer.state == BufferState.FULL:
                if conveyor.state != ConveyorMotorState.IDLE:
                    conveyor.stop()
                    events.append((sim_time, "BUFFER_FULL", "Conveyor stopped - buffer at capacity"))
            elif did_conveyor_started and conveyor.state == ConveyorMotorState.IDLE:
                # 缓冲不满时允许恢复运行，避免长时 demo 因一次满载后全线静止。
                conveyor.start(speed_percent=50.0)
                events.append((sim_time, "CONVEYOR_RESTART", "Conveyor resumed at 50% speed"))

            sim_time += dt

            wall_now = time.monotonic()
            if wall_now - last_status_wall >= 60.0:
                w_elapsed = wall_now - wall_start
                ds_states = " ".join(f"{i}:{stations[i].state.value[:4]}" for i in range(1, 7))
                print(
                    f"[墙钟 {w_elapsed / 60.0:5.1f} min] 仿真 t={sim_time:8.1f}s | "
                    f"active=DS{active_station_id or '-'} | ds={ds_states} | "
                    f"buffer n={buffer.pallet_count} q={buffer.pallet_rfid_at_queue} | "
                    f"press={pneumatic.current_pressure_bar:4.2f}bar"
                )
                last_status_wall = wall_now

            if realtime_sleep:
                time.sleep(dt)

    finally:
        if log_fh is not None:
            log_fh.close()

    wall_elapsed = time.monotonic() - wall_start
    print()
    print("=" * 80)
    print("演示结束")
    print("=" * 80)
    print(f"墙钟实际:     {wall_elapsed / 60.0:.2f} min ({wall_elapsed:.1f} s)")
    print(f"仿真推进:     {sim_time:.1f} s")
    print(f"步数:         {step}")
    print("工位状态:")
    for sid in range(1, 7):
        st = stations[sid]
        print(
            f"  DS{sid}: {st.state.value:16} pallet={st.pallet_rfid or 'None':12} "
            f"mission={st.current_mission or 'None'}"
        )
    print(f"Buffer:       {buffer.state.value} n={buffer.pallet_count} queue={buffer.pallet_rfid_at_queue}")
    print(f"末事件(最多 {len(events)} 条缓存):")
    for ts, et, msg in list(events)[-12:]:
        print(f"  sim {ts:8.1f}s  [{et}] {msg}")
    print("=" * 80)


def main() -> None:
    p = argparse.ArgumentParser(description="墙钟 1:1 实时 WS 输送演示（默认 60 分钟）")
    p.add_argument(
        "--minutes",
        type=float,
        default=60.0,
        help="墙钟运行时长（分钟），默认 60",
    )
    p.add_argument(
        "--timestep",
        type=float,
        default=0.1,
        help="仿真步长 = 每次 sleep 秒数，默认 0.1（与 config 一致）",
    )
    p.add_argument(
        "--no-realtime-sleep",
        action="store_true",
        help="不调用 time.sleep（用于快速测试；墙钟条件仍由 max-steps 或 minutes 控制）",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="最多执行多少仿真步后退出（可选；与 minutes 同时满足先到达者生效）",
    )
    p.add_argument(
        "--deterministic",
        action="store_true",
        help="装配时间为 (min+max)/2 固定值，便于复现（默认关闭 → 2–15min 随机）",
    )
    args = p.parse_args()
    run_realtime_demo(
        wall_minutes=args.minutes,
        timestep_seconds=args.timestep,
        realtime_sleep=not args.no_realtime_sleep,
        max_steps=args.max_steps,
        deterministic=args.deterministic,
    )


if __name__ == "__main__":
    main()
