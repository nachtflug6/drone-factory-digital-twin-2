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
from typing import Dict, Optional, List, Tuple


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
    elevator_transfer_time: float = 3.0  # Seconds for cross-transfer belt
    elevator_positions: List[str] = field(default_factory=lambda: ["DOWN", "UP"])
    elevator_initial_position: str = "DOWN"
    
    # ========================================================================
    # BUFFER SYSTEM
    # ========================================================================
    # Pallet buffer and queue
    buffer_max_capacity: int = 2  # Max 2 pallets in buffer
    buffer_transfer_time: float = 3.0  # Seconds to move pallet in/out
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
    station_transfer_time: float = 2.0  # Physical transfer between queue/WS
    station_allow_auto_pass: bool = True
    station_wait_after_passing: float = 1.0  # hmi_TimeForWaitAfterPassingDS
    station_wait_after_ws_transfer: float = 1.0  # hmi_TimeForWaitAfterTransferdToWS
    # 手册默认约 4000 ms；现实产线可按需调整 / Manual default is about 4000 ms; tune for real line as needed
    station_wait_after_amr_transfer: float = 4.0  # hmi_TimeForWaitAfterTransferdToAMR (s)

    # ========================================================================
    # WORKER ASSEMBLY (WS) — 统计/仿真 / metrics and simulation
    # ========================================================================
    # 工人组装时间（秒）：在 [min, max] 内，默认 2–15 分钟；随机时为截断指数分布 / Worker assembly time (s): within [min, max], default 2-15 min; stochastic mode uses truncated exponential
    assembly_time_min_seconds: float = 120.0   # 2 min
    assembly_time_max_seconds: float = 900.0   # 15 min
    # 在 min 之上叠加指数分量 Exp(scale)，再截断到 max（scale 越大长尾越明显） / Add Exp(scale) above min and cap at max (larger scale yields heavier tail)
    assembly_exponential_scale_seconds: float = 180.0
    # 组装时长分布：truncated_exponential | uniform | deterministic / Assembly duration distribution options
    assembly_duration_distribution: str = "truncated_exponential"
    # True：按上式随机采样；False：固定为 (min+max)/2（便于回归/单元测试） / True: stochastic sampling; False: fixed midpoint for regression/unit tests
    assembly_use_stochastic_duration: bool = True
    # 工人效率系数（1.0 为基准）：>1 更快，<1 更慢；作用于组装耗时 duration/efficiency / Worker efficiency factor (1.0 baseline): >1 faster, <1 slower; applied as duration/efficiency
    worker_efficiency_base: float = 1.0
    # 班次效率表：(start_hour, end_hour, efficiency)。支持跨午夜（如 22->6）。 / Shift efficiency table: (start_hour, end_hour, efficiency), supports crossing midnight (e.g., 22->6).
    # 若为空则始终使用 worker_efficiency_base。 / If empty, always use worker_efficiency_base.
    worker_efficiency_shifts: List[Tuple[float, float, float]] = field(default_factory=list)

    # ========================================================================
    # RAW MATERIAL / AMR INGRESS (DS1 Mission 3)
    # ========================================================================
    # 每隔固定仿真时间有一批原材料托盘经 AMR→DS1→Buffer 进入系统 / A batch of raw-material pallets enters via AMR->DS1->Buffer at fixed simulation intervals
    raw_material_batch_interval_seconds: float = 600.0  # 10 min
    raw_material_pallets_per_batch: int = 1

    # ========================================================================
    # LINE TOPOLOGY (现实产线修订 / real line revision)
    # ========================================================================
    pallet_length_m: float = 0.25  # 25 cm
    ws_ingress_station: int = 1  # WS1: ingress + buffer handoff
    ws_egress_station: int = 6   # WS6: immediate output
    # 仅这些工位执行组装（其余为过渡/接驳位） / Only these stations perform assembly (others are transition/docking points)
    assembly_station_numbers: List[int] = field(default_factory=lambda: [2, 3, 5, 6])
    # WS4 为 AGV 接驳位，当前模型忽略 AGV 动作，仅保留名义站位 / WS4 is AGV docking station; model ignores AGV actions and keeps nominal slot
    agv_docking_station_numbers: List[int] = field(default_factory=lambda: [4])
    # 工位物理顺序（用于路线规划、距离查询） / Physical station order (for route planning and distance lookup)
    ws_path_order: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6])
    # 相邻工位中心距离（米） / Center-to-center distances between neighboring stations (m)
    ws_neighbor_distances_m: Dict[Tuple[int, int], float] = field(
        default_factory=lambda: {
            (1, 2): 3.5,
            (2, 3): 2.0,
            (3, 4): 3.5,
            (4, 5): 3.5,
            (5, 6): 2.0,
        }
    )
    # 主输送线到某 DS 内「装载/接口」工位沿输送方向的行程（米）；用于在 ws_ingress_station 之后追加本节拍时间 / Travel distance from main conveyor to DS loading/interface point along conveyor direction (m); appended after ws_ingress_station segment
    conveyor_to_ws_loading_position_m: float = 1.75

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
    # RFID SYSTEM（名义模型 / 时序占位） / nominal model and timing placeholder
    # ========================================================================
    # 不建模真实射频协议、天线场、多标签冲突等；仅保留「扫描开始 → 等待 / Real RF protocol, antenna field, and multi-tag collision are not modeled; only keep "scan start -> wait
    # detection_delay → IDENTIFIED」的时序与名义标签字符串，用于与 PLC/HMI / detection_delay -> IDENTIFIED" timing and nominal tag strings to align with PLC/HMI
    # 文档中的读码节拍对齐。演示与验收时请保留手册给出的延迟，勿为「跑快」而缩短。 / Align with documented read cadence; keep manual delay in demo/acceptance, do not shorten for speed.
    rfid_detection_delay: float = 0.5  # Seconds to detect tag (from docs; 队列/升降机位读码门限 / queue/elevator read threshold)
    rfid_tag_format: str = "8byte_hex"  # 名义格式说明（仿真中仅用字符串 ID） / Nominal format note (simulation uses string IDs only)
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
    # 整条产线（Buffer + 主线在途 + 各工位接收/在位）同时存在的托盘数上限 / Upper limit of pallets simultaneously on the whole line (Buffer + in-transit main line + station receiving/present)
    max_pallets_on_line: int = 10

    def __post_init__(self):
        """Validate configuration after initialization"""
        assert self.buffer_max_capacity > 0, "Buffer capacity must be positive"
        assert self.conveyor_max_speed_ms > 0, "Conveyor speed must be positive"
        assert self.pneumatic_target_pressure > 0, "Pressure must be positive"
        assert self.elevator_transfer_time >= 0, "Elevator transfer time must be >= 0"
        assert self.buffer_transfer_time >= 0, "Buffer transfer time must be >= 0"
        assert self.station_transfer_time >= 0, "Station transfer time must be >= 0"
        assert len(self.station_numbers) == self.station_count, "Station count mismatch"
        assert (
            self.assembly_time_min_seconds <= self.assembly_time_max_seconds
        ), "Assembly min must be <= max"
        assert self.assembly_exponential_scale_seconds > 0, "Assembly exponential scale must be > 0"
        assert self.assembly_duration_distribution in (
            "truncated_exponential",
            "uniform",
            "deterministic",
        ), "assembly_duration_distribution must be one of: truncated_exponential, uniform, deterministic"
        assert self.worker_efficiency_base > 0, "worker_efficiency_base must be > 0"
        for start_h, end_h, eff in self.worker_efficiency_shifts:
            assert 0.0 <= float(start_h) < 24.0, "shift start hour must be in [0, 24)"
            assert 0.0 <= float(end_h) < 24.0, "shift end hour must be in [0, 24)"
            assert float(eff) > 0.0, "shift worker efficiency must be > 0"
        assert self.raw_material_batch_interval_seconds > 0, "Raw material batch interval must be > 0"
        assert self.raw_material_pallets_per_batch >= 1, "At least one pallet per batch"
        assert self.pallet_length_m > 0, "Pallet length must be > 0"
        assert self.max_pallets_on_line >= 1, "max_pallets_on_line must be >= 1"
        assert self.ws_ingress_station in self.station_numbers, "Ingress station must exist"
        assert self.ws_egress_station in self.station_numbers, "Egress station must exist"
        for sid in self.assembly_station_numbers:
            assert sid in self.station_numbers, f"Assembly station {sid} must exist"
        for sid in self.agv_docking_station_numbers:
            assert sid in self.station_numbers, f"AGV docking station {sid} must exist"
        for a, b in self.ws_neighbor_distances_m.keys():
            assert a in self.station_numbers and b in self.station_numbers, "Distance key station missing"
            assert abs(a - b) == 1, "Neighbor distances should be defined for adjacent stations"
        for d in self.ws_neighbor_distances_m.values():
            assert d > 0, "All neighbor distances must be > 0"
        assert self.conveyor_to_ws_loading_position_m > 0, "conveyor_to_ws_loading_position_m must be > 0"

    def worker_efficiency_at_sim_time_seconds(self, sim_time_seconds: float) -> float:
        """Return effective worker efficiency at current simulation time."""
        if not self.worker_efficiency_shifts:
            return float(self.worker_efficiency_base)
        hour = (float(sim_time_seconds) / 3600.0) % 24.0
        for start_h, end_h, eff in self.worker_efficiency_shifts:
            start = float(start_h)
            end = float(end_h)
            if start < end:
                in_shift = start <= hour < end
            elif start > end:
                # Cross-midnight shift, e.g. 22:00-06:00.
                in_shift = hour >= start or hour < end
            else:
                # start == end means all-day shift.
                in_shift = True
            if in_shift:
                return float(eff)
        return float(self.worker_efficiency_base)


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
        # 名义 RFID：显式保留文档读码延迟（默认 0.5s），演示不缩短 / Nominal RFID: explicitly keep documented delay (default 0.5s), do not shorten for demos
        rfid_detection_delay=0.5,
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
