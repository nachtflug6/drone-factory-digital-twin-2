import pytest

from src.mock_up.config import SimulationConfig
from src.mock_up.state import SystemState
from src.mock_up.components import (
    ConveyorMotorState,
    TransferDirection,
    ElevatorPosition,
    BufferState,
    DockingStationState,
)


def orchestrator_interlock(system: SystemState) -> None:
    """
    Minimal “控制编排层”互锁逻辑 (只在测试里实现，不改现有业务代码)：
    1) 若输送带电机故障，则停止横移皮带转运。
    2) 若 Buffer 满载，则停止输送带并停止横移皮带。
    """
    conveyor = system.get_component("conveyor_motor")
    elevator = system.get_component("elevator")
    buffer = system.get_component("buffer")

    if conveyor.state == ConveyorMotorState.ERROR:
        elevator.stop_transfer()

    if buffer.state == BufferState.FULL and conveyor.state != ConveyorMotorState.IDLE:
        conveyor.stop()
        elevator.stop_transfer()


def try_accept_mission_with_elevator_sync(ds, mission: str, elevator) -> bool:
    """资源争用/同步：电梯横移运行时，不允许另一个工位接收 Mission。"""
    if elevator.transfer_running:
        return False
    return ds.accept_mission(mission)


def orchestrated_ds_update(ds, elapsed_time: float, elevator) -> None:
    """时序依赖：只有当电梯在 UP 时才允许工位推进到下一 SFC 步。"""
    if elevator.position == ElevatorPosition.UP:
        ds.update(elapsed_time=elapsed_time)


class TestIntegratedOrchestrationInterlocks:
    def test_cascade_fault_conveyor_error_stops_elevator_transfer(self):
        """Verify: conveyor ERROR (cascade) => orchestrator stops elevator transfer"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, station_transfer_time=0.5)
        system = SystemState(config)

        conveyor = system.get_component("conveyor_motor")
        elevator = system.get_component("elevator")

        assert elevator.transfer_running is False
        assert elevator.position == ElevatorPosition.DOWN

        assert elevator.start_transfer(TransferDirection.TO_WS) is True
        assert elevator.transfer_running is True

        conveyor.trigger_error()
        assert conveyor.state == ConveyorMotorState.ERROR

        orchestrator_interlock(system)
        assert elevator.transfer_running is False

    def test_resource_contention_elevator_busy_blocks_second_station_mission(self):
        """Verify: elevator.transfer_running => second station cannot accept mission"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1)
        system = SystemState(config)

        elevator = system.get_component("elevator")
        ds_1 = system.get_component("ds_1")
        ds_2 = system.get_component("ds_2")

        # DS1 becomes busy: elevator is transferring to WS
        assert elevator.start_transfer(TransferDirection.TO_WS) is True
        assert elevator.transfer_running is True

        ds_2.pallet_arrived("TAG_002")
        assert ds_2.state == DockingStationState.AWAITING_MISSION
        assert ds_2.current_mission is None

        ok = try_accept_mission_with_elevator_sync(ds_2, "2", elevator)
        assert ok is False
        assert ds_2.current_mission is None
        assert ds_2.state == DockingStationState.AWAITING_MISSION

    def test_synchronization_timing_ds_processing_requires_elevator_up(self):
        """Verify: ds.update() is gated by elevator.position == UP"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, station_transfer_time=1.0)
        system = SystemState(config)

        elevator = system.get_component("elevator")
        # DS1 is ingress-only; Mission 2 在组装工位（如 DS2）上验证
        ds_2 = system.get_component("ds_2")

        ds_2.pallet_arrived("TAG_001")
        ok = ds_2.accept_mission("2")
        assert ok is True
        assert ds_2.state == DockingStationState.RECEIVING
        assert ds_2.current_mission == "2"

        # Attempt to advance DS without elevator up: orchestrator should skip ds.update()
        orchestrated_ds_update(ds_2, elapsed_time=2.0, elevator=elevator)
        assert ds_2.state == DockingStationState.RECEIVING

        # Now elevator reaches UP, orchestrator allows ds.update()
        assert elevator.request_up() is True
        elevator.update(elapsed_time=elevator.travel_time)
        assert elevator.position == ElevatorPosition.UP

        orchestrated_ds_update(ds_2, elapsed_time=2.0, elevator=elevator)  # > transfer_time
        assert ds_2.state == DockingStationState.PROCESSING
        assert ds_2.pallet_at_ws is True
        assert ds_2.pallet_present is False

    def test_buffer_full_resource_interlock_stops_conveyor_and_elevator(self):
        """Verify: Buffer FULL => conveyor.stop() and elevator.stop_transfer()"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, buffer_transfer_time=1.0)
        system = SystemState(config)

        conveyor = system.get_component("conveyor_motor")
        elevator = system.get_component("elevator")
        buffer = system.get_component("buffer")

        # Make buffer FULL
        buffer.pallet_count = buffer.max_capacity
        buffer.update_state()
        assert buffer.state == BufferState.FULL

        # Conveyor running
        assert conveyor.start(speed_percent=60.0) is True
        conveyor.update(elapsed_time=10.0)
        assert conveyor.state == ConveyorMotorState.RUNNING

        # Elevator transfer running
        assert elevator.start_transfer(TransferDirection.TO_WS) is True
        assert elevator.transfer_running is True

        orchestrator_interlock(system)

        assert buffer.state == BufferState.FULL
        assert elevator.transfer_running is False
        assert conveyor.state == ConveyorMotorState.RAMP_DOWN

