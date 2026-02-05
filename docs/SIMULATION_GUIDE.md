# Simulation Guide

## Overview

This guide explains how to build and run simulations of the drone factory digital twin.

---

## Simulation Fundamentals

### What is Simulation?

Simulation is **automated virtual execution** of system logic over time:

1. **Initialize** — Set up initial system state
2. **Advance Time** — Move forward in virtual time
3. **Process Events** — Execute actions triggered by time or conditions
4. **Update State** — Components change based on logic
5. **Log Changes** — Record what happened
6. **Repeat** — Continue until simulation end time

### Why Simulate?

- **Verify behavior** — Does system match documentation?
- **Study dynamics** — How do components interact over time?
- **Test scenarios** — What if conditions change?
- **Find issues** — Can we discover bugs before real deployment?
- **Predict long-term** — What happens over days/weeks?

### Advantages Over Real-Time

- **Fast** — 24 hours simulated in <1 hour real time
- **Repeatable** — Same inputs always produce same outputs (deterministic)
- **Observable** — Log everything that happens
- **Safe** — No physical damage from mistakes
- **Flexible** — Easy to change parameters and re-run

---

## Simulation Architecture

### Event-Driven Model

The simulator operates on an **event queue**:

```
TIME: 0s
├─ Event: Motor_1 START
│  └─ Schedules: "Motor_1 reaches full speed" at time 2s
│  └─ Updates: Motor_1.state = ACCELERATING
│
TIME: 1s
├─ (No events scheduled)
│
TIME: 2s
├─ Event: Motor_1 ACCEL_COMPLETE
│  └─ Updates: Motor_1.state = RUNNING
│
TIME: 5.2s
├─ Event: Conveyor_1 LOAD_THRESHOLD_EXCEEDED
│  └─ Updates: Conveyor_1.state = ERROR
│
TIME: 6s
├─ Event: Operator RESET (manual event)
│  └─ Updates: Conveyor_1.state = IDLE
```

**Advantages:**
- ✓ Only processes time steps where something happens
- ✓ Much faster than step-by-step time advancement
- ✓ Exact timing preserved
- ✓ No computational waste

### Time Management

The simulator maintains a **virtual clock** separate from wall-clock time:

```python
class TimeManager:
    virtual_time: datetime = datetime(2024, 1, 1, 0, 0, 0)  # Start time
    current_event: Event = None
    
    def advance_to(self, target_time: datetime):
        """Jump to next event"""
        self.virtual_time = target_time
    
    def elapsed_since(self, reference_time: datetime) -> float:
        """Time in seconds since reference"""
        return (self.virtual_time - reference_time).total_seconds()
```

**Benefits:**
- ✓ Can simulate months of operation in seconds of real time
- ✓ Deterministic — same random seed produces same results
- ✓ Replayable — can rewind and re-simulate

---

## Building Your Simulation

### Step 1: Create Configuration

Define simulation parameters:

```python
# src/mock_up/config.py
from dataclasses import dataclass

@dataclass
class SimulationConfig:
    # Simulation timing
    start_time: str = "2024-01-01 00:00:00"
    duration_hours: float = 24.0  # How long to simulate
    
    # System parameters
    motor_count: int = 3
    conveyor_count: int = 5
    sensor_count: int = 8
    
    # Motor parameters
    motor_ramp_up_time: float = 2.0  # seconds
    motor_max_rpm: float = 1000.0
    
    # Conveyor parameters
    conveyor_max_load_kg: float = 50.0
    conveyor_speed_rpm: float = 100.0
    
    # Simulation options
    log_format: str = "json"  # json, csv, or binary
    log_level: str = "INFO"   # DEBUG, INFO, WARNING
    seed: int = 42            # For reproducibility
```

### Step 2: Initialize System State

Create all components in their initial state:

```python
# src/simulation/simulator.py
from datetime import datetime, timedelta
from mock_up.state import SystemState
from mock_up.components import Motor, Conveyor
from logging.logger import Logger

def create_system(config: SimulationConfig) -> SystemState:
    """Build system from configuration"""
    system = SystemState()
    
    # Create motors
    for i in range(config.motor_count):
        motor = Motor(
            id=f"motor_{i}",
            max_rpm=config.motor_max_rpm,
            ramp_up_time=config.motor_ramp_up_time
        )
        system.register_component(motor)
    
    # Create conveyors
    for i in range(config.conveyor_count):
        conveyor = Conveyor(
            id=f"conveyor_{i}",
            max_load_kg=config.conveyor_max_load_kg,
            max_speed_rpm=config.conveyor_speed_rpm
        )
        system.register_component(conveyor)
    
    # Create sensors
    for i in range(config.sensor_count):
        sensor = LoadSensor(
            id=f"sensor_{i}",
            attached_to=f"conveyor_{i % config.conveyor_count}"
        )
        system.register_component(sensor)
    
    return system
```

### Step 3: Build Event Scheduler

Events drive the simulation:

