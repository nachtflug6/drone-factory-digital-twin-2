#!/usr/bin/env python3
# examples/basic_simulation.py
"""
Basic Simulation Example

This example shows how to:
1. Create a system configuration
2. Initialize the system state
3. Run a simple simulation loop
4. Log results

Run this to verify your installation:
    python examples/basic_simulation.py
"""

from datetime import datetime, timedelta
from src.mock_up.config import SimulationConfig
from src.mock_up.state import SystemState
from src.mock_up.logic import apply_system_logic
from src.mock_up.components import MotorState, ConveyorState


def main():
    print("=" * 70)
    print("Drone Factory Digital Twin - Basic Simulation Example")
    print("=" * 70)
    
    # ========================================================================
    # Step 1: Configure the simulation
    # ========================================================================
    print("\n[1/4] Setting up configuration...")
    
    config = SimulationConfig(
        start_time="2024-01-15 06:00:00",
        duration_hours=0.1,  # 6 minutes of simulation
        motor_count=2,
        conveyor_count=2,
        sensor_count=2,
        motor_max_rpm=1000,
        motor_ramp_up_time=2.0,
        conveyor_max_load_kg=50.0,
        log_level="INFO"
    )
    
    print(f"   Start time: {config.start_time}")
    print(f"   Duration: {config.duration_hours} hours")
    print(f"   Motors: {config.motor_count}")
    print(f"   Conveyors: {config.conveyor_count}")
    print(f"   Sensors: {config.sensor_count}")
    
    # ========================================================================
    # Step 2: Initialize system state
    # ========================================================================
    print("\n[2/4] Initializing system...")
    
    system = SystemState(config)
    
    print(f"   Components created: {len(system.components)}")
    for comp_id in sorted(system.components.keys()):
        comp = system.components[comp_id]
        print(f"      - {comp_id}: {comp.__class__.__name__}")
    
    # ========================================================================
    # Step 3: Run simulation loop
    # ========================================================================
    print("\n[3/4] Running simulation...")
    
    end_time = datetime.fromisoformat(config.start_time) + timedelta(hours=config.duration_hours)
    current_time = datetime.fromisoformat(config.start_time)
    time_step = 0.1  # seconds
    step_count = 0
    events = []
    
    # Start motors
    for motor in system.get_components_by_type('motor'):
        motor.start(target_speed=1000)
        events.append((current_time, f"START motor {motor.id}"))
    
    # Start conveyors
    for conveyor in system.get_components_by_type('conveyor'):
        conveyor.start()
        events.append((current_time, f"START conveyor {conveyor.id}"))
    
    # Main simulation loop
    while current_time < end_time:
        # Apply control logic
        apply_system_logic(system, current_time)
        
        # Advance time
        current_time += timedelta(seconds=time_step)
        step_count += 1
        
        # Print progress every 100 steps
        if step_count % 100 == 0:
            elapsed_hours = (current_time - datetime.fromisoformat(config.start_time)).total_seconds() / 3600
            print(f"   {step_count:5d} steps, {elapsed_hours:.3f} hours simulated")
    
    print(f"   ✓ Completed {step_count} simulation steps")
    
    # ========================================================================
    # Step 4: Print results
    # ========================================================================
    print("\n[4/4] Simulation results:")
    
    print("\n   Final component states:")
    for comp_id, component in sorted(system.components.items()):
        if hasattr(component, 'state'):
            state = component.state.value if hasattr(component.state, 'value') else str(component.state)
            speed = f", speed={component.speed_rpm:.0f} RPM" if hasattr(component, 'speed_rpm') else ""
            load = f", load={component.load_kg:.1f} kg" if hasattr(component, 'load_kg') else ""
            print(f"      {comp_id:15} {state:15} {speed}{load}")
    
    print("\n   Key events:")
    for timestamp, event in events[:10]:
        print(f"      {timestamp}: {event}")
    
    print("\n" + "=" * 70)
    print("✓ Simulation completed successfully!")
    print("=" * 70)
    
    print("\nNext steps:")
    print("  1. Read docs/PROJECT_PHASES.md for project structure")
    print("  2. Analyze PLC documentation (Kod_WSConv_Sven2022.pdf)")
    print("  3. Implement remaining components in src/mock_up/components.py")
    print("  4. Write unit tests in tests/unit/")
    print("  5. Build full simulator in src/simulation/")
    print("  6. Run extended simulations and analyze logs")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
