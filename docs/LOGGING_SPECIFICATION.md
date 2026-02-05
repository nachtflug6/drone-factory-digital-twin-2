# Logging Specification & Data Format

## Overview

This document defines the standard format for logging simulation events and system state changes.

---

## Why Comprehensive Logging?

Logging captures the complete simulation history, enabling:
- ✓ Verification (compare actual behavior vs. expected)
- ✓ Analysis (study patterns, interactions, performance)
- ✓ Debugging (find where things went wrong)
- ✓ Replay (re-examine specific time windows)
- ✓ Reproducibility (prove results are valid)

---

## Logging Architecture

### Two-Level Logging

**1. Event Logs** — Record every significant event
- State transitions
- Condition evaluations
- Errors and warnings
- Performance metrics

**2. State Snapshots** — Periodic full system state dump
- Every N events or every M seconds of virtual time
- Useful for reconstruction and validation

```
TIME: 0s
├─ Event: Motor_1 START
├─ Event: Conveyor_1 detected item
│
TIME: 0.5s
├─ Event: Motor_1 ACCEL_25%
├─ Snapshot: Full system state (requested)
│
TIME: 1s
├─ Event: Motor_1 ACCEL_50%
│
TIME: 1.5s
├─ Event: Motor_1 ACCEL_75%
│
TIME: 2s
├─ Event: Motor_1 RUNNING
├─ Event: Conveyor_1 RUNNING
```

---

## Event Log Format

### Format 1: JSON (Recommended)

**Advantages:** Structured, queryable, human-readable, hierarchical

```json
{
  "timestamp": "2024-01-15T06:00:00.000Z",
  "timestamp_seconds": 0.0,
  "event_type": "state_change",
  "component_id": "motor_1",
  "component_type": "motor",
  "event_name": "START",
  "old_state": "IDLE",
  "new_state": "ACCELERATING",
  "trigger": "start_signal_received",
  "severity": "info",
  "details": {
    "acceleration_time_ms": 2000,
    "target_speed_rpm": 1000,
    "initial_speed_rpm": 0
  },
  "metadata": {
    "simulation_id": "sim_20240115_001",
    "run_number": 1,
    "random_seed": 42
  }
}
```

**One event per line** (JSONL format — easy to stream and parse):
```
{"timestamp":"2024-01-15T06:00:00.000Z","event_type":"state_change","component_id":"motor_1",...}
{"timestamp":"2024-01-15T06:00:00.002Z","event_type":"condition_check","component_id":"motor_1",...}
{"timestamp":"2024-01-15T06:00:02.000Z","event_type":"state_change","component_id":"motor_1",...}
```

### Format 2: CSV (for Analysis)

**Advantages:** Compatible with Excel, R, pandas

```csv
timestamp,event_type,component_id,component_type,event_name,old_state,new_state,severity,details
2024-01-15T06:00:00.000Z,state_change,motor_1,motor,START,IDLE,ACCELERATING,info,"{""target_rpm"":1000}"
2024-01-15T06:00:00.002Z,condition_check,motor_1,motor,LOAD_CHECK,N/A,N/A,debug,"{""load_kg"":0.0}"
2024-01-15T06:00:02.000Z,state_change,motor_1,motor,RUNNING,ACCELERATING,RUNNING,info,"{}"
```

### Format 3: Binary (for Large Datasets)

**Advantages:** Compact, fast to read/write

Uses Protocol Buffers or MessagePack for efficiency:
```protobuf
message Event {
  double timestamp_seconds = 1;
  string event_type = 2;
  string component_id = 3;
  string event_name = 4;
  string old_state = 5;
  string new_state = 6;
  bytes details = 7;  // Serialized JSON
}
```

---

## Event Types

### 1. State Change Event

Triggered when a component transitions between states.

```json
{
  "timestamp": "2024-01-15T06:00:00.000Z",
  "event_type": "state_change",
  "component_id": "motor_1",
  "component_type": "motor",
  "event_name": "START",
  "old_state": "IDLE",
  "new_state": "ACCELERATING",
  "trigger": "operator_pressed_start_button",
  "severity": "info",
  "details": {
    "acceleration_time_ms": 2000,
    "target_speed_rpm": 1000,
    "ramp_type": "linear"
  }
}
```

**Fields:**
- `timestamp` — ISO 8601 format (e.g., `2024-01-15T06:00:00.000Z`)
- `event_type` — Always `"state_change"`
- `component_id` — Unique ID of component (e.g., `"motor_1"`)
- `component_type` — Type (e.g., `"motor"`, `"conveyor"`, `"sensor"`)
- `event_name` — Human-readable transition name
- `old_state` — Previous state value
- `new_state` — New state value
- `trigger` — What caused the transition
- `severity` — `"debug"`, `"info"`, `"warning"`, `"error"`
- `details` — Additional context (depends on event type)

