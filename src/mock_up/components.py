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

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict
from .config import SimulationConfig


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
        self.is_malfunctioning = False # Added based on PLC code

    ## Error Holding and Reset Methods
    def trigger_error(self):
        """Simulate a motor malfunction."""
        self.is_malfunctioning = True
        self.state = ConveyorMotorState.ERROR
        self.current_speed_percent = 0.0
        self.current_speed_ms = 0.0

    def reset_error(self):
        """Reset warning malfunctioning from HMI."""
        if self.is_malfunctioning:
            self.is_malfunctioning = False
            self.state = ConveyorMotorState.IDLE
    
    def start(self, speed_percent: float = 100.0):
        """Begin acceleration to target speed."""
        if self.is_malfunctioning or self.state not in [ConveyorMotorState.IDLE, ConveyorMotorState.RAMP_DOWN]:
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

class TransferDirection(Enum):
    """Direction of the cross-transfer belt."""
    TO_WS = "to_ws"          # False in PLC
    FROM_WS = "from_ws"      # True in PLC


@dataclass
class TransferElevator:
    """Vertical elevator for pallet transfer. with cross-tranfer belt"""
    id: str
    travel_time: float = 1.5  # seconds for pneumatic cylinder to move
    transfer_time: float = 3.0 # seconds to completely transfer a pallet

    def __post_init__(self):
        self.position = ElevatorPosition.DOWN
        self.target_position = ElevatorPosition.DOWN
        self.is_down = True
        self.is_up = False
        self.transition_start_time: Optional[datetime] = None
        self.up_requested = False
        self.down_requested = False
        self.transfer_running = False
        self.transfer_direction = TransferDirection.TO_WS
        self.transfer_start_time: Optional[datetime] = None
    
# vertical movement methods
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

# Horizontal transfer methods
    def start_transfer(self, direction: TransferDirection):
            """Start the cross-transfer belt."""
            # Interlock: Should not start if elevator is moving
            if self.position == ElevatorPosition.MOVING:
                return False
                
            self.transfer_running = True
            self.transfer_direction = direction
            self.transfer_start_time = datetime.now()
            return True

    def stop_transfer(self):
        """Stop the cross-transfer belt."""
        self.transfer_running = False
        self.transfer_start_time = None

    def update(self, elapsed_time: float):
        """Update physics based on elapsed time."""
        # 1. Update Elevator Vertical Position
        if self.position == ElevatorPosition.MOVING and self.transition_start_time:
            progress = min(elapsed_time / self.travel_time, 1.0)
            if progress >= 1.0:
                self.position = self.target_position
                self.transition_start_time = None

        # 2. Update Transfer Belt (Simulation of pallet movement could be handled here 
        #    or in a higher-level system manager)
        if self.transfer_running and self.transfer_start_time:
            # In a full simulation, we would check if elapsed_time > self.transfer_time
            # to trigger a "transfer complete" event.
            pass        
    
    


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
    transfer_time: float = 3.0  # TIME: Move pallet in/out of buffer
    
    def __post_init__(self):
        self.state = BufferState.EMPTY
        self.pallet_count = 0
        self.stored_rfids: List[str] = []
        self.pallet_at_queue = False
        self.pallet_rfid_at_queue: Optional[str] = None
        self.queue_detect_start_time: Optional[datetime] = None
        self.auto_pass_enabled = False
        self.auto_pass_delay: float = 0.0
        # Added: Transfer state for simulating the time it takes to move a pallet in/out of the buffer
        self.is_transferring = False
        self.transfer_direction: Optional[str] = None  # "in" 或 "out" / "in" or "out"
        self.transition_start_time: Optional[datetime] = None
    
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
        """Start transfer pallet from queue to storage."""
        #Secure queue has pallet, buffer not full, and no ongoing transfer
        if self.pallet_count < self.max_capacity and self.pallet_at_queue and not self.is_transferring:
            self.is_transferring = True
            self.transfer_direction = "in"
            self.transition_start_time = datetime.now()
            return True
        return False

    def remove_from_buffer(self):
        """Start transfer pallet from storage to queue."""
        # Add from buffer to queue logic
        if self.pallet_count > 0 and not self.pallet_at_queue and not self.is_transferring:
            self.is_transferring = True
            self.transfer_direction = "out"
            self.transition_start_time = datetime.now()
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

    def update(self, elapsed_time: float):
        """Progress the physical transfer state based on time."""
        if self.is_transferring and self.transition_start_time:
            progress = min(elapsed_time / self.transfer_time, 1.0)
            
            if progress >= 1.0:
                # 动作完成 / Action complete
                self.is_transferring = False
                self.transition_start_time = None
                
                if self.transfer_direction == "in":
                    # add palalet to buffer logic
                    self.pallet_count += 1
                    self.stored_rfids.append(self.pallet_rfid_at_queue)
                    self.pallet_at_queue = False
                    self.pallet_rfid_at_queue = None
                elif self.transfer_direction == "out":
                    # remove pallet from buffer to queue logic
                    self.pallet_count -= 1
                    rfid = self.stored_rfids.pop(0)
                    self.pallet_at_queue = True
                    self.pallet_rfid_at_queue = rfid
                    
                self.transfer_direction = None
                self.update_state()

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
    # 现实产线改版：Mission 4 在 DS6 交给 AMR 后的等待 (对应 hmi_TimeForWaitAfterTransferdToAMR) / Real line revision: Mission 4 wait after DS6 transfer to AMR (maps to hmi_TimeForWaitAfterTransferdToAMR)
    AMR_HANDOFF_WAIT = "amr_handoff_wait"
    ERROR = "error"


