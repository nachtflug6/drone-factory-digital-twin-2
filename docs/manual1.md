# Manual 1 — 项目进度与使用说明

本文档描述 **WS 输送线数字孪生 mock-up** 当前实现范围、现实产线约定、`src/mock_up` 全部模块与部件设定、以及可运行入口，便于新成员上手与验收对照。

---

## 1. 项目定位

- **目标**：在 Python 中搭建与 `Kod_WSConv_Sven2022` 文档对齐的 **可配置、可步进仿真** 模型，用于演示、联调与验证清单。
- **范围**：`src/mock_up` 为核心物理/逻辑抽象；`examples` 为场景脚本；`src/simulation` 提供最小 **验证用仿真器**；`tests` 含仿真有效性测试。

---

## 2. 当前进度概览

| 领域 | 状态 |
|------|------|
| 核心组件 | `ConveyorMotor`、`TransferElevator`、`Buffer`、`DockingStation`、`PneumaticSystem`、`RFIDReader` 已实现并可 `update(elapsed)` |
| 全局状态 | `SystemState` 统一容器；`update(datetime)` 将时间换算为各组件所需的 elapsed 秒 |
| 配置 | `SimulationConfig` 集中参数；含工位拓扑、托盘尺寸、装配时间、原材料批次、名义 RFID 等 |
| 现实产线修订 | WS1=进线+Buffer；WS2/3/5/6=组装；WS4=AGV 接驳（模型内忽略 AGV）；WS6=成品立即输出 |
| 原材料入线 | `RawMaterialIngressScheduler`：按间隔在 DS1 下发 Mission 3 → Buffer |
| 演示脚本 | 短时仿真、墙钟 1:1 长演示、100 分钟压缩为 1 分钟的事件驱动日志等 |
| 仿真验证 | `Simulator` + `tests/simulation/test_simulation_validity.py`（状态一致性、时序、确定性） |

---

## 3. `src/mock_up` 文件夹 — 全部内容与职责

`mock_up` 共 **5 个 Python 文件**，无子包。

| 文件 | 职责 |
|------|------|
| `__init__.py` | 包说明；导出 `SystemState`、`SimulationConfig`；`from .components import *` 暴露所有组件类与工厂 |
| `config.py` | `SimulationConfig` 数据类（全站参数 + `__post_init__` 校验）；预设 `config_normal_operation` / `config_stress_test` / `config_fault_testing` / `config_long_horizon`；`DEFAULT_CONFIG` |
| `components.py` | 输送/升降机/缓冲/工位/气路/RFID 等 **部件类**、相关 **枚举**、`create_ws_conveyor_system(config)` **系统工厂** |
| `state.py` | `SystemState`：持有 `components` 字典、仿真时钟、`update` 统一步进；`create_system` 便捷函数 |
| `logic.py` | 自文档化控制逻辑占位与 **产线辅助**：`RawMaterialIngressScheduler`、`build_station_processing_route`、`conveyor_travel_time_seconds`；电机/输送辅助函数；`apply_system_logic`、`validate_system_state` |

### 3.1 包导出（`__init__.py`）

- **`__all__`**：`SystemState`、`SimulationConfig`（显式列出）；组件侧通过 `import *` 在运行时可用，但未写入 `__all__`。

### 3.2 系统工厂 `create_ws_conveyor_system(config)`

由 `SimulationConfig` 实例化下列 **字典键 → 对象**（与 `SystemState.components` 一致）：

| 键名 | 类型 | 说明 |
|------|------|------|
| `conveyor_motor` | `ConveyorMotor` | `id='main_conveyor'`，`ramp_time=config.conveyor_ramp_time` |
| `elevator` | `TransferElevator` | `id='transfer_elevator'`，`travel_time` / `transfer_time` 来自配置 |
| `buffer` | `Buffer` | `id='buffer'`，容量与转移时间、RFID 延迟来自配置 |
| `ds_1` … `ds_6` | `DockingStation` | `id=f'ds_{i}'`，按工位号赋 `StationRole`、`is_assembly_station`、`immediate_output`（仅 egress 站） |
| `pneumatic` | `PneumaticSystem` | `id='pneumatic_system'` |
| `rfid_queue` | `RFIDReader` | `location='queue'` |
| `rfid_elevator` | `RFIDReader` | `location='elevator'` |

