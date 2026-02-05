# About the Documentation Translation

## Overview

This project requires translating **Kod_WSConv_Sven2022.pdf** (PLC documentation) into executable Python code. This document clarifies the approach, scope, and expectations.

---

## What's Been Done (Reference Implementation)

### ✅ Provided as **Orientation/Backbone**

The repository contains a **starting point**, not a complete implementation:

1. **System Analysis** — [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md)
   - Initial analysis of major components
   - Key parameters extracted
   - State machines documented
   - **Status**: 🟡 Starting point for students

2. **Component Classes** — [src/mock_up/components.py](src/mock_up/components.py)
   - 7 skeleton component classes
   - Basic state enums
   - Core method signatures
   - **Status**: 🟡 Needs implementation detail

3. **Configuration** — [src/mock_up/config.py](src/mock_up/config.py)
   - Parameters from documentation
   - Timing values, limits
   - **Status**: ✅ Good reference values

4. **Example** — [examples/ws_conveyor_simulation.py](examples/ws_conveyor_simulation.py)
   - Working demonstration
   - Shows component interaction patterns
   - **Status**: ✅ Reference implementation

### ❌ **NOT Complete** — Students Must Implement

- Detailed control logic in components
- Full state machine implementations
- Edge case handling
- Error recovery logic
- System simulator ([src/simulation/](src/simulation/))
- Logger implementation ([src/logging/](src/logging/))
- Comprehensive test suite
- Integration of all PLC logic

---

## Translation Philosophy

### 🎯 Goal: Functional Digital Twin, Not 1:1 Copy

**You do NOT need to translate every line of PLC code.**

The goal is to create a Python implementation that:
- ✅ **Captures core behavior** of the WS Conveyor system
- ✅ **Preserves essential control logic** (state machines, sequences)
- ✅ **Maintains timing constraints** (ramps, delays, detection times)
- ✅ **Enforces safety rules** (pressure limits, buffer capacity)
- ✅ **Produces realistic simulation results** for analysis

### What to Focus On

#### ✅ High Priority (Must Translate)

1. **State Machines** — IDLE → RUNNING → STOPPED transitions
2. **Control Logic** — When to start/stop components
3. **Sequencing** — Order of operations (elevator up before transfer)
4. **Timing** — Ramp times, detection delays, processing durations
5. **Safety Interlocks** — Pressure limits, buffer overflow prevention
6. **Key Parameters** — Speeds, pressures, capacities

#### 🟡 Medium Priority (Simplify if Needed)

1. **Error Handling** — Basic error states (can simplify recovery)
2. **Mode Selection** — Focus on primary operating mode
3. **Detailed Sensor Logic** — Simplified threshold detection OK
4. **Communication** — Ignore network/protocol details

#### ❌ Low Priority (Can Ignore)

1. **Hardware Addresses** — EtherCAT I/O mappings, device IDs
2. **HMI Details** — Button layouts, screen graphics
3. **Diagnostic Counters** — Runtime statistics, maintenance counters
4. **Calibration Routines** — System-specific tuning procedures
5. **Vendor-Specific Code** — Device driver implementations

---

## Understanding the PLC Documentation

### Types of Code in Kod_WSConv_Sven2022.pdf

#### 1. Structured Text (ST) — Pages 10-11, 33-39
**Text-based programming language**

Example from PDF:
```
IF conveyer_on AND NOT error THEN
    motor_speed := target_speed;
ELSE
    motor_speed := 0;
END_IF;
```

**Translation to Python**:
```python
if self.conveyor_on and not self.error:
    self.motor_speed = self.target_speed
else:
    self.motor_speed = 0
```

✅ **Easiest to translate** — Almost line-by-line mapping possible

---

#### 2. Sequential Function Chart (SFC) — Pages 12-15, 28-30
**Visual state machine diagrams**

Shows:
- **Steps** (rectangular boxes): States like "INIT", "RECEIVING", "PROCESSING"
- **Transitions** (horizontal lines): Conditions to move between states
- **Actions** (in boxes): What happens in each state

Example from Page 15:
```
┌──────────────┐
│     INIT     │  ← Initial step
└──────┬───────┘
       │ [mission_assigned]  ← Transition condition
┌──────▼───────┐
│  RECEIVING   │  ← Next step
└──────┬───────┘
       │ [pallet_arrived]
┌──────▼───────┐
│ PROCESSING   │
└──────────────┘
```

**Translation to Python**:
```python
class DockingStationState(Enum):
    INIT = "init"
    RECEIVING = "receiving"
    PROCESSING = "processing"

def update(self):
    if self.state == DockingStationState.INIT:
        if self.mission_assigned:
            self.state = DockingStationState.RECEIVING
    
    elif self.state == DockingStationState.RECEIVING:
        if self.pallet_arrived:
            self.state = DockingStationState.PROCESSING
```

⚠️ **Requires visual understanding** — Must read diagrams, not just text

