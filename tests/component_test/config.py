# config.py

# 任务代码 (Mission)
MISSION_NONE = 0
MISSION_PASS = 1
MISSION_MC_TO_WS = 2   # 主线到工作台
MISSION_WS_TO_MC = 3   # 工作台回主线
MISSION_BUFF_TO_DS = 6 # 缓冲到下放

# 时序常量
AUTO_PASS_DELAY_MS = 5000      # 自动放行延迟 (ms)
RFID_STABILIZATION_MS = 500    # RFID 稳定读取时间 (ms)

# 超时与等待常量 (秒)
MAX_ELEVATOR_TIMEOUT_S = 10.0  # 升降机最大超时时间 (Step420)
MAX_WAIT_AFTER_TRANSFER_S = 4.0 # 转移后最大等待时间

# 传感器校准常量
HEIGHT_OFFSET = 100            # 工作台高度默认偏移
HEIGHT_SCALE_FACTOR = 0.5      # 传感器读数到毫米的转换率