**特殊装配规则**：

- **DS1**：挂载 **同一** `buffer` 实例，供 Mission 3（AMR→Buffer）使用。
- **DS6**：`wait_after_amr_transfer=config.station_wait_after_amr_transfer`（Mission 4 / AMR 路径）。
- **组装随机数**：每站 `assembly_rng = Random(config.seed + i * 9973)`；`assembly_deterministic = config.deterministic or (not config.assembly_use_stochastic_duration)`。

---

## 4. 部件设定（`components.py`）

以下「默认/典型值」以 `SimulationConfig` 的字段为准；类上另有 dataclass 默认值（若工厂未覆盖则以工厂传入为准）。

### 4.1 `ConveyorMotor` / `ConveyorMotorState`

| 项目 | 说明 |
|------|------|
| **状态** | `IDLE` → `RAMP_UP` → `RUNNING`；停止时 `RAMP_DOWN` → `IDLE`；故障 `ERROR` |
| **主要字段** | `max_speed_percent`（默认 100）、`max_speed_ms`（默认 0.18 m/s）、`ramp_time`（默认 2 s）；`current_speed_percent` / `current_speed_ms`；`transition_start_time`；`is_malfunctioning` |
| **速度约束** | `start(speed_percent)` 将目标限制在 **20–100%**（与文档「20–100% 调速」一致） |
| **接口** | `start`、`stop`、`update(elapsed_time)`（按 ramp 线性插值）；`trigger_error` / `reset_error` |
| **配置映射** | `conveyor_max_speed_ms`、`conveyor_ramp_time`；工厂写入 `ramp_time` |

### 4.2 `TransferElevator` / `ElevatorPosition` / `TransferDirection`

| 项目 | 说明 |
|------|------|
| **垂直位置** | `DOWN`、`UP`、`MOVING`、`ERROR`（上下请求冲突时置 `ERROR`） |
| **横移方向** | `TransferDirection.TO_WS` / `FROM_WS`（与 PLC 布尔语义注释对应） |
| **主要字段** | `travel_time`（竖直行程，默认实例 1.5 s，**工厂用** `config.elevator_travel_time`）、`transfer_time`（横移带，工厂用 `elevator_transfer_time`）；`up_requested` / `down_requested`；`transfer_running`、`transfer_start_time` |
| **接口** | `request_up`、`request_down`；`start_transfer(direction)`（`MOVING` 时互锁返回 `False`）；`stop_transfer`；`update`（完成竖直段；横移完成逻辑为占位 `pass`） |
| **配置映射** | `elevator_travel_time`、`elevator_transfer_time` |

### 4.3 `Buffer` / `BufferState`

| 项目 | 说明 |
|------|------|
| **状态** | `EMPTY` / `PARTIAL`（1 托）/ `FULL`（满容） |
| **容量** | `max_capacity`（配置默认 2） |
| **队列位** | `pallet_at_queue`、`pallet_rfid_at_queue`、`queue_detect_start_time`；`rfid_detection_delay` 字段保留，读码节拍可由上层配合 RFIDReader 使用 |
| **移载** | `transfer_time`（入/出缓冲的物理时间，配置 `buffer_transfer_time`）；`is_transferring`、`transfer_direction`（`"in"` / `"out"`） |
| **接口** | `pallet_enters(rfid)`、`pallet_leaves()`；`add_to_buffer()` / `remove_from_buffer()` 启动定时移载；`update` 结束后更新 `pallet_count`、`stored_rfids` |
| **配置映射** | `buffer_max_capacity`、`buffer_transfer_time`、`rfid_detection_delay`（写入 Buffer 实例） |

### 4.4 `DockingStation` / `DockingStationState` / `StationRole`

