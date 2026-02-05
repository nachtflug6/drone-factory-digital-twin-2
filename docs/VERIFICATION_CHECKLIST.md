# Verification Checklist & Methodology

## Overview

This document describes how to verify that your mock-up implementation correctly reflects the documented system behavior.

---

## Verification Philosophy

**Verification = Evidence that implementation matches documentation**

Your goal is to build confidence that:
1. ✓ All documented states and transitions exist
2. ✓ All timing constraints are met
3. ✓ All dependencies between components are correct
4. ✓ All edge cases are handled
5. ✓ System is deterministic and repeatable

---

## Phase 1: Static Verification (Code Review)

Before running anything, check the code itself.

### Checklist: Component Coverage

- [ ] All components mentioned in documentation have Python classes
- [ ] Each component has all documented states defined in an Enum
- [ ] Each component has all documented inputs/outputs as fields/methods
- [ ] Documentation and code use consistent terminology
- [ ] No typos in state names (case-sensitive!)

**Example:**
```python
# From documentation: "Motor has states: IDLE, ACCELERATING, RUNNING, ERROR"
# Code should have:
class MotorState(Enum):
    IDLE = "idle"
    ACCELERATING = "accelerating"
    RUNNING = "running"
    ERROR = "error"
```

### Checklist: Transition Coverage

For each component, verify transitions:

- [ ] Every transition mentioned in documentation is implemented
- [ ] Every transition has clear conditions
- [ ] Transitions are implemented in guard functions or conditional logic
- [ ] Invalid transitions are prevented (e.g., no direct IDLE→RUNNING without acceleration)

**Example:**

Documentation says:
> Motor state machine:
> - IDLE → ACCELERATING: When START_SIGNAL received
> - ACCELERATING → RUNNING: After 2 seconds
> - RUNNING → IDLE: When STOP_SIGNAL received

Code should have:
```python
# Can only transition IDLE→ACCELERATING when condition met
if motor.state == MotorState.IDLE and start_signal == True:
    motor.state = MotorState.ACCELERATING
    schedule_event(2.0, motor.finish_acceleration)

# Can't transition IDLE→RUNNING directly
if motor.state == MotorState.IDLE and target_state == MotorState.RUNNING:
    raise InvalidTransitionError("Must accelerate first")
```

### Checklist: Timing Constraints

- [ ] All timing constants are extracted from documentation
- [ ] Timing values are stored in configuration (not hardcoded)
- [ ] Timing is implemented correctly (delays, ramps, etc.)
- [ ] Time calculations are accurate to documentation

**Example:**

Documentation says:
> "Motor reaches full speed in 2.0 ± 0.5 seconds"

Code should have:
```python
# In config.py
MOTOR_RAMP_UP_TIME = 2.0  # seconds (documented as ~2 seconds)

# In component
def update(self, elapsed_seconds):
    progress = min(elapsed_seconds / MOTOR_RAMP_UP_TIME, 1.0)
    self.speed_rpm = self.target_speed_rpm * progress
```

---

## Phase 2: Unit Testing

Test individual components in isolation.

### Test Structure

```python
# tests/unit/test_motor.py

import pytest
from mock_up.components import Motor, MotorState

class TestMotorStateTransitions:
    """Test all documented state transitions"""
    
    def test_motor_idle_to_accelerating(self):
        """Verify: IDLE → ACCELERATING on START signal"""
        motor = Motor(id='m1')
        assert motor.state == MotorState.IDLE
        
        motor.start(target_speed=1000)
        
        assert motor.state == MotorState.ACCELERATING
    
    def test_motor_cannot_start_twice(self):
        """Verify: Can't start motor that's already running"""
        motor = Motor(id='m1')
        motor.start(target_speed=1000)
        
        # Trying to start again should fail
        with pytest.raises(InvalidTransitionError):
            motor.start(target_speed=500)
    
    def test_motor_acceleration_timing(self):
        """Verify: Motor takes 2.0 seconds to reach full speed"""
        from datetime import datetime, timedelta
        
        motor = Motor(id='m1')
        start_time = datetime.now()
        
        motor.start(target_speed=1000)
        
        # After 1 second
        elapsed_1s = start_time + timedelta(seconds=1)
        motor.update(elapsed_1s)
        assert 450 < motor.speed_rpm < 550  # ~50% of target
        
        # After 2 seconds
        elapsed_2s = start_time + timedelta(seconds=2)
        motor.update(elapsed_2s)
        assert motor.speed_rpm == 1000  # Full speed
        assert motor.state == MotorState.RUNNING
```