class StationRole(Enum):
    """Physical role of each WS station in current line revision."""
    INGRESS_BUFFER = "ingress_buffer"      # WS1
    ASSEMBLY = "assembly"                  # WS2/3/5/6
    AGV_DOCKING_IGNORED = "agv_docking_ignored"  # WS4 (modeled as bypass)
    OTHER = "other"



@dataclass
class DockingStation:
    """Docking station with pallet processing.

    现实产线修订（项目约定）：/ Real line revision (project convention):
    - WS1: ingress + buffer handoff（不做组装）/ no assembly.
    - WS2/WS3/WS5/WS6: 组装工位 / assembly stations.
    - WS4: AGV 接驳位，当前模型忽略 AGV 动作（名义占位，不参与组装）/ AGV docking station; model ignores AGV actions (nominal placeholder, no assembly).
    - WS6: 制成品立即输出（``immediate_output=True``）/ finished products output immediately.
    - Mission 3（AMR → 产线）：仅 DS1 接受，托盘进入 Buffer / only DS1 accepts; pallet enters Buffer.
    - Mission 4：保留兼容路径；当前主流程通常不触发 / compatibility path retained; usually not triggered in main flow.
    """
    id: str
    station_number: int  # 1-6
    mission_queue: List[str] = field(default_factory=list)
    time_wait_at_queue: float = 5.0    # 排队位最大等待时间 (秒) / Max queue wait time (s)
    transfer_time: float = 2.0       # 模拟从排队位到工作站的物理转移时间 (秒) / Simulated physical transfer time from queue to station (s)
    allow_auto_pass: bool = True       # 是否允许超时自动通过 (看门狗) / Allow timeout auto-pass (watchdog)
    # DS1：AMR 卸货进 Buffer 时使用；其它工位为 None / DS1 only: used when AMR unloads into Buffer; None for others
    buffer: Optional[Buffer] = None
    # DS6：交给 AMR 后的等待时间 (秒)，其它工位为 0 / DS6 wait time after AMR handoff (s); 0 for others
    wait_after_amr_transfer: float = 0.0
    role: StationRole = StationRole.OTHER
    is_assembly_station: bool = True
    immediate_output: bool = False
    # 工人在 WS 的组装时长 [min, max]（秒），默认 2–15 分钟；随机模式为截断指数分布 / Worker assembly duration at WS [min, max] in seconds; default 2-15 min; stochastic mode uses truncated exponential
    assembly_time_min_seconds: float = 120.0
    assembly_time_max_seconds: float = 900.0
    # 指数分布尺度：在 min 之上叠加 Exp(scale)，再截断到 max（scale 越大越偏长） / Exponential scale: add Exp(scale) above min and cap at max (larger scale gives longer tail)
    assembly_exponential_scale_seconds: float = 180.0
    # 组装时长分布：truncated_exponential | uniform | deterministic / Assembly duration distribution options
    assembly_duration_distribution: str = "truncated_exponential"
    # 工人效率系数：>1 更快，<1 更慢；作用为 duration / efficiency / Worker efficiency factor: >1 faster, <1 slower; applied as duration / efficiency
    worker_efficiency: float = 1.0
    assembly_rng: Optional[random.Random] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        self.state = DockingStationState.INIT
        self.pallet_present = False
        self.pallet_rfid: Optional[str] = None
        self.current_mission: Optional[str] = None
        self.mission_start_time: Optional[datetime] = None
        self.sequence_step = 0
        self.blocked = False  # For manual testing

        # 新增: 用于物理流转状态追踪的变量 / Added variables for physical transfer state tracking
        self.pallet_at_ws = False  # 托盘是否已进入工作台 (WS) / Whether pallet has entered the workstation
        self.transition_start_time: Optional[datetime] = None
        # Mission 3：AMR 拟进入 Buffer 的托盘 RFID（在 RECEIVING 结束时写入 buffer） / Mission 3: RFID of AMR incoming pallet for Buffer (written when RECEIVING completes)
        self._mission3_incoming_rfid: Optional[str] = None
        # PROCESSING：本次在 WS 的目标组装时长（秒），进入 PROCESSING 时采样 / PROCESSING: sampled target assembly duration at WS (s)
        self._processing_target_seconds: Optional[float] = None
        if self.assembly_rng is None:
            self.assembly_rng = random.Random()

    def _sample_assembly_duration_seconds(self) -> float:
        """Sample assembly time: truncated shifted exponential on [min, max]."""
        lo = float(self.assembly_time_min_seconds)
        hi = float(self.assembly_time_max_seconds)
        if hi <= lo:
            return lo
        mode = str(self.assembly_duration_distribution).strip().lower()
        if mode == "deterministic":
            base = 0.5 * (lo + hi)
        elif mode == "uniform":
            base = self.assembly_rng.uniform(lo, hi)
        else:
            scale = max(float(self.assembly_exponential_scale_seconds), 1e-6)
            # T = min(hi, lo + Exp(1/scale)) — 常见截断指数实现，落在 [lo, hi] / Common truncated exponential implementation in [lo, hi]
            base = min(hi, lo + self.assembly_rng.expovariate(1.0 / scale))
        eff = max(float(self.worker_efficiency), 1e-6)
        return base / eff

    def accept_mission(self, mission: str, pallet_rfid: Optional[str] = None) -> bool:
        """Receive mission assignment from HMI.

        Args:
            mission: "1", "2", "3", or "4" (see class docstring for station binding).
            pallet_rfid: Required for **Mission 3** on DS1 — RFID of pallet coming from AMR.
        """
        if mission in ["1", "2"] and self.state == DockingStationState.AWAITING_MISSION:
            if mission == "2" and not self.is_assembly_station:
                return False
            self.current_mission = mission
            self.mission_start_time = datetime.now()
            self.state = DockingStationState.RECEIVING
            self.transition_start_time = datetime.now()  # 开始计算移载耗时 / Start timing transfer duration
            return True

        # Mission 3：仅 DS1 + Buffer（AMR → Buffer） / Mission 3: DS1 + Buffer only (AMR -> Buffer)
        if mission == "3":
            if self.station_number != 1 or self.buffer is None:
                return False
            if self.state != DockingStationState.INIT:
                return False
            if not pallet_rfid or not str(pallet_rfid).strip():
                return False
            self.current_mission = "3"
            self._mission3_incoming_rfid = str(pallet_rfid).strip()
            self.mission_start_time = datetime.now()
            self.state = DockingStationState.RECEIVING
            self.transition_start_time = datetime.now()
            return True

        # Mission 4：仅 DS6（兼容旧工艺；当前主流程一般由 immediate_output 直接出线） / Mission 4: DS6 only (legacy compatibility; main flow usually exits via immediate_output)
        if mission == "4":
            if self.station_number != 6:
                return False
            if self.state not in (
                DockingStationState.AWAITING_MISSION,
                DockingStationState.PROCESSING,
            ):
                return False
            if not (self.pallet_present or self.pallet_at_ws):
                return False
            self.current_mission = "4"
            self.mission_start_time = datetime.now()
            self.state = DockingStationState.SENDING
            self.transition_start_time = datetime.now()
            return True

        return False
    
    def pallet_arrived(self, rfid_tag: str):
        """Pallet transferred to station."""
        self.pallet_present = True
        self.pallet_rfid = rfid_tag
        self.sequence_step += 1

        # 逻辑补充: 状态变为等待任务，并启动看门狗计时 / Logic addition: switch to awaiting mission and start watchdog timer
        self.state = DockingStationState.AWAITING_MISSION
        self.transition_start_time = datetime.now()
        return True
    
    def complete_processing(self):
        """Work on pallet is complete (人工或定时完成 / manual or timed completion) — 进入送出阶段（非 Mission 3/4 编号 / enter send-out stage, not Mission 3/4)."""
        if self.state == DockingStationState.PROCESSING:
            # WS6 现实产线规则：制成品立即输出（不等待 AMR） / WS6 real-line rule: finished products output immediately (no AMR wait)
            if self.immediate_output:
                self._processing_target_seconds = None
                self.pallet_removed()
                return
            # Mission 3 已专用于 DS1 AMR→Buffer；加工完成后的送出使用内部标记 / Mission 3 is reserved for DS1 AMR->Buffer; post-processing send-out uses internal marker
            self._processing_target_seconds = None
            self.state = DockingStationState.SENDING
            self.current_mission = "_ws_sendout"
            self.sequence_step += 1
            self.transition_start_time = datetime.now()
    
    def pallet_removed(self):
        """Pallet transferred away from station."""
        self.pallet_present = False
        self.pallet_at_ws = False
        self.pallet_rfid = None
        self.state = DockingStationState.CLEANUP
        self.current_mission = None
        self.transition_start_time = datetime.now()  # 开始清理延时 / Start cleanup delay timer

    # ==========================================
    # 以下为新增的 update 方法，用于处理时间步进 / Newly added update method for time-step progression
    # ==========================================
    def update(self, elapsed_time: float):
        """更新物理动作进度与看门狗超时 / Update physical action progress and watchdog timeout."""
        
        # 1. 看门狗: 如果在队列等待太久，触发自动通过 (Auto-Pass) / Watchdog: auto-pass if queue wait is too long
        if self.state == DockingStationState.AWAITING_MISSION and self.transition_start_time:
            if elapsed_time >= self.time_wait_at_queue and self.allow_auto_pass:
                print(f"[{self.id}] ⚠️ 队列超时 ({elapsed_time:.1f}s)，看门狗强制放行 (Mission 1)! / Queue timeout, watchdog forces release.")
                self.accept_mission("1")

        # 2. 正在接收 (Mission 1 / 2 / 3) / Receiving in progress (Mission 1 / 2 / 3)
        elif self.state == DockingStationState.RECEIVING and self.transition_start_time:
            if elapsed_time >= self.transfer_time:
                if self.current_mission == "1":
                    # Mission 1 穿过完成 / Mission 1 pass-through complete
                    self.pallet_removed()
                elif self.current_mission == "2":
                    # Mission 2 进站完成 / Mission 2 station entry complete
                    self.pallet_present = False  # 离开主线 / Leave main line
                    self.pallet_at_ws = True     # 进入工作台 / Enter workstation
                    self.state = DockingStationState.PROCESSING
                    self._processing_target_seconds = self._sample_assembly_duration_seconds()
                    self.transition_start_time = datetime.now()
                elif self.current_mission == "3" and self.station_number == 1 and self.buffer is not None:
                    # Mission 3：AMR → Buffer（卸货完成） / Mission 3: AMR -> Buffer (unload complete)
                    rfid = self._mission3_incoming_rfid
                    ok = False
                    if rfid:
                        ok = self.buffer.pallet_enters(rfid)
                    if ok:
                        self._mission3_incoming_rfid = None
                        self.current_mission = None
                        self.state = DockingStationState.INIT
                        self.transition_start_time = None
                    else:
                        # Buffer 队列位可能被临时占用（例如刚好在出队）；此时等待后重试， / Buffer queue slot may be temporarily occupied (e.g., dequeuing); wait and retry,
                        # 避免把短时背压误判为错误停机。 / to avoid misclassifying short backpressure as fault stop.
                        self.state = DockingStationState.RECEIVING
                        self.transition_start_time = datetime.now()

        # 2b. 正在加工 (WS)：组装时间到达后自动进入送出阶段 / Processing at WS: auto-enter send-out when assembly time is reached
        elif (
            self.state == DockingStationState.PROCESSING
            and self.transition_start_time
            and self.pallet_at_ws
        ):
            target = self._processing_target_seconds
            if target is not None and elapsed_time >= target:
                self.complete_processing()

        # 3. 正在送出 (内部送出 或 Mission 4) / Sending in progress (internal send-out or Mission 4)
        elif self.state == DockingStationState.SENDING and self.transition_start_time:
            if elapsed_time >= self.transfer_time:
                if self.current_mission == "4":
                    # DS6：托盘离站，进入 AMR 交接后等待 / DS6: pallet leaves station, then waits after AMR handoff
                    self.pallet_present = False
                    self.pallet_at_ws = False
                    self.pallet_rfid = None
                    self.current_mission = None
                    self.state = DockingStationState.AMR_HANDOFF_WAIT
                    self.transition_start_time = datetime.now()
                else:
                    self.pallet_removed()

        # 4. AMR 交接后等待（仅 DS6 Mission 4 路径；其它工位 wait_after_amr_transfer 为 0 可不用） / Post-AMR handoff wait (DS6 Mission 4 path only; others can keep wait_after_amr_transfer=0)
        elif self.state == DockingStationState.AMR_HANDOFF_WAIT and self.transition_start_time:
            wait_s = max(self.wait_after_amr_transfer, 0.0)
            if elapsed_time >= wait_s:
                self.state = DockingStationState.INIT
                self.transition_start_time = None

        # 5. 清理状态 (0.5秒恢复到 INIT) / Cleanup state (return to INIT after 0.5s)
        elif self.state == DockingStationState.CLEANUP and self.transition_start_time:
            if elapsed_time >= 0.5:
                self.state = DockingStationState.INIT
                self.transition_start_time = None

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
# RFID READER（名义读码器：仅时序与状态，无真实射频） / RFID READER (nominal reader: timing/state only, no real RF)
# ============================================================================