| 项目 | 说明 |
|------|------|
| **SFC 状态** | `INIT`、`AWAITING_MISSION`、`RECEIVING`、`PROCESSING`、`SENDING`、`CLEANUP`、`AMR_HANDOFF_WAIT`、`ERROR` |
| **工位角色** | `INGRESS_BUFFER`（WS1）、`ASSEMBLY`（WS2/3/5/6）、`AGV_DOCKING_IGNORED`（WS4）、`OTHER` |
| **Mission 约定** | **1**：过站；**2**：组装工位进站 → `PROCESSING`（非组装站 `accept_mission` 拒绝）；**3**：仅 **DS1** 且需 `buffer`，需 `pallet_rfid`，`RECEIVING` 结束后托盘进 Buffer；**4**：仅 **DS6**，兼容 AMR 交出路径 → `SENDING` → `AMR_HANDOFF_WAIT` |
| **组装时间** | `_sample_assembly_duration_seconds()`：`min(hi, lo + Exp(1/scale))` 截断到 `[assembly_time_min_seconds, assembly_time_max_seconds]`；`assembly_deterministic` 时为区间中点 |
| **WS6 特例** | `immediate_output=True` 时，`complete_processing()` 直接 `pallet_removed()`，不进入 Mission 4 主流程 |
| **看门狗** | `AWAITING_MISSION` 下若 `elapsed >= time_wait_at_queue` 且 `allow_auto_pass`，自动 `accept_mission("1")`（会 `print` 告警） |
| **其它字段** | `buffer`（仅 DS1）、`wait_after_amr_transfer`（DS6）；`pallet_at_ws`、`_processing_target_seconds`、`_mission3_incoming_rfid` 等 |
| **配置映射** | `station_wait_at_queue`（代码中 HMI 注释与字段名 `time_wait_at_queue` 对应需注意）、`station_transfer_time`、`station_allow_auto_pass`、`station_wait_after_amr_transfer`；装配三参数 + `deterministic` / `assembly_use_stochastic_duration` / `seed` |

### 4.5 `PneumaticSystem` / `PneumaticState`

| 项目 | 说明 |
|------|------|
| **状态** | `OFF`、`STABILIZING`、`NORMAL`、`HIGH_PRESSURE`、`LEAK_DETECTED` |
| **压力/流量** | `target_pressure_bar`、`min_pressure_bar`、`max_pressure_bar`、`max_flow_nm3h`；`stabilization_time` 内升至目标压力 |
| **接口** | `enable` / `disable`；`update`（关闭时压力缓慢泄漏衰减；NORMAL 下简单越限检测） |
| **配置映射** | `pneumatic_*`、`pneumatic_enabled`（启用由场景/上层决定，组件自身有 `is_enabled`） |

### 4.6 `RFIDReader` / `RFIDState`（名义模型）

| 项目 | 说明 |
|------|------|
| **状态** | `IDLE` → `DETECTING` → `IDENTIFIED`；`ERROR` 枚举保留 |
| **语义** | **不**仿真真实射频、EPC、防碰撞；仅用字符串标签 + `detection_delay` 对齐文档节拍 |
| **接口** | `detect(tag)`、`clear()`、`update(elapsed_time)` |
| **配置映射** | `rfid_detection_delay`、`rfid_locations`（说明性）；工厂创建 `queue` / `elevator` 两台读码器 |

---

## 5. `SimulationConfig` 字段分组（`config.py`）

| 分组 | 字段（默认值摘要） |
|------|---------------------|
| 仿真节拍 | `duration_hours`、`timestep_seconds`、`seed`、`deterministic`、`verbose` |
| 输送 | `conveyor_max_speed_ms`（0.18）、`conveyor_speed_range`（20–100%）、`conveyor_ramp_time`（2 s）、`conveyor_enabled` |
| 升降机 | `elevator_travel_time`（0.5）、`elevator_transfer_time`（3）、`elevator_positions`、`elevator_initial_position` |
| 缓冲 | `buffer_max_capacity`（2）、`buffer_transfer_time`（3）、`buffer_queue_position`、`buffer_auto_pass_enabled`、`buffer_auto_pass_delay` |
| 工位通用 | `station_count`、`station_numbers`、`station_wait_at_queue`（2）、`station_transfer_time`（2）、`station_allow_auto_pass`、`station_wait_after_passing`、`station_wait_after_ws_transfer`、`station_wait_after_amr_transfer`（4） |
| 装配统计 | `assembly_time_min_seconds`（120）、`assembly_time_max_seconds`（900）、`assembly_exponential_scale_seconds`（180）、`assembly_use_stochastic_duration` |
| 原材料入线 | `raw_material_batch_interval_seconds`（600）、`raw_material_pallets_per_batch`（1） |
| 产线拓扑 | `pallet_length_m`（0.25）、`ws_ingress_station`（1）、`ws_egress_station`（6）、`assembly_station_numbers`（2,3,5,6）、`agv_docking_station_numbers`（4）、`ws_path_order`、`ws_neighbor_distances_m` |
| 气路 | `pneumatic_target_pressure`（6 bar）、`pneumatic_min_pressure`（5.5）、`pneumatic_max_pressure`（7）、`pneumatic_max_flow`（15）、`pneumatic_stabilization_time`（5）、`pneumatic_enabled` |
| RFID | `rfid_detection_delay`（0.5）、`rfid_tag_format`、`rfid_locations` |
| 日志 | `log_format`、`log_level`、`log_file`、`log_state_changes`、`log_sensor_values`、`log_pallet_movements`、`log_errors`、`log_state_snapshots`、`snapshot_interval_seconds` |
| 任务字典 | `available_missions`（按站号的占位任务名列表） |
| 安全/约束 | `allow_conflicting_elevator_commands`、`allow_direction_change_during_transfer`、`enforce_pressure_limits`、`prevent_buffer_overflow` |

