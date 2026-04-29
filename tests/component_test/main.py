# main.py
"""
系统级时间步进模拟入口 (Time-step Simulation Entry)
将物理组件、状态容器和控制逻辑整合到一个统一的虚拟时间轴上。
"""

import time
from datetime import datetime, timedelta
from config import config_normal_operation, MISSION_MC_TO_WS
from state import SystemState
from logic import apply_system_logic, validate_system_state

def run_simulation():
    # 1. 初始化配置与系统状态
    config = config_normal_operation()
    config.timestep_seconds = 0.1 # 设定步长为 100ms
    system = SystemState(config)
    
    # 设定虚拟起始时间
    virtual_time = datetime.now()
    sim_duration_seconds = 20.0   # 模拟 20 秒的流程
    total_steps = int(sim_duration_seconds / config.timestep_seconds)
    
    print("=" * 60)
    print("🚀 启动 WS Conveyor 联合组件模拟")
    print(f"设定时长: {sim_duration_seconds} 秒 | 步长: {config.timestep_seconds} 秒")
    print("=" * 60)

    # 获取组件引用以便在循环中注入外部事件
    conveyor = system.get_component('main_conveyor')
    queue_stop = system.get_component('buffer_queue_stop')
    elevator = system.get_component('transfer_elevator')
    transfer_belt = system.get_component('cross_transfer_belt')

    for step in range(total_steps):
        current_sim_time_s = step * config.timestep_seconds
        
        # ----------------------------------------------------------------
        # 剧本编排：在特定时间点注入物理事件 (模拟外部传感器触发或 HMI 指令)
        # ----------------------------------------------------------------
        
        # [0.0s] 阶段 0: 启动主传送带
        if abs(current_sim_time_s - 0.0) < 0.01:
            print(f"[{current_sim_time_s:.1f}s] 阶段 0: 启动主传送带")
            conveyor.conveyor_on = True
            conveyor.speed = 50

        # [2.0s] 阶段 1: 托盘到达缓冲区，触发传感器
        if abs(current_sim_time_s - 2.0) < 0.01:
            print(f"[{current_sim_time_s:.1f}s] 阶段 1: 托盘到达挡停器，开始等待自动放行")
            queue_stop.pallet_detected = True
            system.allow_timer_for_passing = True

        # [8.0s] 阶段 2: 改变主意，分配转移到工作台的任务 (MISSION_MC_TO_WS)
        if abs(current_sim_time_s - 8.0) < 0.01:
            print(f"\n[{current_sim_time_s:.1f}s] 阶段 2: HMI 介入，分配入站任务 (Mission 2)")
            system.active_mission = MISSION_MC_TO_WS
            queue_stop.stop_down = False # 恢复挡停

        # [10.0s] 阶段 3: 升降机开始上升
        if abs(current_sim_time_s - 10.0) < 0.01:
            print(f"[{current_sim_time_s:.1f}s] 阶段 3: 升降机执行上升指令")
            elevator.elevator_up = True
            elevator.sensor_down = False # 离开底部

        # [11.5s] 阶段 4: 升降机到达顶部，启动横移皮带入站
        if abs(current_sim_time_s - 11.5) < 0.01:
            print(f"[{current_sim_time_s:.1f}s] 阶段 4: 升降机到达顶部，启动横移皮带")
            elevator.sensor_up = True    # 触发顶部传感器
            transfer_belt.transfer_on = True
            transfer_belt.dir_from_wspace = False # 入站方向

        # ----------------------------------------------------------------
        # 核心驱动：应用系统控制逻辑并推演时间
        # ----------------------------------------------------------------
        apply_system_logic(system, virtual_time)
        
        # 系统状态合法性校验
        is_valid, violations = validate_system_state(system)
        if not is_valid:
            print(f"[{current_sim_time_s:.1f}s] ❌ 发生物理冲突: {violations}")
            break

        # 时间轴步进
        virtual_time += timedelta(seconds=config.timestep_seconds)
        time.sleep(0.02) # 仅为了在终端看清打印输出，实际模拟可移除

    print("\n" + "=" * 60)
    print("✅ 模拟结束。最终系统状态快照：")
    print(f"  传送带状态: {conveyor.state.name}")
    print(f"  挡停器状态: {queue_stop.state.name}")
    print(f"  升降机状态: {elevator.state.name}")
    print(f"  横移皮带状态: {transfer_belt.state.name}")
    print("=" * 60)

if __name__ == "__main__":
    run_simulation()