# components.py
from enum import Enum, auto
from config import HEIGHT_OFFSET, HEIGHT_SCALE_FACTOR

class ConveyorState(Enum):
    STOPPED = auto()
    RUNNING = auto()
    ERROR = auto()

class MainConveyor:
    def __init__(self):
        self.conveyor_on = False 
        self.speed = 0 
        self.is_malfunctioning = False 
        self.state = ConveyorState.STOPPED

    def update(self):
        if self.is_malfunctioning:
            self.state = ConveyorState.ERROR
        elif self.conveyor_on and self.speed > 0:
            self.state = ConveyorState.RUNNING
        else:
            self.state = ConveyorState.STOPPED

class QueueStopState(Enum):
    BLOCKED = auto() 
    WAITING = auto() 
    PASSING = auto() 

class BufferQueueStop:
    def __init__(self):
        self.stop_down = False 
        self.pallet_detected = False 
        self.state = QueueStopState.BLOCKED

    def update(self):
        if self.stop_down:
            self.state = QueueStopState.PASSING
        elif self.pallet_detected and not self.stop_down:
            self.state = QueueStopState.WAITING
        else:
            self.state = QueueStopState.BLOCKED

# --- 新增组件 ---

class ElevatorState(Enum):
    DOWN = auto()
    UP = auto()
    MOVING = auto()
    ERROR = auto()

class TransferElevator:
    """升降机组件，负责主线与工作台层级的垂直移动"""
    def __init__(self):
        self.elevator_up = False     # 指令
        self.elevator_down = False   # 指令
        self.sensor_up = False       # 物理限位反馈
        self.sensor_down = True      # 默认在底部
        self.state = ElevatorState.DOWN

    def update(self):
        if self.sensor_up and self.sensor_down:
            self.state = ElevatorState.ERROR # 传感器冲突
        elif self.sensor_up:
            self.state = ElevatorState.UP
        elif self.sensor_down:
            self.state = ElevatorState.DOWN
        else:
            self.state = ElevatorState.MOVING

class CrossTransferBeltState(Enum):
    IDLE = auto()
    INBOUND = auto()   # To Workstation
    OUTBOUND = auto()  # From Workstation

class CrossTransferBelt:
    """横向转移皮带"""
    def __init__(self):
        self.transfer_on = False
        self.dir_from_wspace = False # False = 入站, True = 出站
        self.state = CrossTransferBeltState.IDLE

    def update(self):
        if not self.transfer_on:
            self.state = CrossTransferBeltState.IDLE
        elif self.dir_from_wspace:
            self.state = CrossTransferBeltState.OUTBOUND
        else:
            self.state = CrossTransferBeltState.INBOUND

class WorktableHeightSensor:
    """工作台高度计算逻辑"""
    def __init__(self):
        self.raw_sensor_value = 0 # 0-32767
        self.actual_height_mm = 0.0

    def update(self):
        # 计算公式: (传感器值 + 偏移量) * 缩放因子
        self.actual_height_mm = (self.raw_sensor_value + HEIGHT_OFFSET) * HEIGHT_SCALE_FACTOR