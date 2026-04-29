import pytest

from src.mock_up.components import (
    TransferElevator,
    ElevatorPosition,
    TransferDirection,
)


class TestTransferElevatorTransitions:
    """Test TransferElevator documented transitions/constraints."""

    def test_down_to_up_to_down(self):
        """Verify: DOWN -> MOVING -> UP -> MOVING -> DOWN"""
        elevator = TransferElevator(id="e1", travel_time=1.5)
        assert elevator.position == ElevatorPosition.DOWN

        assert elevator.request_up() is True
        assert elevator.position == ElevatorPosition.MOVING

        elevator.update(elapsed_time=1.5)
        assert elevator.position == ElevatorPosition.UP
        assert elevator.transition_start_time is None

        # Clear latch like HMI/PLC would do after reaching target.
        elevator.up_requested = False

        assert elevator.request_down() is True
        assert elevator.position == ElevatorPosition.MOVING

        elevator.update(elapsed_time=1.5)
        assert elevator.position == ElevatorPosition.DOWN
        assert elevator.transition_start_time is None

    def test_direction_conflict_sets_error(self):
        """Verify: request_up 后立即 request_down => ERROR"""
        elevator = TransferElevator(id="e1", travel_time=1.5)
        assert elevator.request_up() is True
        assert elevator.position == ElevatorPosition.MOVING

        ok = elevator.request_down()
        assert ok is False
        assert elevator.position == ElevatorPosition.ERROR

    def test_start_transfer_to_ws_and_stop(self):
        """Verify: start_transfer(TO_WS) -> transfer_running True, stop_transfer -> False"""
        elevator = TransferElevator(id="e1", travel_time=1.5, transfer_time=3.0)
        assert elevator.position == ElevatorPosition.DOWN
        assert elevator.transfer_running is False

        ok = elevator.start_transfer(TransferDirection.TO_WS)
        assert ok is True
        assert elevator.transfer_running is True
        assert elevator.transfer_direction == TransferDirection.TO_WS

        elevator.stop_transfer()
        assert elevator.transfer_running is False
        assert elevator.transfer_start_time is None

    def test_start_transfer_is_blocked_while_elevator_moving(self):
        """Verify: elevator.position==MOVING 时 start_transfer 返回 False"""
        elevator = TransferElevator(id="e1", travel_time=1.5, transfer_time=3.0)
        assert elevator.request_up() is True
        assert elevator.position == ElevatorPosition.MOVING

        ok = elevator.start_transfer(TransferDirection.TO_WS)
        assert ok is False
        assert elevator.transfer_running is False

