import pytest

from datetime import timedelta

from src.mock_up.components import (
    ConveyorMotor,
    ConveyorMotorState,
    TransferElevator,
    ElevatorPosition,
    TransferDirection,
    Buffer,
    BufferState,
    DockingStation,
    DockingStationState,
    PneumaticSystem,
    PneumaticState,
    RFIDReader,
    RFIDState,
)


def _log(component: str, step: str) -> None:
    # Prints are helpful when running `pytest -s`; harmless for normal runs.
    print(f"[TEST] {component}: {step}")


def test_conveyor_motor_idle_to_ramp_up_to_running():
    _log("ConveyorMotor", "IDLE -> RAMP_UP -> RUNNING")
    motor = ConveyorMotor(id="mc1", ramp_time=2.0, max_speed_percent=100.0)
    assert motor.state == ConveyorMotorState.IDLE

    ok = motor.start(speed_percent=50.0)
    assert ok is True
    assert motor.state == ConveyorMotorState.RAMP_UP
    assert motor.target_speed_percent == 50.0

    motor.update(elapsed_time=1.0)
    _log("ConveyorMotor", "RAMP_UP mid-way (speed should be between 0 and target)")
    assert motor.state == ConveyorMotorState.RAMP_UP
    assert 0.0 < motor.current_speed_percent < motor.target_speed_percent

    motor.update(elapsed_time=2.0)
    _log("ConveyorMotor", "RAMP_UP -> RUNNING at full speed")
    assert motor.state == ConveyorMotorState.RUNNING
    assert motor.current_speed_percent == motor.target_speed_percent


def test_conveyor_motor_running_to_idle_on_stop():
    _log("ConveyorMotor", "RUNNING -> RAMP_DOWN -> IDLE")
    motor = ConveyorMotor(id="mc1", ramp_time=2.0)
    assert motor.start(speed_percent=50.0) is True
    motor.update(elapsed_time=2.0)  # now running
    assert motor.state == ConveyorMotorState.RUNNING

    assert motor.stop() is True
    assert motor.state == ConveyorMotorState.RAMP_DOWN

    motor.update(elapsed_time=2.0)
    _log("ConveyorMotor", "RAMP_DOWN -> IDLE (speed=0)")
    assert motor.state == ConveyorMotorState.IDLE
    assert motor.current_speed_percent == 0.0


def test_conveyor_motor_error_blocks_start_and_reset_returns_idle():
    _log("ConveyorMotor", "trigger_error -> ERROR (start blocked), then reset_error -> IDLE")
    motor = ConveyorMotor(id="mc1", ramp_time=2.0)
    motor.trigger_error()
    assert motor.state == ConveyorMotorState.ERROR

    # Start should be blocked while malfunctioning
    assert motor.start(speed_percent=50.0) is False
    assert motor.state == ConveyorMotorState.ERROR

    motor.reset_error()
    assert motor.is_malfunctioning is False
    assert motor.state == ConveyorMotorState.IDLE


def test_transfer_elevator_down_to_up_and_back_to_down():
    _log("TransferElevator", "DOWN -> MOVING -> UP -> MOVING -> DOWN")
    elevator = TransferElevator(id="e1", travel_time=1.5)
    assert elevator.position == ElevatorPosition.DOWN

    assert elevator.request_up() is True
    assert elevator.position == ElevatorPosition.MOVING

    elevator.update(elapsed_time=1.5)
    _log("TransferElevator", "UP reached; transition_start_time cleared")
    assert elevator.position == ElevatorPosition.UP
    assert elevator.transition_start_time is None

    # The component uses request latches for interlocks; in normal flow
    # HMI/PLC would reset those latches after reaching target.
    elevator.up_requested = False

    assert elevator.request_down() is True
    assert elevator.position == ElevatorPosition.MOVING
    elevator.update(elapsed_time=1.5)
    _log("TransferElevator", "DOWN reached; transition_start_time cleared")
    assert elevator.position == ElevatorPosition.DOWN
    assert elevator.transition_start_time is None


def test_transfer_elevator_direction_conflict_sets_error():
    _log("TransferElevator", "UP request latched, then conflicting DOWN request => ERROR")
    elevator = TransferElevator(id="e1", travel_time=1.5)
    assert elevator.request_up() is True
    assert elevator.position == ElevatorPosition.MOVING

    # Conflict while up_requested is still latched
    ok = elevator.request_down()
    _log("TransferElevator", "Conflicting request should be rejected and set ERROR")
    assert ok is False
    assert elevator.position == ElevatorPosition.ERROR


def test_transfer_elevator_transfer_start_stop():
    _log("TransferElevator", "start_transfer(TO_WS) -> stop_transfer")
    elevator = TransferElevator(id="e1", travel_time=1.5, transfer_time=3.0)
    assert elevator.position == ElevatorPosition.DOWN
    assert elevator.transfer_running is False

    assert elevator.start_transfer(TransferDirection.TO_WS) is True
    assert elevator.transfer_running is True
    assert elevator.transfer_direction == TransferDirection.TO_WS

    elevator.stop_transfer()
    _log("TransferElevator", "transfer_running cleared and transfer_start_time None")
    assert elevator.transfer_running is False
    assert elevator.transfer_start_time is None


