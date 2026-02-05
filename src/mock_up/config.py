# src/mock_up/config.py
"""System Configuration for WS Conveyor System

Define all configurable parameters extracted from Kod_WSConv_Sven2022.pdf

Key Parameters from Documentation:
- Conveyor: Max speed 0.18 m/s, speed control 20-100%, ramp time ~2 seconds
- Elevator: Discrete UP/DOWN positions, travel time <1s
- Buffer: Max 2 pallets, queue detection 0.5s
- Pneumatic: Target 6 bar, range 5.5-7.0 bar, max flow 15 nm³/h
- RFID: Detection delay 0.5 seconds, 8-byte tag format
- Stations: 6 docking stations (DS1-DS6) with SFC state machines
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List


@dataclass
class SimulationConfig:
    """Configuration for WS Conveyor system simulation"""
    
    # ========================================================================
    # SIMULATION TIMING
    # ========================================================================
    duration_hours: float = 24.0  # Run for 24 virtual hours
    timestep_seconds: float = 0.1  # Simulation step size
    
    # ========================================================================
    # CONVEYOR SYSTEM
    # ========================================================================
    # Main conveyor belt specifications
    conveyor_max_speed_ms: float = 0.18  # meters per second (from docs)
    conveyor_speed_range: tuple = (20, 100)  # Percentage of max
    conveyor_ramp_time: float = 2.0  # Seconds to accelerate/decelerate
    conveyor_enabled: bool = True
    
    # ========================================================================
    # ELEVATOR SYSTEM
    # ========================================================================
    # Vertical transfer elevator
    elevator_travel_time: float = 0.5  # Seconds to move between positions
    elevator_positions: List[str] = field(default_factory=lambda: ["DOWN", "UP"])
    elevator_initial_position: str = "DOWN"
    
    # ========================================================================
    # BUFFER SYSTEM
    # ========================================================================
    # Pallet buffer and queue
    buffer_max_capacity: int = 2  # Max 2 pallets in buffer
    buffer_queue_position: str = "queue_stop"
    buffer_auto_pass_enabled: bool = False
    buffer_auto_pass_delay: float = 5.0  # Seconds before auto-advancing
    
    # ========================================================================
    # DOCKING STATIONS
    # ========================================================================
    # DS1-DS6 configuration
    station_count: int = 6
    station_numbers: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6])
    
    # Timing gates for auto-advance (from HMI documentation)
    station_wait_at_queue: float = 2.0  # hmi_TimeForWaitAtQueue
    station_wait_after_passing: float = 1.0  # hmi_TimeForWaitAfterPassingDS
    station_wait_after_ws_transfer: float = 1.0  # hmi_TimeForWaitAfterTransferdToWS
    station_wait_after_amr_transfer: float = 1.0  # hmi_TimeForWaitAfterTransferdToAMR
    
    # ========================================================================
    # PNEUMATIC SYSTEM
    # ========================================================================
    # Air pressure and flow monitoring (from Appendix)
    pneumatic_target_pressure: float = 6.0  # bar
    pneumatic_min_pressure: float = 5.5  # bar (warning threshold)
    pneumatic_max_pressure: float = 7.0  # bar (safety relief)
    pneumatic_max_flow: float = 15.0  # nm³/h (normal max flow)
    pneumatic_stabilization_time: float = 5.0  # Seconds to reach pressure
    pneumatic_enabled: bool = True
    
    # ========================================================================
    # RFID SYSTEM
    # ========================================================================
    # Pallet identification
    rfid_detection_delay: float = 0.5  # Seconds to detect tag (from docs)
    rfid_tag_format: str = "8byte_hex"  # 8-byte tag → HEX string
    rfid_locations: List[str] = field(default_factory=lambda: ["queue", "elevator"])
    
    # ========================================================================
    # LOGGING & OUTPUT
    # ========================================================================
    log_format: str = "json"  # "json" or "csv"
    log_level: str = "INFO"  # "DEBUG", "INFO", "WARNING"
    log_file: str = "data/logs/ws_conveyor_simulation.jsonl"
    
    # Log event types to include
    log_state_changes: bool = True  # Log all state transitions
    log_sensor_values: bool = True  # Log sensor readings (pressure, flow, etc.)
    log_pallet_movements: bool = True  # Log pallet transfers
    log_errors: bool = True  # Log fault conditions
    
    # Logging frequency
    log_state_snapshots: bool = True  # Periodically save full state
    snapshot_interval_seconds: float = 10.0  # Snapshot every 10 sim seconds
    
    # ========================================================================
    # SIMULATION OPTIONS
    # ========================================================================
    seed: int = 42  # For reproducible random behavior
    deterministic: bool = True  # Use fixed seed, no randomness
    verbose: bool = False  # Print simulation progress
    
    # ========================================================================
    # MISSION CONFIGURATION (Optional)
    # ========================================================================
    # Available missions for each station
    available_missions: Dict[int, List[str]] = field(default_factory=lambda: {
        1: ["PROCESS_TYPE_A", "QUALITY_CHECK"],
        2: ["PROCESS_TYPE_B", "ASSEMBLY"],
        3: ["PROCESS_TYPE_A", "QUALITY_CHECK"],
        4: ["PROCESS_TYPE_C", "PACKAGING"],
        5: ["PROCESS_TYPE_B", "ASSEMBLY"],
        6: ["PROCESS_TYPE_A", "INSPECTION"],
    })
    
    # ========================================================================
    # SYSTEM CONSTRAINTS (from documentation)
    # ========================================================================
    # Safety rules enforced
    allow_conflicting_elevator_commands: bool = False
    allow_direction_change_during_transfer: bool = False
    enforce_pressure_limits: bool = True
    prevent_buffer_overflow: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        assert self.buffer_max_capacity > 0, "Buffer capacity must be positive"
        assert self.conveyor_max_speed_ms > 0, "Conveyor speed must be positive"
        assert self.pneumatic_target_pressure > 0, "Pressure must be positive"
        assert len(self.station_numbers) == self.station_count, "Station count mismatch"


# ============================================================================
# FACTORY FUNCTIONS FOR COMMON SCENARIOS
# ============================================================================

def config_normal_operation() -> SimulationConfig:
    """Configuration for normal 24-hour operation"""
    return SimulationConfig(
        duration_hours=24.0,
        conveyor_enabled=True,
        pneumatic_enabled=True,
        buffer_auto_pass_enabled=False,  # Manual mode
    )


def config_stress_test() -> SimulationConfig:
    """Configuration for stress testing (high load, short duration)"""
    return SimulationConfig(
        duration_hours=1.0,
        timestep_seconds=0.05,  # Finer resolution
        buffer_auto_pass_enabled=True,
        buffer_auto_pass_delay=1.0,  # Faster cycling
        log_level="DEBUG",
    )


def config_fault_testing() -> SimulationConfig:
    """Configuration for fault condition testing"""
    config = SimulationConfig(
        duration_hours=2.0,
        log_level="DEBUG",
        log_state_changes=True,
        log_errors=True,
    )
    return config


def config_long_horizon() -> SimulationConfig:
    """Configuration for long-horizon (multi-day) analysis"""
    return SimulationConfig(
        duration_hours=168.0,  # 1 week
        timestep_seconds=1.0,  # Coarser resolution for speed
        log_level="INFO",
        snapshot_interval_seconds=300.0,  # Less frequent snapshots
    )


# Default configuration
DEFAULT_CONFIG = config_normal_operation()
