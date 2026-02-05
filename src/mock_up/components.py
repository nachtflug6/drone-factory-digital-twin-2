"""
Component classes for WS Conveyor digital twin simulation.

This module defines components specific to the Kod_WSConv_Sven2022 system:
- ConveyorMotor: Main belt drive with speed control
- TransferElevator: Vertical pallet movement (UP/DOWN positions)
- Buffer: Pallet queue with max 2 capacity
- DockingStation: Process station with SFC state machine
- PneumaticSystem: Pressure/flow/temperature monitoring
- RFIDReader: Pallet identification system

Reference: docs/SYSTEM_ANALYSIS.md
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict


# ============================================================================
# CONVEYOR MOTOR
# ============================================================================

class ConveyorMotorState(Enum):
    """States for conveyor motor."""
    IDLE = "idle"
    RAMP_UP = "ramp_up"
    RUNNING = "running"
    RAMP_DOWN = "ramp_down"
    ERROR = "error"


@dataclass
class ConveyorMotor:
    """Main conveyor belt motor with speed ramping."""
    id: str
    max_speed_percent: float = 100.0  # Percent of max speed (0.18 m/s)
    max_speed_ms: float = 0.18  # meters per second
    ramp_time: float = 2.0  # seconds to reach target speed
    
    def __post_init__(self):
        self.state = ConveyorMotorState.IDLE
        self.current_speed_percent = 0.0
        self.target_speed_percent = 0.0
        self.transition_start_time: Optional[datetime] = None
        self.current_speed_ms = 0.0
    
    def start(self, speed_percent: float = 100.0):
        """Begin acceleration to target speed."""
        if self.state not in [ConveyorMotorState.IDLE, ConveyorMotorState.RAMP_DOWN]:
            return False
        
        # Limit speed to valid range (20-100%)
        self.target_speed_percent = max(20.0, min(speed_percent, 100.0))
        
        if self.current_speed_percent == 0.0:
            self.state = ConveyorMotorState.RAMP_UP
            self.transition_start_time = datetime.now()
        elif abs(self.current_speed_percent - self.target_speed_percent) > 5.0:
            self.state = ConveyorMotorState.RAMP_UP
            self.transition_start_time = datetime.now()
        else:
            self.state = ConveyorMotorState.RUNNING
        
        return True
    
    def stop(self):
        """Begin deceleration."""
        if self.state == ConveyorMotorState.IDLE:
            return False
        
        self.target_speed_percent = 0.0
        self.state = ConveyorMotorState.RAMP_DOWN
        self.transition_start_time = datetime.now()
        return True
    
    def update(self, elapsed_time: float):
        """Progress motor state. elapsed_time is seconds since transition start."""
        if self.state == ConveyorMotorState.IDLE:
            return
        
        if self.state == ConveyorMotorState.RAMP_UP:
            progress = min(elapsed_time / self.ramp_time, 1.0)
            self.current_speed_percent = self.target_speed_percent * progress
            self.current_speed_ms = self.max_speed_ms * self.current_speed_percent / 100.0
            
            if progress >= 1.0:
                self.state = ConveyorMotorState.RUNNING
                self.current_speed_percent = self.target_speed_percent
        
        elif self.state == ConveyorMotorState.RUNNING:
            self.current_speed_percent = self.target_speed_percent
            self.current_speed_ms = self.max_speed_ms * self.target_speed_percent / 100.0
        
        elif self.state == ConveyorMotorState.RAMP_DOWN:
            progress = min(elapsed_time / self.ramp_time, 1.0)
            self.current_speed_percent = self.target_speed_percent * (1.0 - progress)
            self.current_speed_ms = self.max_speed_ms * self.current_speed_percent / 100.0
            
            if progress >= 1.0:
                self.state = ConveyorMotorState.IDLE
                self.current_speed_percent = 0.0
                self.current_speed_ms = 0.0
                self.transition_start_time = None


# ============================================================================
# TRANSFER ELEVATOR
# ============================================================================

class ElevatorPosition(Enum):
    """Elevator discrete positions."""
    DOWN = "down"  # Docking level (queue/lower)
    UP = "up"      # Working height (workspace)
    MOVING = "moving"  # In motion between positions
    ERROR = "error"    # Stuck or conflicting commands


@dataclass
class TransferElevator:
    """Vertical elevator for pallet transfer."""
    id: str
    travel_time: float = 0.5  # seconds to move between positions
    
    def __post_init__(self):
        self.position = ElevatorPosition.DOWN
        self.target_position = ElevatorPosition.DOWN
        self.is_down = True
        self.is_up = False
        self.transition_start_time: Optional[datetime] = None
        self.up_requested = False
        self.down_requested = False
    
    def request_up(self):
        """Request move to UP position."""
        if self.position == ElevatorPosition.UP:
            return True  # Already there
        
        if self.down_requested:  # Conflict
            self.position = ElevatorPosition.ERROR
            return False
        
        self.up_requested = True
        self.target_position = ElevatorPosition.UP
        
        if self.position in [ElevatorPosition.DOWN, ElevatorPosition.MOVING]:
            self.position = ElevatorPosition.MOVING
            self.transition_start_time = datetime.now()
        
        return True
    
    def request_down(self):
        """Request move to DOWN position."""
        if self.position == ElevatorPosition.DOWN:
            return True  # Already there
        
        if self.up_requested:  # Conflict
            self.position = ElevatorPosition.ERROR
            return False
        
        self.down_requested = True
        self.target_position = ElevatorPosition.DOWN
        
        if self.position in [ElevatorPosition.UP, ElevatorPosition.MOVING]:
            self.position = ElevatorPosition.MOVING
            self.transition_start_time = datetime.now()
        
        return True
    
    def update(self, elapsed_time: float):
        """Update elevator position based on movement time."""
        if self.position == ElevatorPosition.MOVING:
            progress = min(elapsed_time / self.travel_time, 1.0)
            
            if progress >= 1.0:
                # Movement complete
                if self.target_position == ElevatorPosition.UP:
                    self.position = ElevatorPosition.UP
                    self.is_up = True
                    self.is_down = False
                    self.up_requested = False
                elif self.target_position == ElevatorPosition.DOWN:
                    self.position = ElevatorPosition.DOWN
                    self.is_down = True
                    self.is_up = False
                    self.down_requested = False
                
                self.transition_start_time = None


# ============================================================================
# BUFFER
# ============================================================================

class BufferState(Enum):
    """Buffer storage states."""
    EMPTY = "empty"
    PARTIAL = "partial"  # 1 pallet
    FULL = "full"        # 2 pallets


@dataclass
class Buffer:
    """Pallet buffer with queue position."""
    id: str
    max_capacity: int = 2
    rfid_detection_delay: float = 0.5  # seconds
    
    def __post_init__(self):
        self.state = BufferState.EMPTY
        self.pallet_count = 0
        self.pallet_at_queue = False
        self.pallet_rfid_at_queue: Optional[str] = None
        self.queue_detect_start_time: Optional[datetime] = None
        self.auto_pass_enabled = False
        self.auto_pass_delay: float = 0.0
    
    def pallet_enters(self, rfid_tag: str):
        """Pallet arrives at queue position."""
        if self.pallet_at_queue:
            return False  # Queue occupied
        
        self.pallet_at_queue = True
        self.pallet_rfid_at_queue = rfid_tag
        self.queue_detect_start_time = datetime.now()
        return True
    
    def pallet_leaves(self):
        """Pallet leaves queue (transferred or passed)."""
        self.pallet_at_queue = False
        self.pallet_rfid_at_queue = None
        self.queue_detect_start_time = None
        self.pallet_count = max(0, self.pallet_count - 1)
    
    def add_to_buffer(self):
        """Transfer pallet from queue to storage."""
        if self.pallet_count < self.max_capacity:
            self.pallet_count += 1
            self.update_state()
            return True
        return False
    
    def update_state(self):
        """Update buffer state based on pallet count."""
        if self.pallet_count == 0:
            self.state = BufferState.EMPTY
        elif self.pallet_count == 1:
            self.state = BufferState.PARTIAL
        else:
            self.state = BufferState.FULL


# ============================================================================
# DOCKING STATION
# ============================================================================

class DockingStationState(Enum):
    """DS state machine (SFC-based)."""
    INIT = "init"
    AWAITING_MISSION = "awaiting_mission"
    RECEIVING = "receiving"
    PROCESSING = "processing"
    SENDING = "sending"
    CLEANUP = "cleanup"
    ERROR = "error"


@dataclass
class DockingStation:
    """Docking station with pallet processing."""
    id: str
    station_number: int  # 1-6
    mission_queue: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.state = DockingStationState.INIT
        self.pallet_present = False
        self.pallet_rfid: Optional[str] = None
        self.current_mission: Optional[str] = None
        self.mission_start_time: Optional[datetime] = None
        self.sequence_step = 0
        self.blocked = False  # For manual testing
    
    def accept_mission(self, mission: str) -> bool:
        """Receive mission assignment from HMI."""
        if self.state not in [DockingStationState.INIT, DockingStationState.AWAITING_MISSION]:
            return False
        
        self.current_mission = mission
        self.mission_start_time = datetime.now()
        self.state = DockingStationState.RECEIVING
        return True
    
    def pallet_arrived(self, rfid_tag: str):
        """Pallet transferred to station."""
        self.pallet_present = True
        self.pallet_rfid = rfid_tag
        self.sequence_step += 1
    
    def complete_processing(self):
        """Work on pallet is complete."""
        self.state = DockingStationState.SENDING
        self.sequence_step += 1
    
    def pallet_removed(self):
        """Pallet transferred away from station."""
        self.pallet_present = False
        self.pallet_rfid = None
        self.state = DockingStationState.CLEANUP
        self.current_mission = None


# ============================================================================
# PNEUMATIC SYSTEM
# ============================================================================

class PneumaticState(Enum):
    """Pneumatic system states."""
    OFF = "off"
    STABILIZING = "stabilizing"
    NORMAL = "normal"
    HIGH_PRESSURE = "high_pressure"
    LEAK_DETECTED = "leak_detected"


@dataclass
class PneumaticSystem:
    """Pressure and air flow monitoring."""
    id: str
    target_pressure_bar: float = 6.0
    min_pressure_bar: float = 5.5
    max_pressure_bar: float = 7.0
    max_flow_nm3h: float = 15.0
    stabilization_time: float = 5.0  # seconds to reach target
    
    def __post_init__(self):
        self.state = PneumaticState.OFF
        self.current_pressure_bar = 0.0
        self.current_flow_nm3h = 0.0
        self.current_temp_celsius = 20.0
        self.is_enabled = False
        self.transition_start_time: Optional[datetime] = None
    
    def enable(self):
        """Turn on air supply."""
        if self.is_enabled:
            return
        
        self.is_enabled = True
        self.state = PneumaticState.STABILIZING
        self.transition_start_time = datetime.now()
    
    def disable(self):
        """Turn off air supply."""
        self.is_enabled = False
        self.state = PneumaticState.OFF
        self.current_pressure_bar = 0.0
        self.current_flow_nm3h = 0.0
    
    def update(self, elapsed_time: float):
        """Update pneumatic system based on time and state."""
        if not self.is_enabled:
            if self.current_pressure_bar > 0.0:
                self.current_pressure_bar *= 0.95  # Leak down slowly
            return
        
        if self.state == PneumaticState.STABILIZING:
            progress = min(elapsed_time / self.stabilization_time, 1.0)
            self.current_pressure_bar = self.target_pressure_bar * progress
            
            if progress >= 1.0:
                self.state = PneumaticState.NORMAL
                self.current_pressure_bar = self.target_pressure_bar
        
        elif self.state == PneumaticState.NORMAL:
            self.current_pressure_bar = self.target_pressure_bar
            self.current_flow_nm3h = 0.5  # Minimal normal flow
            
            # Check for faults
            if self.current_pressure_bar > self.max_pressure_bar:
                self.state = PneumaticState.HIGH_PRESSURE
            elif self.current_flow_nm3h > self.max_flow_nm3h:
                self.state = PneumaticState.LEAK_DETECTED


# ============================================================================
# RFID READER
# ============================================================================

class RFIDState(Enum):
    """RFID detection states."""
    IDLE = "idle"
    DETECTING = "detecting"
    IDENTIFIED = "identified"
    ERROR = "error"


@dataclass
class RFIDReader:
    """RFID tag reader for pallet identification."""
    id: str
    location: str  # "queue" or "elevator"
    detection_delay: float = 0.5  # seconds
    
    def __post_init__(self):
        self.state = RFIDState.IDLE
        self.tag_detected: Optional[str] = None
        self.detect_start_time: Optional[datetime] = None
    
    def detect(self, tag: str):
        """Start detecting a pallet tag."""
        if self.state == RFIDState.IDLE:
            self.tag_detected = tag
            self.state = RFIDState.DETECTING
            self.detect_start_time = datetime.now()
            return True
        return False
    
    def clear(self):
        """Clear detection when pallet leaves."""
        self.state = RFIDState.IDLE
        self.tag_detected = None
        self.detect_start_time = None
    
    def update(self, elapsed_time: float):
        """Complete detection after delay."""
        if self.state == RFIDState.DETECTING:
            if elapsed_time >= self.detection_delay:
                self.state = RFIDState.IDENTIFIED


def create_ws_conveyor_system(config) -> Dict[str, object]:
    """
    Factory to create WS Conveyor system components from config.
    
    Args:
        config: SimulationConfig with system parameters
        
    Returns:
        Dictionary of component instances
    """
    components = {}
    
    # Main conveyor motor
    components['conveyor_motor'] = ConveyorMotor(
        id='main_conveyor',
        max_speed_percent=100.0,
        ramp_time=config.conveyor_ramp_time
    )
    
    # Transfer elevator
    components['elevator'] = TransferElevator(
        id='transfer_elevator',
        travel_time=config.elevator_travel_time
    )
    
    # Buffer
    components['buffer'] = Buffer(
        id='buffer',
        max_capacity=config.buffer_max_capacity,
        rfid_detection_delay=config.rfid_detection_delay
    )
    
    # Docking stations (DS1-DS6)
    for i in range(1, 7):
        components[f'ds_{i}'] = DockingStation(
            id=f'ds_{i}',
            station_number=i
        )
    
    # Pneumatic system
    components['pneumatic'] = PneumaticSystem(
        id='pneumatic_system',
        target_pressure_bar=config.pneumatic_target_pressure,
        max_flow_nm3h=config.pneumatic_max_flow
    )
    
    # RFID readers
    components['rfid_queue'] = RFIDReader(
        id='rfid_queue',
        location='queue',
        detection_delay=config.rfid_detection_delay
    )
    components['rfid_elevator'] = RFIDReader(
        id='rfid_elevator',
        location='elevator',
        detection_delay=config.rfid_detection_delay
    )
    
    return components
