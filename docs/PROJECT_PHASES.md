# Project Phases & Timeline

## Overview

The project is broken into **5 core phases** plus an **optional extension**. Each phase has clear objectives, deliverables, and success criteria.

---

## Phase 1: Analysis & Documentation Review

**Duration:** 1-2 weeks  
**Objective:** Understand the drone factory system deeply

### Tasks

1. **Read System Documentation**
   - Review provided PLC documentation (Kod_WSConv_Sven2022.pdf)
   - Identify key subsystems and components
   - Map input/output signals
   - Document state transitions and timing constraints
   - Follow guide: [docs/PLC_DOCUMENTATION.md](PLC_DOCUMENTATION.md)

2. **Create System Analysis Document**
   - List all components (conveyors, motors, sensors, actuators)
   - Document their interactions
   - Identify timing constraints and dependencies
   - Map state machines for each subsystem

3. **Design High-Level Architecture**
   - Sketch component hierarchy
   - Define state representations
   - Plan simulation interfaces
   - Refer to: [docs/ARCHITECTURE.md](ARCHITECTURE.md)

### Deliverables

- ✓ System analysis report (markdown or PDF)
- ✓ Component inventory with specifications
- ✓ State transition diagrams (for key subsystems)
- ✓ Architecture design document (draft)

### Success Criteria

- [ ] All major components identified
- [ ] All state transitions documented
- [ ] Timing constraints clearly specified
- [ ] Team agrees on architecture approach

---

## Phase 2: Mock-up Implementation (Python)

**Duration:** 2-3 weeks  
**Objective:** Translate documentation into executable Python code

### Tasks

1. **Implement Core Components**
   - Location: `src/mock_up/components.py`
   - Create classes for each major component
   - Define states (enums)
   - Implement transition logic
   - Start with simplest components first (sensors)

2. **Implement State Management**
   - Location: `src/mock_up/state.py`
   - Create global system state container
   - Track component states
   - Handle state persistence

3. **Translate PLC Logic**
   - Location: `src/mock_up/logic.py`
   - Convert state diagrams to code
   - Implement conditional logic
   - Handle timing and delays
   - Manage inter-component dependencies

4. **Create Configuration**
   - Location: `src/mock_up/config.py`
   - Define all configurable parameters
   - Timing constants
   - Initial states
   - System thresholds

### Code Structure Example

```python
# src/mock_up/components.py

from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class ConveyorState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ConveyorMotor:
    id: str
    state: ConveyorState = ConveyorState.IDLE
    speed: float = 0.0
    
    def start(self):
        """Transition to RUNNING state"""
        self.state = ConveyorState.RUNNING
        self.speed = 100.0  # RPM
    
    def stop(self):
        """Transition to STOPPED state"""
        self.state = ConveyorState.STOPPED
        self.speed = 0.0
```

### Deliverables

- ✓ Functional Python mock-up of all components
- ✓ State management system
- ✓ Logic implementation matching documentation
- ✓ Configuration file with all parameters
- ✓ Code documentation (docstrings)

### Success Criteria

- [ ] All components implement documented behavior
- [ ] No syntax errors, passes basic imports
- [ ] State transitions work correctly
- [ ] Configuration is externalized
- [ ] Code is readable and documented

### Guidance: Translating PLC Documentation

**Step 1: Identify State Diagrams**
- Extract state transition tables from documentation
- Create visual maps (tools: draw.io, Lucidchart)
- Note transition conditions and timing

**Step 2: Define Data Structures**
```python
# Example: Motor with states
class MotorState(Enum):
    OFF = "off"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"

@dataclass
class Motor:
    state: MotorState
    power: float  # watts
    rpm: float
    start_time: datetime
```

**Step 3: Implement Transition Logic**
```python
def on_start_signal(motor: Motor, timestamp: datetime):
    """Handle start signal - translate PLC logic"""
    if motor.state == MotorState.OFF:
        motor.state = MotorState.STARTING
        motor.start_time = timestamp
        # Set startup ramp
    else:
        # Invalid state transition - log error
        pass
```

**Step 4: Test Transitions**
- Create simple test cases for each transition
- Verify timing and conditions match documentation

---

## Phase 3: Verification & Testing

**Duration:** 1-2 weeks  
**Objective:** Ensure implementation matches documentation

### Tasks

1. **Create Test Cases**
   - Location: `tests/` folder
   - Unit tests for each component
   - Integration tests for subsystems
   - Edge case and error scenarios
   - Follow guide: [docs/VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)