```python
# src/simulation/scheduler.py
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

@dataclass
class Event:
    time: datetime          # When to execute
    name: str              # Event name (for logging)
    handler: Callable      # Function to call
    args: tuple = ()       # Arguments to pass
    
    def execute(self):
        """Run this event"""
        return self.handler(*self.args)

class EventScheduler:
    def __init__(self):
        self.queue = []  # Priority queue by time
    
    def schedule(self, time: datetime, event: Event):
        """Add event to queue"""
        self.queue.append((time, event))
        self.queue.sort()  # Keep sorted by time
    
    def get_next(self) -> (datetime, Event):
        """Get next event to process"""
        if self.queue:
            return self.queue.pop(0)
        return None, None
    
    def is_empty(self) -> bool:
        return len(self.queue) == 0
```

### Step 4: Implement Simulator Loop

Main simulation engine:

```python
# src/simulation/simulator.py
class Simulator:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.system = create_system(config)
        self.scheduler = EventScheduler()
        self.logger = Logger(config)
        self.current_time = datetime.fromisoformat(config.start_time)
        self.end_time = self.current_time + timedelta(hours=config.duration_hours)
        self.errors = []
        
        # Schedule initial events
        self._initialize_events()
    
    def _initialize_events(self):
        """Schedule events that should happen at start"""
        # Example: Start all motors at T=0
        for component in self.system.components.values():
            if isinstance(component, Motor):
                self.scheduler.schedule(
                    self.current_time,
                    Event(
                        time=self.current_time,
                        name=f"{component.id}_START",
                        handler=component.start
                    )
                )
    
    def run(self):
        """Main simulation loop"""
        print(f"Starting simulation: {self.current_time} to {self.end_time}")
        
        event_count = 0
        try:
            while self.current_time < self.end_time and not self.scheduler.is_empty():
                # Get next event
                event_time, event = self.scheduler.get_next()
                
                if event_time is None:
                    break  # No more events
                
                if event_time > self.end_time:
                    break  # Event is beyond simulation end
                
                # Advance time
                self.current_time = event_time
                
                # Execute event
                self.logger.log_event(event, self.current_time)
                try:
                    event.execute()
                except Exception as e:
                    self.logger.log_error(f"Event {event.name} failed: {e}", self.current_time)
                    self.errors.append(e)
                
                # Schedule follow-up events (depends on logic)
                self._on_state_change(event)
                
                event_count += 1
                if event_count % 1000 == 0:
                    print(f"  {event_count} events processed, current time: {self.current_time}")
        
        except Exception as e:
            print(f"SIMULATION FAILED: {e}")
            self.errors.append(e)
        
        finally:
            self.logger.finalize()
            print(f"Simulation complete. {event_count} events processed.")
            print(f"Logs saved to {self.logger.path}")
    
    def _on_state_change(self, event: Event):
        """Schedule follow-up events based on state change"""
        # This depends on your system logic
        # Example: Motor finishes starting, schedule next state change
        
        for component in self.system.components.values():
            # Check if any delayed events need scheduling
            if hasattr(component, 'pending_events'):
                for future_event in component.pending_events:
                    self.scheduler.schedule(future_event.time, future_event)
                component.pending_events.clear()
    
    def get_results(self):
        """Return simulation results"""
        return {
            'start_time': str(self.current_time),
            'end_time': str(self.end_time),
            'log_file': self.logger.path,
            'errors': len(self.errors),
            'error_messages': [str(e) for e in self.errors[:10]]
        }
```

### Step 5: Run the Simulation

```python
# main.py or run_simulation.py
from mock_up.config import SimulationConfig
from simulation.simulator import Simulator

def main():
    # Create configuration
    config = SimulationConfig(
        duration_hours=24,
        motor_count=3,
        conveyor_count=5,
        log_format="json"
    )
    
    # Run simulation
    simulator = Simulator(config)
    simulator.run()
    
    # Print results
    results = simulator.get_results()
    print("\nSimulation Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
```

Run it:
```bash
python run_simulation.py
```

---

## Advanced Simulation Techniques

### Scenario 1: Multiple Scenarios

Run the same simulation with different parameters:

```python
# Run simulations with different motor counts
for motor_count in [1, 3, 5, 10]:
    config = SimulationConfig(
        duration_hours=24,
        motor_count=motor_count,
        seed=42
    )
    simulator = Simulator(config)
    simulator.run()
    print(f"Motor count {motor_count}: {len(simulator.logger.events)} events logged")
```

### Scenario 2: Long-Duration Studies

Study multi-day behavior:

```python
config = SimulationConfig(
    duration_hours=7*24,  # 1 week
    motor_count=5,
    log_format="json"
)
simulator = Simulator(config)
simulator.run()
# Analyze logs for weekly patterns
```

### Scenario 3: Fault Injection

Test system response to failures:

```python
class FaultSimulator(Simulator):
    def _initialize_events(self):
        super()._initialize_events()
        
        # Schedule a motor failure at T=12 hours
        fault_time = self.current_time + timedelta(hours=12)
        self.scheduler.schedule(
            fault_time,
            Event(
                time=fault_time,
                name="motor_1_FAILURE",
                handler=self._inject_motor_failure
            )
        )
    
    def _inject_motor_failure(self):
        """Simulate motor failure"""
        motor = self.system.get_component("motor_1")
        motor.state = MotorState.ERROR
        motor.speed_rpm = 0.0
        self.logger.log_event("FAULT_INJECTED", motor, self.current_time)
```

