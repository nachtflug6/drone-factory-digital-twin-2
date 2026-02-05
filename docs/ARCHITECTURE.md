# System Architecture & Design Guide

## Overview

This document describes the overall architecture for the drone factory digital twin. It explains the design decisions, component interactions, and how to structure your implementation.

---

## Architecture Principles

1. **Separation of Concerns** — Components are independent, with clear interfaces
2. **State Machines** — Each component has discrete states and explicit transitions
3. **Event-Driven** — System evolves through triggered events, not polling
4. **Deterministic** — Same inputs produce same outputs (for testing)
5. **Observable** — All significant changes are logged
6. **Configurable** — System parameters are externalized, not hardcoded

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SIMULATOR                             │
│  (Manages virtual time, event scheduling, coordinates)   │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼──────────┐   ┌─────▼────────────┐
│ SYSTEM STATE     │   │   COMPONENTS     │
│ (Global state    │   │ (Motors, sensors,│
│  tracking)       │   │  conveyors, etc.)│
└──────────────────┘   └─────┬────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
             ┌──────▼──────┐   ┌──────▼──────┐
             │ LOGIC       │   │ CONFIG      │
             │ (PLC rules) │   │ (Parameters)│
             └─────────────┘   └─────────────┘
                    │
                    │
            ┌───────▼────────┐
            │   LOGGER       │
            │   (Captures    │
            │    events)     │
            └────────────────┘
```

---

## Core Components

### 1. System State (`src/mock_up/state.py`)

**Purpose:** Central state management for the entire system

**Responsibilities:**
- Track current state of all components
- Provide read/write interface to component states
- Maintain consistency invariants
- Support state snapshots (for checkpoints)

**Interface:**
```python
class SystemState:
    def __init__(self, config):
        self.components = {}  # Dict of component_id -> component_state
    
    def update_component(self, component_id: str, new_state):
        """Update a component's state"""
        pass
    
    def get_component_state(self, component_id: str):
        """Read current state of a component"""
        pass
    
    def get_system_snapshot(self):
        """Return complete system state snapshot"""
        pass
    
    def check_invariants(self) -> bool:
        """Verify system is in valid state"""
        pass
```

### 2. Components (`src/mock_up/components.py`)

**Purpose:** Model individual physical/logical components

**Examples:**
- Conveyor motor
- Position sensor
- Temperature sensor
- Actuator arm
- Sorting mechanism
- Assembly station

**Each Component Should Have:**
- **State enum** — All possible states (IDLE, RUNNING, ERROR, etc.)
- **Data class** — Component parameters (ID, speed, position, etc.)
- **Transition methods** — How to move between states
- **Query methods** — Get current properties

**Example Structure:**
```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class ConveyorState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class Conveyor:
    """Physical conveyor belt in the system"""
    id: str
    state: ConveyorState = ConveyorState.IDLE
    speed_rpm: float = 0.0
    load_kg: float = 0.0
    position_mm: float = 0.0
    
    def start(self, speed: float = 100.0):
        """Start conveyor at specified speed"""
        if self.state == ConveyorState.IDLE:
            self.state = ConveyorState.RUNNING
            self.speed_rpm = speed
        else:
            raise InvalidStateTransition(f"Cannot start from {self.state}")
    
    def stop(self):
        """Stop conveyor"""
        if self.state == ConveyorState.RUNNING:
            self.state = ConveyorState.STOPPED
            self.speed_rpm = 0.0
    
    def get_info(self) -> dict:
        """Return component info for logging"""
        return {
            "id": self.id,
            "state": self.state.value,
            "speed_rpm": self.speed_rpm,
            "load_kg": self.load_kg,
            "position_mm": self.position_mm
        }