---

#### 3. Function Blocks (FB) — Pages 10, 12-14
**Reusable logic modules**

Example: `FB_MC_DOS_Control_DS2toDS6_V1` (Page 14)

This function block controls docking stations DS2-DS6 with:
- Inputs: mission commands, sensor signals
- Outputs: motor controls, status flags
- Internal state: sequence tracking

**Translation to Python**:
```python
class DockingStation:
    """Reusable docking station with mission control"""
    def __init__(self, station_number):
        self.station_number = station_number
        # ... implementation
```

✅ **Maps to Python classes** — One FB ≈ One class

---

#### 4. Global Variable Lists (GVL) — Pages 33-39
**Configuration and data structures**

Example from Appendix:
```
GVL_Pneumatic
  - ifm_q3_pressure_sensor_value: REAL (bar)
  - ifm_sd5000_temperature_sensor_value: REAL (°C)
  - ifm_sd5000_flow_rate_sensor_value: REAL (nm³/h)
```

**Translation to Python** (already done in [src/mock_up/config.py](src/mock_up/config.py)):
```python
@dataclass
class SimulationConfig:
    pneumatic_target_pressure: float = 6.0  # bar
    pneumatic_max_flow: float = 15.0  # nm³/h
```

✅ **Straightforward extraction** — Copy values to config

---

#### 5. Ladder Logic (If Present)
**Visual relay-based logic**

Shows logical connections between variables using:
- Contacts (switches)
- Coils (outputs)
- Parallel/series connections

⚠️ **Not prevalent in this PDF** — Mostly SFC and ST

If encountered, translate logic gates to Python:
```
--| |--   (normally open contact)   →  if variable:
--|\|--   (normally closed contact) →  if not variable:
--( )--   (coil)                     →  output = True
```

---

## Translation Workflow (Step-by-Step)

### Step 1: Identify Components (Week 1)
1. Read through Kod_WSConv_Sven2022.pdf
2. List all major subsystems:
   - Conveyor motor (done ✅)
   - Transfer elevator (done ✅)
   - Buffer system (done ✅)
   - Docking stations DS1-DS6 (skeleton ✅)
   - Pneumatic system (done ✅)
   - RFID readers (done ✅)
3. For each, note:
   - Inputs (sensors, commands)
   - Outputs (actuators, status)
   - States (from SFC diagrams)

### Step 2: Analyze One Component (Week 1)
Pick the **simplest component** first (e.g., RFID reader):

1. Find all references in PDF:
   - Page 9: POU_ReadRFID_Tag (logic)
   - Page 35: GVL_RFID (variables)
2. Draw state machine:
   ```
   IDLE → DETECTING (0.5s delay) → IDENTIFIED
   ```
3. List transitions:
   - IDLE → DETECTING: pallet arrives
   - DETECTING → IDENTIFIED: 0.5s elapsed
   - IDENTIFIED → IDLE: pallet leaves
4. Note parameters:
   - Detection delay: 0.5 seconds
   - Tag format: 8-byte array → HEX string

### Step 3: Implement Component (Week 2)
Extend skeleton in [src/mock_up/components.py](src/mock_up/components.py):

```python
class RFIDReader:
    def detect(self, tag: str):
        """Start detecting pallet tag"""
        if self.state == RFIDState.IDLE:
            self.tag_detected = tag
            self.state = RFIDState.DETECTING
            self.detect_start_time = datetime.now()
            return True
        return False
    
    def update(self, elapsed_time: float):
        """Complete detection after 0.5s delay"""
        if self.state == RFIDState.DETECTING:
            if elapsed_time >= self.detection_delay:
                self.state = RFIDState.IDENTIFIED
```

### Step 4: Test Component (Week 3)
Write unit tests in [tests/unit/](tests/unit/):

```python
def test_rfid_detection_delay():
    """RFID should take 0.5s to detect"""
    rfid = RFIDReader(id="test", detection_delay=0.5)
    rfid.detect("PALLET_001")
    
    # Immediately after detection starts
    rfid.update(elapsed_time=0.1)
    assert rfid.state == RFIDState.DETECTING
    
    # After 0.5 seconds
    rfid.update(elapsed_time=0.5)
    assert rfid.state == RFIDState.IDENTIFIED
```

### Step 5: Repeat for All Components (Weeks 2-5)
- Conveyor motor → control logic for speed ramping
- Elevator → UP/DOWN positioning sequence
- Buffer → queue management and capacity limits
- Docking stations → full SFC implementation
- Pneumatic → pressure monitoring and fault detection

### Step 6: Integration (Week 5)
Implement system-level logic in [src/mock_up/logic.py](src/mock_up/logic.py):

```python
def transfer_pallet_to_station(system_state, station_id, pallet_rfid):
    """Coordinate elevator + transfer + station"""
    # 1. Move elevator down
    # 2. Load pallet
    # 3. Move elevator up
    # 4. Transfer to station
    # Implementation based on pages 15-16 mission sequences
```