def test_buffer_queue_to_storage_and_back_out():
    _log("Buffer", "pallet_enters -> add_to_buffer(IN) -> update, then remove_from_buffer(OUT) -> update")
    buf = Buffer(id="buf1", max_capacity=2, transfer_time=2.0)
    assert buf.state == BufferState.EMPTY
    assert buf.pallet_count == 0
    assert buf.pallet_at_queue is False

    # Arrive at queue and transfer IN to storage
    assert buf.pallet_enters("TAG_001") is True
    assert buf.pallet_at_queue is True
    assert buf.add_to_buffer() is True
    assert buf.is_transferring is True

    buf.update(elapsed_time=2.0)
    _log("Buffer", "IN transfer completed (pallet_count should increase and queue clear)")
    assert buf.is_transferring is False
    assert buf.pallet_count == 1
    assert buf.state == BufferState.PARTIAL
    assert buf.pallet_at_queue is False
    assert buf.pallet_rfid_at_queue is None
    assert buf.stored_rfids == ["TAG_001"]

    # Transfer OUT back to queue
    assert buf.remove_from_buffer() is True
    assert buf.is_transferring is True
    buf.update(elapsed_time=2.0)
    _log("Buffer", "OUT transfer completed (pallet_count should decrease and queue RFID restored)")
    assert buf.pallet_count == 0
    assert buf.state == BufferState.EMPTY
    assert buf.pallet_at_queue is True
    assert buf.pallet_rfid_at_queue == "TAG_001"
    assert buf.stored_rfids == []


def test_docking_station_main_processing_cycle_mission_2():
    _log("DockingStation(ds_1)", "INIT -> AWAITING_MISSION -> RECEIVING(mission2) -> PROCESSING -> SENDING -> CLEANUP -> INIT")
    ds = DockingStation(id="ds1", station_number=1, time_wait_at_queue=10.0, transfer_time=2.0, allow_auto_pass=False)

    # INIT -> AWAITING_MISSION on pallet arrival
    ds.pallet_arrived("TAG_001")
    assert ds.state == DockingStationState.AWAITING_MISSION
    assert ds.pallet_present is True
    assert ds.current_mission is None

    # AWAITING_MISSION -> RECEIVING on mission 2
    ok = ds.accept_mission("2")
    assert ok is True
    assert ds.state == DockingStationState.RECEIVING
    assert ds.current_mission == "2"

    # RECEIVING (mission 2) -> PROCESSING on transfer completion
    ds.update(elapsed_time=2.0)
    _log("DockingStation", "RECEIVING(mission2) -> PROCESSING")
    assert ds.state == DockingStationState.PROCESSING
    assert ds.pallet_present is False
    assert ds.pallet_at_ws is True
    assert ds.current_mission == "2"

    # PROCESSING -> SENDING on operator completion
    ds.complete_processing()
    _log("DockingStation", "PROCESSING -> SENDING(_ws_sendout)")
    assert ds.state == DockingStationState.SENDING
    assert ds.current_mission == "_ws_sendout"

    # SENDING -> CLEANUP on transfer completion
    ds.update(elapsed_time=2.0)
    _log("DockingStation", "SENDING -> CLEANUP")
    assert ds.state == DockingStationState.CLEANUP

    # CLEANUP -> INIT after cleanup delay (0.5s)
    ds.update(elapsed_time=0.5)
    _log("DockingStation", "CLEANUP -> INIT")
    assert ds.state == DockingStationState.INIT
    assert ds.current_mission is None


def test_pneumatic_enable_to_normal_and_fault_on_low_max_flow():
    _log("PneumaticSystem", "OFF -> STABILIZING -> (fault) LEAK_DETECTED, then disable -> OFF")
    pneu = PneumaticSystem(
        id="p1",
        target_pressure_bar=6.0,
        min_pressure_bar=5.5,
        max_pressure_bar=7.0,
        max_flow_nm3h=0.1,  # Force LEAK_DETECTED (normal flow is 0.5 in NORMAL)
        stabilization_time=2.0,
    )
    assert pneu.state == PneumaticState.OFF
    assert pneu.is_enabled is False

    pneu.enable()
    assert pneu.state == PneumaticState.STABILIZING
    assert pneu.is_enabled is True

    pneu.update(elapsed_time=2.0)
    _log("PneumaticSystem", "After stabilization_time, state should become NORMAL/LEAK/HIGH_PRESSURE")
    assert pneu.state in (PneumaticState.NORMAL, PneumaticState.LEAK_DETECTED, PneumaticState.HIGH_PRESSURE)

    # Now in NORMAL branch; the update() logic may detect LEAK_DETECTED immediately
    pneu.update(elapsed_time=0.0)
    assert pneu.state == PneumaticState.LEAK_DETECTED

    pneu.disable()
    assert pneu.state == PneumaticState.OFF
    assert pneu.current_pressure_bar == 0.0
    assert pneu.current_flow_nm3h == 0.0


def test_rfid_reader_detect_to_identified_and_clear():
    _log("RFIDReader", "IDLE -> DETECTING -> IDENTIFIED -> clear() -> IDLE")
    rfid = RFIDReader(id="r1", location="queue", detection_delay=0.5)
    assert rfid.state == RFIDState.IDLE
    assert rfid.detect("TAG_001") is True
    assert rfid.state == RFIDState.DETECTING
    assert rfid.tag_detected == "TAG_001"

    rfid.update(elapsed_time=0.49)
    _log("RFIDReader", "Before detection_delay: still DETECTING")
    assert rfid.state == RFIDState.DETECTING

    rfid.update(elapsed_time=0.5)
    _log("RFIDReader", "At/after detection_delay: IDENTIFIED")
    assert rfid.state == RFIDState.IDENTIFIED
    assert rfid.detect_start_time is None

    rfid.clear()
    _log("RFIDReader", "After clear(): back to IDLE, tag cleared")
    assert rfid.state == RFIDState.IDLE
    assert rfid.tag_detected is None
    assert rfid.detect_start_time is None