```

### 3. Logic (`src/mock_up/logic.py`)

**Purpose:** Implement the control logic from PLC documentation

**Translate PLC Logic Into:**
- Decision functions (given inputs, what should happen?)
- Condition checks (is transition X valid?)
- Timing calculations (when should event Y occur?)
- Dependency resolution (component A affects B)

**Example Translation:**

*PLC Documentation Says:*
> "If conveyor_1 reaches 80% capacity AND motor_1 speed < 100 RPM, slow conveyor_2 by 50%"

*Translate To:*
```python
def conveyor_load_logic(system: SystemState) -> List[Action]:
    """Logic for handling conveyor overload"""
    actions = []
    
    conveyor_1 = system.get_component('conveyor_1')
    if conveyor_1.load_kg >= (conveyor_1.max_capacity_kg * 0.8):
        motor_1 = system.get_component('motor_1')
        if motor_1.speed_rpm < 100:
            # Issue action to slow conveyor_2
            actions.append(SlowConveyor('conveyor_2', 0.5))
    
    return actions
```

### 4. Configuration (`src/mock_up/config.py`)

**Purpose:** Externalize all configurable parameters

**Include:**
- Physical parameters (conveyor length, motor max speed, sensor range)
- Timing constants (startup time, transition delays)
- Capacity thresholds (conveyor max load, buffer size)
- Initial states (what components start in)

**Structure:**
```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class ComponentConfig:
    """Configuration for a single component"""
    id: str
    max_speed: float
    max_capacity: float
    startup_time: float  # seconds
    shutdown_time: float  # seconds
    cycle_time: float  # seconds

@dataclass
class SimulationConfig:
    """Overall simulation configuration"""
    components: Dict[str, ComponentConfig]
    simulation_time_hours: int = 24
    log_level: str = "INFO"
    log_format: str = "json"
    
    @classmethod
    def from_yaml(cls, path: str):
        """Load configuration from YAML file"""
        pass
```

### 5. Simulator (`src/simulation/simulator.py`)

**Purpose:** Orchestrate simulation execution

**Key Responsibilities:**
- Manage virtual time
- Schedule and execute events
- Coordinate component updates
- Interface with logger

**Execution Model:**

```
┌─────────────────────────────────────┐
│ Initialize System (state, config)   │
└────────────────┬────────────────────┘
                 │
         ┌───────▼────────┐
         │ Get next event │
         │ from scheduler │
         └────────┬───────┘
                  │
          ┌───────▼────────┐
          │ Execute event  │
          │ (may trigger   │
          │  state changes)│
          └────────┬───────┘
                   │
           ┌───────▼────────┐
           │ Log changes    │
           │ to logger      │
           └────────┬───────┘
                    │
            ┌───────▼────────┐
        ┌───┤ More time?    │
        │   └────────────────┘
    YES │        │ NO
        │        └──────────────────┐
        │                            │
        └────────────────────┐       │
                            │       │
                    ┌───────┴───┐   │
                    │ Finalize  │   │
                    │ logging   │   │
                    └───────────┘   │
                                    │
                            ┌───────▼───┐
                            │ Return    │
                            │ results   │
                            └───────────┘
```

### 6. Logger (`src/logging/logger.py`)

**Purpose:** Capture and persist system behavior

**Log Every:**
- State change (component, old state, new state, timestamp)
- Event triggered (what, when, why)
- Condition evaluated (expression, result)
- Performance metric (throughput, cycle time)
- Error or warning

**Example Log Entry:**
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "type": "state_change",
  "component": "conveyor_1",
  "old_state": "IDLE",
  "new_state": "RUNNING",
  "trigger": "start_signal_received",
  "details": {
    "speed_rpm": 100.0,
    "acceleration_time_ms": 500
  }
}
```

---

## Component Interaction Model

### Event Flow

Most interactions follow this pattern:

```
1. INPUT EVENT
   ↓
2. CHECK CONDITIONS (from logic.py)
   ├─ Is state transition valid?
   ├─ Are timing constraints met?
   ├─ Are dependencies satisfied?
   ↓
3. EXECUTE TRANSITION
   ├─ Update component state
   ├─ Update affected subsystems
   └─ Calculate side effects (e.g., heat, power consumption)
   ↓
4. LOG EVENT
   └─ Record state change and metadata
   ↓
5. SCHEDULE NEXT EVENTS
   └─ E.g., "motor will reach full speed in 2 seconds"
```