class RFIDState(Enum):
    """名义 RFID 读码状态机（不对应真实读写器硬件状态寄存器）/ Nominal RFID read state machine (not mapped to real hardware registers)."""
    IDLE = "idle"
    DETECTING = "detecting"
    IDENTIFIED = "identified"
    ERROR = "error"


@dataclass
class RFIDReader:
    """名义 RFID：用字符串标签 + ``detection_delay`` 模拟「触发读码 → 等待 → 识别完成」/ Nominal RFID: simulate "trigger -> wait -> identified" with string tags + ``detection_delay``.

    不包含真实 RFID 的空中接口、EPC/TID 存储体、RSSI、防碰撞等。``tag_detected`` 仅为 / Does not model real RFID air interface, EPC/TID banks, RSSI, anti-collision, etc. ``tag_detected`` is only
    与托盘关联的名义 ID；``update()`` 在累计时间达到 ``detection_delay`` 后进入 / a nominal ID linked to a pallet; ``update()`` transitions when elapsed time reaches
    ``IDENTIFIED``，用于与文档中的读码节拍、互锁时序对齐。 / ``IDENTIFIED`` to align with documented read cadence and interlock timing.
    """
    id: str
    location: str  # "queue" or "elevator"
    detection_delay: float = 0.5  # 名义读码耗时（秒），默认与手册一致；演示宜保持完整时长 / Nominal read time (s); keep manual default for demos
    
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
        if self.state == RFIDState.DETECTING and self.detect_start_time:
            if elapsed_time >= self.detection_delay:
                self.state = RFIDState.IDENTIFIED
                self.detect_start_time = None


