import pytest

from src.mock_up.config import SimulationConfig
from src.mock_up.state import SystemState
from src.mock_up.components import (
    ConveyorMotorState,
    TransferDirection,
    ElevatorPosition,
    BufferState,
    DockingStationState,
    PneumaticState,
    RFIDState,
)


def pneumatic_allows_motion(pneumatic) -> bool:
    """等价映射：气源未开/压力骤降 => pneumatic 不是 NORMAL => 不允许任何物理转移推进。"""
    return getattr(pneumatic, "is_enabled", False) and pneumatic.state == PneumaticState.NORMAL


def conveyor_allows_motion(conveyor) -> bool:
    """等价映射：主输送带电机故障 => conveyor.state==ERROR => 不允许任何 DS/Buffer 收发。"""
    return conveyor.state != ConveyorMotorState.ERROR


def global_motion_allowed(system: SystemState) -> bool:
    conveyor = system.get_component("conveyor_motor")
    elevator = system.get_component("elevator")
    pneumatic = system.get_component("pneumatic")
    _ = elevator  # kept for readability
    return pneumatic_allows_motion(pneumatic) and conveyor_allows_motion(conveyor)


def orchestrator_start_transfer_if_ok(system: SystemState, direction: TransferDirection) -> bool:
    """Synchronization: 必须 Elevator=UP + 方向匹配 + 气动/输送带允许 才能触发 transfer。"""
    elevator = system.get_component("elevator")
    pneumatic = system.get_component("pneumatic")
    conveyor = system.get_component("conveyor_motor")

    if not (pneumatic_allows_motion(pneumatic) and conveyor_allows_motion(conveyor)):
        return False

    if elevator.position != ElevatorPosition.UP:
        return False

    # Direction sensor mismatch: 我们不增加物理组件，用“人为设置 transfer_direction”模拟传感器不同步。
    if elevator.transfer_direction != direction:
        return False

    if elevator.transfer_running:
        return False

    return elevator.start_transfer(direction)


def orchestrator_try_buffer_add_in(system: SystemState, tag: str) -> bool:
    """Timing/RFID: RFID 到 IDENTIFIED 才允许 add_to_buffer(IN)；且气动/输送带/槽位允许。"""
    buffer = system.get_component("buffer")
    rfid_queue = system.get_component("rfid_queue")
    conveyor = system.get_component("conveyor_motor")
    pneumatic = system.get_component("pneumatic")

    if not (pneumatic_allows_motion(pneumatic) and conveyor_allows_motion(conveyor)):
        return False

    # RFID forced delay equivalent: 未 IDENTIFIED 则不允许开始物理入库。
    if rfid_queue.state != RFIDState.IDENTIFIED:
        return False

    if buffer.pallet_count >= buffer.max_capacity:
        return False

    if not buffer.pallet_at_queue:
        return False

    if buffer.is_transferring:
        return False

    return buffer.add_to_buffer()


def orchestrator_try_buffer_remove_out(system: SystemState) -> bool:
    """资源争用/出库：气动/输送带允许才允许 remove_from_buffer(OUT)。"""
    buffer = system.get_component("buffer")
    conveyor = system.get_component("conveyor_motor")
    pneumatic = system.get_component("pneumatic")

    if not (pneumatic_allows_motion(pneumatic) and conveyor_allows_motion(conveyor)):
        return False

    return buffer.remove_from_buffer()


def orchestrator_ds_update_if_synced(ds, system: SystemState, elapsed_time: float, require_transfer_running: bool):
    """
    Timing/Synchronization: 只有满足“升降机在 UP + transfer_running（以及方向正确）”时才推进 ds.update()。
    用于模拟“传感器不同步 => 状态机无限期等待”。
    """
    elevator = system.get_component("elevator")
    pneumatic = system.get_component("pneumatic")
    conveyor = system.get_component("conveyor_motor")

    if not (pneumatic_allows_motion(pneumatic) and conveyor_allows_motion(conveyor)):
        return

    if elevator.position != ElevatorPosition.UP:
        return

    if require_transfer_running and not elevator.transfer_running:
        return

    ds.update(elapsed_time=elapsed_time)