### 2. Condition Evaluation Event

Triggered when a logical condition is evaluated (for debugging).

```json
{
  "timestamp": "2024-01-15T06:00:01.500Z",
  "event_type": "condition_check",
  "component_id": "conveyor_1",
  "event_name": "LOAD_THRESHOLD_CHECK",
  "condition": "load_kg > 50",
  "result": false,
  "severity": "debug",
  "details": {
    "load_kg": 35.2,
    "threshold_kg": 50.0,
    "percentage": 70.4
  }
}
```

### 3. Performance Metric Event

Logged at intervals to track performance.

```json
{
  "timestamp": "2024-01-15T06:05:00.000Z",
  "event_type": "performance_metric",
  "component_id": "system_global",
  "event_name": "THROUGHPUT_SAMPLE",
  "severity": "info",
  "details": {
    "components_active": 8,
    "events_per_second": 125.3,
    "avg_cycle_time_ms": 47.2,
    "total_events_processed": 37659
  }
}
```

### 4. Error/Warning Event

Logged when something unexpected happens.

```json
{
  "timestamp": "2024-01-15T06:12:34.567Z",
  "event_type": "error",
  "component_id": "motor_3",
  "event_name": "TEMPERATURE_EXCEEDED",
  "old_state": "RUNNING",
  "new_state": "ERROR",
  "severity": "error",
  "details": {
    "temperature_celsius": 95.3,
    "max_safe_temperature": 80.0,
    "error_code": "THERMAL_SHUTDOWN",
    "recovery_possible": false
  }
}
```

### 5. State Snapshot Event

Periodic dump of entire system state.

```json
{
  "timestamp": "2024-01-15T06:10:00.000Z",
  "event_type": "state_snapshot",
  "component_id": "system_global",
  "severity": "debug",
  "details": {
    "components": {
      "motor_1": {
        "state": "RUNNING",
        "speed_rpm": 1000.0,
        "temperature_celsius": 65.3,
        "power_watts": 750.0,
        "error_flag": false
      },
      "motor_2": {
        "state": "IDLE",
        "speed_rpm": 0.0,
        "temperature_celsius": 20.0,
        "power_watts": 0.0,
        "error_flag": false
      },
      "conveyor_1": {
        "state": "RUNNING",
        "speed_rpm": 100.0,
        "load_kg": 42.5,
        "items_count": 15
      },
      "sensor_1": {
        "state": "DETECTED",
        "value": 1,
        "last_change_time": "2024-01-15T06:09:58.234Z"
      }
    },
    "system_metrics": {
      "total_events": 12453,
      "runtime_seconds": 600.0,
      "uptime_percentage": 99.8
    }
  }
}
```

---

## Logging Best Practices

### 1. Always Include Timestamps

```python
import datetime
timestamp = datetime.datetime.utcnow().isoformat() + "Z"
# Results in: 2024-01-15T06:00:00.000Z
```

### 2. Use Consistent Field Names

```python
# ✓ Good: Consistent
log_entry = {
    "timestamp": "2024-01-15T06:00:00.000Z",
    "event_type": "state_change",
    "component_id": "motor_1"
}

# ✗ Bad: Inconsistent naming
log_entry = {
    "time": "2024-01-15T06:00:00.000Z",
    "EventType": "state_change",
    "ComponentId": "motor_1"
}
```

### 3. Log at Appropriate Levels

```python
logger.debug("condition_check: load_kg=35.2, threshold=50.0")  # Too detailed
logger.info("motor_1 state changed: IDLE → RUNNING")           # Good
logger.warning("motor_1 approaching temperature limit")        # Concerning
logger.error("motor_1 thermal shutdown triggered")             # Problem
```

### 4. Include Sufficient Detail

```python
# ✗ Insufficient detail
log_entry = {
    "event": "change",
    "component": "m1"
}

# ✓ Sufficient detail
log_entry = {
    "timestamp": "2024-01-15T06:00:00.000Z",
    "event_type": "state_change",
    "component_id": "motor_1",
    "component_type": "motor",
    "event_name": "START",
    "old_state": "IDLE",
    "new_state": "ACCELERATING",
    "trigger": "operator_pressed_start",
    "details": {
        "target_speed_rpm": 1000,
        "acceleration_time_ms": 2000
    }
}
```

### 5. Batch Write for Performance

```python
# ✗ Slow: Write immediately
for event in events:
    logger.write_line(json.dumps(event))

# ✓ Fast: Buffer and batch
buffer = []
for event in events:
    buffer.append(json.dumps(event))
    if len(buffer) >= 100:
        logger.write_lines(buffer)
        buffer.clear()
if buffer:
    logger.write_lines(buffer)
```

---

## Implementation Example

