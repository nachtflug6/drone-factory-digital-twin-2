# WS Conveyor System Analysis (Kod_WSConv_Sven2022)

**Document**: Kod_WSConv_Sven2022.pdf  
**System**: Modular WorkStation with Conveyor, Elevator, and Buffer  
**PLC**: Beckhoff Soft PLC X2 Control 7B (CoDeSys V3.5)  
**Date Analysis**: February 2026

---

## System Overview

The **WS Conveyor System** is a modular workstation component that handles:
- **Pallet Transfer**: Moving pallets between multiple docking stations (DS1-DS6)
- **Queue Management**: Buffer with capacity for max 2 pallets
- **Elevation Control**: Vertical transfer with up/down positions
- **Pneumatic Operations**: Pressure/airflow control for actuators
- **RFID Tracking**: Identify pallets via RFID tags at key positions

### Key Subsystems
1. **Main Conveyor**: Runs at configurable speed (20-100% = 0-0.18 m/s)
2. **Transfer Elevator**: Moves pallets between floor and working height
3. **Buffer Storage**: Holds up to 2 pallets waiting for processing
4. **Six Docking Stations (DS1-DS6)**: Process pallets, each with state machine
5. **Pneumatic System**: Provides air pressure/flow for actuators
6. **RFID System**: Reads pallet identification at queue and elevator positions
7. **HMI Interface**: Operator control and status visualization

---

## Major Components & States

### 1. Main Conveyor System
**Component**: `Conveyor`

**Inputs**:
- `conveyor_on` (BOOL): Start/stop command
- `hmi_conveyer_speed` (INT 0-100): Speed percentage

**Outputs**:
- `conveyor_running` (BOOL): Motor status
- `conveyor_speed_percent` (INT): Current speed
- `conveyor_direction` (BOOL): Directional control

**States**:
```
IDLE
  → START (conveyor_on=TRUE)
RUNNING
  → RAMP_UP (accelerate to target speed)
  → RAMP_DOWN (decelerate)
  → STOP (conveyor_on=FALSE)
```

**Parameters**:
- Maximum speed: 0.18 m/s
- Speed range: 20-100% of max
- Default ramp time: ~2 seconds (implicit)

---

### 2. Transfer Elevator
**Component**: `TransferElevator`

**Inputs**:
- `elevator_up` (BOOL): Move up command
- `elevator_down` (BOOL): Move down command
- `transfer_on` (BOOL): Enable transfer

**Outputs**:
- `elevator_sensor_up` (BOOL): At upper level
- `elevator_sensor_down` (BOOL): At lower level
- `elevator_is_up` (BOOL): Current position (up=TRUE)

**States**:
```
DOWN (at lower/docking level)
UP (at working height)
MOVING_UP (in motion)
MOVING_DOWN (in motion)
ERROR (conflicting commands or stuck)
```

**Parameters**:
- Two discrete positions: UP or DOWN
- Movement time: Not specified (assumed <1s or configurable)
- Safe state: Neutral position (neither fully up nor down)

---

### 3. Buffer System
**Component**: `Buffer`

**Inputs**:
- `buffer_queue_stop_down` (BOOL): Lower stop position active
- `buffer_queue_stop_sensor` (BOOL): Pallet present at queue

**Outputs**:
- `pallets_in_buffer` (INT): Count (0-2)
- `buffer_full` (BOOL): Capacity reached

**States**:
```
EMPTY (0 pallets)
PARTIAL (1 pallet)
FULL (2 pallets)
```

**Parameters**:
- Max capacity: 2 pallets
- Queue position: Single stop point
- Auto-pass option: Timer-based (configurable delay)

---

### 4. Docking Stations (DS1-DS6)
**Component**: `DockingStation`

**Inputs**:
- `transfer_on` (BOOL): Transfer active
- `transfer_direction` (BOOL): Direction (from_MC=0, to_MC=1)
- `queue_pallet_tag` (STRING): RFID pallet identifier

**Outputs**:
- `pallet_at_ds` (BOOL): Pallet present
- `ds_ready` (BOOL): Ready to transfer
- `station_sequence_state` (INT): Current SFC step

**States** (Sequence-based, DS-specific):
```
INIT
  → Wait for mission
RECEIVING (from buffer/elevator)
  → Pallet transferred in
  → Wait for processing
PROCESSING (station-dependent work)
  → Apply mission logic
SENDING (to buffer/elevator)
  → Pallet transferred out
  → Complete mission
```

