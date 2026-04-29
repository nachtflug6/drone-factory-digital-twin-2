# state.py
import time
from components import (
    MainConveyor, BufferQueueStop, TransferElevator, 
    CrossTransferBelt, WorktableHeightSensor
)
from config import (
    MISSION_NONE, MISSION_PASS, AUTO_PASS_DELAY_MS, 
    MAX_ELEVATOR_TIMEOUT_S
)

class SystemState:
    def __init__(self):
        self.conveyor = MainConveyor()
        self.queue_stop = BufferQueueStop()
        self.elevator = TransferElevator()
        self.transfer_belt = CrossTransferBelt()
        self.height_sensor = WorktableHeightSensor()
        
        self.active_mission = MISSION_NONE
        self.allow_timer_for_passing = False
        
        # 内部计时器
        self._queue_wait_start = None
        self._elevator_move_start = None

    def run_plc_cycle(self):
        # 1. 更新所有物理组件状态
        self.conveyor.update()
        self.queue_stop.update()
        self.elevator.update()
        self.transfer_belt.update()
        self.height_sensor.update()
        
        # 2. 挡停器自动放行逻辑
        if self.queue_stop.state.name == "WAITING":
            if self.active_mission == MISSION_NONE and self.allow_timer_for_passing:
                if self._queue_wait_start is None:
                    self._queue_wait_start = time.time()
                if (time.time() - self._queue_wait_start) * 1000 >= AUTO_PASS_DELAY_MS:
                    self.queue_stop.stop_down = True
                    self.active_mission = MISSION_PASS
                    self._queue_wait_start = None
        else:
            self._queue_wait_start = None

        # 3. 升降机超时监控逻辑 (Step420 保护)
        if self.elevator.state.name == "MOVING":
            if self._elevator_move_start is None:
                self._elevator_move_start = time.time()
            elif time.time() - self._elevator_move_start > MAX_ELEVATOR_TIMEOUT_S:
                print(f"\n[警报] 升降机移动超时 (超过 {MAX_ELEVATOR_TIMEOUT_S} 秒)！")
                self.elevator.state = self.elevator.state.ERROR # 强制进入错误状态
        else:
            self._elevator_move_start = None