### Scenario 4: Load Variation

Simulate varying workload:

```python
class VariableLoadSimulator(Simulator):
    def _initialize_events(self):
        super()._initialize_events()
        
        # Schedule load changes every hour
        for hours in range(int(self.config.duration_hours)):
            load_time = self.current_time + timedelta(hours=hours)
            self.scheduler.schedule(
                load_time,
                Event(
                    time=load_time,
                    name=f"LOAD_CHANGE_H{hours}",
                    handler=self._update_load,
                    args=(hours,)
                )
            )
    
    def _update_load(self, hour):
        """Change system load based on hour"""
        # E.g., lower load during night, higher during day
        load_factor = 0.3 if 22 <= hour or hour < 6 else 1.0
        for component in self.system.components.values():
            if hasattr(component, 'load_kg'):
                component.load_kg *= load_factor
```

---

## Performance Optimization

### 1. Event Batching

For systems with many components, batch updates:

```python
def _on_state_change(self, event: Event):
    """Efficient batch processing of follow-up events"""
    new_events = []
    for component in self.system.components.values():
        if hasattr(component, 'get_pending_events'):
            new_events.extend(component.get_pending_events())
    
    # Add all at once instead of one-by-one
    for evt in new_events:
        self.scheduler.schedule(evt.time, evt)
```

### 2. Time Skipping

Skip periods with no events:

```python
def run_optimized(self):
    """Skip empty time periods"""
    while self.current_time < self.end_time:
        event_time, event = self.scheduler.get_next()
        
        if event_time is None:
            # No more events, jump to end
            self.current_time = self.end_time
            break
        
        # Jump directly to next event time
        self.current_time = event_time
        event.execute()
```

### 3. Log Filtering

Only log important events:

```python
def should_log_event(self, event: Event) -> bool:
    """Filter out unimportant events"""
    # Don't log state checks, only actual changes
    if event.name.startswith("CHECK_"):
        return False
    # Log errors and state changes
    if event.name in ["ERROR", "STATE_CHANGE"]:
        return True
    # Log at specified interval (e.g., every 10th non-error event)
    return self.event_count % 10 == 0
```

### 4. Memory Management

For very long simulations, stream logs instead of keeping all in memory:

```python
class Logger:
    def __init__(self, path: str):
        self.file = open(path, 'w')  # Write to disk immediately
    
    def log_event(self, event: Event, timestamp: datetime):
        """Write immediately instead of buffering"""
        import json
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'event': event.name,
            ...
        }
        self.file.write(json.dumps(log_entry) + '\n')
        self.file.flush()  # Ensure it's written
    
    def finalize(self):
        self.file.close()
```

---

## Validation Checklist

Before declaring simulation results valid:

- [ ] Simulation completes without errors
- [ ] Virtual time advances monotonically (never goes backward)
- [ ] All state transitions are valid (per documentation)
- [ ] No impossible states (e.g., motor both ON and OFF)
- [ ] Timing constraints are respected (e.g., motor reaches full speed in specified time)
- [ ] Dependencies are correct (e.g., conveyor stops when motor stops)
- [ ] Logs are complete and parseable
- [ ] Same configuration produces identical results (determinism)
- [ ] Log timestamps match simulation time

---

## Example: Complete Simulation Run

```python
# examples/basic_simulation.py
from datetime import datetime, timedelta
from mock_up.config import SimulationConfig
from simulation.simulator import Simulator

def main():
    print("=" * 60)
    print("Drone Factory Digital Twin - Basic Simulation")
    print("=" * 60)
    
    # Configure
    config = SimulationConfig(
        start_time="2024-01-15 06:00:00",  # Start at 6 AM
        duration_hours=24,
        motor_count=3,
        conveyor_count=5,
        sensor_count=8,
        log_format="json",
        log_level="INFO",
        seed=42
    )
    
    print(f"\nConfiguration:")
    print(f"  Duration: {config.duration_hours} hours")
    print(f"  Motors: {config.motor_count}")
    print(f"  Conveyors: {config.conveyor_count}")
    print(f"  Sensors: {config.sensor_count}")
    
    # Run
    print(f"\nRunning simulation...")
    simulator = Simulator(config)
    simulator.run()
    
    # Results
    results = simulator.get_results()
    print(f"\nResults:")
    for key, value in results.items():
        print(f"  {key}: {value}")
    
    # Verify
    if len(simulator.errors) == 0:
        print("\n✓ Simulation completed successfully!")
    else:
        print(f"\n✗ Simulation had {len(simulator.errors)} errors")
        for err in simulator.errors[:5]:
            print(f"    - {err}")

if __name__ == "__main__":
    main()
```

---

## Next Steps

1. Build your components (Phase 2)
2. Create simulator framework (Phase 4)
3. Run basic simulation
4. Extend with advanced scenarios
5. Analyze logs (Phase 5)

See [PROJECT_PHASES.md](PROJECT_PHASES.md) for detailed timeline.
