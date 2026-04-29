#!/usr/bin/env python3
"""
Event-driven compressed demo:
- Simulate 100 minutes of plant time
- Compress into ~1 minute wall clock (100:1)
- Print logs only when events/state changes occur (no periodic wall-clock prints)

Run:
    PYTHONPATH=. python3 examples/event_driven_demo_100min.py
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import replace
from datetime import datetime, timedelta

from src.mock_up.config import config_normal_operation
from src.mock_up.logic import (
    RawMaterialIngressScheduler,
    build_station_processing_route,
    conveyor_travel_time_ingress_to_station,
    count_pallets_on_line,
)
from src.mock_up.components import (
    create_ws_conveyor_system,
    ConveyorMotorState,
    ElevatorPosition,
    TransferDirection,
    BufferState,
    DockingStationState,
    RFIDState,
    PalletAlignmentWindow,
)


def _ev(v):
    if hasattr(v, "value"):
        return v.value
    return v


def run_event_driven_compressed_demo(
    sim_minutes: float = 100.0,
    wall_minutes: float = 1.0,
    timestep_seconds: float = 0.1,
    deterministic: bool = False,
    no_pacing: bool = False,
) -> None:
    if sim_minutes <= 0 or wall_minutes <= 0 or timestep_seconds <= 0:
        raise ValueError("sim_minutes, wall_minutes, timestep_seconds must be > 0")

    sim_total_seconds = sim_minutes * 60.0
    target_wall_seconds = wall_minutes * 60.0
    compression_ratio = sim_total_seconds / target_wall_seconds  # e.g. 100:1

    base = config_normal_operation()
    config = replace(
        base,
        duration_hours=sim_minutes / 60.0,
        timestep_seconds=timestep_seconds,
        # keep nominal RFID full timing
        rfid_detection_delay=0.5,
        deterministic=deterministic,
        log_file="data/logs/event_driven_100min_demo.jsonl",
    )
    components = create_ws_conveyor_system(config)

    os.makedirs("data/logs", exist_ok=True)
    event_log_path = config.log_file
    log_fh = open(event_log_path, "a", encoding="utf-8")

    sim_start_dt = datetime.now()
    wall_start = time.monotonic()
    sim_time = 0.0
    step = 0

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

    did_start = False
    did_conveyor_started = False
    did_request_up = False
    did_request_down = False
    did_elevator_receive_ping = False
    transfer_to_ws_started_at: float | None = None
    transfer_from_ws_started_at: float | None = None
    did_transfer_to_ws = False
    did_transfer_from_ws = False
    active_station_id: int | None = None
    active_pallet_id: str | None = None
    station_order = build_station_processing_route(config)
    next_station_idx = 0
    seq = 0
    # Buffer 放行后沿主线 + conveyor_to_ws_loading_position_m 延迟到达目标 DS
    pending_line_transfers: list[dict[str, float | int | str]] = []

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
        return count_pallets_on_line(components, pending_line_transfers, config.station_numbers)

    def elapsed_from(ts):
        if isinstance(ts, datetime):
            return max((sim_start_dt + timedelta(seconds=sim_time) - ts).total_seconds(), 0.0)
        return 0.0

    def retime_if_wall_based(obj, attr_name: str, sim_now_dt: datetime, wall_now_dt: datetime) -> None:
        """
        Components stamp transitions with datetime.now().
        In compressed-time runs, wall clock and sim clock diverge.
        If a timestamp looks wall-based (close to wall_now), map it to sim_now.
        """
        ts = getattr(obj, attr_name, None)
        if not isinstance(ts, datetime):
            return
        if abs((ts - wall_now_dt).total_seconds()) <= 2.0:
            setattr(obj, attr_name, sim_now_dt)

    def emit(event_type: str, message: str, component: str = "system") -> None:
        nonlocal seq
        payload = {
            "seq": seq,
            "sim_time_s": round(sim_time, 3),
            "sim_time_hms": f"{int(sim_time // 3600):02d}:{int((sim_time % 3600) // 60):02d}:{int(sim_time % 60):02d}",
            "event": event_type,
            "component": component,
            "message": message,
        }
        seq += 1
        print(f"[SIM {payload['sim_time_hms']}] [{event_type}] {message}")
        log_fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print("=" * 88)
    print("EVENT-DRIVEN COMPRESSED DEMO")
    print(f"Simulated: {sim_minutes:.1f} min | Target wall: {wall_minutes:.1f} min | Ratio: {compression_ratio:.1f}:1")
    print(f"RFID delay kept at full nominal: {config.rfid_detection_delay:.1f}s")
    print(f"Route: WS{config.ws_ingress_station}(ingress) -> {station_order} -> WS{config.ws_egress_station}(egress)")
    print(f"Pallet length: {config.pallet_length_m:.2f} m")
    print(
        f"Line transit model: neighbor distances + {config.conveyor_to_ws_loading_position_m:.2f} m "
        f"approach @ {config.conveyor_max_speed_ms:.2f} m/s"
    )
    print(
        "Pallet alignment: dual-sensor WINDOW centering (1,1)=in window — "
        "interlock main conveyor vs station slave belt + station-in-place"
    )
    # 各组装工位：主-从接口窗（离散演示）；间距 = 托盘边长
    iface_windows: dict[int, PalletAlignmentWindow] = {
        sid: PalletAlignmentWindow(
            id=f"ds_{sid}_main_slave_iface",
            sensor_spacing_m=config.pallet_length_m,
        )
        for sid in config.assembly_station_numbers
    }
    print(f"Log file: {event_log_path}")
    print("=" * 88)

    try:
        while sim_time < sim_total_seconds:
            step += 1

            # In-transit pallets: arrive at DS when due (simulation clock)
            still_pt: list[dict[str, float | int | str]] = []
            for item in pending_line_transfers:
                if sim_time + 1e-9 < float(item["due"]):
                    still_pt.append(item)
                    continue
                target_id = int(item["target_id"])
                rid = str(item["rid"])
                target_station = stations[target_id]
                if target_station.state != DockingStationState.INIT:
                    still_pt.append(item)
                    continue
                target_station.pallet_arrived(rid)
                rfid_elevator.detect(rid)
                mission = "2"
                if target_station.accept_mission(mission):
                    active_station_id = target_id
                    active_pallet_id = rid
                    next_station_idx = (next_station_idx + 1) % len(station_order)
                    emit(
                        "MISSION_ASSIGNED",
                        f"{rid} -> DS{target_id} Mission {mission}",
                        f"ds_{target_id}",
                    )
                    emit(
                        "LINE_TRANSIT_ARRIVED",
                        f"{rid} at DS{target_id} (transit {float(item['travel_s']):.2f} s)",
                        "conveyor",
                    )
                    w_iface = iface_windows.get(target_id)
                    if w_iface is not None:
                        w_iface.set_centered(True)
                        s1, s2 = w_iface.sensor_bits
                        emit(
                            "PALLET_WINDOW_IFACE",
                            f"DS{target_id} main/slave interface (S1,S2)=({s1},{s2}) "
                            f"window-centered | handoff_permitted={w_iface.main_slave_handoff_permitted()}",
                            f"align_ds_{target_id}",
                        )
            pending_line_transfers.clear()
            pending_line_transfers.extend(still_pt)

            for rid in ingress.tick(
                sim_time,
                stations[1],
                max_pallets_on_line=config.max_pallets_on_line,
                get_pallet_count=_line_pallet_count,
            ):
                emit("RAW_BATCH_INGRESS", f"Mission 3 accepted for {rid}", "ds_1")

            if buffer.pallet_at_queue and buffer.pallet_rfid_at_queue and rfid_queue.state == RFIDState.IDLE:
                if rfid_queue.detect(buffer.pallet_rfid_at_queue):
                    emit("RFID_QUEUE_DETECT", f"tag={buffer.pallet_rfid_at_queue}", "rfid_queue")

            if not did_start:
                pneumatic.enable()
                did_start = True
                emit("SIM_START", "Simulation begins")
                emit("PNEUMATIC_ENABLE", "Air supply activated", "pneumatic")

            if sim_time >= 3.0 and conveyor.state == ConveyorMotorState.IDLE and not did_conveyor_started:
                conveyor.start(speed_percent=50.0)
                did_conveyor_started = True
                emit("CONVEYOR_START", "Conveyor started at 50% speed", "conveyor_motor")

            if active_station_id is None and buffer.pallet_at_queue and rfid_queue.state.value == "identified":
                target_id = station_order[next_station_idx]
                target_station = stations[target_id]
                blocked = any(int(p["target_id"]) == target_id for p in pending_line_transfers)
                if target_station.state == DockingStationState.INIT and not blocked:
                    rid = buffer.pallet_rfid_at_queue
                    travel_s = conveyor_travel_time_ingress_to_station(config, target_id)
                    buffer.pallet_leaves()
                    rfid_queue.clear()
                    pending_line_transfers.append(
                        {"due": sim_time + travel_s, "target_id": target_id, "rid": rid, "travel_s": travel_s}
                    )
                    emit(
                        "LINE_TRANSIT_SCHEDULED",
                        f"{rid} -> DS{target_id} in {travel_s:.2f} s (line+{config.conveyor_to_ws_loading_position_m:.2f} m approach)",
                        "conveyor",
                    )

            active_station = stations.get(active_station_id) if active_station_id is not None else None
            if (
                active_station is not None
                and not did_elevator_receive_ping
                and active_station.state == DockingStationState.RECEIVING
                and elevator.position == ElevatorPosition.DOWN
            ):
                elevator.request_down()
                did_elevator_receive_ping = True
                emit("ELEVATOR_DOWN", f"Receive DS{active_station_id}", "elevator")

            if (
                active_station is not None
                and not did_request_up
                and elevator.position == ElevatorPosition.DOWN
                and active_station.state == DockingStationState.PROCESSING
            ):
                elevator.up_requested = False
                elevator.down_requested = False
                elevator.request_up()
                did_request_up = True
                emit("ELEVATOR_UP", f"Move to UP for DS{active_station_id}", "elevator")

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
                    emit("ELEVATOR_XFER_TO_WS_START", f"DS{active_station_id}", "elevator")

            if (
                transfer_to_ws_started_at is not None
                and elevator.transfer_running
                and sim_time - transfer_to_ws_started_at >= elevator.transfer_time
            ):
                elevator.stop_transfer()
                transfer_to_ws_started_at = None
                did_transfer_to_ws = True
                emit("ELEVATOR_XFER_TO_WS_STOP", "Transfer to WS completed", "elevator")

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
                did_request_down = True
                emit("ELEVATOR_DOWN", f"Return DOWN for DS{active_station_id}", "elevator")

            if (
                active_station is not None
                and active_station.state == DockingStationState.SENDING
                and elevator.position == ElevatorPosition.DOWN
                and not elevator.transfer_running
                and transfer_from_ws_started_at is None
                and did_transfer_to_ws
                and not did_transfer_from_ws
            ):
                if elevator.start_transfer(TransferDirection.FROM_WS):
                    transfer_from_ws_started_at = sim_time
                    emit("ELEVATOR_XFER_FROM_WS_START", f"DS{active_station_id}", "elevator")

            if (
                transfer_from_ws_started_at is not None
                and elevator.transfer_running
                and sim_time - transfer_from_ws_started_at >= elevator.transfer_time
            ):
                elevator.stop_transfer()
                transfer_from_ws_started_at = None
                did_transfer_from_ws = True
                emit("ELEVATOR_XFER_FROM_WS_STOP", "Transfer from WS completed", "elevator")

            conveyor.update(elapsed_from(conveyor.transition_start_time))
            elevator.update(elapsed_from(elevator.transition_start_time))
            buffer.update(elapsed_from(buffer.transition_start_time))
            pneumatic.update(elapsed_from(pneumatic.transition_start_time))
            rfid_queue.update(elapsed_from(rfid_queue.detect_start_time))
            rfid_elevator.update(elapsed_from(rfid_elevator.detect_start_time))
            for station in stations.values():
                station.update(elapsed_from(station.transition_start_time))

            if active_station_id is not None:
                done_station = stations[active_station_id]
                if done_station.state == DockingStationState.INIT and not done_station.pallet_present and not done_station.pallet_at_ws:
                    emit(
                        "STATION_CYCLE_DONE",
                        f"DS{active_station_id} finished pallet {active_pallet_id}",
                        f"ds_{active_station_id}",
                    )
                    w_done = iface_windows.get(active_station_id)
                    if w_done is not None:
                        w_done.clear()
                        emit(
                            "PALLET_WINDOW_IFACE",
                            f"DS{active_station_id} interface cleared (S1,S2)=(0,0) | main/slave handoff locked-out",
                            f"align_ds_{active_station_id}",
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

            # Retimestamp newly-created wall-clock marks to simulation clock.
            sim_now_dt = sim_start_dt + timedelta(seconds=sim_time)
            wall_now_dt = datetime.now()
            for comp in [conveyor, elevator, buffer, pneumatic, rfid_queue, rfid_elevator]:
                for attr in ("transition_start_time", "detect_start_time", "transfer_start_time"):
                    retime_if_wall_based(comp, attr, sim_now_dt, wall_now_dt)
            for st in stations.values():
                retime_if_wall_based(st, "transition_start_time", sim_now_dt, wall_now_dt)
                retime_if_wall_based(st, "mission_start_time", sim_now_dt, wall_now_dt)

            if buffer.state == BufferState.FULL and conveyor.state != ConveyorMotorState.IDLE:
                conveyor.stop()
                emit("BUFFER_FULL", "Conveyor stopped - buffer at capacity", "buffer")
            elif did_conveyor_started and conveyor.state == ConveyorMotorState.IDLE and buffer.state != BufferState.FULL:
                conveyor.start(speed_percent=50.0)
                emit("CONVEYOR_RESTART", "Conveyor resumed at 50% speed", "conveyor_motor")

            # state-change events (event-driven)
            if prev["conveyor_motor"] != conveyor.state:
                emit(
                    "STATE_CHANGE",
                    f"conveyor_motor: {_ev(prev['conveyor_motor'])} -> {_ev(conveyor.state)}",
                    "conveyor_motor",
                )
                prev["conveyor_motor"] = conveyor.state
            if prev["elevator_position"] != elevator.position:
                emit(
                    "STATE_CHANGE",
                    f"elevator.position: {_ev(prev['elevator_position'])} -> {_ev(elevator.position)}",
                    "elevator",
                )
                prev["elevator_position"] = elevator.position
            if prev["buffer_state"] != buffer.state:
                emit(
                    "STATE_CHANGE",
                    f"buffer: {_ev(prev['buffer_state'])} -> {_ev(buffer.state)} (n={buffer.pallet_count})",
                    "buffer",
                )
                prev["buffer_state"] = buffer.state
            if prev["pneumatic_state"] != pneumatic.state:
                emit(
                    "STATE_CHANGE",
                    f"pneumatic: {_ev(prev['pneumatic_state'])} -> {_ev(pneumatic.state)}",
                    "pneumatic",
                )
                prev["pneumatic_state"] = pneumatic.state
            if prev["rfid_queue_state"] != rfid_queue.state:
                emit(
                    "STATE_CHANGE",
                    f"rfid_queue: {_ev(prev['rfid_queue_state'])} -> {_ev(rfid_queue.state)}",
                    "rfid_queue",
                )
                prev["rfid_queue_state"] = rfid_queue.state
            if prev["rfid_elevator_state"] != rfid_elevator.state:
                emit(
                    "STATE_CHANGE",
                    f"rfid_elevator: {_ev(prev['rfid_elevator_state'])} -> {_ev(rfid_elevator.state)}",
                    "rfid_elevator",
                )
                prev["rfid_elevator_state"] = rfid_elevator.state
            for i, st in stations.items():
                k = f"ds_{i}_state"
                if prev[k] != st.state:
                    emit(
                        "STATE_CHANGE",
                        f"ds_{i}: {_ev(prev[k])} -> {_ev(st.state)}",
                        f"ds_{i}",
                    )
                    prev[k] = st.state

            sim_time += timestep_seconds

            if not no_pacing:
                # pace to target compression ratio: wall_elapsed ~= sim_elapsed / ratio
                expected_wall = sim_time / compression_ratio
                actual_wall = time.monotonic() - wall_start
                if expected_wall > actual_wall:
                    time.sleep(expected_wall - actual_wall)
    finally:
        log_fh.close()

    wall_elapsed = time.monotonic() - wall_start
    print("=" * 88)
    print(
        f"Done. Simulated {sim_time/60.0:.2f} min in wall {wall_elapsed:.2f} s "
        f"(actual ratio {(sim_time / max(wall_elapsed, 1e-9)):.1f}:1)"
    )
    print("Final DS states:")
    for i in range(1, 7):
        st = stations[i]
        print(f"  DS{i}: {st.state.value} pallet={st.pallet_rfid} mission={st.current_mission}")
    print("=" * 88)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compress 100min simulation to 1min with event-driven logs.")
    parser.add_argument("--sim-minutes", type=float, default=100.0, help="Simulation minutes (default: 100)")
    parser.add_argument("--wall-minutes", type=float, default=1.0, help="Target wall-clock minutes (default: 1)")
    parser.add_argument("--timestep", type=float, default=0.1, help="Simulation timestep in seconds")
    parser.add_argument("--deterministic", action="store_true", help="Use deterministic processing durations")
    parser.add_argument(
        "--no-pacing",
        action="store_true",
        help="Run as fast as possible (ignore wall-minute compression pacing)",
    )
    args = parser.parse_args()

    run_event_driven_compressed_demo(
        sim_minutes=args.sim_minutes,
        wall_minutes=args.wall_minutes,
        timestep_seconds=args.timestep,
        deterministic=args.deterministic,
        no_pacing=args.no_pacing,
    )


if __name__ == "__main__":
    main()