**校验**：`__post_init__` 中断言容量、速度、压力、工位与距离键、装配区间、批次间隔等一致性与正值。

---

## 6. `SystemState`（`state.py`）

| 项目 | 说明 |
|------|------|
| **构造** | `SystemState(config)` → `create_ws_conveyor_system(config)` 填充 `self.components`；`current_time`、`event_count` |
| **访问** | `get_component(component_id)`；`get_components_by_type(name)` 支持别名（如 `motor`/`conveyormotor`、`rfid`/`rfidreader`、`station`/`dockingstation`） |
| **注册** | `register_component`（要求对象有 `id`） |
| **快照** | `get_snapshot()`：将各组件 `__dict__` 中非 `_` 前缀项序列化为可日志形式（枚举等转 `str`） |
| **不变式** | `check_invariants()`：基础检查（可扩展） |
| **步进** | `update(current_time)`：计算 `delta_seconds`，对每个带 `update` 的组件调用 `_get_component_elapsed_time`（优先 `transition_start_time` / `detect_start_time` / `transfer_start_time` 与当前时间差，否则用 `delta`） |
| **日志行** | `log_state()`：时间戳 + 快照 + `event_count` |
| **便捷** | `create_system(config)` → `SystemState(config)` |

---

## 7. `logic.py` — 调度与控制辅助

| 符号 | 说明 |
|------|------|
| `RawMaterialIngressScheduler` | 按 `interval_seconds` 生成 `RAW_000001` 形式 RFID；`tick(sim_time, ds1)` 在 DS1 为 `INIT` 时对 `pending_rfids` 调用 `accept_mission("3", pallet_rfid=...)` |
| `build_station_processing_route(config)` | 返回 `[sid for sid in assembly_station_numbers if sid in ws_path_order]`（当前即 2,3,5,6 顺序过滤） |
| `conveyor_travel_time_seconds(config, from_station, to_station)` | 沿 `ws_path_order` 相邻段累加 `ws_neighbor_distances_m`，除以 `conveyor_max_speed_ms` |
| `should_motor_run` / `update_motor_acceleration` | 基于 `ConveyorMotor` 故障标志与 RAMP 状态推进 |
| `should_conveyor_run` / `check_conveyor_load` | 兼容未实现字段的轻量规则 |
| `update_sensor_readings` | 占位（TODO），遍历 `loadsensor` 类型 |
| `apply_system_logic` | 每周期：传感器占位 → 各电机加速辅助 → 输送负载检查 → **`system.update(current_time)`** |
| `validate_system_state` | `check_invariants` + 速度/负载等简单校验 |

---



## 8. 现实产线约定（与 PDF 可能不一致处已显式建模）

### 8.1 工位角色（`SimulationConfig` + `DockingStation.role`）

- **WS1**：进线装置 + **Buffer**，**不做组装**；Mission 3（AMR→产线）仅在此工位将托盘写入 Buffer。
- **WS2、WS3、WS5、WS6**：**组装工位**（可接受 Mission 2 并进入加工时序）。
- **WS4**：与 AGV 接驳；**当前模型不实现 AGV**，仅作名义占位，**不参与组装**。
- **WS6**：制成品 **立即输出**（`immediate_output`），不依赖 Mission 4/AMR 主流程。