**Timing Gates** (auto-advance delays):
- `hmi_TimeForWaitAtQueue`: Delay before auto-pass DS
- `hmi_TimeForWaitAfterPassingDS`: Delay after passing
- `hmi_TimeForWaitAfterTransferdToWS`: Delay after transfer to workspace
- `hmi_TimeForWaitAfterTransferdToAMR`: Delay after transfer to AMR

**Parameters**:
- 6 instances (DS1-DS6), each independent
- RFID tracking: Pallet tag stored on entry, cleared on exit
- Mission-driven: Each pallet follows a mission path

---

### 5. Pneumatic System
**Component**: `PneumaticSystem`

**Inputs**:
- `hmi_pneumatic_pressure_on` (BOOL): Enable air supply
- Sensor inputs from system

**Outputs**:
- `ifm_q3_pressure_sensor_value` (REAL): Current pressure (bar)
- `ifm_sd5000_temperature_sensor_value` (REAL): Air temperature (°C)
- `ifm_sd5000_flow_rate_sensor_value` (REAL): Air flow (nm³/h)

**States**:
```
OFF (no air pressure)
STABILIZING (building pressure)
NORMAL (pressure stable)
HIGH_PRESSURE (>6 bar - warning)
LEAK (flow too high, pressure dropping)
```

**Parameters**:
- Target pressure: 6 bar
- Acceptable range: 5.5-6.5 bar
- Max flow: 15 nm³/h
- Normal temperature: ~20°C
- High flow warning: >15 nm³/h (potential leak)

---

### 6. RFID System
**Component**: `RFIDReader`

**Inputs**:
- Antenna at queue position
- Antenna at elevator position

**Outputs**:
- `rfid_tag_at_queue` (BYTE[8]): 8-byte pallet identifier
- `rfid_tag_at_elevator` (BYTE[8]): Pallet ID in elevator
- `rfid_string` (STRING): Hex representation

**State Machine**:
```
IDLE
  → Pallet enters queue
DETECTING (0.5 second wait)
  → Convert BYTE array to HEX string
IDENTIFIED
  → Store tag for mission
  → Clear when pallet leaves
```

**Parameters**:
- Detection delay: 0.5 seconds
- Tag format: 8-byte array → HEX string (16 chars)
- Movable antenna at queue position
- Fixed antenna at elevator

---

## Data Flow & Signal Paths

### Mission-Driven Sequence
```
1. Pallet arrives at buffer queue
2. RFID detects pallet (0.5s delay)
3. HMI operator selects DS (DS1-DS6) and mission
4. Mission transmitted to selected DS
5. Transfer moves pallet from queue → Elevator → DS
6. Elevator at working height, pallet at DS
7. DS executes mission (process-specific)
8. Transfer moves pallet from DS → Elevator → Buffer or Main Conveyor
9. Elevator returns to lower position
10. Pallet leaves system or awaits next mission
```

### Typical Signal Flows

**Start Conveyor**:
- HMI sets `hmi_conveyer_on = TRUE`
- POU_HMI_Control validates speed/ramp settings
- Conveyor transitions: IDLE → RUNNING
- Status shows on HMI (blinking arrow = main conveyor running)

**Move Pallet to DS**:
- `transfer_on = TRUE`, `transfer_direction = 0` (from main conveyor)
- Elevator moves: `elevator_down = TRUE` → wait for `elevator_sensor_down`
- Transfer engages (direction control)
- Pallet moves to docking station
- Elevator moves: `elevator_up = TRUE` → wait for `elevator_sensor_up`

**Pressure Monitoring**:
- POU_Sensors reads `ifm_q3_pressure_sensor_value`
- Triggers warning if pressure < 5.5 bar or > 7 bar
- Monitors `ifm_sd5000_flow_rate_sensor_value` for leaks

---

## Key Timing Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| RFID detection delay | 0.5 s | Wait for tag to stabilize |
| Elevator movement time | <1 s (est) | Discrete UP/DOWN movement |
| Conveyor ramp time | ~2 s (est) | Speed acceleration |
| Auto-pass at queue | Configurable | Wait before auto-advancing DS |
| Wait after DS pass | Configurable | Delay before next DS ready |
| Wait after WS transfer | Configurable | Delay for workspace ready |
| Wait after AMR transfer | Configurable | Delay for AMR handling |

---