### Unit Test Checklist

For each component type:

- [ ] Create test file in `tests/unit/test_<component>.py`
- [ ] Test each documented state
- [ ] Test each documented transition
- [ ] Test timing constraints
- [ ] Test invalid transitions (should fail)
- [ ] Test edge cases (boundary conditions)
- [ ] Achieve >80% code coverage

### Running Unit Tests

```bash
# Run all tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=src/mock_up

# Run specific test
pytest tests/unit/test_motor.py::TestMotorStateTransitions::test_motor_idle_to_accelerating -v
```

---

## Phase 3: Integration Testing

Test components working together.

### Test Component Interactions

```python
# tests/integration/test_conveyor_system.py

import pytest
from datetime import datetime, timedelta
from mock_up.state import SystemState
from mock_up.config import SimulationConfig

class TestConveyorSystem:
    """Test motor driving conveyor"""
    
    def test_motor_start_drives_conveyor(self):
        """Verify: When motor starts, conveyor runs"""
        config = SimulationConfig()
        system = SystemState(config)
        
        # Get components
        motor = system.get_component('motor_1')
        conveyor = system.get_component('conveyor_1')
        
        # Initial state
        assert motor.state == MotorState.IDLE
        assert conveyor.state == ConveyorState.IDLE
        
        # Start motor
        motor.start(target_speed=1000)
        
        # After acceleration, conveyor should run
        current_time = datetime.now() + timedelta(seconds=2.5)
        system.update(current_time)
        
        assert motor.state == MotorState.RUNNING
        assert conveyor.state == ConveyorState.RUNNING
    
    def test_conveyor_stops_when_overloaded(self):
        """Verify: Overloaded conveyor stops and alerts"""
        config = SimulationConfig()
        system = SystemState(config)
        conveyor = system.get_component('conveyor_1')
        
        conveyor.start()
        assert conveyor.state == ConveyorState.RUNNING
        
        # Simulate load increase
        conveyor.load_kg = 60  # Exceeds 50 kg limit
        system.update(datetime.now())
        
        assert conveyor.state == ConveyorState.ERROR
        assert conveyor.alert_active == True
```

### Integration Test Checklist

- [ ] Test components that depend on each other
- [ ] Test cascading failures (one component failure affects others)
- [ ] Test synchronization (multiple components coordinated)
- [ ] Test resource contention (competition for shared resources)
- [ ] Test timing dependencies (component B waits for component A)

---

## Phase 4: Simulation Validation

Run simulations and verify behavior.

### Behavioral Validation