### 8.2 站间距离与托盘（配置项）

- 托盘长度：`pallet_length_m = 0.25`（25 cm）。
- 相邻工位中心距（米）：WS1–WS2 `3.5`；WS2–WS3 `2.0`；WS3–WS4 `3.5`；WS4–WS5 `3.5`；WS5–WS6 `2.0`。
- 辅助函数：`logic.conveyor_travel_time_seconds(config, from_station, to_station)` 可按距离与 `conveyor_max_speed_ms` 估算输送时间。

### 8.3 任务编号（与历史约定）

- **Mission 3**：仅 **DS1**，且需注入 `Buffer`；`accept_mission("3", pallet_rfid=...)`。
- **Mission 2**：组装工位进站加工。
- **Mission 4**：仍保留在组件内以兼容旧工艺；当前主线演示以 **WS6 立即输出** 为主。

---

## 9. 名义 RFID

- **不建模**真实射频协议、防碰撞、RSSI 等。
- 保留 **状态机** `IDLE → DETECTING → IDENTIFIED` 与 **`rfid_detection_delay`（默认 0.5 s）**，用于节拍与互锁演示。
- 详见 `docs/VERIFICATION_CHECKLIST.md` 中 RFID 小节。

---

## 10. 装配与原材料

- **装配时间**：默认区间 **2–15 分钟**（秒为单位配置），可选用截断指数分布；`deterministic=True` 或 `assembly_use_stochastic_duration=False` 时可用固定中点。
- **原材料批次**：默认每 **600 s** 一批（可配置 `raw_material_batch_interval_seconds`、`raw_material_pallets_per_batch`）。

---

## 11. 可运行示例

在仓库根目录执行，**需** `PYTHONPATH=.`（或安装为包）。

| 脚本 | 说明 |
|------|------|
| `examples/ws_conveyor_simulation.py` | 短时 JSONL 日志仿真 |
| `examples/pallet_lifecycle_monitor.py` | 单托盘生命周期监视（演示可缩短装配时间） |
| `examples/realtime_demo_60min.py` | 墙钟 **60 分钟**、仿真 1:1；路线 **WS1 → [2,3,5,6]** |
| `examples/event_driven_demo_100min.py` | 将 **100 分钟仿真压缩到约 1 分钟墙钟**，事件驱动打印 + JSONL |

示例：

```bash
PYTHONPATH=. python3 examples/ws_conveyor_simulation.py
PYTHONPATH=. python3 examples/realtime_demo_60min.py
PYTHONPATH=. python3 examples/event_driven_demo_100min.py
```

---

## 12. Phase 3 测试进展（对照 `PROJECT_PHASES.md`）

[docs/PROJECT_PHASES.md](PROJECT_PHASES.md) 中 **Phase 3: Verification & Testing** 的目标包括：在 `tests/` 下建立单元/集成测试、实现校验器、并与文档行为对照。当前仓库内 **已完成** 的测试工作如下（不含 Phase 3 成功准则中的覆盖率百分比、全文档逐条对照等 **暂未闭环** 项）。

### 12.1 与阶段任务的对应关系

| Phase 3 任务 | 当前状态 |
|--------------|----------|
| 各部件单元测试 + 边界/错误场景 | `tests/unit/` 下按组件分文件，另有 `test_mockup_transitions.py` 跨组件主路径烟雾测试 |
| 子系统集成测试 | `tests/integration/` 内编排互锁与「依赖规格→门控」等价场景 |

### 12.2 具体测试场景清单

下列为各文件中 **pytest 用例名** 及场景说明（与源码中 `def test_...` 一一对应）。运行时可指定节点 id，例如：  
`PYTHONPATH=. python3 -m pytest tests/unit/test_buffer.py::TestBufferTransitions::test_initial_state_empty -q`。

#### 仿真（`tests/simulation/test_simulation_validity.py`）

