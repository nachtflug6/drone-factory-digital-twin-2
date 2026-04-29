import sys
import time
from datetime import datetime

# 1. 动态添加你的项目路径，确保能准确找到 components.py
PROJECT_PATH = '/workspaces/drone-factory-digital-twin-2/src/mock_up'
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

# 2. 从真实的 components.py 导入类
try:
    from components import ConveyorMotor, TransferElevator, ElevatorPosition, TransferDirection
    print("✅ 成功从目标路径加载 components.py")
except ImportError as e:
    print(f"❌ 导入失败，请检查路径 {PROJECT_PATH} 及其内容: {e}")
    sys.exit(1)


# ============================================================================
# 测试场景与模拟引擎 (Simulation Runner)
# ============================================================================

def log_motor_status(motor: ConveyorMotor):
    print(f"[Motor: {motor.id}] State: {motor.state.name:<10} | "
          f"Speed: {motor.current_speed_percent:5.1f}% ({motor.current_speed_ms:.3f} m/s)")

def log_elevator_status(elevator: TransferElevator):
    # 注意：模板中 transfer_running 是布尔值，transfer_direction 是 Enum
    transfer_status = f"RUNNING ({elevator.transfer_direction.name})" if elevator.transfer_running else "STOPPED"
    print(f"[Elevator: {elevator.id}] Pos: {elevator.position.name:<6} | Belt: {transfer_status}")

def run_tests():
    print("\n=== 初始化数字孪生组件 ===")
    
    # 这里的 ConveyorMotor 将会使用你 components.py 中定义的默认值 (即你修改的 0.5 m/s)
    main_motor = ConveyorMotor(id="MC_Motor_1", ramp_time=1.0)
    print(f"[*] 当前电机的理论最大速度被配置为: {main_motor.max_speed_ms} m/s")
    
    elevator = TransferElevator(id="DS1_Elevator", travel_time=1.5)
    
    # ---------------------------------------------------------
    print("\n--- 测试场景 1: 主电机启动 (验证新速度) ---")
    print(">> 发送启动命令 (目标速度 100%)")
    main_motor.start(100.0)
    
    # 模拟 1.2 秒的运行 (应该看到最终速度稳定在你修改的 0.5 m/s)
    for _ in range(6):
        # 计算自状态切换以来经过的总时间，传入 update 方法
        elapsed = 0.0
        if main_motor.transition_start_time:
            elapsed = (datetime.now() - main_motor.transition_start_time).total_seconds()
            
        main_motor.update(elapsed_time=elapsed)
        log_motor_status(main_motor)
        time.sleep(0.2)

    # ---------------------------------------------------------
    print("\n--- 测试场景 2: 传送升降单元动作 ---")
    print(">> 发送升起命令 (Elevator UP)")
    elevator.request_up()
    
    # 模拟 2.0 秒的运行
    for i in range(10):
        # 计算经过时间
        elapsed = 0.0
        if elevator.transition_start_time:
            elapsed = (datetime.now() - elevator.transition_start_time).total_seconds()
            
        elevator.update(elapsed_time=elapsed)
        log_elevator_status(elevator)
        
        # 在运行到一半时，尝试非法启动皮带
        if elevator.position == ElevatorPosition.MOVING and i == 4:
            print(">> 尝试在升降中启动横向皮带 (预期: 互锁拦截或状态不变)")
            # 这里调用你在 components.py 里的逻辑
            # 注意：你可能需要在你的 components.py 里的 start_transfer 加互锁判断
            success = elevator.start_transfer(TransferDirection.TO_WS)
            if not success:
                print("   -> 拦截成功！")
            
        time.sleep(0.2)

    print("\n>> 升降机到位，正式启动横向皮带")
    success = elevator.start_transfer(TransferDirection.TO_WS)
    print(f"启动成功: {success}")
    log_elevator_status(elevator)
        
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    run_tests()


from components import Buffer, PneumaticSystem, DockingStation, DockingStationState, RFIDReader

def log_buffer(buf: Buffer):
    action = f"MOVING {buf.transfer_direction.upper()}" if buf.is_transferring else "IDLE"
    print(f"[{buf.id}] State: {buf.state.name:<7} | Count: {buf.pallet_count}/2 | "
          f"Queue: {buf.pallet_rfid_at_queue} | Action: {action} | "
          f"Stored RFIDs: {buf.stored_rfids}")