## Control Logic Patterns

### 1. Conveyor Control
```
IF conveyor_speed_changed
  THEN calculate_new_target_speed()
  CHECK current_speed < target_speed  [ramp up]
  CHECK current_speed > target_speed  [ramp down]
  CHECK speeds_match  [maintain constant]
```

### 2. Elevator Sequence
```
LOOP:
  IF elevator_up_requested AND NOT elevator_sensor_up
    THEN set elevator motor ON
  IF elevator_sensor_up THEN stop motor
  
  IF elevator_down_requested AND NOT elevator_sensor_down
    THEN set elevator motor ON
  IF elevator_sensor_down THEN stop motor
```

### 3. Station State Machine (SFC)
```
INIT:
  Wait for mission from HMI
  → Transition on mission_available

RECEIVE_FROM_TRANSFER:
  Move elevator to working height
  Engage transfer to bring pallet
  → Transition on pallet_at_station

PROCESS:
  Apply station-specific work
  Delay for work completion
  → Transition on work_done

SEND_TO_TRANSFER:
  Prepare pallet for transfer
  Move elevator down
  Release to transfer
  → Transition on pallet_left

CLEANUP:
  Reset station state
  Clear RFID tag
  Return to INIT
```

### 4. Buffer Management
```
IF pallet_at_queue_sensor
  THEN Read RFID tag (wait 0.5s)
  STORE tag for mission tracking
  
  IF hmi_allow_timer_for_passing
    THEN Start delay timer
    IF timer >= hmi_TimeForWaitAtQueue
      THEN trigger auto_pass
```

### 5. Pneumatic Monitoring
```
LOOP:
  pressure = Read ifm_q3_pressure_sensor_value
  flow = Read ifm_sd5000_flow_rate_sensor_value
  temp = Read ifm_sd5000_temperature_sensor_value
  
  IF pressure < 5.5 bar THEN warning_low_pressure
  IF pressure > 7.0 bar THEN warning_high_pressure
  IF flow > 15 nm³/h THEN warning_leak_detected
  
  IF hmi_pneumatic_pressure_on = FALSE
    THEN expect_pressure_to_drop
```

---

## Implementation Structure (PLC Code)

The PLC code is organized into:

### Functional Blocks (FB) & Program Organization Units (POU)
- **POU_HMI_Control**: Handle operator input, validate changes
- **POU_Sensors**: Read and calculate sensor values (pressure, flow, temperature)
- **POU_ReadRFID_Tag**: Detect pallet, convert byte array to hex string
- **FB_MC_DOS_Control_DS1**: Motion control for DS1
- **FB_MC_DOS_Control_DS2toDS6**: Motion control for DS2-DS6
- **Conveyer_Control_Converter**: Conveyor speed and direction management

### Global Variable Lists (GVL)
- **GVL_HMI**: Operator controls and timing parameters
- **GVL_Pneumatic**: Pressure, flow, temperature values
- **GVL_Conveyer**: Conveyor state and speed
- **GVL_Conveyer_Motor**: Motor control signals
- **GVL_RFID**: RFID tag data and strings
- **GVL_DS1, GVL_DS2-DS6**: Station-specific state and missions

---

## Translation to Python Components

### Recommended Component Classes

```python
# Core infrastructure
class ConveyorMotor          # Main belt drive
class TransferElevator       # Vertical pallet movement
class Buffer                 # Pallet queue storage
class DockingStation         # Generic DS with SFC state machine
class PneumaticSystem        # Pressure/flow monitoring
class RFIDReader             # Pallet identification

# Specific implementations
class DS_Type_A              # Station variant (if needed)
class DS_Type_B              # Station variant (if needed)

# System coordinator
class WSConveyorSystem       # Top-level orchestrator
```

### Configuration Structure

```python
class SimulationConfig:
    # Conveyor
    conveyor_max_speed: float = 0.18  # m/s
    conveyor_ramp_time: float = 2.0   # seconds
    
    # Elevator
    elevator_travel_time: float = 0.5  # seconds
    
    # Buffer
    buffer_max_capacity: int = 2
    
    # Stations
    station_count: int = 6
    station_timing_config: Dict[str, float]  # Per-station delays
    
    # Pneumatic
    pneumatic_target_pressure: float = 6.0  # bar
    pneumatic_max_flow: float = 15.0  # nm³/h
    
    # RFID
    rfid_detection_delay: float = 0.5  # seconds
    
    # Missions
    available_missions: List[str]  # DS1-DS6 specific
```

