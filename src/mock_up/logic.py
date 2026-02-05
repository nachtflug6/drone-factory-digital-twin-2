# src/mock_up/logic.py
"""System Logic

Implements the control logic translated from PLC documentation.
This is where you implement the state machine transitions and conditions.

IMPORTANT:
Analyze the PLC documentation and implement the logic rules here.
Each function should represent a decision from the documentation.
"""

from datetime import datetime
from typing import List, Dict, Any, Tuple
from .state import SystemState
from .components import Motor, Conveyor, MotorState, ConveyorState


# ============================================================================
# MOTOR CONTROL LOGIC
# ============================================================================

def should_motor_run(system: SystemState, motor_id: str) -> bool:
    """
    Determine if a motor should be running
    
    From documentation:
        "Motor runs if no error and start signal active"
    
    Args:
        system: Current system state
        motor_id: ID of motor
    
    Returns:
        True if motor should be running
    """
    motor = system.get_component(motor_id)
    if motor is None:
        return False
    
    return not motor.error_flag


def update_motor_acceleration(system: SystemState, motor_id: str, current_time: datetime) -> None:
    """
    Progress motor through acceleration phase
    
    From documentation:
        "Motor accelerates for ~2 seconds to reach full speed"
    
    Args:
        system: Current system state
        motor_id: ID of motor
        current_time: Current simulation time
    """
    motor = system.get_component(motor_id)
    if motor is None or motor.state != MotorState.ACCELERATING:
        return
    
    motor.update(current_time)


# ============================================================================
# CONVEYOR CONTROL LOGIC
# ============================================================================

def should_conveyor_run(system: SystemState, conveyor_id: str) -> bool:
    """
    Determine if conveyor should be running
    
    From documentation:
        "Conveyor runs if:
         - Start signal active
         - Load below threshold
         - No error condition"
    
    Args:
        system: Current system state
        conveyor_id: ID of conveyor
    
    Returns:
        True if conveyor should run
    """
    conveyor = system.get_component(conveyor_id)
    if conveyor is None:
        return False
    
    # Check load threshold
    if conveyor.load_kg > conveyor.max_load_kg:
        return False
    
    # Check error flag
    if conveyor.error_flag:
        return False
    
    return True


def check_conveyor_load(system: SystemState, conveyor_id: str) -> None:
    """
    Check conveyor load and take action if overloaded
    
    From documentation:
        "If load exceeds 50 kg:
         - Stop conveyor
         - Set error flag
         - Alert operator"
    
    Args:
        system: Current system state
        conveyor_id: ID of conveyor
    """
    conveyor = system.get_component(conveyor_id)
    if conveyor is None:
        return
    
    conveyor.check_load()


# ============================================================================
# SENSOR LOGIC
# ============================================================================

def update_sensor_readings(system: SystemState) -> None:
    """
    Update all sensor readings
    
    From documentation:
        "Sensors are read every 100ms"
    
    Args:
        system: Current system state
    """
    # TODO: Implement actual sensor reading logic
    # For now, sensors pull data from components they're attached to
    for sensor in system.get_components_by_type('loadsensor'):
        if hasattr(sensor, 'attached_to'):
            component = system.get_component(sensor.attached_to)
            if hasattr(component, 'load_kg'):
                sensor.read_load(component.load_kg)


# ============================================================================
# TODO: ADD MORE LOGIC FUNCTIONS
# ============================================================================
# Based on your analysis of the PLC documentation, add more logic here:
#
# - assembly_arm_control()
# - quality_check_logic()
# - safety_interlocks()
# - error_handling()
# - etc.
#
# Each function should represent a decision rule or control algorithm
# from the documentation.


def apply_system_logic(system: SystemState, current_time: datetime) -> None:
    """
    Apply all system logic rules
    
    Call this once per simulation cycle to advance the system state
    according to control rules.
    
    Args:
        system: Current system state
        current_time: Current simulation time
    """
    # Update sensor readings
    update_sensor_readings(system)
    
    # Motor control
    for motor in system.get_components_by_type('motor'):
        update_motor_acceleration(system, motor.id, current_time)
    
    # Conveyor control
    for conveyor in system.get_components_by_type('conveyor'):
        check_conveyor_load(system, conveyor.id)
    
    # Update all components
    system.update(current_time)


# ============================================================================
# LOGIC VALIDATION
# ============================================================================

def validate_system_state(system: SystemState) -> Tuple[bool, List[str]]:
    """
    Validate that system is in consistent state
    
    Args:
        system: Current system state
    
    Returns:
        Tuple of (is_valid, list_of_violations)
    """
    violations = system.check_invariants()
    
    # Add domain-specific validation
    for motor in system.get_components_by_type('motor'):
        # Motor can't exceed max speed
        if motor.speed_rpm > motor.max_rpm:
            violations.append(f"{motor.id}: Speed {motor.speed_rpm} exceeds max {motor.max_rpm}")
    
    for conveyor in system.get_components_by_type('conveyor'):
        # Conveyor can't have negative load
        if conveyor.load_kg < 0:
            violations.append(f"{conveyor.id}: Negative load {conveyor.load_kg}")
    
    return (len(violations) == 0, violations)
