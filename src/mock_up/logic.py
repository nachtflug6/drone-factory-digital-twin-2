# src/mock_up/logic.py
"""System Logic

Implements the control logic translated from PLC documentation.
This is where you implement the state machine transitions and conditions.

IMPORTANT:
Analyze the PLC documentation and implement the logic rules here.
Each function should represent a decision from the documentation.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from .state import SystemState
from .components import ConveyorMotorState, DockingStationState
from .config import SimulationConfig


def count_pallets_on_line(
    comps: Dict[str, Any],
    pending_line_arrivals: Sequence[Any],
    station_numbers: List[int],
) -> int:
    """场上托盘数：Buffer 存储与队列位、主线在途、各 DS（接收中或托盘在位）/ Pallets currently on line: buffer storage/queue, in-transit main line, and each DS (receiving or pallet present)."""
    buffer = comps["buffer"]
    n = int(buffer.pallet_count) + (1 if buffer.pallet_at_queue else 0)
    n += len(pending_line_arrivals)
    for sid in station_numbers:
        ds = comps[f"ds_{sid}"]
        st = getattr(ds.state, "value", None)
        if st == "receiving":
            n += 1
        elif getattr(ds, "pallet_present", False) or getattr(ds, "pallet_at_ws", False):
            n += 1
    return n


# ============================================================================
# RAW MATERIAL INGRESS (DS1 Mission 3, AMR → Buffer)
# ============================================================================


class RawMaterialIngressScheduler:
    """
    按固定仿真时间间隔产生「一批」原材料托盘 RFID，并在 DS1 为 INIT 时下发 Mission 3。 / Generate one batch of raw-material RFID pallets at fixed simulation intervals and dispatch Mission 3 when DS1 is INIT.

    若 DS1 正忙，RFID 在 ``pending_rfids`` 中排队，不丢失批次。 / If DS1 is busy, RFIDs queue in ``pending_rfids`` without losing batches.
    """

    def __init__(
        self,
        interval_seconds: float,
        pallets_per_batch: int = 1,
        pallet_id_prefix: str = "RAW",
    ):
        self.interval_seconds = float(interval_seconds)
        self.pallets_per_batch = max(1, int(pallets_per_batch))
        self.pallet_id_prefix = pallet_id_prefix
        self._next_fire: float = 0.0
        self._seq: int = 0
        self.pending_rfids: List[str] = []

    def tick(
        self,
        sim_time: float,
        ds1: Any,
        *,
        max_pallets_on_line: Optional[int] = None,
        get_pallet_count: Optional[Callable[[], int]] = None,
    ) -> List[str]:
        """
        每个仿真步调用一次。返回本步成功触发 Mission 3 的 RFID 列表。 / Call once per simulation step and return RFIDs that successfully triggered Mission 3 in this step.

        若同时传入 ``max_pallets_on_line`` 与 ``get_pallet_count``：场上已达上限时 / If both ``max_pallets_on_line`` and ``get_pallet_count`` are provided and on-line count reaches limit,
        暂停按间隔向 ``pending_rfids`` 追加新批次，且不再接受新的 Mission 3，直至计数下降。 / pause appending new batches and stop accepting new Mission 3 until the count drops.
        """
        ingressed: List[str] = []
        eps = 1e-9
        limit = max_pallets_on_line is not None and get_pallet_count is not None

        while sim_time + eps >= self._next_fire:
            if limit and get_pallet_count() >= max_pallets_on_line:
                break
            for _ in range(self.pallets_per_batch):
                self._seq += 1
                self.pending_rfids.append(f"{self.pallet_id_prefix}_{self._seq:06d}")
            self._next_fire += self.interval_seconds

        while self.pending_rfids and getattr(ds1, "state", None) == DockingStationState.INIT:
            if limit and get_pallet_count() >= max_pallets_on_line:
                break
            buffer = getattr(ds1, "buffer", None)
            # DS1 Mission 3 下发前先看 Buffer 队列位是否空闲，避免在接收完成时触发拥塞错误。 / Check Buffer queue availability before dispatching DS1 Mission 3 to avoid congestion errors at receive completion.
            if buffer is not None and (getattr(buffer, "pallet_at_queue", False) or getattr(buffer, "is_transferring", False)):
                break
            rfid = self.pending_rfids[0]
            if ds1.accept_mission("3", pallet_rfid=rfid):
                ingressed.append(rfid)
                self.pending_rfids.pop(0)
            else:
                break
        return ingressed


@dataclass
class PerformanceMetricsCollector:
    """Collect station/system/logistics performance metrics in simulation time."""

    config: SimulationConfig
    sample_interval_seconds: float = 10.0
    uph_window_seconds: float = 3600.0

    station_cycle_times: Dict[int, List[float]] = field(default_factory=dict)
    station_starvation_seconds: Dict[int, float] = field(default_factory=dict)
    station_starvation_episodes: Dict[int, int] = field(default_factory=dict)
    station_blockage_seconds: Dict[int, float] = field(default_factory=dict)
    station_ready_since: Dict[int, float] = field(default_factory=dict)
    station_processing_since: Dict[int, float] = field(default_factory=dict)
    station_sending_since: Dict[int, float] = field(default_factory=dict)

    resource_wait_start: Dict[int, float] = field(default_factory=dict)
    resource_wait_seconds_total: float = 0.0
    resource_wait_samples: List[float] = field(default_factory=list)

    pallet_ingress_time: Dict[str, float] = field(default_factory=dict)
    pallet_lead_times: List[float] = field(default_factory=list)
    completed_output_times: deque = field(default_factory=deque)
    completed_units_total: int = 0

    wip_current: int = 0  # 场上未完成物理托盘数（与 count_pallets_on_line 一致，由采样更新） / Unfinished physical pallet count on line (sampled, consistent with count_pallets_on_line)
    wip_samples: List[int] = field(default_factory=list)

    buffer_full_count: int = 0
    buffer_occupancy_samples: List[float] = field(default_factory=list)

    last_sample_at: float = 0.0

    def __post_init__(self) -> None:
        if self.sample_interval_seconds <= 0:
            self.sample_interval_seconds = max(float(self.config.snapshot_interval_seconds), 1.0)
        for sid in self.config.station_numbers:
            self.station_cycle_times.setdefault(sid, [])
            self.station_starvation_seconds.setdefault(sid, 0.0)
            self.station_starvation_episodes.setdefault(sid, 0)
            self.station_blockage_seconds.setdefault(sid, 0.0)

    def on_station_state_change(
        self,
        station_id: int,
        old_state: str,
        new_state: str,
        sim_time_s: float,
    ) -> None:
        # Starvation window starts when station is ready and empty.
        if new_state in ("init", "awaiting_mission") and old_state not in ("init", "awaiting_mission"):
            self.station_ready_since[station_id] = sim_time_s
        if new_state == "receiving":
            started = self.station_ready_since.pop(station_id, None)
            if started is not None and sim_time_s >= started:
                self.station_starvation_seconds[station_id] += sim_time_s - started
                self.station_starvation_episodes[station_id] = (
                    int(self.station_starvation_episodes.get(station_id, 0)) + 1
                )

        # Actual cycle time: processing -> next state.
        if new_state == "processing":
            self.station_processing_since[station_id] = sim_time_s
        if old_state == "processing" and new_state in ("sending", "cleanup", "init", "amr_handoff_wait"):
            started = self.station_processing_since.pop(station_id, None)
            if started is not None and sim_time_s >= started:
                self.station_cycle_times[station_id].append(sim_time_s - started)

        # Blockage: in sending until pallet can leave.
        if new_state == "sending":
            self.station_sending_since[station_id] = sim_time_s
        if old_state == "sending" and new_state in ("cleanup", "init", "amr_handoff_wait"):
            started = self.station_sending_since.pop(station_id, None)
            if started is not None and sim_time_s >= started:
                self.station_blockage_seconds[station_id] += sim_time_s - started

    def on_ingress(self, pallet_id: str, sim_time_s: float) -> None:
        self.pallet_ingress_time.setdefault(pallet_id, sim_time_s)

    def on_product_output(self, pallet_id: Optional[str], sim_time_s: float) -> None:
        self.completed_units_total += 1
        self.completed_output_times.append(sim_time_s)
        while self.completed_output_times and sim_time_s - self.completed_output_times[0] > self.uph_window_seconds:
            self.completed_output_times.popleft()
        if pallet_id:
            started = self.pallet_ingress_time.pop(pallet_id, None)
            if started is not None and sim_time_s >= started:
                self.pallet_lead_times.append(sim_time_s - started)

    def on_buffer_state_change(self, old_state: str, new_state: str) -> None:
        if old_state != "full" and new_state == "full":
            self.buffer_full_count += 1

    def on_resource_wait_start(self, station_id: int, sim_time_s: float) -> None:
        # 不区分 up/down：站点级资源争抢等待统一统计。 / No up/down split: aggregate resource contention wait at station level.
        if station_id not in self.resource_wait_start:
            self.resource_wait_start[station_id] = sim_time_s

    def on_resource_transfer_started(self, station_id: int, sim_time_s: float) -> None:
        started = self.resource_wait_start.pop(station_id, None)
        if started is not None and sim_time_s >= started:
            wait_s = sim_time_s - started
            self.resource_wait_seconds_total += wait_s
            self.resource_wait_samples.append(wait_s)

    def maybe_sample(
        self,
        sim_time_s: float,
        buffer_count: int,
        buffer_capacity: int,
        *,
        wip_on_line: int,
    ) -> bool:
        if sim_time_s + 1e-9 < self.last_sample_at + self.sample_interval_seconds:
            return False
        self.last_sample_at = sim_time_s
        self.wip_current = max(0, int(wip_on_line))
        cap = max(int(buffer_capacity), 1)
        self.buffer_occupancy_samples.append(float(buffer_count) / float(cap))
        self.wip_samples.append(int(self.wip_current))
        return True

    def snapshot(self, sim_time_s: float) -> Dict[str, Any]:
        uph_window_units = len(self.completed_output_times)
        uph = (uph_window_units * 3600.0 / self.uph_window_seconds) if self.uph_window_seconds > 0 else 0.0
        station = {}
        for sid in self.config.station_numbers:
            cycles = self.station_cycle_times.get(sid, [])
            starv_s = float(self.station_starvation_seconds.get(sid, 0.0))
            starv_n = int(self.station_starvation_episodes.get(sid, 0))
            station[f"ds_{sid}"] = {
                "actual_cycle_time_avg_s": (sum(cycles) / len(cycles)) if cycles else None,
                "actual_cycle_time_samples": len(cycles),
                "starvation_time_s": starv_s,
                "starvation_episodes": starv_n,
                "starvation_avg_s": (starv_s / starv_n) if starv_n > 0 else None,
                "starvation_fraction_of_sim": (starv_s / sim_time_s) if sim_time_s > 1e-9 else None,
                "blockage_time_s": self.station_blockage_seconds.get(sid, 0.0),
            }
        return {
            "sim_time_s": sim_time_s,
            "station_metrics": station,
            "system_metrics": {
                "throughput_total_units": self.completed_units_total,
                "throughput_uph_window": uph,
                "lead_time_avg_s": (sum(self.pallet_lead_times) / len(self.pallet_lead_times))
                if self.pallet_lead_times
                else None,
                "lead_time_samples": len(self.pallet_lead_times),
                "wip_current": int(self.wip_current),
                "wip_avg_sampled": (sum(self.wip_samples) / len(self.wip_samples)) if self.wip_samples else 0.0,
            },
            "logistics_metrics": {
                "buffer_full_count": self.buffer_full_count,
                "buffer_occupancy_avg": (
                    sum(self.buffer_occupancy_samples) / len(self.buffer_occupancy_samples)
                    if self.buffer_occupancy_samples
                    else 0.0
                ),
                "resource_contention_wait_total_s": self.resource_wait_seconds_total,
                "resource_contention_wait_avg_s": (
                    sum(self.resource_wait_samples) / len(self.resource_wait_samples)
                    if self.resource_wait_samples
                    else 0.0
                ),
                "resource_contention_wait_samples": len(self.resource_wait_samples),
            },
        }


def build_station_processing_route(config: SimulationConfig) -> List[int]:
    """
    Current plant revision route:
    - WS1 ingress/buffer (no assembly)
    - WS4 AGV docking (ignored in model)
    - Assembly stations: WS2, WS3, WS5, WS6
    """
    return [sid for sid in config.assembly_station_numbers if sid in config.ws_path_order]


def conveyor_travel_time_seconds(config: SimulationConfig, from_station: int, to_station: int) -> float:
    """Estimate conveyor travel time between two stations using configured distances."""
    if from_station == to_station:
        return 0.0
    order_idx = {sid: idx for idx, sid in enumerate(config.ws_path_order)}
    if from_station not in order_idx or to_station not in order_idx:
        raise ValueError("from_station/to_station not in ws_path_order")
    a = order_idx[from_station]
    b = order_idx[to_station]
    lo, hi = (a, b) if a < b else (b, a)
    total_distance_m = 0.0
    for idx in range(lo, hi):
        s0 = config.ws_path_order[idx]
        s1 = config.ws_path_order[idx + 1]
        key = (s0, s1) if (s0, s1) in config.ws_neighbor_distances_m else (s1, s0)
        if key not in config.ws_neighbor_distances_m:
            raise ValueError(f"missing neighbor distance between {s0} and {s1}")
        total_distance_m += config.ws_neighbor_distances_m[key]
    speed = max(config.conveyor_max_speed_ms, 1e-9)
    return total_distance_m / speed


def conveyor_travel_time_ingress_to_station(config: SimulationConfig, target_station: int) -> float:
    """
    自进线工位 ``ws_ingress_station``（Buffer/主线接驳点）起，沿主线至 ``target_station`` 中心， / Starting from ingress station ``ws_ingress_station`` (Buffer/main-line handoff), travel along main line to center of ``target_station``,
    再经 ``conveyor_to_ws_loading_position_m`` 到达该 DS 的输送接口/装载位置名义点的行程时间（秒）。 / then add ``conveyor_to_ws_loading_position_m`` to reach the DS conveyor interface/loading nominal point (seconds).

    速度取 ``conveyor_max_speed_ms``（名义满载速），不单独拆开加速度；与 ``conveyor_travel_time_seconds`` 一致。 / Speed uses ``conveyor_max_speed_ms`` (nominal full-load speed), without separate acceleration model; consistent with ``conveyor_travel_time_seconds``.
    """
    ingress = config.ws_ingress_station
    speed = max(config.conveyor_max_speed_ms, 1e-9)
    line_s = conveyor_travel_time_seconds(config, ingress, target_station)
    approach_s = float(config.conveyor_to_ws_loading_position_m) / speed
    return line_s + approach_s


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
    
    if hasattr(motor, "is_malfunctioning"):
        return not motor.is_malfunctioning
    return True


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
    if motor is None:
        return
    if not hasattr(motor, "state") or not hasattr(motor, "update"):
        return
    if motor.state not in (ConveyorMotorState.RAMP_UP, ConveyorMotorState.RAMP_DOWN):
        return

    transition_start = getattr(motor, "transition_start_time", None)
    if isinstance(transition_start, datetime):
        elapsed_seconds = max((current_time - transition_start).total_seconds(), 0.0)
    else:
        elapsed_seconds = 0.0
    motor.update(elapsed_seconds)


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

    # Backward-compatible minimal checks: only enforce rules that exist.
    if hasattr(conveyor, "load_kg") and hasattr(conveyor, "max_load_kg"):
        if conveyor.load_kg > conveyor.max_load_kg:
            return False

    if hasattr(conveyor, "error_flag") and conveyor.error_flag:
        return False
    if hasattr(conveyor, "is_malfunctioning") and conveyor.is_malfunctioning:
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
    
    if hasattr(conveyor, "check_load"):
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
    for motor in system.get_components_by_type('conveyormotor'):
        update_motor_acceleration(system, motor.id, current_time)
    
    # Conveyor control
    for conveyor in system.get_components_by_type('conveyormotor'):
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
    for motor in system.get_components_by_type('conveyormotor'):
        # Motor can't exceed max speed
        if hasattr(motor, "current_speed_percent") and hasattr(motor, "max_speed_percent"):
            if motor.current_speed_percent > motor.max_speed_percent:
                violations.append(
                    f"{motor.id}: Speed {motor.current_speed_percent} exceeds max {motor.max_speed_percent}"
                )
    
    for conveyor in system.get_components_by_type('conveyormotor'):
        # Conveyor can't have negative load
        if hasattr(conveyor, "load_kg") and conveyor.load_kg < 0:
            violations.append(f"{conveyor.id}: Negative load {conveyor.load_kg}")
    
    return (len(violations) == 0, violations)