```python
# tests/simulation/test_simulation_validity.py

def test_simulation_no_invalid_states():
    """Verify: No component is in impossible state"""
    from simulation.simulator import Simulator
    from mock_up.config import SimulationConfig
    
    config = SimulationConfig(duration_hours=1)
    simulator = Simulator(config)
    simulator.run()
    
    # Check logs for invalid states
    logs = simulator.logger.get_logs()
    state_changes = [l for l in logs if l['event_type'] == 'state_change']
    
    for log in state_changes:
        component = simulator.system.get_component(log['component_id'])
        
        # Verify new_state matches actual component state
        assert log['new_state'] == component.state.value

def test_simulation_timing_constraints():
    """Verify: All timing constraints from documentation are met"""
    from simulation.simulator import Simulator
    
    simulator = Simulator(config)
    simulator.run()
    logs = simulator.logger.get_logs()
    
    # Find all motor acceleration events
    motor_accel_logs = [l for l in logs 
                       if l['component_id'] == 'motor_1' 
                       and 'ACCELERATING' in l.get('event_name', '')]
    
    for i, log in enumerate(motor_accel_logs):
        start_time = datetime.fromisoformat(log['timestamp'])
        # Find when acceleration ends
        end_log = next((l for l in logs[i:] 
                       if l['component_id'] == 'motor_1' 
                       and l.get('new_state') == 'RUNNING'), None)
        
        if end_log:
            end_time = datetime.fromisoformat(end_log['timestamp'])
            accel_duration = (end_time - start_time).total_seconds()
            
            # Should take 2.0 seconds (allow 1% tolerance)
            assert 1.98 < accel_duration < 2.02, \
                f"Acceleration took {accel_duration}s, expected ~2.0s"

def test_simulation_determinism():
    """Verify: Same seed produces same results"""
    from simulation.simulator import Simulator
    
    # Run 1
    config1 = SimulationConfig(seed=42, duration_hours=1)
    sim1 = Simulator(config1)
    sim1.run()
    logs1 = sim1.logger.get_logs()
    
    # Run 2 (same seed)
    config2 = SimulationConfig(seed=42, duration_hours=1)
    sim2 = Simulator(config2)
    sim2.run()
    logs2 = sim2.logger.get_logs()
    
    # Compare logs
    assert len(logs1) == len(logs2), "Different number of events"
    
    for log1, log2 in zip(logs1, logs2):
        assert log1['timestamp'] == log2['timestamp'], "Timestamp differs"
        assert log1['event_type'] == log2['event_type'], "Event type differs"
        assert log1['component_id'] == log2['component_id'], "Component ID differs"
```

### Simulation Validation Checklist

- [ ] Simulation completes without errors
- [ ] All events are properly timestamped
- [ ] No impossible states in logs
- [ ] Timing constraints verified
- [ ] Same seed produces identical results (determinism)
- [ ] Component dependencies respected
- [ ] No deadlocks or livelocks
- [ ] Memory usage stays reasonable

---

## Phase 5: Conformance Testing

Detailed comparison against documentation.

### Test Specification Conformance

Create a test case for each statement in the documentation:

**Documentation Statement:**
> "Motor can only start from IDLE state. Starting takes 2 seconds. After start, motor runs at constant speed until stopped."

**Corresponding Test:**
```python
def test_motor_specification_conformance():
    """Verify complete motor specification"""
    motor = Motor(id='m1')
    
    # "Motor can only start from IDLE state"
    motor.state = MotorState.IDLE
    assert motor.start() == True
    
    motor.state = MotorState.RUNNING
    with pytest.raises(Exception):
        motor.start()  # Should fail
    
    # "Starting takes 2 seconds"
    motor.state = MotorState.IDLE
    start_time = motor.start()
    
    # Not ready after 1 second
    motor.update(start_time + timedelta(seconds=1))
    assert motor.state == MotorState.ACCELERATING
    
    # Ready after 2 seconds
    motor.update(start_time + timedelta(seconds=2))
    assert motor.state == MotorState.RUNNING
    
    # "Motor runs at constant speed until stopped"
    motor.update(start_time + timedelta(seconds=5))  # After 3 more seconds
    assert motor.state == MotorState.RUNNING
    assert motor.speed_rpm == motor.target_speed  # Still constant
```

### Conformance Test Checklist

- [ ] Document every requirement from PLC documentation
- [ ] Create test case for each requirement
- [ ] All tests pass
- [ ] Requirements are prioritized (must-have vs. nice-to-have)
- [ ] Deviations from documentation are documented
- [ ] Document says "ambiguous" → tests clarify interpretation

---

## Phase 6: Property-Based Testing (Advanced)

Use hypothesis library for automated test generation.