---

## System Constraints & Rules

### Safety Rules
1. **No Conflicting Elevator Commands**: Cannot request UP and DOWN simultaneously
2. **Transfer Direction Control**: Cannot change direction while transfer is active
3. **Pressure Safety**: Must not exceed 7 bar (safety relief engaged)
4. **Buffer Overflow Prevention**: Conveyor stops if buffer full

### Operational Constraints
1. **Sequential Movement**: Elevator UP before pallet can be at workspace
2. **Queue Locking**: Only one pallet can be at queue_stop position
3. **RFID Dependency**: Mission cannot start without valid pallet ID
4. **Station Sequencing**: Must follow SFC state machine (no state skipping)

### Timing Constraints
1. **Conveyor ramp must complete before next command**
2. **Elevator must reach endpoint before releasing pallet**
3. **RFID detection requires 0.5 second stabilization**
4. **Auto-pass timers must be respected**

---

## Failure Modes & Error Handling

| Failure | Detection | Recovery |
|---------|-----------|----------|
| **Low Pressure** (<5.5 bar) | Sensor value | Operator intervention, check air supply |
| **High Pressure** (>7 bar) | Sensor value | Relief valve engages, reduce source |
| **Leak Detected** (flow >15 nm³/h) | Flow sensor | Locate and repair leak |
| **Elevator Stuck** | Timeout on position sensor | Manual reset required |
| **RFID Unreadable** | No tag detected | Reposition pallet, retry read |
| **Conveyor Jam** | Motor current/load | Stop and clear manually |
| **Buffer Overflow** | Queue sensor + count | Prevent new pallet entry |

---

## Simulation Scenarios

### Scenario 1: Normal Operation
- Start conveyor at 50% speed
- Pallet arrives at buffer
- RFID detects pallet (0.5s)
- Operator sends pallet to DS2
- Elevator receives, processes, returns
- Pallet exits system

**Expected Duration**: ~10-15 seconds

### Scenario 2: Multi-Pallet Processing
- Two pallets in buffer queue
- Auto-pass enabled with 5s delay
- Pallets pass through DS1, DS3 sequentially
- Monitor buffer levels and timing

**Expected Duration**: ~30-45 seconds

### Scenario 3: Pressure Fault Condition
- Start normal operation
- Simulate pressure drop (leak)
- Monitor alarm triggering
- Operator stops pneumatic supply
- Verify safe shutdown

**Expected Duration**: Variable based on leak rate

### Scenario 4: Long-Horizon Mixed Operations
- Run for 24+ simulated hours
- Random mission assignments to DS1-DS6
- Variable conveyor speeds
- Monitor system stability
- Track throughput metrics

**Expected Duration**: Seconds of wall-clock time, hours of simulated time

---

## Key Metrics to Track

### Performance Metrics
- **Throughput**: Pallets per hour
- **Cycle Time**: Queue entry to exit time
- **Utilization**: Percent time each station is processing
- **Buffer Efficiency**: Avg queue depth, max wait time

### Reliability Metrics
- **Pressure Stability**: Time in normal range (5.5-6.5 bar)
- **Airflow Stability**: Avg flow, variance
- **Elevator Reliability**: Successful moves per attempt
- **RFID Success Rate**: Successful reads per detection attempt

### Safety Metrics
- **Pressure Exceedances**: Times exceeding limits
- **Error Conditions**: Count and duration
- **Manual Interventions**: Required resets/restarts
- **Constraint Violations**: Rule breaks detected

---

## Notes for Students

1. **Start Simple**: Implement conveyor and buffer first, test thoroughly
2. **State Machines are Key**: DS sequencing follows strict SFC logic
3. **Timing Matters**: 0.5s RFID delay is hard requirement, others are tunable
4. **Pressure Monitoring**: Continuous sampling needed for fault detection
5. **Deterministic Simulation**: Use fixed seed for reproducible testing
6. **Extensibility**: Design to support custom station types and missions

---

## Document References

- **System Architecture**: docs/ARCHITECTURE.md
- **Component Design**: src/mock_up/components.py
- **Configuration**: src/mock_up/config.py
- **State Management**: src/mock_up/state.py
- **Logic Rules**: src/mock_up/logic.py
- **Example Simulation**: examples/ws_conveyor_simulation.py (to be created)