def run_tests():
    print("=== 初始化 Buffer ===")
    buf = Buffer(id="Buffer_1", transfer_time=2.0)
    log_buffer(buf)

    print("\n--- 1. 托盘到达排队位并开始存入 ---")
    buf.pallet_enters("TAG_001")
    buf.add_to_buffer()
    
    # 模拟物理传输时间
    for i in range(12):
        elapsed = (datetime.now() - buf.transition_start_time).total_seconds() if buf.transition_start_time else 0.0
        buf.update(elapsed)
        if i % 3 == 0 or not buf.is_transferring:
            log_buffer(buf)
        if not buf.is_transferring:
            break
        time.sleep(0.2)

    print("\n--- 2. 第二个托盘到达并存入 (测试满载) ---")
    buf.pallet_enters("TAG_002")
    buf.add_to_buffer()
    for i in range(12):
        elapsed = (datetime.now() - buf.transition_start_time).total_seconds() if buf.transition_start_time else 0.0
        buf.update(elapsed)
        time.sleep(0.2)
    log_buffer(buf)

    print("\n--- 3. 尝试取出托盘到排队位 ---")
    buf.remove_from_buffer()
    for i in range(12):
        elapsed = (datetime.now() - buf.transition_start_time).total_seconds() if buf.transition_start_time else 0.0
        buf.update(elapsed)
        if i % 5 == 0 or not buf.is_transferring:
            log_buffer(buf)
        if not buf.is_transferring:
            break
        time.sleep(0.2)
        
    print("\n>> 托盘离开排队位，随主线走掉")
    buf.pallet_leaves()
    log_buffer(buf)

    print("\n" + "="*50)
    print("--- 测试场景 4: Docking Station 标准作业流 ---")
    print("="*50)
        
    ds3 = DockingStation(id="DS3", station_number=3, time_wait_at_queue=3.0)
        
    def log_station(ds: DockingStation):
            loc = "Queue" if ds.pallet_present else ("WS" if ds.pallet_at_ws else "None")
            print(f"[{ds.id}] State: {ds.state.name:<16} | Mission: {ds.current_mission} | Pallet Loc: {loc}")

    log_station(ds3)

    print("\n>> 托盘 [TAG_777] 到达排队位 (pallet_arrived)")
    ds3.pallet_arrived("TAG_777")
    log_station(ds3)

    print(">> 下发指令: 进站加工 (accept_mission '2')")
    ds3.accept_mission("2")
        
        # 等待移载完成
    for i in range(12):
        elapsed = (datetime.now() - ds3.transition_start_time).total_seconds() if ds3.transition_start_time else 0.0
        ds3.update(elapsed)
        if i % 4 == 0 or ds3.state == DockingStationState.PROCESSING:
            log_station(ds3)
        if ds3.state == DockingStationState.PROCESSING:
            break
        time.sleep(0.2)

    print("\n>> 操作员完成作业 (complete_processing)")
    ds3.complete_processing()
    log_station(ds3)

    # 等待移出完成
    for i in range(12):
        elapsed = (datetime.now() - ds3.transition_start_time).total_seconds() if ds3.transition_start_time else 0.0
        ds3.update(elapsed)
        if ds3.state == DockingStationState.INIT:
            log_station(ds3)
            break
        time.sleep(0.2)


    print("\n--- 测试场景 5: Docking Station 看门狗防堵死 ---")
    print(">> 托盘 [TAG_888] 到达排队位，但不下发任何任务...")
    ds3.pallet_arrived("TAG_888")
    log_station(ds3)
        
        # 等待超过 3.0 秒触发看门狗
    for i in range(20):
            elapsed = (datetime.now() - ds3.transition_start_time).total_seconds() if ds3.transition_start_time else 0.0
            ds3.update(elapsed)
            
            # 只要状态发生改变，或者每隔 5 帧打印一次
            if ds3.state != DockingStationState.AWAITING_MISSION and i % 2 == 0:
                log_station(ds3)
            
            if ds3.state == DockingStationState.INIT:
                break
            time.sleep(0.2)

    # === 在文件顶部 import 补充 RFIDReader ===
    
    print("\n" + "="*50)
    print("--- 测试场景 7: RFID 识别系统 (物理防抖与读取故障) ---")
    print("="*50)
    
    rfid_reader = RFIDReader(id="RFID_DS1_Queue", location="queue", detection_delay=0.5)
    
    def log_rfid(reader: RFIDReader):
        tag = reader.tag_detected if reader.tag_detected else "None"
        print(f"[{reader.id}] Loc: {reader.location:<6} | State: {reader.state.name:<10} | Tag: {tag}")

    log_rfid(rfid_reader)

    print("\n>> 1. 托盘到达，传感器触发开始读取 (将经历 0.5s 物理稳定延迟)")
    rfid_reader.detect("EC2489664422FFFF")
    
    # 模拟 0.5 秒的读取与防抖过程
    for _ in range(5):
        elapsed = (datetime.now() - rfid_reader.detect_start_time).total_seconds() if rfid_reader.detect_start_time else 0.0
        rfid_reader.update(elapsed)
        log_rfid(rfid_reader)
        time.sleep(0.15)  # 更密集的打印以观察 DETECTING -> IDENTIFIED 的瞬间

    print("\n>> 2. 托盘离开本站，清空读取器")
    rfid_reader.clear()
    log_rfid(rfid_reader)

    print("\n>> 3. 突发异常：注入硬件故障 (如天线损坏/标签脏污)")
    rfid_reader.trigger_error()
    log_rfid(rfid_reader)
    
    print("\n>> 4. 尝试在故障状态下读取新托盘 (预期：动作被拒绝)")
    success = rfid_reader.detect("TAG_NEW_123")
    print(f"读取指令接收成功: {success}")
    log_rfid(rfid_reader)

    print("\n>> 5. HMI 故障复位")
    rfid_reader.reset_error()
    log_rfid(rfid_reader)

# === 在文件顶部 import 补充 PneumaticSystem ===
    
    

    

if __name__ == "__main__":
    run_tests()
