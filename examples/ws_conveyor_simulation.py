"""
WS Conveyor System Simulation Example

This example demonstrates a complete simulation of the Kod_WSConv_Sven2022
system with all major components:

- Conveyor motor with speed ramps
- Transfer elevator moving pallets UP/DOWN
- Buffer queue with 2-pallet capacity
- 6 docking stations with mission processing
- Pneumatic system with pressure monitoring
- 名义 RFID：仅保留读码延迟与状态（``rfid_detection_delay``，默认 0.5s），不建模真实射频

Run: python examples/ws_conveyor_simulation.py
"""

import json
import os
from datetime import datetime, timedelta
from src.mock_up.config import config_normal_operation
from src.mock_up.logic import RawMaterialIngressScheduler, count_pallets_on_line
from src.mock_up.components import (
    create_ws_conveyor_system,
    ConveyorMotorState,
    ElevatorPosition,
    BufferState,
    DockingStationState,
    PneumaticState,
    RFIDState,
)


def _to_enum_value(v):
    """Normalize Enum values for JSON logging."""
    if hasattr(v, "value"):
        return v.value
    return v


def simulate_ws_conveyor():
    """Run a complete WS Conveyor system simulation."""
    
    # Setup
    config = config_normal_operation()
    components = create_ws_conveyor_system(config)

    # Optional JSONL logging for state transitions (useful for regression/debugging).
    log_enabled = getattr(config, "log_state_changes", True)
    log_file = getattr(config, "log_file", "data/logs/ws_conveyor_simulation_state_changes.jsonl")
    if log_enabled:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    log_fh = open(log_file, "a", encoding="utf-8") if log_enabled else None
    log_seq = 0
    
    print("=" * 80)
    print("WS CONVEYOR SYSTEM SIMULATION")
    print("=" * 80)
    print(f"Duration: {config.duration_hours} hours")
    print(f"Timestep: {config.timestep_seconds} seconds")
    print(f"Total steps: {int(config.duration_hours * 3600 / config.timestep_seconds)}")
    print(
        f"Raw material: every {config.raw_material_batch_interval_seconds:.0f}s, "
        f"{config.raw_material_pallets_per_batch} pallet(s)/batch (DS1 Mission 3 → Buffer)"
    )
    print(
        f"Assembly: {config.assembly_time_min_seconds:.0f}–{config.assembly_time_max_seconds:.0f}s "
        f"({'stochastic' if config.assembly_use_stochastic_duration and not config.deterministic else 'fixed midpoint'})"
    )
    print()
    
    # Simulation state
    sim_time = 0.0
    step = 0
    events = []
    sim_start_dt = datetime.now()

    # One-shot guards（多托盘时在 DS1 CLEANUP→INIT 时复位升降机相关标志）
    did_start = False
    did_request_up = False
    did_request_down = False
    did_elevator_receive_ping = False
    
    # Extract components for easier access
    conveyor = components['conveyor_motor']
    elevator = components['elevator']
    buffer = components['buffer']
    stations = {i: components[f'ds_{i}'] for i in range(1, 7)}
    pneumatic = components['pneumatic']
    rfid_queue = components['rfid_queue']
    rfid_elevator = components['rfid_elevator']

    ingress = RawMaterialIngressScheduler(
        interval_seconds=config.raw_material_batch_interval_seconds,
        pallets_per_batch=config.raw_material_pallets_per_batch,
    )

    def log_state_change(component: str, old_state, new_state, details: dict, event: str = "state_change"):
        """Write one JSONL line when a component's key state changes."""
        nonlocal log_seq
        if not log_enabled or log_fh is None:
            return

        payload = {
            "timestamp": (sim_start_dt + timedelta(seconds=sim_time)).isoformat(timespec="milliseconds") + "Z",
            "component": component,
            "event": event,
            "old_state": _to_enum_value(old_state),
            "new_state": _to_enum_value(new_state),
            "details": details,
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

    # =========================================================================
    # SIMULATION SCENARIO: Normal Operation
    # =========================================================================
    # Phase 1: Startup (0-5 seconds)
    # - Enable pneumatic system
    # - Start conveyor at 50% speed
    
    # Phase 2: Pallet Processing (5-30 seconds)
    # - Simulate pallet arriving at buffer
    # - RFID detection (0.5s delay)
    # - Send pallet to DS1
    # - Elevator up/down sequence
    # - Station processing
    
    # Phase 3: Multiple Pallets (30-60 seconds)
    # - More pallets in queue
    # - Cycling through stations
    
    # Phase 4: Fault Condition (60-70 seconds, optional)
    # - Simulate pressure drop
    # - Monitor system response
    
    total_steps = int(config.duration_hours * 3600 / config.timestep_seconds)
    
    print("Starting simulation loop...")
    print()
    
    def elapsed_from(ts):
        if isinstance(ts, datetime):
            return max((sim_start_dt + timedelta(seconds=sim_time) - ts).total_seconds(), 0.0)
        return 0.0

    while sim_time < config.duration_hours * 3600:
        step += 1

        # Periodic AMR → DS1 Mission 3 → Buffer (simulation time)
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

        # ===================================================================
        # PHASE 1: STARTUP (0-5 seconds)
        # ===================================================================
        if not did_start and sim_time >= 0.0:
            events.append((sim_time, "SIM_START", "Simulation begins"))
            pneumatic.enable()
            events.append((sim_time, "PNEUMATIC_ENABLE", "Air supply activated"))
            did_start = True
        
        # Start conveyor at 50% after pneumatic stabilizes
        if sim_time >= 3.0 and conveyor.state == ConveyorMotorState.IDLE:
            conveyor.start(speed_percent=50.0)
            events.append((sim_time, "CONVEYOR_START", "Conveyor started at 50% speed"))
        
        # ===================================================================
        # PHASE 2: Buffer queue → DS1 queue → Mission 2 (to WS)
        # ===================================================================
        if (
            buffer.pallet_at_queue
            and rfid_queue.state.value == "identified"
            and stations[1].state == DockingStationState.INIT
        ):
            rid = buffer.pallet_rfid_at_queue
            buffer.pallet_leaves()
            stations[1].pallet_arrived(rid)
            rfid_queue.clear()
            rfid_elevator.detect(rid)
            events.append((sim_time, "BUFFER_TO_DS1", f"Pallet {rid} handed to DS1 queue"))
        if (
            stations[1].state == DockingStationState.AWAITING_MISSION
            and stations[1].pallet_present
        ):
            if stations[1].accept_mission("2"):
                events.append(
                    (sim_time, "MISSION_ASSIGNED", f"{stations[1].pallet_rfid} → DS1 Mission 2 (to WS)"),
                )

        # ===================================================================
        # PHASE 3: TRANSFER SEQUENCE (elevator + WS processing is time-driven)
        # ===================================================================
        if (
            not did_elevator_receive_ping
            and sim_time >= 8.0
            and stations[1].state == DockingStationState.RECEIVING
            and elevator.position == ElevatorPosition.DOWN
        ):
            elevator.request_down()
            events.append((sim_time, "ELEVATOR_DOWN", "Elevator at lower position (receive)"))
            did_elevator_receive_ping = True

        if (not did_request_up and
            elevator.position == ElevatorPosition.DOWN and
            stations[1].state == DockingStationState.PROCESSING):
            # 托盘已进入 WS，升台（原脚本约 12s，此处改为状态触发）
            elevator.request_up()
            events.append((sim_time, "ELEVATOR_UP", "Elevator moving to working height"))
            did_request_up = True

        # PROCESSING 时长由 DockingStation 内截断指数分布 + update() 自动完成

        if (not did_request_down and
            elevator.position == ElevatorPosition.UP and
            stations[1].state == DockingStationState.SENDING):
            
            # Return to lower level
            elevator.request_down()
            events.append((sim_time, "ELEVATOR_DOWN", "Elevator returning to lower level"))
            did_request_down = True

        # 托盘离站由 DockingStation.update() 在 SENDING 阶段自动 pallet_removed()

        # ===================================================================
        # CONTINUOUS MONITORING
        # ===================================================================
        
        # Update component states with elapsed simulation time
        ds1_before_update = stations[1].state
        conveyor.update(elapsed_from(conveyor.transition_start_time))
        elevator.update(elapsed_from(elevator.transition_start_time))
        buffer.update(elapsed_from(buffer.transition_start_time))
        pneumatic.update(elapsed_from(pneumatic.transition_start_time))
        rfid_queue.update(elapsed_from(rfid_queue.detect_start_time))
        rfid_elevator.update(elapsed_from(rfid_elevator.detect_start_time))
        for station in stations.values():
            station.update(elapsed_from(station.transition_start_time))

        # 多托盘：DS1 本步内从 CLEANUP → INIT 时复位升降机脚本标志
        ds1_after = stations[1].state
        if (
            ds1_before_update == DockingStationState.CLEANUP
            and ds1_after == DockingStationState.INIT
        ):
            did_request_up = False
            did_request_down = False
            did_elevator_receive_ping = False

        # ===================================================================
        # JSONL STATE-CHANGE LOGGING
        # ===================================================================
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
        
        # ===================================================================
        # MONITOR CRITICAL CONDITIONS
        # ===================================================================
        if pneumatic.current_pressure_bar > pneumatic.max_pressure_bar:
            events.append((sim_time, "PRESSURE_HIGH", f"Pressure {pneumatic.current_pressure_bar:.1f} bar (max {pneumatic.max_pressure_bar} bar)"))
        
        if buffer.state == BufferState.FULL:
            # Conveyor should stop to prevent overflow
            if conveyor.state != ConveyorMotorState.IDLE:
                conveyor.stop()
                events.append((sim_time, "BUFFER_FULL", "Conveyor stopped - buffer at capacity"))
        
        # ===================================================================
        # ADVANCE TIME
        # ===================================================================
        sim_time += config.timestep_seconds
        
        # Progress indicator
        if step % 1000 == 0:
            progress = (sim_time / (config.duration_hours * 3600)) * 100
            print(f"  Step {step:6d}: {sim_time:8.1f}s ({progress:5.1f}%) - "
                  f"Conveyor: {conveyor.state.value:12} @ {conveyor.current_speed_percent:5.1f}% | "
                  f"Elevator: {elevator.position.value:8} | "
                  f"Pressure: {pneumatic.current_pressure_bar:5.2f} bar")
    
    # =========================================================================
    # RESULTS & ANALYSIS
    # =========================================================================
    print()
    print("=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)
    print()
    
    print("FINAL SYSTEM STATE:")
    print(f"  Conveyor:  {conveyor.state.value} @ {conveyor.current_speed_percent:.1f}%")
    print(f"  Elevator:  {elevator.position.value}")
    print(f"  Buffer:    {buffer.state.value} ({buffer.pallet_count} pallets)")
    print(f"  Pneumatic: {pneumatic.state.value} ({pneumatic.current_pressure_bar:.2f} bar)")
    print()
    
    print(f"TOTAL EVENTS: {len(events)}")
    print()
    
    print("KEY EVENTS:")
    for timestamp, event_type, description in events[:20]:  # Show first 20
        print(f"  {timestamp:8.2f}s: [{event_type:20}] {description}")
    
    if len(events) > 20:
        print(f"  ... ({len(events) - 20} more events)")
    
    print()
    print("STATION STATUS:")
    for i, station in stations.items():
        print(f"  DS{i}: {station.state.value:20} | Pallet: {station.pallet_rfid or 'None':15} | Mission: {station.current_mission or 'None'}")
    
    print()
    print("=" * 80)

    if log_enabled and log_fh is not None:
        log_fh.close()


if __name__ == "__main__":
    simulate_ws_conveyor()