---

## Using LLMs for Translation

### Helpful Prompts

**Analyzing SFC Diagrams**:
```
I have an SFC (Sequential Function Chart) from PLC code showing these steps:

INIT → [condition1] → RECEIVING → [condition2] → PROCESSING → [condition3] → SENDING

Help me translate this to Python:
1. Create state enum
2. Suggest transition logic
3. Generate test cases for each transition
```

**Parsing Structured Text**:
```
Here's PLC Structured Text code:

IF buffer_queue_stop_sensor AND NOT buffer_full THEN
    pallet_count := pallet_count + 1;
    buffer_state := PARTIAL;
END_IF;

Translate to Python with:
1. Proper variable names
2. State updates
3. Error checking
```

**Extracting Parameters**:
```
From the GVL (Global Variable List), extract timing parameters:

GVL_HMI:
- hmi_TimeForWaitAtQueue: TIME = T#2s
- hmi_TimeForWaitAfterPassingDS: TIME = T#1s

Convert to Python dataclass fields with appropriate types and defaults.
```

### LLM Limitations

⚠️ **LLMs cannot**:
- Understand visual SFC diagrams (you must describe them textually)
- Know your specific system context (you provide domain knowledge)
- Verify correctness (you must test)
- Replace understanding (you must comprehend the logic)

✅ **LLMs can**:
- Generate boilerplate code structures
- Suggest translation patterns
- Create test case templates
- Explain PLC syntax

---

## Simplification Guidelines

### When to Simplify

**Acceptable simplifications**:
1. **Merge similar states**: If DS2-DS6 behave identically, use one class
2. **Combine minor transitions**: Simplify multi-step sequences if behavior is atomic
3. **Approximate timing**: Use representative values if exact timing isn't critical
4. **Ignore rare modes**: Focus on normal operation, skip diagnostic modes

**Unacceptable simplifications**:
1. ❌ Removing safety interlocks (pressure limits, buffer capacity)
2. ❌ Skipping major states (e.g., removing PROCESSING state)
3. ❌ Ignoring timing constraints (e.g., RFID 0.5s delay)
4. ❌ Removing critical components (e.g., skipping elevator)

### Documentation of Simplifications

**If you simplify**, document it:

```python
class DockingStation:
    """
    Simplified docking station implementation.
    
    Simplifications from PLC code:
    - Merged DS2-DS6 into single class (behavior identical)
    - Omitted diagnostic mode (rarely used)
    - Simplified error recovery (auto-reset after 5s)
    
    Preserved behavior:
    - Full SFC state machine (INIT → RECEIVING → PROCESSING → SENDING)
    - Mission-driven operation
    - RFID pallet tracking
    """
```

---

## Verification Strategy

### How to Know Your Translation is Correct

1. **State Coverage**
   - ✅ All states from SFC diagrams implemented?
   - ✅ All transitions documented?

2. **Timing Validation**
   - ✅ Ramp times match documentation? (2s conveyor ramp)
   - ✅ Detection delays correct? (0.5s RFID)
   - ✅ Movement times realistic? (0.5s elevator)

3. **Parameter Accuracy**
   - ✅ Speeds within documented range? (0-0.18 m/s conveyor)
   - ✅ Pressures match specifications? (6 bar ± 0.5)
   - ✅ Capacities correct? (2 pallet buffer)

4. **Behavior Testing**
   - ✅ Unit tests for each component?
   - ✅ Integration tests for sequences?
   - ✅ Simulation produces expected results?

### Compare Against Reference

Use [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md) as a checklist:
- Did you implement all 7 components?
- Do state machines match documented states?
- Are timing parameters within specified ranges?

---

## Expected Deliverables

By end of **Phase 2 (Implementation)**, students should have:

1. **Extended Component Classes** (src/mock_up/components.py)
   - All states from SFC diagrams implemented
   - Transition logic for each component
   - Input/output handling
   - Error states and recovery

2. **Control Logic** (src/mock_up/logic.py)
   - System-level coordination
   - Sequence management (mission execution)
   - Safety interlock enforcement

3. **Documentation**
   - README explaining translation choices
   - Comments in code referencing PDF pages
   - List of simplifications made

4. **Tests** (tests/unit/, tests/integration/)
   - Unit test for each component
   - Integration tests for key sequences
   - >80% code coverage

---

## Summary

**What you have**: Backbone/orientation showing translation approach
**What you need**: Complete, tested implementation of all components
**How to proceed**: Analyze PDF → Translate incrementally → Test thoroughly
**Goal**: Functional digital twin capturing essential behavior (not 1:1 copy)

**Remember**: The provided code is a **starting point**, not a solution. Your job is to analyze the PLC documentation, extend the components, implement the logic, and verify correctness.

Good luck! 🚀
