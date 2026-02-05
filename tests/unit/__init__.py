# tests/unit/test_motor.py
"""Unit tests for Motor component"""

import pytest
from datetime import datetime, timedelta
from src.mock_up.components import Motor, MotorState


class TestMotorStateTransitions:
    """Test motor state transitions"""
    
    def test_motor_initial_state(self):
        """Motor starts in IDLE state"""
        motor = Motor(id='m1')
        assert motor.state == MotorState.IDLE
        assert motor.speed_rpm == 0.0
    
    def test_motor_start_transition(self):
        """Motor transitions IDLE → ACCELERATING on start"""
        motor = Motor(id='m1')
        result = motor.start(target_speed=1000)
        
        assert result == True
        assert motor.state == MotorState.ACCELERATING
        assert motor.target_speed_rpm == 1000
    
    def test_motor_cannot_start_twice(self):
        """Motor can't start if already accelerating"""
        motor = Motor(id='m1')
        motor.start(target_speed=1000)
        
        result = motor.start(target_speed=500)
        assert result == False
        assert motor.state == MotorState.ACCELERATING
    
    def test_motor_acceleration_timing(self):
        """Motor takes ~2 seconds to accelerate"""
        motor = Motor(id='m1', acceleration_time=2.0)
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        
        motor.start(target_speed=1000)
        motor.transition_start_time = start_time
        
        # After 1 second (should be ~50% of target)
        t1 = start_time + timedelta(seconds=1)
        motor.update(t1)
        assert 450 < motor.speed_rpm < 550
        assert motor.state == MotorState.ACCELERATING
        
        # After 2 seconds (should be at target)
        t2 = start_time + timedelta(seconds=2)
        motor.update(t2)
        assert motor.speed_rpm == 1000
        assert motor.state == MotorState.RUNNING
    
    def test_motor_stop_transition(self):
        """Motor transitions RUNNING → DECELERATING on stop"""
        motor = Motor(id='m1')
        motor.state = MotorState.RUNNING
        motor.speed_rpm = 1000
        
        result = motor.stop()
        
        assert result == True
        assert motor.state == MotorState.DECELERATING
    
    def test_motor_speed_limit(self):
        """Motor respects max RPM"""
        motor = Motor(id='m1', max_rpm=1000)
        motor.start(target_speed=2000)  # Try to exceed max
        
        assert motor.target_speed_rpm == 1000  # Capped at max


class TestMotorEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_motor_stop_from_idle(self):
        """Can't stop motor that's already idle"""
        motor = Motor(id='m1')
        result = motor.stop()
        assert result == False
    
    def test_motor_zero_target_speed(self):
        """Motor can start with zero target speed"""
        motor = Motor(id='m1')
        result = motor.start(target_speed=0)
        assert result == True
        assert motor.target_speed_rpm == 0


# TODO: Add more test cases
# - TestMotorErrors
# - TestMotorTiming
# - TestMotorIntegration