2. **Implement Validators**
   - Location: `src/verification/validators.py`
   - Check invariants (e.g., motor can't be at 2 states simultaneously)
   - Verify timing constraints
   - Validate state transition rules

3. **Run Conformance Tests**
   - Compare mock-up behavior against documentation
   - Document any discrepancies
   - Create test scenarios that exercise all transitions
   - Verify with real system data (if available)

### Test Structure

```python
# tests/unit/test_motor.py

import pytest
from mock_up.components import Motor, MotorState

def test_motor_start_transition():
    """Verify motor transitions from OFF to RUNNING"""
    motor = Motor(state=MotorState.OFF)
    motor.start()
    assert motor.state == MotorState.RUNNING
    assert motor.rpm > 0

def test_motor_invalid_transition():
    """Verify invalid transitions are rejected"""
    motor = Motor(state=MotorState.STARTING)
    # Can't transition from STARTING to OFF (invalid)
    with pytest.raises(InvalidTransitionError):
        motor.stop_immediately()

def test_motor_timing():
    """Verify motor respects timing constraints"""
    # E.g., motor must take 2 seconds to reach full speed
    motor = Motor(state=MotorState.OFF)
    motor.start()
    assert motor.rpm < 100  # Not at full speed immediately
    # After 2 seconds (simulated time)
    simulate_time(2.0)
    assert motor.rpm >= 100  # Now at full speed
```

### Deliverables

- ✓ Comprehensive test suite (unit + integration)
- ✓ Verification report documenting conformance
- ✓ Test coverage report (aim for >80%)
- ✓ Identified discrepancies and resolutions

### Success Criteria

- [ ] All documented behaviors have test cases
- [ ] Test coverage ≥80%
- [ ] All tests pass
- [ ] Discrepancies with documentation resolved
- [ ] Verification artifacts saved for final report

---

## Phase 4: Simulation & Logging

**Duration:** 1-2 weeks  
**Objective:** Build simulation engine and data logging

### Tasks

1. **Develop Simulation Engine**
   - Location: `src/simulation/simulator.py`
   - Manage virtual time
   - Schedule and execute events
   - Coordinate components
   - Follow guide: [docs/SIMULATION_GUIDE.md](SIMULATION_GUIDE.md)

2. **Implement Time Management**
   - Location: `src/simulation/time_manager.py`
   - Virtual clock (accelerated/real-time)
   - Event scheduling and execution
   - Deterministic behavior

3. **Create Logging Framework**
   - Location: `src/logging/logger.py`
   - Capture state changes
   - Record events and transitions
   - Log performance metrics
   - Follow guide: [docs/LOGGING_SPECIFICATION.md](LOGGING_SPECIFICATION.md)

4. **Design Log Format**
   - JSON for structured queries
   - CSV for analysis
   - Binary (optional) for large datasets
   - Example:
     ```json
     {
       "timestamp": "2024-01-15T10:30:45.123Z",
       "component": "motor_1",
       "event": "state_change",
       "old_state": "OFF",
       "new_state": "RUNNING",
       "details": {"rpm": 1000, "power": 500}
     }
     ```

5. **Run Extended Simulations**
   - Execute 24+ hour (virtual) simulations
   - Save logs to `data/logs/`
   - Organize by date and scenario
   - Monitor system stability

### Simulation Code Example

```python
# src/simulation/simulator.py

from datetime import datetime, timedelta
from mock_up.state import SystemState
from logging.logger import Logger

class Simulator:
    def __init__(self, config, duration_hours=24):
        self.config = config
        self.system = SystemState()
        self.logger = Logger(config.log_file)
        self.duration = timedelta(hours=duration_hours)
        self.current_time = datetime.now()
    
    def run(self):
        """Run simulation for configured duration"""
        end_time = self.current_time + self.duration
        
        while self.current_time < end_time:
            # Check for triggered events
            events = self.system.get_pending_events(self.current_time)
            for event in events:
                event.execute()
                self.logger.log_event(event, self.current_time)
            
            # Advance time
            self.current_time += timedelta(seconds=1)
        
        self.logger.finalize()
        print(f"Simulation complete. Logs saved to {self.logger.path}")
```

### Deliverables

- ✓ Working simulation engine
- ✓ Deterministic virtual time system
- ✓ Comprehensive logging framework
- ✓ Multiple 24+ hour simulation runs
- ✓ Log files in standardized format
- ✓ Documentation of logging schema

### Success Criteria

- [ ] Simulator runs without crashes
- [ ] Virtual time advances predictably
- [ ] All state changes are logged
- [ ] Logs are parseable and queryable
- [ ] Simulation completes 24+ hours without errors
- [ ] Performance is reasonable (simulation runs faster than real-time)

---

## Phase 5: Analysis & System Dynamics

**Duration:** 2-3 weeks  
**Objective:** Analyze simulation results and extract insights

### Tasks

1. **Parse and Load Logs**
   - Location: `src/logging/parser.py`
   - Read log files efficiently
   - Build DataFrames (pandas)
   - Handle large datasets

2. **Analyze System Behavior**
   - Create Jupyter notebooks in `analysis/notebooks/`
   - Study state distribution
   - Identify patterns and cycles
   - Detect anomalies or deviations
   - Measure performance metrics (throughput, cycle time)

3. **Generate Visualizations**
   - Timeline plots of component states
   - Scatter plots of interactions
   - Heatmaps of state transitions
   - Performance metrics dashboards

4. **Document Findings**
   - System dynamics report
   - Interaction patterns
   - Performance characteristics
   - Deviations from expected behavior
   - Recommendations for improvement

### Analysis Example

```python
# analysis/notebooks/01_system_dynamics.ipynb

import pandas as pd
import matplotlib.pyplot as plt

# Load logs
logs = pd.read_json('data/logs/simulation_2024_01_15.jsonl', lines=True)

# Analyze state transitions
motor_logs = logs[logs['component'] == 'motor_1']
transitions = motor_logs.groupby(['old_state', 'new_state']).size()

# Visualize
plt.figure(figsize=(10, 6))
logs.groupby(['component', 'event']).size().plot(kind='bar')
plt.title('Event Distribution Across Components')
plt.ylabel('Count')
plt.show()
```

### Deliverables

- ✓ Analysis notebooks (Jupyter)
- ✓ Parsed and cleaned datasets
- ✓ System dynamics report
- ✓ Visualizations and plots
- ✓ Performance metrics summary
- ✓ Anomaly/deviation analysis

### Success Criteria

- [ ] All simulation logs are analyzed
- [ ] Key findings are documented
- [ ] Visualizations support findings
- [ ] Recommendations are actionable
- [ ] Report is clear and well-organized

---

## Phase 6 (Optional): Embeddings & Anomaly Detection

**Duration:** 1-2 weeks (if time permits)  
**Objective:** Apply ML-based techniques for pattern analysis

### Tasks

1. **Feature Engineering**
   - Extract behavioral vectors from logs
   - Examples: state duration, transition patterns, timing deviations
   - Normalize features

2. **Generate Embeddings**
   - Use autoencoders or similar techniques
   - Create vector representations of system behavior windows
   - Store in `data/embeddings/`

3. **Similarity & Anomaly Detection**
   - Implement similarity search
   - Identify unusual behavior patterns
   - Cluster similar operational modes
   - Detect deviations early

4. **Report Findings**
   - Novel patterns discovered
   - Anomalies detected in simulation
   - Implications for system health

### Deliverables

- ✓ Feature extraction pipeline
- ✓ Embedding model (trained or pre-trained)
- ✓ Similarity search implementation
- ✓ Anomaly detection results
- ✓ Analysis and insights report

---

## Timeline & Milestones

| Phase | Duration | Key Deliverable | Checkpoint |
|-------|----------|-----------------|-----------|
| 1. Analysis | 1-2 weeks | System documentation & design | Team agreement on architecture |
| 2. Mock-up | 2-3 weeks | Working Python implementation | All components functional |
| 3. Verification | 1-2 weeks | Test suite + conformance report | Test coverage ≥80%, all tests pass |
| 4. Simulation & Logging | 1-2 weeks | 24+ hour simulation runs, logs | Multiple clean simulation runs |
| 5. Analysis | 2-3 weeks | Analysis report + visualizations | Findings documented and validated |
| 6. Optional Extension | 1-2 weeks | Embedding analysis report | Novel insights from ML analysis |

**Total Duration:** 8-14 weeks (depending on team size and scope)

---

## Important Checkpoints

After each phase, verify:

✓ **Code Quality**
- No syntax errors
- Consistent naming and style
- Comprehensive docstrings
- Tests passing

✓ **Documentation**
- Changes logged (git commits)
- Design decisions documented
- Discrepancies from original system noted
- Future improvements identified

✓ **Reproducibility**
- Simulations can be re-run with same results
- Logs are parseable and consistent
- Configuration is version-controlled

---

## How to Track Progress

1. **Use Git for version control**
   ```bash
   git add .
   git commit -m "Phase X: Specific accomplishment"
   git push
   ```

2. **Maintain PROGRESS.md in repo**
   - Track completed tasks
   - Note blockers or decisions
   - Update regularly

3. **Create Issues for blockers**
   - Document problems found
   - Assign to team members
   - Discuss and resolve

4. **Review code regularly**
   - Weekly team code reviews
   - Discuss design decisions
   - Share learnings

---

## Getting Unstuck

If you're blocked:

1. **Check similar implementations** — Review `src/` for working examples
2. **Review tests** — `tests/` shows expected behavior
3. **Read documentation** — Each module has detailed docs
4. **Trace execution** — Add print statements or use debugger
5. **Consult team** — Discuss with colleagues

---

## Next Steps

- ✅ Understand project timeline → Ready for Phase 1
- 📖 Read [docs/PLC_DOCUMENTATION.md](PLC_DOCUMENTATION.md) → Start system analysis
- 🔧 Read [docs/ARCHITECTURE.md](ARCHITECTURE.md) → Design approach
- 💻 Begin implementation → Follow Phase 2 guidance
