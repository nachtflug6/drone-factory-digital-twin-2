#!/usr/bin/env python3
"""Single-pallet lifecycle monitor for WS conveyor mock-up."""

from datetime import datetime, timedelta
from src.mock_up.config import SimulationConfig
from src.mock_up.components import (
    create_ws_conveyor_system,
    ConveyorMotorState,
    ElevatorPosition,
    TransferDirection,
    DockingStationState,
    PneumaticState,
    RFIDState,
)


def run_pallet_lifecycle_monitor() -> None:
    # Keep the run short but observable.
    config = SimulationConfig(
        duration_hours=0.01,  # ~36s virtual time
        timestep_seconds=0.1,
        conveyor_ramp_time=1.0,
        elevator_travel_time=1.0,
        elevator_transfer_time=1.0,
        buffer_transfer_time=1.2,
        station_wait_at_queue=4.0,
        station_transfer_time=1.5,
        station_allow_auto_pass=False,
        # 名义 RFID：保留与手册一致的读码门限（勿为演示缩短）
        rfid_detection_delay=0.5,
        # 生产上为 2–15 分钟指数分布；本演示缩短时间轴并用确定性中点装配
        assembly_time_min_seconds=2.0,
        assembly_time_max_seconds=8.0,
        assembly_use_stochastic_duration=False,
        deterministic=True,
    )

    components = create_ws_conveyor_system(config)
    conveyor = components["conveyor_motor"]
    elevator = components["elevator"]
    buffer = components["buffer"]
    station = components["ds_1"]
    pneumatic = components["pneumatic"]
    rfid_queue = components["rfid_queue"]
    rfid_elevator = components["rfid_elevator"]

    pallet_id = "PALLET_001"
    started_at = datetime.now()
    sim_time = 0.0
    finished = False

    # One-shot flags to keep the scenario deterministic.
    did_enable = False
    did_start_conveyor = False
    did_arrive_queue = False
    did_buffer_in = False
    did_buffer_out = False
    did_to_station = False
    did_accept_mission2 = False
    did_elevator_up = False
    did_transfer_to_ws = False
    did_stop_transfer_to_ws = False
    did_log_assembly_done = False
    did_elevator_down = False
    did_transfer_from_ws = False
    did_stop_transfer_from_ws = False

    processing_started_at = None
    transfer_to_ws_started_at = None
    transfer_from_ws_started_at = None

    def elapsed_from(ts):
        if isinstance(ts, datetime):
            now_dt = started_at + timedelta(seconds=sim_time)
            return max((now_dt - ts).total_seconds(), 0.0)
        return 0.0

    def pallet_location() -> str:
        if station.pallet_at_ws:
            return "AT_WORKSTATION"
        if station.pallet_present:
            return "AT_STATION_QUEUE"
        if buffer.pallet_at_queue and buffer.pallet_rfid_at_queue == pallet_id:
            return "AT_BUFFER_QUEUE"
        if pallet_id in buffer.stored_rfids:
            return "IN_BUFFER_STORAGE"
        if rfid_elevator.tag_detected == pallet_id:
            return "ON_ELEVATOR"
        return "LEFT_SYSTEM_OR_UNKNOWN"

    def monitor_line() -> str:
        return (
            f"t={sim_time:05.1f}s | pallet={pallet_location():>20} | "
            f"conv={conveyor.state.value:>8} {conveyor.current_speed_percent:5.1f}% | "
            f"elev={elevator.position.value:>6} xfer={str(elevator.transfer_running):>5} | "
            f"buffer={buffer.state.value:>7} n={buffer.pallet_count} queue={buffer.pallet_rfid_at_queue} | "
            f"ds1={station.state.value:>16} mission={station.current_mission} | "
            f"air={pneumatic.state.value:>11} {pneumatic.current_pressure_bar:4.1f}bar | "
            f"rfidQ={rfid_queue.state.value:>10} rfidE={rfid_elevator.state.value:>10}"
        )

    print("=" * 120)
    print("PALLET LIFECYCLE MONITOR")
    print("=" * 120)

    total_seconds = config.duration_hours * 3600
    while sim_time <= total_seconds and not finished:
        # 1) Plant startup
        if not did_enable and sim_time >= 0.0:
            pneumatic.enable()
            did_enable = True
            print(f"[EVENT] {sim_time:05.1f}s pneumatic enabled")

        if not did_start_conveyor and sim_time >= 0.5:
            conveyor.start(speed_percent=60.0)
            did_start_conveyor = True
            print(f"[EVENT] {sim_time:05.1f}s conveyor start 60%")

        # 2) Pallet enters queue and gets identified
        if not did_arrive_queue and sim_time >= 1.0:
            buffer.pallet_enters(pallet_id)
            rfid_queue.detect(pallet_id)
            did_arrive_queue = True
            print(f"[EVENT] {sim_time:05.1f}s pallet arrived at buffer queue")

        if did_arrive_queue and not did_buffer_in and rfid_queue.state == RFIDState.IDENTIFIED:
            if buffer.add_to_buffer():
                did_buffer_in = True
                print(f"[EVENT] {sim_time:05.1f}s buffer transfer IN started")

        # 3) Move pallet out from storage to queue for DS1 pickup
        if did_buffer_in and not did_buffer_out and pallet_id in buffer.stored_rfids and not buffer.is_transferring:
            if buffer.remove_from_buffer():
                did_buffer_out = True
                print(f"[EVENT] {sim_time:05.1f}s buffer transfer OUT started")

        # 4) Hand over to station queue and assign mission 2 (to WS)
        if (
            did_buffer_out
            and not did_to_station
            and buffer.pallet_at_queue
            and buffer.pallet_rfid_at_queue == pallet_id
            and not buffer.is_transferring
        ):
            station.pallet_arrived(pallet_id)
            buffer.pallet_leaves()
            rfid_queue.clear()
            rfid_elevator.detect(pallet_id)
            did_to_station = True
            print(f"[EVENT] {sim_time:05.1f}s pallet handed over to DS1 queue")

        if did_to_station and not did_accept_mission2 and station.state == DockingStationState.AWAITING_MISSION:
            if station.accept_mission("2"):
                did_accept_mission2 = True
                print(f"[EVENT] {sim_time:05.1f}s DS1 accepted mission 2 (to WS)")

        # 5) Elevator and cross transfer to workstation
        if did_accept_mission2 and not did_elevator_up and elevator.position == ElevatorPosition.DOWN:
            elevator.request_up()
            did_elevator_up = True
            print(f"[EVENT] {sim_time:05.1f}s elevator request UP")

        if did_elevator_up and not did_transfer_to_ws and elevator.position == ElevatorPosition.UP:
            if elevator.start_transfer(TransferDirection.TO_WS):
                did_transfer_to_ws = True
                transfer_to_ws_started_at = sim_time
                # Clear UP request latch to avoid false conflict on later DOWN request.
                elevator.up_requested = False
                print(f"[EVENT] {sim_time:05.1f}s elevator transfer TO_WS started")

        if (
            did_transfer_to_ws
            and not did_stop_transfer_to_ws
            and transfer_to_ws_started_at is not None
            and sim_time - transfer_to_ws_started_at >= elevator.transfer_time
        ):
            elevator.stop_transfer()
            did_stop_transfer_to_ws = True
            print(f"[EVENT] {sim_time:05.1f}s elevator transfer TO_WS stopped")

        if station.state == DockingStationState.PROCESSING and processing_started_at is None:
            processing_started_at = sim_time
            tgt = getattr(station, "_processing_target_seconds", None)
            print(
                f"[EVENT] {sim_time:05.1f}s DS1 entered PROCESSING"
                + (f" (target {tgt:.1f}s)" if isinstance(tgt, (int, float)) else "")
            )

        # 装配时长由 DockingStation.update() 按配置采样/超时自动 complete_processing()
        if (
            did_accept_mission2
            and not did_log_assembly_done
            and station.state == DockingStationState.SENDING
            and station.current_mission == "_ws_sendout"
        ):
            did_log_assembly_done = True
            print(f"[EVENT] {sim_time:05.1f}s DS1 assembly done → SENDING (WS sendout)")

        # 6) Send pallet back and finish

        if did_log_assembly_done and not did_elevator_down and elevator.position == ElevatorPosition.UP:
            # Defensive clear of latches before direction change.
            elevator.up_requested = False
            elevator.down_requested = False
            elevator.request_down()
            did_elevator_down = True
            print(f"[EVENT] {sim_time:05.1f}s elevator request DOWN")

        if did_elevator_down and not did_transfer_from_ws and elevator.position == ElevatorPosition.DOWN:
            if elevator.start_transfer(TransferDirection.FROM_WS):
                did_transfer_from_ws = True
                transfer_from_ws_started_at = sim_time
                print(f"[EVENT] {sim_time:05.1f}s elevator transfer FROM_WS started")

        if (
            did_transfer_from_ws
            and not did_stop_transfer_from_ws
            and transfer_from_ws_started_at is not None
            and sim_time - transfer_from_ws_started_at >= elevator.transfer_time
        ):
            elevator.stop_transfer()
            did_stop_transfer_from_ws = True
            print(f"[EVENT] {sim_time:05.1f}s elevator transfer FROM_WS stopped")

        if did_stop_transfer_from_ws and station.state == DockingStationState.INIT:
            rfid_elevator.clear()
            conveyor.stop()
            finished = True
            print(f"[EVENT] {sim_time:05.1f}s lifecycle complete (station returned INIT)")

        # Physics/state progression
        conveyor.update(elapsed_from(conveyor.transition_start_time))
        elevator.update(elapsed_from(elevator.transition_start_time))
        buffer.update(elapsed_from(buffer.transition_start_time))
        pneumatic.update(elapsed_from(pneumatic.transition_start_time))
        rfid_queue.update(elapsed_from(rfid_queue.detect_start_time))
        rfid_elevator.update(elapsed_from(rfid_elevator.detect_start_time))
        station.update(elapsed_from(station.transition_start_time))

        # Monitor prints: every 0.5s
        if int(sim_time * 10) % 5 == 0:
            print(monitor_line())

        sim_time += config.timestep_seconds

    print("=" * 120)
    print("FINAL SNAPSHOT")
    print(monitor_line())
    print("=" * 120)


if __name__ == "__main__":
    run_pallet_lifecycle_monitor()