| 用例 | 场景说明 |
|------|----------|
| `test_simulation_no_invalid_states` | `Simulator` 跑一段后，近期 `state_change` 日志中的 `new_state` 与对应组件 `state.value` 一致 |
| `test_simulation_timing_constraints_rfid_and_motor_ramp` | 名义 RFID 延迟、输送电机 `ramp_up`→`running` 间隔约 **2 s**（配置 `conveyor_ramp_time`） |
| `test_simulation_determinism_fixed_mode` | `deterministic=True`、固定 `seed` 下两次完整运行的日志等价 |

#### 单元 — 输送电机（`tests/unit/test_conveyor_motor.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestConveyorMotorStateTransitions::test_motor_initial_state` | 新建电机为 `IDLE`、速度为零 |
| `TestConveyorMotorStateTransitions::test_motor_idle_to_ramp_up_to_running` | `start` 后经 `update` 进入 `RUNNING`、速度趋近目标 |
| `TestConveyorMotorStateTransitions::test_motor_cannot_start_when_not_idle` | 非 `IDLE`/`RAMP_DOWN` 时 `start` 被拒绝 |
| `TestConveyorMotorStateTransitions::test_motor_running_to_idle_on_stop` | `stop` 后经 `RAMP_DOWN` 回 `IDLE` |
| `TestConveyorMotorStateTransitions::test_motor_stop_from_idle_returns_false` | `IDLE` 上 `stop` 返回 `False` |
| `TestConveyorMotorStateTransitions::test_motor_error_blocks_start_and_reset_returns_idle` | `ERROR` 禁止 `start`；`reset_error` 后回到可启动状态 |

#### 单元 — 升降机（`tests/unit/test_transfer_elevator.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestTransferElevatorTransitions::test_down_to_up_to_down` | `request_up`/`request_down` 与 `update` 完成竖直往返 |
| `TestTransferElevatorTransitions::test_direction_conflict_sets_error` | 同时请求上/下导致 `ERROR` |
| `TestTransferElevatorTransitions::test_start_transfer_to_ws_and_stop` | 横移 `start_transfer` / `stop_transfer` |
| `TestTransferElevatorTransitions::test_start_transfer_is_blocked_while_elevator_moving` | `MOVING` 时不可 `start_transfer` |

#### 单元 — 缓冲（`tests/unit/test_buffer.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestBufferTransitions::test_initial_state_empty` | 初始 `EMPTY`、无托盘 |
| `TestBufferTransitions::test_queue_pallet_enters_and_add_to_buffer_in_then_update` | 队列到货→`add_to_buffer`(in)→`update` 后入库、`PARTIAL` |
| `TestBufferTransitions::test_buffer_transfer_out_to_queue` | 先入库再 `remove_from_buffer`(out)→`update`，队列侧有货 |
| `TestBufferTransitions::test_pallet_enters_refused_when_queue_occupied` | 队列已有货时拒绝第二次 `pallet_enters` |

#### 单元 —  docking 工位（`tests/unit/test_docking_station.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestDockingStationTransitions::test_mission_2_to_ws_then_operator_complete_then_cleanup_to_init` | Mission 2：`RECEIVING`→`PROCESSING`→人工 `complete_processing`→`SENDING`/`CLEANUP`→`INIT` |
| `TestDockingStationTransitions::test_auto_pass_from_awaiting_mission_to_receiving_mission_1` | `AWAITING_MISSION` 超时看门狗触发 Mission 1 进入 `RECEIVING` |

#### 单元 — 气路（`tests/unit/test_pneumatic_system.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestPneumaticSystemTransitions::test_enable_stabilizing_to_normal` | `enable` 后经 `STABILIZING` 到 `NORMAL`、压力达标 |
| `TestPneumaticSystemTransitions::test_enable_and_disable_resets_pressure` | `disable` 后压力/流量归零 |
| `TestPneumaticSystemTransitions::test_fault_flow_causes_leak_detected` | 流量超上限触发 `LEAK_DETECTED` |

#### 单元 — RFID（`tests/unit/test_rfid_reader.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestRFIDReaderTransitions::test_detect_idle_to_detecting_and_identified` | `detect`→`update` 后进入 `IDENTIFIED` |
| `TestRFIDReaderTransitions::test_detect_refused_when_not_idle` | `DETECTING` 下再次 `detect` 返回 `False` |
| `TestRFIDReaderTransitions::test_clear_resets_to_idle` | `clear` 恢复 `IDLE` |