# ============================================================================
# PALLET WINDOW ALIGNMENT（双探头窗口对中 — 主/从输送接口 + 工位内到位） / PALLET WINDOW ALIGNMENT (dual-sensor centering at main/slave interface + in-station positioning)
# ============================================================================
#
# 几何（沿输送方向）：主输送 ↔ 通往工站的从输送带接口、以及 DS 安装工位窗均可抽象为一对探头， / Geometry (along conveyor): main-to-WS slave interface and DS station window can both be abstracted as dual sensors,
# 轴线间距 = 正方形托盘边长（通常等于 SimulationConfig.pallet_length_m）。(1,1)=窗内对中； / sensor spacing equals pallet edge length (usually SimulationConfig.pallet_length_m). (1,1)=centered in window;
# (0,0)=窗内无托；(1,0)/(0,1) 由真实 PLC 滤波。离散 mock 常用 (0,0)→(1,1)→(0,0)。 / (0,0)=no pallet in window; (1,0)/(0,1) are filtered by real PLC. Discrete mock usually uses (0,0)->(1,1)->(0,0).
# 主从互锁：仅 is_window_centered 时建议允许主带与从带同步交接。 / Main/slave interlock: synchronized handoff only when is_window_centered is true.


@dataclass
class PalletAlignmentWindow:
    """双传感器窗口对中检测（离散名义模型）/ Dual-sensor window centering detection (discrete nominal model).

    用于工位内到位判定，以及主 conveyor 与至 WS 的从 conveyor 在接口处的对齐互锁。 / Used for in-station positioning and interface alignment interlock between main conveyor and WS slave conveyor.
    """

    id: str
    sensor_spacing_m: float = 0.25
    sensor_a_active: bool = field(default=False)
    sensor_b_active: bool = field(default=False)

    @property
    def sensor_bits(self) -> tuple[int, int]:
        """与上层约定一致的 (S1, S2) / (S1, S2) bits consistent with upper-layer convention."""
        return (1 if self.sensor_a_active else 0, 1 if self.sensor_b_active else 0)

    @property
    def is_window_centered(self) -> bool:
        """托盘在窗内对中 — 用于工位内判定与主/从输送交接许可条件 / Pallet centered in window; used for in-station checks and main/slave handoff permission."""
        return self.sensor_a_active and self.sensor_b_active

    @property
    def is_clear(self) -> bool:
        """窗口内无有效遮挡（离开或未进入）/ No valid blockage in window (left or not entered)."""
        return not self.sensor_a_active and not self.sensor_b_active

    def clear(self) -> None:
        """复位为 (0, 0) / Reset to (0, 0)."""
        self.sensor_a_active = False
        self.sensor_b_active = False

    def set_centered(self, centered: bool) -> None:
        """离散演示：居中则 (1,1)，否则 (0,0)。连续运动中的 (1,0) 等由上层扩展。 / Discrete demo: centered -> (1,1), else (0,0); transients like (1,0) can be extended by upper layers."""
        if centered:
            self.sensor_a_active = True
            self.sensor_b_active = True
        else:
            self.clear()

    def main_slave_handoff_permitted(self) -> bool:
        """主输送与从输送（至工站带）是否允许同步交接 / Whether synchronized handoff between main and slave conveyors (to station belt) is allowed."""
        return self.is_window_centered