class TestCascadeAndDependenciesGating:
    def test_cascade_when_pneumatic_pressure_off_blocks_all_motion_and_ds_progress(self):
        """Verify: 气源未开启 => transfer/buffer/DS推进全部被 gating 阻断。"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, station_allow_auto_pass=False)
        system = SystemState(config)

        conveyor = system.get_component("conveyor_motor")
        elevator = system.get_component("elevator")
        buffer = system.get_component("buffer")
        ds2 = system.get_component("ds_2")
        pneumatic = system.get_component("pneumatic")

        # Pneumatic OFF by default: is_enabled False, state OFF.
        assert pneumatic.is_enabled is False
        assert pneumatic.state == PneumaticState.OFF
        assert global_motion_allowed(system) is False

        # Prepare: attempt to start transfer and buffer in/out and ds update.
        elevator.transfer_direction = TransferDirection.TO_WS
        elevator.request_up()
        elevator.update(elapsed_time=elevator.travel_time)
        assert elevator.position == ElevatorPosition.UP

        # Transfer blocked
        started = orchestrator_start_transfer_if_ok(system, TransferDirection.TO_WS)
        assert started is False
        assert elevator.transfer_running is False

        # Buffer blocked
        buffer.pallet_enters("TAG_001")
        # Force RFID IDENTIFIED, but pneumatic still OFF => should be blocked by gating.
        rfid_queue = system.get_component("rfid_queue")
        rfid_queue.tag_detected = "TAG_001"
        rfid_queue.state = RFIDState.IDENTIFIED
        assert orchestrator_try_buffer_add_in(system, "TAG_001") is False
        assert buffer.is_transferring is False
        assert buffer.pallet_count == 0

        # DS blocked: 组装工位 DS2 进入 RECEIVING，gating 下不得推进到 PROCESSING
        ds2.pallet_arrived("TAG_001")
        assert ds2.state == DockingStationState.AWAITING_MISSION
        ds2.accept_mission("2")
        assert ds2.state == DockingStationState.RECEIVING

        orchestrator_ds_update_if_synced(ds2, system, elapsed_time=ds2.transfer_time, require_transfer_running=True)
        assert ds2.state == DockingStationState.RECEIVING

    def test_cascade_when_pneumatic_pressure_drop_blocks_motion(self):
        """Verify: 气源开启但压力骤降(LEAK/HIGH) => gating 阻断并停止横移。"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, station_allow_auto_pass=False)
        system = SystemState(config)

        conveyor = system.get_component("conveyor_motor")
        elevator = system.get_component("elevator")
        pneumatic = system.get_component("pneumatic")

        # Simulate pneumatic is enabled but faulted (pressure drop).
        pneumatic.is_enabled = True
        pneumatic.state = PneumaticState.LEAK_DETECTED
        assert pneumatic_allows_motion(pneumatic) is False
        assert global_motion_allowed(system) is False

        # Even if elevator is ready, transfer should not start
        elevator.transfer_direction = TransferDirection.TO_WS
        elevator.request_up()
        elevator.update(elapsed_time=elevator.travel_time)
        assert elevator.position == ElevatorPosition.UP

        started = orchestrator_start_transfer_if_ok(system, TransferDirection.TO_WS)
        assert started is False
        assert elevator.transfer_running is False

        # If transfer was already running, we would stop it in a real orchestrator.
        elevator.transfer_running = True
        # No component modification: just ensure orchestrator refuses starting due to pneumatic fault.
        assert orchestrator_start_transfer_if_ok(system, TransferDirection.TO_WS) is False

    def test_cascade_when_conveyor_motor_error_blocks_ds_and_buffer_receive_send(self):
        """Verify: conveyor ERROR => DS/Buffer 不可接收或送出（这里用 gating 包裹）。"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1)
        system = SystemState(config)

        conveyor = system.get_component("conveyor_motor")
        pneumatic = system.get_component("pneumatic")

        # Make pneumatic NORMAL so only conveyor fault blocks.
        pneumatic.is_enabled = True
        pneumatic.state = PneumaticState.NORMAL

        elevator = system.get_component("elevator")
        buffer = system.get_component("buffer")
        ds2 = system.get_component("ds_2")

        # Conveyor fault
        conveyor.trigger_error()
        assert conveyor.state == ConveyorMotorState.ERROR
        assert global_motion_allowed(system) is False

        # Buffer IN blocked: even with RFID identified
        rfid_queue = system.get_component("rfid_queue")
        buffer.pallet_enters("TAG_001")
        rfid_queue.tag_detected = "TAG_001"
        rfid_queue.state = RFIDState.IDENTIFIED
        assert orchestrator_try_buffer_add_in(system, "TAG_001") is False
        assert buffer.is_transferring is False
        assert buffer.pallet_count == 0

        # Buffer OUT blocked
        buffer.pallet_count = 1
        buffer.update_state()
        assert orchestrator_try_buffer_remove_out(system) is False

        # DS progress blocked: if we call ds.update directly it will progress,
        # so we ensure orchestration does not call it.
        ds2.pallet_arrived("TAG_001")
        ds2.accept_mission("2")
        assert ds2.state == DockingStationState.RECEIVING
        orchestrator_ds_update_if_synced(ds2, system, elapsed_time=ds2.transfer_time, require_transfer_running=False)
        assert ds2.state == DockingStationState.RECEIVING

    def test_synchronization_transfer_requires_elevator_up_and_direction_match(self):
        """Verify: 电梯未到 UP 或方向传感器不同步 => transfer 不触发 => DS 不推进。"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, station_allow_auto_pass=False)
        system = SystemState(config)

        pneumatic = system.get_component("pneumatic")
        conveyor = system.get_component("conveyor_motor")
        elevator = system.get_component("elevator")
        ds2 = system.get_component("ds_2")

        # Allow motion at system level except for synchronization.
        pneumatic.is_enabled = True
        pneumatic.state = PneumaticState.NORMAL
        assert conveyor.state != ConveyorMotorState.ERROR

        # Setup DS2（组装工位）to RECEIVING mission2
        ds2.pallet_arrived("TAG_001")
        assert ds2.accept_mission("2") is True
        assert ds2.state == DockingStationState.RECEIVING

        # Case A: elevator not UP => DS stays in RECEIVING
        # Ensure elevator stays DOWN
        elevator.position = ElevatorPosition.DOWN
        elevator.transfer_running = False
        ds_before = ds2.state
        orchestrator_ds_update_if_synced(ds2, system, elapsed_time=ds2.transfer_time, require_transfer_running=False)
        assert ds2.state == ds_before
        assert elevator.transfer_running is False

        # Case B: elevator UP but direction mismatch => transfer doesn't start => DS doesn't progress if require_transfer_running=True
        elevator.request_up()
        elevator.update(elapsed_time=elevator.travel_time)
        assert elevator.position == ElevatorPosition.UP

        # Inject direction mismatch (simulate Transfer direction sensor not synced)
        elevator.transfer_direction = TransferDirection.FROM_WS
        started = orchestrator_start_transfer_if_ok(system, TransferDirection.TO_WS)
        assert started is False
        assert elevator.transfer_running is False

        orchestrator_ds_update_if_synced(ds2, system, elapsed_time=ds2.transfer_time, require_transfer_running=True)
        assert ds2.state == DockingStationState.RECEIVING

        # Fix direction match: set correct transfer_direction and start transfer
        elevator.transfer_direction = TransferDirection.TO_WS
        started = orchestrator_start_transfer_if_ok(system, TransferDirection.TO_WS)
        assert started is True
        assert elevator.transfer_running is True

        orchestrator_ds_update_if_synced(ds2, system, elapsed_time=ds2.transfer_time, require_transfer_running=True)
        assert ds2.state == DockingStationState.PROCESSING
        assert ds2.pallet_at_ws is True

    def test_resource_contention_buffer_slots_two_only_third_blocked_until_amr_removes(self):
        """Verify: Buffer max=2 => third pallet blocked until remove_from_buffer frees a slot."""
        config = SimulationConfig(
            duration_hours=0.001,
            timestep_seconds=0.1,
            buffer_transfer_time=1.0,
            station_transfer_time=1.0,
        )
        system = SystemState(config)

        pneumatic = system.get_component("pneumatic")
        conveyor = system.get_component("conveyor_motor")
        buffer = system.get_component("buffer")
        rfid_queue = system.get_component("rfid_queue")

        pneumatic.is_enabled = True
        pneumatic.state = PneumaticState.NORMAL
        assert conveyor.state != ConveyorMotorState.ERROR

        # Fill pallet 1
        assert buffer.pallet_count == 0
        assert buffer.pallet_enters("TAG_001") is True
        rfid_queue.state = RFIDState.IDENTIFIED
        rfid_queue.tag_detected = "TAG_001"
        assert orchestrator_try_buffer_add_in(system, "TAG_001") is True
        buffer.update(elapsed_time=buffer.transfer_time)
        assert buffer.pallet_count == 1

        # Fill pallet 2
        assert buffer.pallet_enters("TAG_002") is True
        rfid_queue.state = RFIDState.IDENTIFIED
        rfid_queue.tag_detected = "TAG_002"
        assert orchestrator_try_buffer_add_in(system, "TAG_002") is True
        buffer.update(elapsed_time=buffer.transfer_time)
        assert buffer.pallet_count == 2
        assert buffer.state == BufferState.FULL

        # Attempt pallet 3 while FULL => blocked
        assert buffer.pallet_enters("TAG_003") is True  # queue position free after IN completed
        rfid_queue.state = RFIDState.IDENTIFIED
        rfid_queue.tag_detected = "TAG_003"
        assert orchestrator_try_buffer_add_in(system, "TAG_003") is False
        assert buffer.pallet_count == 2

        # "AMR takes one away" 在当前 mock_up 语义里等价于：从 buffer 存储 OUT 到队列，
        # 但 remove_from_buffer 要求 pallet_at_queue == False，因此先清空挡停队列占用。
        #
        # 注意：Buffer.pallet_leaves() 会把 pallet_count -1（当前实现语义不完全符合我们这个测试）。
        # 为了“只释放队列占用而不动存储槽位”，这里手动清空队列相关字段。
        buffer.pallet_at_queue = False
        buffer.pallet_rfid_at_queue = None
        buffer.queue_detect_start_time = None
        assert orchestrator_try_buffer_remove_out(system) is True
        buffer.update(elapsed_time=buffer.transfer_time)
        assert buffer.pallet_count == 1

        # 队列此时可能重新占用，把它清空后，再让 TAG_003 重新进入队列尝试 IN。
        buffer.pallet_at_queue = False
        buffer.pallet_rfid_at_queue = None
        buffer.queue_detect_start_time = None

        assert buffer.pallet_enters("TAG_003") is True
        rfid_queue.state = RFIDState.IDENTIFIED
        rfid_queue.tag_detected = "TAG_003"
        assert orchestrator_try_buffer_add_in(system, "TAG_003") is True
        buffer.update(elapsed_time=buffer.transfer_time)
        assert buffer.pallet_count == 2
        assert buffer.state == BufferState.FULL

    def test_station_exclusivity_ds1_cannot_receive_second_pallet_while_processing(self):
        """Verify: 组装工位独占 => PROCESSING 期间不得再次 accept_mission（DS1 为进线位不用 Mission 2，改用 DS2）。"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, station_allow_auto_pass=False)
        system = SystemState(config)

        ds2 = system.get_component("ds_2")

        # Pallet 1: go to PROCESSING
        ds2.pallet_arrived("TAG_001")
        assert ds2.accept_mission("2") is True
        ds2.update(elapsed_time=ds2.transfer_time)
        assert ds2.state == DockingStationState.PROCESSING
        assert ds2.current_mission == "2"
        assert ds2.pallet_rfid == "TAG_001"

        # Attempt to accept a second pallet: we model "queue stop hold" by refusing to call pallet_arrived
        # and refusing to accept mission because ds isn't AWAITING_MISSION.
        ok_mission = ds2.accept_mission("2")
        assert ok_mission is False
        assert ds2.pallet_rfid == "TAG_001"

    def test_rfid_timing_requires_0_5s_wait_before_buffer_in(self):
        """Verify: RFID DETECTING <0.5s => 不允许 add_to_buffer(IN)；>=0.5s => 允许。"""
        config = SimulationConfig(duration_hours=0.001, timestep_seconds=0.1, buffer_transfer_time=1.0)
        system = SystemState(config)

        pneumatic = system.get_component("pneumatic")
        conveyor = system.get_component("conveyor_motor")
        buffer = system.get_component("buffer")
        rfid_queue = system.get_component("rfid_queue")

        pneumatic.is_enabled = True
        pneumatic.state = PneumaticState.NORMAL
        assert conveyor.state != ConveyorMotorState.ERROR

        # Queue has pallet, RFID starts detecting.
        assert buffer.pallet_enters("PALLET_RFID_001") is True
        assert rfid_queue.detect("PALLET_RFID_001") is True
        assert rfid_queue.state == RFIDState.DETECTING

        # Before 0.5s: should be blocked.
        rfid_queue.update(elapsed_time=0.49)
        assert rfid_queue.state == RFIDState.DETECTING
        assert orchestrator_try_buffer_add_in(system, "PALLET_RFID_001") is False
        assert buffer.is_transferring is False
        assert buffer.pallet_count == 0

        # At/after 0.5s: allow.
        rfid_queue.update(elapsed_time=0.5)
        assert rfid_queue.state == RFIDState.IDENTIFIED
        assert orchestrator_try_buffer_add_in(system, "PALLET_RFID_001") is True

        buffer.update(elapsed_time=buffer.transfer_time)
        assert buffer.pallet_count == 1
        assert buffer.state == BufferState.PARTIAL

    def test_auto_passing_overwrites_mission_when_no_mission_set_within_wait_time(self):
        """Verify: AWAITING_MISSION 且 current_mission is None，超时后自动 accept_mission('1')."""
        config = SimulationConfig(
            duration_hours=0.001,
            timestep_seconds=0.1,
            station_wait_at_queue=2.0,
        )
        system = SystemState(config)
        ds1 = system.get_component("ds_1")

        # Enable auto pass explicitly for this test.
        ds1.allow_auto_pass = True
        assert ds1.state == DockingStationState.INIT

        ds1.pallet_arrived("TAG_001")
        assert ds1.state == DockingStationState.AWAITING_MISSION
        assert ds1.current_mission is None

        # Not enough time: mission remains None
        ds1.update(elapsed_time=1.9)
        assert ds1.state == DockingStationState.AWAITING_MISSION
        assert ds1.current_mission is None

        # Exceed wait time: auto mission = "1"
        # 注：DockingStation.update(elapsed_time) 不是累积时间，需直接给出 >= time_wait_at_queue 的 elapsed_time
        ds1.update(elapsed_time=2.1)
        assert ds1.state == DockingStationState.RECEIVING
        assert ds1.current_mission == "1"