#### 单元 — 组合过渡（`tests/unit/test_mockup_transitions.py`，函数级用例）

| 用例 | 场景说明 |
|------|----------|
| `test_conveyor_motor_idle_to_ramp_up_to_running` | 电机加速片段 |
| `test_conveyor_motor_running_to_idle_on_stop` | 电机减速停机片段 |
| `test_conveyor_motor_error_blocks_start_and_reset_returns_idle` | 电机故障与复位 |
| `test_transfer_elevator_down_to_up_and_back_to_down` | 升降机往返 |
| `test_transfer_elevator_direction_conflict_sets_error` | 升降机冲突 |
| `test_transfer_elevator_transfer_start_stop` | 横移启停 |
| `test_buffer_queue_to_storage_and_back_out` | 缓冲入出库连贯动作 |
| `test_docking_station_main_processing_cycle_mission_2` | DS Mission 2 主循环（与单测文件场景类似，独立实例） |
| `test_pneumatic_enable_to_normal_and_fault_on_low_max_flow` | 气路正常与将 `max_flow` 压得过低导致的异常分支 |
| `test_rfid_reader_detect_to_identified_and_clear` | RFID 识别与清除 |

#### 集成 — 编排互锁（`tests/integration/test_system_orchestration_interlocks.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestIntegratedOrchestrationInterlocks::test_cascade_fault_conveyor_error_stops_elevator_transfer` | 主电机 `ERROR` 后编排逻辑停止升降机横移 |
| `TestIntegratedOrchestrationInterlocks::test_resource_contention_elevator_busy_blocks_second_station_mission` | 横移占用时，第二工位无法接受 Mission |
| `TestIntegratedOrchestrationInterlocks::test_synchronization_timing_ds_processing_requires_elevator_up` | 仅当升降机 `UP` 时，`orchestrated_ds_update` 才推进 DS 离开 `RECEIVING` |
| `TestIntegratedOrchestrationInterlocks::test_buffer_full_resource_interlock_stops_conveyor_and_elevator` | `Buffer` `FULL` 时停止输送与横移 |

#### 集成 — 依赖/门控等价（`tests/integration/test_dependency_specs_gating_equivalent.py`）

| 用例 | 场景说明 |
|------|----------|
| `TestCascadeAndDependenciesGating::test_cascade_when_pneumatic_pressure_off_blocks_all_motion_and_ds_progress` | 气源未建立时禁止运动与 DS 接收推进 |
| `TestCascadeAndDependenciesGating::test_cascade_when_pneumatic_pressure_drop_blocks_motion` | 压力异常后封锁运动 |
| `TestCascadeAndDependenciesGating::test_cascade_when_conveyor_motor_error_blocks_ds_and_buffer_receive_send` | 输送 `ERROR` 阻止 DS/缓冲侧收发编排路径 |
| `TestCascadeAndDependenciesGating::test_synchronization_transfer_requires_elevator_up_and_direction_match` | 横移需 `UP` 且 `transfer_direction` 与请求一致 |
| `TestCascadeAndDependenciesGating::test_resource_contention_buffer_slots_two_only_third_blocked_until_amr_removes` | 两库位占满后第三托阻塞，直到出库释放 |
| `TestCascadeAndDependenciesGating::test_station_exclusivity_ds1_cannot_receive_second_pallet_while_processing` | DS1 加工中单托盘独占（不接受第二套 Mission 2） |
| `TestCascadeAndDependenciesGating::test_rfid_timing_requires_0_5s_wait_before_buffer_in` | 队列 RFID 未到 `IDENTIFIED` 时不允许编排层 `add_to_buffer` |
| `TestCascadeAndDependenciesGating::test_auto_passing_overwrites_mission_when_no_mission_set_within_wait_time` | 队列等待超时自动 Mission 1 与后续状态 |

**合计**：**47** 项（仿真 3 + 单元 32 + 集成 12）。与本地一致时可运行：  
`PYTHONPATH=. python3 -m pytest tests/unit tests/integration tests/simulation --collect-only -q`（末尾显示 `47 tests collected`）。

### 12.3 单元测试文件概要（`tests/unit/`）