# ============================================================================
# SYSTEM FACTORY
# ============================================================================

def create_ws_conveyor_system(config: SimulationConfig) -> Dict[str, object]:
    """Instantiate all physical components from simulation config."""
    components = {}

    components['conveyor_motor'] = ConveyorMotor(
        id='main_conveyor', max_speed_percent=100.0, ramp_time=config.conveyor_ramp_time
    )
    # 每台组装工位独立升降机（并行产线）；保留 legacy 名 ``elevator`` 指向第一台组装升降机 / Each assembly station has an independent elevator (parallel line); keep legacy alias ``elevator`` to first assembly elevator
    _asm = list(config.assembly_station_numbers)
    for sid in _asm:
        components[f"elevator_ds{sid}"] = TransferElevator(
            id=f"elevator_ds{sid}",
            travel_time=config.elevator_travel_time,
            transfer_time=config.elevator_transfer_time,
        )
    components["elevator"] = components[f"elevator_ds{_asm[0]}"] if _asm else TransferElevator(
        id="transfer_elevator",
        travel_time=config.elevator_travel_time,
        transfer_time=config.elevator_transfer_time,
    )
    components['buffer'] = Buffer(
        id='buffer',
        max_capacity=config.buffer_max_capacity,
        rfid_detection_delay=config.rfid_detection_delay,
        transfer_time=config.buffer_transfer_time,
    )
    _buffer = components['buffer']

    for i in range(1, config.station_count + 1):
        asm_rng = random.Random(config.seed + i * 9973)
        assembly_distribution = str(config.assembly_duration_distribution).strip().lower()
        if config.deterministic or (not config.assembly_use_stochastic_duration):
            # 兼容旧开关：deterministic=True 或 use_stochastic=False 时固定中点。 / Backward compatibility: force midpoint when deterministic=True or use_stochastic=False.
            assembly_distribution = "deterministic"
        is_assembly = i in config.assembly_station_numbers
        if i == config.ws_ingress_station:
            role = StationRole.INGRESS_BUFFER
        elif i in config.agv_docking_station_numbers:
            role = StationRole.AGV_DOCKING_IGNORED
        elif is_assembly:
            role = StationRole.ASSEMBLY
        else:
            role = StationRole.OTHER
        ds_common = dict(
            id=f'ds_{i}',
            station_number=i,
            time_wait_at_queue=config.station_wait_at_queue,
            transfer_time=config.station_transfer_time,
            allow_auto_pass=config.station_allow_auto_pass,
            assembly_time_min_seconds=config.assembly_time_min_seconds,
            assembly_time_max_seconds=config.assembly_time_max_seconds,
            assembly_exponential_scale_seconds=config.assembly_exponential_scale_seconds,
            assembly_duration_distribution=assembly_distribution,
            worker_efficiency=config.worker_efficiency_base,
            assembly_rng=asm_rng,
            role=role,
            is_assembly_station=is_assembly,
            immediate_output=(i == config.ws_egress_station),
        )
        # DS1：Mission 3（AMR → Buffer）注入 Buffer；DS6：可配置旧工艺的 AMR 等待时间 / DS1 injects Mission 3 (AMR -> Buffer); DS6 can configure legacy AMR wait time
        if i == 1:
            components[f'ds_{i}'] = DockingStation(
                **ds_common,
                buffer=_buffer,
            )
        elif i == 6:
            components[f'ds_{i}'] = DockingStation(
                **ds_common,
                wait_after_amr_transfer=config.station_wait_after_amr_transfer,
            )
        else:
            components[f'ds_{i}'] = DockingStation(**ds_common)

    components['pneumatic'] = PneumaticSystem(
        id='pneumatic_system', target_pressure_bar=config.pneumatic_target_pressure, max_flow_nm3h=config.pneumatic_max_flow
    )
    components['rfid_queue'] = RFIDReader(
        id='rfid_queue', location='queue', detection_delay=config.rfid_detection_delay
    )
    components['rfid_elevator'] = RFIDReader(
        id='rfid_elevator', location='elevator', detection_delay=config.rfid_detection_delay
    )
    
    return components