```python
from hypothesis import given, strategies as st
from datetime import datetime

class TestMotorProperties:
    """Test invariants that should always be true"""
    
    @given(
        target_speed=st.floats(min_value=0, max_value=10000),
        time_steps=st.lists(st.floats(min_value=0, max_value=0.1), min_size=1, max_size=100)
    )
    def test_speed_never_exceeds_target(self, target_speed, time_steps):
        """Invariant: Motor speed never exceeds target speed"""
        motor = Motor(id='m1')
        motor.start(target_speed=target_speed)
        
        current_time = datetime.now()
        for dt in time_steps:
            current_time += timedelta(seconds=dt)
            motor.update(current_time)
            assert motor.speed_rpm <= target_speed + 0.01, \
                f"Speed {motor.speed_rpm} exceeds target {target_speed}"
    
    @given(st.integers(min_value=1, max_value=100))
    def test_component_count_consistency(self, num_components):
        """Invariant: Component count never changes during simulation"""
        config = SimulationConfig(motor_count=num_components)
        system = SystemState(config)
        
        initial_count = len(system.components)
        
        # Run simulation
        for _ in range(1000):
            system.update(datetime.now())
        
        final_count = len(system.components)
        assert initial_count == final_count
```

---

## Creating a Verification Report

Document your verification efforts:

### Report Template

```markdown
# Verification Report: Drone Factory Digital Twin

## Executive Summary
This report documents verification that the Python mock-up conforms to the documented system behavior.

## 1. Static Verification
- [x] All 12 component types implemented
- [x] 45 state transitions verified
- [x] Timing constraints in config match documentation
- [x] No hardcoded values except in config.py

## 2. Unit Testing
- [x] 85% code coverage
- [x] 127 unit tests pass
- [x] Motor tests: PASS (12 tests)
- [x] Conveyor tests: PASS (15 tests)
- [x] Sensor tests: PASS (8 tests)
- [x] Integration tests: PASS (18 tests)

## 3. Simulation Validation
- [x] 100 hours simulated without error
- [x] No invalid states in logs
- [x] Determinism verified (seed=42 produces identical results)
- [x] Timing constraints within 1% tolerance

## 4. Conformance Testing
- [x] All 34 documented requirements tested
- [x] 3 requirements needed clarification (documented)
- [x] 100% of must-have requirements pass

## 5. Known Issues & Deviations
- Issue: Documentation section 3.2 is ambiguous about conveyor max load
  - Resolution: Implemented as 50 kg, verified with domain expert
  
## 6. Conclusion
The implementation conforms to documented behavior within acceptable tolerances.

Verified by: [Name]
Date: [Date]
```

---

## Verification Checklist

Use this checklist before declaring implementation complete:

### Component Completeness
- [ ] All components from documentation implemented
- [ ] All states defined for each component
- [ ] All inputs/outputs mapped to component fields

### Transition Completeness  
- [ ] All documented transitions implemented
- [ ] Invalid transitions blocked (guards)
- [ ] Timing constraints honored
- [ ] Dependencies between components respected

### Testing Coverage
- [ ] Unit tests: >80% code coverage
- [ ] Integration tests: All components interacting correctly
- [ ] Simulation tests: Extended runs validated
- [ ] Edge cases: Boundary conditions tested

### Determinism & Correctness
- [ ] Same configuration produces same results
- [ ] Random seed controls reproducibility
- [ ] Timing is accurate (±1% tolerance)
- [ ] No deadlocks or livelocks

### Documentation
- [ ] All deviations from documentation noted
- [ ] Ambiguities clarified and documented
- [ ] Assumptions documented
- [ ] Design decisions explained

---

## Next Steps

1. Implement unit tests (Phase 3)
2. Run simulations (Phase 4)
3. Create verification report
4. Address any failures
5. Iterate until all tests pass

See [PROJECT_PHASES.md](PROJECT_PHASES.md#phase-3-verification--testing) for detailed Phase 3 timeline.