| 文件 | 覆盖要点 |
|------|----------|
| `test_conveyor_motor.py` | 初始 `IDLE`；`start`→`RAMP_UP`→`RUNNING`；非法 `start`；`stop` 减速至 `IDLE`；`IDLE` 上 `stop`；`ERROR` 与 `reset_error` |
| `test_transfer_elevator.py` | 下→上→下；上下请求冲突→`ERROR`；`start_transfer` / `stop`；`MOVING` 互锁 |
| `test_buffer.py` | 初始 `EMPTY`；队列入站→`add_to_buffer`→`update`→`PARTIAL`；出库到队列；队列占用时拒绝再次 `pallet_enters` |
| `test_docking_station.py` | Mission 2 进站→加工→`complete_processing`→清理回 `INIT`；`AWAITING_MISSION` 看门狗自动 Mission 1 |
| `test_pneumatic_system.py` | `enable` 稳压至 `NORMAL`；`disable` 归零；异常流量→`LEAK_DETECTED` |
| `test_rfid_reader.py` | `detect`→识别时序；非 `IDLE` 拒绝重复 `detect`；`clear` 复位 |
| `test_mockup_transitions.py` | 单文件串联：电机、升降机、缓冲、DS Mission 2、气路、RFID |

### 12.4 集成测试文件概要（`tests/integration/`）

| 文件 | 覆盖要点 |
|------|----------|
| `test_system_orchestration_interlocks.py` | 测试内编排层：`conveyor` `ERROR` 级联停止升降机横移；升降机横移占用时第二工位无法接受 Mission；仅当升降机 `UP` 时工位 `update` 才推进 `RECEIVING`；`Buffer` 满载时停止输送与横移 |
| `test_dependency_specs_gating_equivalent.py` | 气动未就绪/压力异常时全局禁止运动与 DS 推进；输送 `ERROR` 阻止 DS/Buffer 收发；横移需 `UP` + 方向一致；缓冲两槽满员时第三托阻塞；DS1 加工中单托盘独占；RFID 需约 **0.5 s** 后才允许入缓冲；队列等待超时自动放行（Mission 1） |

### 12.5 仿真层验证（亦服务于 Phase 3 回归）

见 **§13**；`tests/simulation/test_simulation_validity.py` 三条用例见 **§12.2** 表格。

### 12.6 建议运行命令

```bash
PYTHONPATH=. python3 -m pytest tests/unit tests/integration tests/simulation -q
```

维护时请用上述命令做全量回归；个别用例若与最新工位约定（例如 DS1 仅 ingress / Mission 3）或 `Simulator` 日志粒度不一致，需同步更新测试断言——**以你当前分支上 `pytest` 的实际通过与失败为准**，本小节描述的是测试**已落地文件与意图**，不保证永远全绿。

---

## 13. 仿真验证测试

- **引擎**：`src/simulation/simulator.py` 中的 `Simulator`（内存日志 `InMemoryLogger`）。
- **用例**：`tests/simulation/test_simulation_validity.py`
  - 状态变更日志与组件真实状态一致
  - 电机 ramp 与 RFID 延迟约束
  - 确定性模式下两次运行日志一致

运行（需已安装 pytest）：

```bash
PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py -q
```

---

## 14. 配置入口

- 默认场景：`mock_up.config.config_normal_operation()`。
- 全量字段与校验：`mock_up.config.SimulationConfig` 及 `__post_init__`。

---

## 15. 已知局限与后续可做

- `TransferElevator.update` 内横移完成仍为占位；完整托盘过升降机需编排层或后续补全。
- `logic.update_sensor_readings` 等为 TODO；`apply_system_logic` 与具体 `examples` 脚本可能并行存在多套驱动方式。
- 未实现真实 AGV、真实 RFID 硬件、多段输送线独立电机等；需要时在 `mock_up` 扩展组件或在编排层增加策略。

---

## 16. 文档与清单

- 验证哲学与检查项：`docs/VERIFICATION_CHECKLIST.md`
- 项目阶段：`docs/PROJECT_PHASES.md`
- 本手册：`docs/manual1.md`（Manual 1）

---

*文档版本：与仓库当前 `src/mock_up` / `examples` / `tests` 状态同步；若你更新产线约定或部件行为，请同时改源码与本手册对应小节。*