### Dependency Management

Components often depend on others:

```
Example: Conveyor requires motor to run

┌─────────────────┐
│   Motor        │
│ (provides RPM) │
└────────┬────────┘
         │ controls
         │
┌────────▼────────┐
│   Conveyor      │
│ (needs RPM>0)   │
└─────────────────┘

Implementation:
- Conveyor reads Motor.speed_rpm
- Logic checks "if motor.speed_rpm > 0 then conveyor can run"
- Motor state change triggers conveyor update
```

---

## State Machine Patterns

### Pattern 1: Simple On/Off Component

```
     ┌──────────┐
     │   OFF    │
     └────┬─────┘
          │ start()
          │
     ┌────▼────┐
     │   ON     │
     └────┬─────┘
          │ stop()
          │
          └─────────┘
```

**Example: Light sensor**
```python
class LightSensor:
    state: LightSensorState  # ON or OFF
    
    def detect_light(self):
        self.state = LightSensorState.ON
    
    def no_light(self):
        self.state = LightSensorState.OFF
```

### Pattern 2: Multi-Stage Process

```
┌──────────┐
│  IDLE    │
└─────┬────┘
      │ start()
      │
┌─────▼────────┐
│  WARMING_UP  │
└─────┬────────┘
      │ (after 2s)
      │
┌─────▼──────┐
│  RUNNING   │
└─────┬──────┘
      │ shutdown()
      │
┌─────▼────────┐
│  COOLING_DOWN│
└─────┬────────┘
      │ (after 1s)
      │
┌─────▼────────┐
│  OFF         │
└──────────────┘
```

**Example: Motor with startup sequence**
```python
class Motor:
    state: MotorState
    
    def start(self):
        if self.state == MotorState.IDLE:
            self.state = MotorState.WARMING_UP
            # Schedule transition to RUNNING after 2 seconds
            schedule_event(2.0, self._finish_startup)
    
    def _finish_startup(self):
        self.state = MotorState.RUNNING
```

### Pattern 3: Conditional Transitions

```
          ┌──────────┐
          │   IDLE   │
          └─────┬────┘
                │
         ┌──────┴──────┐
         │ check_input()│
         └──┬───────┬──┘
            │       │
    ┌───────▼─┐  ┌──▼─────────┐
    │ FAST_RUN│  │ SLOW_RUN   │
    └─────────┘  └────────────┘
```

**Example: Conveyor speed based on load**
```python
def update_conveyor_speed(conveyor: Conveyor, system: SystemState):
    if conveyor.load_kg > 80:
        conveyor.state = ConveyorState.SLOW_RUN
        conveyor.speed_rpm = 50
    elif conveyor.load_kg > 50:
        conveyor.state = ConveyorState.MEDIUM_RUN
        conveyor.speed_rpm = 75
    else:
        conveyor.state = ConveyorState.FAST_RUN
        conveyor.speed_rpm = 100
```

---

## Design Patterns for Common Scenarios

### Scenario 1: Timing-Based Transitions

**Problem:** Motor needs 3 seconds to reach full speed

**Solution:** Schedule a follow-up event

```python
class Motor:
    def start(self):
        self.state = MotorState.STARTING
        self.speed_rpm = 0
        
        # Schedule ramp-up completion
        simulator.schedule_event(
            delay=3.0,
            callback=self._finish_startup
        )
    
    def _finish_startup(self):
        self.speed_rpm = 100.0
        self.state = MotorState.RUNNING
```

### Scenario 2: Cross-Component Synchronization

**Problem:** Multiple components need to start/stop together

**Solution:** Centralized logic function

```python
def synchronize_conveyor_group(system: SystemState):
    """Ensure all conveyors in group are synced"""
    leader_conveyor = system.get_component('conveyor_1')
    other_conveyors = [
        system.get_component(f'conveyor_{i}')
        for i in [2, 3, 4]
    ]
    
    for conveyor in other_conveyors:
        conveyor.state = leader_conveyor.state
        conveyor.speed_rpm = leader_conveyor.speed_rpm
```

