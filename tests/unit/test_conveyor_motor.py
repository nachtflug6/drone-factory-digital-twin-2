import pytest

from src.mock_up.components import ConveyorMotor, ConveyorMotorState


class TestConveyorMotorStateTransitions:
    """Test ConveyorMotor documented transitions/constraints."""

    def test_motor_initial_state(self):
        """Verify: 初始状态为 IDLE"""
        motor = ConveyorMotor(id="mc1")
        assert motor.state == ConveyorMotorState.IDLE
        assert motor.current_speed_percent == 0.0

    def test_motor_idle_to_ramp_up_to_running(self):
        """Verify: IDLE -> RAMP_UP -> RUNNING on start() + update()"""
        motor = ConveyorMotor(id="mc1", ramp_time=2.0, max_speed_percent=100.0)
        ok = motor.start(speed_percent=50.0)
        assert ok is True
        assert motor.state == ConveyorMotorState.RAMP_UP
        assert motor.target_speed_percent == 50.0

        # After 1 second: progress=0.5 => speed=25%
        motor.update(elapsed_time=1.0)
        assert motor.state == ConveyorMotorState.RAMP_UP
        assert 0.0 < motor.current_speed_percent < 50.0

        # After 2 seconds: progress=1.0 => RUNNING at target
        motor.update(elapsed_time=2.0)
        assert motor.state == ConveyorMotorState.RUNNING
        assert motor.current_speed_percent == motor.target_speed_percent

    def test_motor_cannot_start_when_not_idle(self):
        """Verify: 在 RAMP_UP/RUNNING 等非 IDLE 状态 start() 返回 False"""
        motor = ConveyorMotor(id="mc1", ramp_time=2.0)
        assert motor.start(speed_percent=50.0) is True
        motor.update(elapsed_time=2.0)  # -> RUNNING
        assert motor.state == ConveyorMotorState.RUNNING

        ok = motor.start(speed_percent=80.0)
        assert ok is False
        assert motor.state == ConveyorMotorState.RUNNING

    def test_motor_running_to_idle_on_stop(self):
        """Verify: RUNNING -> RAMP_DOWN -> IDLE on stop() + update()"""
        motor = ConveyorMotor(id="mc1", ramp_time=2.0)
        assert motor.start(speed_percent=50.0) is True
        motor.update(elapsed_time=2.0)  # -> RUNNING

        ok = motor.stop()
        assert ok is True
        assert motor.state == ConveyorMotorState.RAMP_DOWN

        motor.update(elapsed_time=2.0)
        assert motor.state == ConveyorMotorState.IDLE
        assert motor.current_speed_percent == 0.0

    def test_motor_stop_from_idle_returns_false(self):
        """Verify: IDLE 下 stop() 返回 False"""
        motor = ConveyorMotor(id="mc1")
        assert motor.stop() is False

    def test_motor_error_blocks_start_and_reset_returns_idle(self):
        """Verify: ERROR 时 start() 被阻止，reset_error() 后可恢复到 IDLE"""
        motor = ConveyorMotor(id="mc1", ramp_time=2.0)
        motor.trigger_error()
        assert motor.state == ConveyorMotorState.ERROR

        ok = motor.start(speed_percent=50.0)
        assert ok is False
        assert motor.state == ConveyorMotorState.ERROR

        motor.reset_error()
        assert motor.is_malfunctioning is False
        assert motor.state == ConveyorMotorState.IDLE

