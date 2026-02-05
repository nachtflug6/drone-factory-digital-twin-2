"""
WS Conveyor System Simulation Example

This example demonstrates a complete simulation of the Kod_WSConv_Sven2022
system with all major components:

- Conveyor motor with speed ramps
- Transfer elevator moving pallets UP/DOWN
- Buffer queue with 2-pallet capacity
- 6 docking stations with mission processing
- Pneumatic system with pressure monitoring
- RFID pallet tracking

Run: python examples/ws_conveyor_simulation.py
"""

from datetime import datetime, timedelta
from src.mock_up.config import config_normal_operation
from src.mock_up.components import (
    create_ws_conveyor_system,
    ConveyorMotorState,
    ElevatorPosition,
    BufferState,
    DockingStationState,
    PneumaticState
)


def simulate_ws_conveyor():
    """Run a complete WS Conveyor system simulation."""
    
    # Setup
    config = config_normal_operation()
    components = create_ws_conveyor_system(config)
    
    print("=" * 80)
    print("WS CONVEYOR SYSTEM SIMULATION")
    print("=" * 80)
    print(f"Duration: {config.duration_hours} hours")
    print(f"Timestep: {config.timestep_seconds} seconds")
    print(f"Total steps: {int(config.duration_hours * 3600 / config.timestep_seconds)}")
    print()
    
    # Simulation state
    sim_time = 0.0
    step = 0
    events = []
    
    # Extract components for easier access
    conveyor = components['conveyor_motor']
    elevator = components['elevator']
    buffer = components['buffer']
    stations = {i: components[f'ds_{i}'] for i in range(1, 7)}
    pneumatic = components['pneumatic']
    rfid_queue = components['rfid_queue']
    rfid_elevator = components['rfid_elevator']
    
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
    
    while sim_time < config.duration_hours * 3600:
        step += 1
        
        # ===================================================================
        # PHASE 1: STARTUP (0-5 seconds)
        # ===================================================================
        if sim_time == 0:
            events.append((sim_time, "SIM_START", "Simulation begins"))
            pneumatic.enable()
            events.append((sim_time, "PNEUMATIC_ENABLE", "Air supply activated"))
        
        # Start conveyor at 50% after pneumatic stabilizes
        if sim_time >= 3.0 and conveyor.state == ConveyorMotorState.IDLE:
            conveyor.start(speed_percent=50.0)
            events.append((sim_time, "CONVEYOR_START", "Conveyor started at 50% speed"))
        
        # ===================================================================
        # PHASE 2: PALLET ARRIVES AT BUFFER (5-10 seconds)
        # ===================================================================
        if sim_time >= 5.0 and not buffer.pallet_at_queue:
            buffer.pallet_enters("PALLET_001")
            rfid_queue.detect("PALLET_001")
            events.append((sim_time, "PALLET_ARRIVES", "PALLET_001 arrives at buffer"))
        
        # RFID detection complete, pallet identified
        if (sim_time >= 5.5 and 
            rfid_queue.state.value == "identified" and 
            stations[1].state == DockingStationState.INIT):
            
            # Send pallet to DS1
            stations[1].accept_mission("PROCESS_TYPE_A")
            events.append((sim_time, "MISSION_ASSIGNED", "PALLET_001 → DS1, Mission: PROCESS_TYPE_A"))
        
        # ===================================================================
        # PHASE 3: TRANSFER SEQUENCE (10-20 seconds)
        # ===================================================================
        if (sim_time >= 8.0 and 
            stations[1].state == DockingStationState.RECEIVING and 
            elevator.position == ElevatorPosition.DOWN):
            
            # Elevator down to receive pallet
            elevator.request_down()
            events.append((sim_time, "ELEVATOR_DOWN", "Elevator at lower position"))
        
        if (sim_time >= 10.0 and 
            elevator.is_down and 
            not stations[1].pallet_present):
            
            # Transfer pallet from buffer to elevator
            buffer.pallet_leaves()
            stations[1].pallet_arrived("PALLET_001")
            rfid_queue.clear()
            rfid_elevator.detect("PALLET_001")
            events.append((sim_time, "PALLET_TRANSFERRED", "PALLET_001 transferred to elevator"))
        
        if (sim_time >= 12.0 and 
            elevator.position == ElevatorPosition.DOWN and 
            stations[1].pallet_present):
            
            # Move elevator to working height
            elevator.request_up()
            events.append((sim_time, "ELEVATOR_UP", "Elevator moving to working height"))
        
        if (sim_time >= 13.0 and 
            elevator.is_up and 
            stations[1].state == DockingStationState.RECEIVING):
            
            # Elevator at working height, pallet can be processed
            stations[1].state = DockingStationState.PROCESSING
            events.append((sim_time, "PROCESSING_START", "PALLET_001 processing starts at DS1"))
        
        # ===================================================================
        # PHASE 4: PROCESSING & COMPLETION (20-30 seconds)
        # ===================================================================
        if (sim_time >= 20.0 and 
            stations[1].state == DockingStationState.PROCESSING):
            
            # Simulate work completion
            stations[1].complete_processing()
            events.append((sim_time, "PROCESSING_COMPLETE", "PALLET_001 processing complete"))
        
        if (sim_time >= 22.0 and 
            elevator.position == ElevatorPosition.UP and 
            stations[1].state == DockingStationState.SENDING):
            
            # Return to lower level
            elevator.request_down()
            events.append((sim_time, "ELEVATOR_DOWN", "Elevator returning to lower level"))
        
        if (sim_time >= 24.0 and 
            elevator.is_down and 
            stations[1].state == DockingStationState.SENDING):
            
            # Pallet leaves station
            stations[1].pallet_removed()
            rfid_elevator.clear()
            events.append((sim_time, "PALLET_EXIT", "PALLET_001 exits DS1, ready for next mission"))
        
        # ===================================================================
        # CONTINUOUS MONITORING
        # ===================================================================
        
        # Update component states
        if conveyor.state != ConveyorMotorState.IDLE and conveyor.transition_start_time:
            elapsed = sim_time - (conveyor.transition_start_time.timestamp() if isinstance(conveyor.transition_start_time, datetime) else 0)
            # Simplified for example
        
        if elevator.position == ElevatorPosition.MOVING and elevator.transition_start_time:
            elapsed = sim_time - (elevator.transition_start_time.timestamp() if isinstance(elevator.transition_start_time, datetime) else 0)
            if elapsed >= elevator.travel_time:
                # Movement complete (handled in update)
                pass
        
        if pneumatic.state == PneumaticState.STABILIZING and pneumatic.transition_start_time:
            elapsed = sim_time - (pneumatic.transition_start_time.timestamp() if isinstance(pneumatic.transition_start_time, datetime) else 0)
            if elapsed >= pneumatic.stabilization_time:
                pneumatic.state = PneumaticState.NORMAL
        
        if rfid_queue.state.value == "detecting" and rfid_queue.detect_start_time:
            elapsed = sim_time - (rfid_queue.detect_start_time.timestamp() if isinstance(rfid_queue.detect_start_time, datetime) else 0)
            if elapsed >= rfid_queue.detection_delay:
                rfid_queue.state.value = "identified"
        
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


if __name__ == "__main__":
    simulate_ws_conveyor()