```python
# src/logging/logger.py
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class Logger:
    def __init__(self, path: str, level: str = "INFO"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, 'w')
        self.level = level
        self.buffer = []
        self.buffer_size = 100
    
    def log_state_change(self, 
                        component_id: str, 
                        component_type: str,
                        old_state: str, 
                        new_state: str, 
                        trigger: str,
                        details: Optional[Dict] = None,
                        timestamp: Optional[datetime] = None):
        """Log a component state transition"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        event = {
            "timestamp": timestamp.isoformat() + "Z",
            "timestamp_seconds": timestamp.timestamp(),
            "event_type": "state_change",
            "component_id": component_id,
            "component_type": component_type,
            "event_name": f"{old_state}_{new_state}",
            "old_state": old_state,
            "new_state": new_state,
            "trigger": trigger,
            "severity": "info",
            "details": details or {}
        }
        
        self._write_event(event)
    
    def log_condition(self,
                     component_id: str,
                     condition_name: str,
                     result: bool,
                     details: Optional[Dict] = None):
        """Log condition evaluation (debug level)"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "condition_check",
            "component_id": component_id,
            "event_name": condition_name,
            "result": result,
            "severity": "debug",
            "details": details or {}
        }
        
        self._write_event(event)
    
    def log_error(self,
                 component_id: str,
                 error_name: str,
                 message: str,
                 details: Optional[Dict] = None):
        """Log error event"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "error",
            "component_id": component_id,
            "event_name": error_name,
            "message": message,
            "severity": "error",
            "details": details or {}
        }
        
        self._write_event(event)
    
    def _write_event(self, event: Dict[str, Any]):
        """Add event to buffer, flush if full"""
        self.buffer.append(json.dumps(event))
        
        if len(self.buffer) >= self.buffer_size:
            self.flush()
    
    def flush(self):
        """Write buffered events to disk"""
        for line in self.buffer:
            self.file.write(line + '\n')
        self.buffer.clear()
        self.file.flush()  # Force write to disk
    
    def finalize(self):
        """Close logger and flush remaining data"""
        self.flush()
        self.file.close()
        print(f"Log file written: {self.path}")

# Usage
logger = Logger("data/logs/simulation_2024_01_15.jsonl")

logger.log_state_change(
    component_id="motor_1",
    component_type="motor",
    old_state="IDLE",
    new_state="ACCELERATING",
    trigger="start_signal_received",
    details={"target_speed_rpm": 1000, "acceleration_time_ms": 2000}
)

logger.log_condition(
    component_id="conveyor_1",
    condition_name="LOAD_THRESHOLD_CHECK",
    result=False,
    details={"load_kg": 35.2, "threshold_kg": 50.0}
)

logger.finalize()
```

---

## Parsing Logs

### Read JSON Logs

```python
import pandas as pd
import json

# Read JSONL file into DataFrame
def load_logs(path: str) -> pd.DataFrame:
    with open(path, 'r') as f:
        logs = [json.loads(line) for line in f]
    
    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# Usage
logs = load_logs('data/logs/simulation_2024_01_15.jsonl')

# Filter to state changes only
state_changes = logs[logs['event_type'] == 'state_change']

# Find all transitions for specific component
motor_1_changes = state_changes[state_changes['component_id'] == 'motor_1']

# Count transitions per component
transitions_per_component = state_changes.groupby('component_id').size()
```

### Analyze Patterns

```python
# Time between state changes
motor_logs = logs[logs['component_id'] == 'motor_1']
motor_logs['time_diff'] = motor_logs['timestamp'].diff()
avg_time_between_changes = motor_logs['time_diff'].mean()

# State duration
state_changes = logs[logs['event_type'] == 'state_change']
state_changes['duration'] = state_changes['timestamp'].shift(-1) - state_changes['timestamp']
```

---

## Storage Optimization

### Compression

For long runs (>100 GB logs):

```bash
# Gzip compression
gzip data/logs/simulation_2024_01_15.jsonl

# Results in ~10% of original size
ls -lh data/logs/simulation_2024_01_15.jsonl.gz
```

### Archival

```bash
# Create compressed archives by day
tar czf data/logs/logs_week_1.tar.gz data/logs/2024_01_0*.jsonl

# Keep raw logs for analysis, archive old ones
```

---

## Validation Checklist

- [ ] All events have valid timestamps
- [ ] Timestamps are monotonically increasing
- [ ] All required fields present in each event
- [ ] Event types match allowed values
- [ ] Component IDs match registered components
- [ ] States match component state enums
- [ ] No duplicate events at same timestamp
- [ ] File format is parseable (test parse)

---

## Next Steps

1. Implement Logger class in your project
2. Add logging calls at key points in simulation
3. Test that logs are written correctly
4. Validate log format with parsers
5. Analyze logs to find patterns (Phase 5)

See [ARCHITECTURE.md](ARCHITECTURE.md) for where to add logging.