### Scenario 3: Cascading Failures

**Problem:** Motor failure should stop downstream components

**Solution:** Propagate state changes

```python
def on_motor_failure(motor: Motor, system: SystemState):
    """Handle motor failure impact"""
    motor.state = MotorState.ERROR
    
    # Find dependent conveyors
    dependent = find_dependent_components(motor, system)
    for component in dependent:
        component.state = ComponentState.STOPPED
        component.speed_rpm = 0.0
    
    # Log cascade
    logger.log_event(
        event="cascade_failure",
        source=motor.id,
        affected=len(dependent)
    )
```

---

## Testing Architecture

### Unit Tests (Test Individual Components)

```python
# tests/unit/test_motor.py

def test_motor_start():
    motor = Motor(id='m1')
    assert motor.state == MotorState.IDLE
    motor.start()
    assert motor.state == MotorState.WARMING_UP

def test_motor_invalid_transition():
    motor = Motor(id='m1', state=MotorState.RUNNING)
    with pytest.raises(InvalidTransitionError):
        motor.start()  # Can't start twice
```

### Integration Tests (Test Component Interactions)

```python
# tests/integration/test_conveyor_system.py

def test_motor_drives_conveyor():
    system = SystemState(config)
    motor = system.get_component('motor_1')
    conveyor = system.get_component('conveyor_1')
    
    motor.start()
    update_system(system)  # Apply logic
    
    assert conveyor.state == ConveyorState.RUNNING
    assert conveyor.speed_rpm == motor.speed_rpm
```

### Simulation Tests (Test Overall Behavior)

```python
# tests/simulation/test_long_run.py

def test_24_hour_simulation():
    sim = Simulator(config, duration_hours=24)
    sim.run()
    
    # Verify simulation completed
    assert not sim.has_errors
    
    # Verify logs exist and are valid
    logs = sim.get_logs()
    assert len(logs) > 10000  # Many events in 24 hours
    assert all(log.timestamp.valid for log in logs)
```

---

## Performance Considerations

### Simulation Speed

Target: **Faster than real-time** (e.g., 24 hours simulated in <1 hour real time)

**Optimization Strategies:**
- Use event-driven model (don't poll every millisecond)
- Cache frequently-accessed states
- Batch log writes
- Use NumPy for numerical calculations

### Memory Usage

Target: **<1 GB** for 24-hour simulation

**Optimization Strategies:**
- Stream logs to disk rather than keeping all in memory
- Use compressed format for historical data
- Prune irrelevant log entries (e.g., no-op events)

### Scalability

**Design allows:**
- ✓ 100+ components
- ✓ 1000+ state transitions per second
- ✓ Extended simulation periods (weeks/months virtual time)

---

## Summary: Implementation Order

1. **Define Components** (`src/mock_up/components.py`)
   - Identify all physical components
   - Define states for each
   - Implement basic data classes

2. **Implement Logic** (`src/mock_up/logic.py`)
   - Translate PLC documentation
   - Implement decision functions
   - Test against documentation

3. **Build State Manager** (`src/mock_up/state.py`)
   - Create system-wide state tracker
   - Ensure consistency invariants

4. **Create Configuration** (`src/mock_up/config.py`)
   - Externalize all parameters
   - Make system configurable

5. **Develop Simulator** (`src/simulation/simulator.py`)
   - Implement event loop
   - Add time management
   - Connect to logger

6. **Build Logger** (`src/logging/logger.py`)
   - Capture all events
   - Implement multiple formats
   - Add filtering/compression

7. **Write Tests** (`tests/`)
   - Unit tests for components
   - Integration tests for interactions
   - Simulation validation tests

---

## Next Steps

- Review [docs/PLC_DOCUMENTATION.md](PLC_DOCUMENTATION.md) to understand system specifics
- Check [docs/LOGGING_SPECIFICATION.md](LOGGING_SPECIFICATION.md) for logging standards
- Start with Phase 1 in [docs/PROJECT_PHASES.md](PROJECT_PHASES.md)
