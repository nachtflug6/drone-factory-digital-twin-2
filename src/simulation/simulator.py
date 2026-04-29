from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.mock_up.config import SimulationConfig
from src.mock_up.logic import (
    PerformanceMetricsCollector,
    RawMaterialIngressScheduler,
    build_station_processing_route,
    conveyor_travel_time_ingress_to_station,
    conveyor_travel_time_seconds,
    count_pallets_on_line,
)
from src.mock_up.state import SystemState
from src.mock_up.components import (
    ConveyorMotorState,
    DockingStationState,
    ElevatorPosition,
    PalletAlignmentWindow,
    RFIDState,
    TransferDirection,
)


@dataclass
class _ElevatorTrack:
    """Per assembly station: elevator sub-state for parallel lines."""

    did_elevator_receive_ping: bool = False
    did_request_up: bool = False
    did_request_down: bool = False
    did_transfer_to_ws: bool = False
    did_transfer_from_ws: bool = False
    transfer_to_ws_started_at: Optional[float] = None
    transfer_from_ws_started_at: Optional[float] = None


@dataclass
class InMemoryLogger:
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def log(self, payload: Dict[str, Any]) -> None:
        self.logs.append(payload)

    def get_logs(self) -> List[Dict[str, Any]]:
        return list(self.logs)


class Simulator:
    """Current project baseline simulator (step-driven, event-emitting, metrics-aware)."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.system = SystemState(config)
        self.logger = InMemoryLogger()

        self._sim_started_at = datetime(2026, 1, 1, 0, 0, 0)
        self._sim_time_s = 0.0

        self._ingress = RawMaterialIngressScheduler(
            interval_seconds=config.raw_material_batch_interval_seconds,
            pallets_per_batch=config.raw_material_pallets_per_batch,
        )
        self._station_route = build_station_processing_route(config)
        self._next_station_idx = 0
        # 并行产线：多个组装工位可同时各有一托在加工流程中 / Parallel line: multiple assembly stations can each process one pallet concurrently
        self._active_by_station: Dict[int, str] = {}
        self._elev_track: Dict[int, _ElevatorTrack] = {}

        self._did_conveyor_started = False

        # (due_sim_time_s, target_station_id, pallet_rfid)
        self._pending_line_arrivals: List[Tuple[float, int, str]] = []
        # (due_sim_time_s, pallet_rfid, source_station_id): 组装完成后回流到 DS6 输出口 / After assembly completion, return flow goes to DS6 egress
        self._pending_egress_arrivals: List[Tuple[float, str, int]] = []
        # WS 接口窗（主/从带对中）；用于 lead-time 终点“窗口清零” / WS interface window (main/slave alignment), used to clear at lead-time endpoint
        self._iface_windows: Dict[int, PalletAlignmentWindow] = {
            sid: PalletAlignmentWindow(
                id=f"ds_{sid}_main_slave_iface",
                sensor_spacing_m=config.pallet_length_m,
            )
            for sid in config.assembly_station_numbers
        }

        self._prev_states: Dict[str, str] = {}
        self._prime_prev_states()
        self._metrics = PerformanceMetricsCollector(
            config,
            sample_interval_seconds=max(float(config.snapshot_interval_seconds), 1.0),
        )

    def _now(self) -> datetime:
        return self._sim_started_at + timedelta(seconds=self._sim_time_s)

    def _prime_prev_states(self) -> None:
        for cid, comp in self.system.components.items():
            st = getattr(comp, "state", None)
            if hasattr(st, "value"):
                self._prev_states[cid] = st.value

    def _emit(self, event_type: str, component_id: str, **fields: Any) -> None:
        self.logger.log(
            {
                "timestamp": self._now().isoformat(timespec="milliseconds") + "Z",
                "sim_time_s": round(self._sim_time_s, 6),
                "event_type": event_type,
                "component_id": component_id,
                **fields,
            }
        )

    def _count_pallets_on_line(self) -> int:
        n = count_pallets_on_line(
            self.system.components,
            self._pending_line_arrivals,
            self.config.station_numbers,
        )
        # 回流到 DS6 输出口的在途托盘同样属于场上 WIP。 / Pallets in transit back to DS6 egress are also counted as on-line WIP.
        return int(n) + len(self._pending_egress_arrivals)

    def _capture_state_changes(self) -> None:
        for cid, comp in self.system.components.items():
            st = getattr(comp, "state", None)
            if not hasattr(st, "value"):
                continue
            new_val = st.value
            old_val = self._prev_states.get(cid)
            if old_val != new_val:
                self._emit(
                    "state_change",
                    cid,
                    old_state=old_val,
                    new_state=new_val,
                )
                if cid.startswith("ds_"):
                    try:
                        sid = int(cid.split("_", 1)[1])
                    except Exception:
                        sid = 0
                    if sid:
                        self._metrics.on_station_state_change(sid, str(old_val), str(new_val), self._sim_time_s)
                if cid == "buffer":
                    self._metrics.on_buffer_state_change(str(old_val), str(new_val))
                self._prev_states[cid] = new_val

    def _step_orchestration(self) -> None:
        cfg = self.config
        comps = self.system.components

        # 按仿真时间更新各工位工人效率，用于模拟班次熟练度差异。 / Update worker efficiency by simulation time to model shift skill differences.
        current_eff = cfg.worker_efficiency_at_sim_time_seconds(self._sim_time_s)
        for sid in cfg.station_numbers:
            ds = comps.get(f"ds_{sid}")
            if ds is not None and hasattr(ds, "worker_efficiency"):
                ds.worker_efficiency = current_eff

        conveyor = comps["conveyor_motor"]
        elevator = comps["elevator"]
        buffer = comps["buffer"]
        ds1 = comps["ds_1"]
        pneumatic = comps["pneumatic"]
        rfid_queue = comps["rfid_queue"]
        rfid_elevator = comps["rfid_elevator"]

        # 0) Main-line transit arrivals
        kept_arrivals: List[Tuple[float, int, str]] = []
        for due_s, target_id, rid in self._pending_line_arrivals:
            if self._sim_time_s + 1e-9 < due_s:
                kept_arrivals.append((due_s, target_id, rid))
                continue
            target = comps[f"ds_{target_id}"]
            if getattr(target.state, "value", None) != "init":
                kept_arrivals.append((due_s, target_id, rid))
                continue
            target.pallet_arrived(rid)
            rfid_elevator.detect(rid)
            w = self._iface_windows.get(target_id)
            if w is not None:
                w.set_centered(True)
                s1, s2 = w.sensor_bits
                self._emit(
                    "event",
                    f"align_ds_{target_id}",
                    name="iface_window",
                    sensor_bits=[s1, s2],
                    centered=w.is_window_centered,
                )
            if target.accept_mission("2"):
                self._active_by_station[target_id] = rid
                self._elev_track[target_id] = _ElevatorTrack()
                self._emit("event", f"ds_{target_id}", name="mission_assigned", mission="2", pallet_id=rid)
        self._pending_line_arrivals = kept_arrivals

        # 0b) Egress transit arrivals（并行组装站完成后，回流到 DS6 输出口计产；不占用 ds_6 工位） / Completed pallets from parallel stations return to DS6 egress for counting without occupying ds_6 station
        kept_egress: List[Tuple[float, str, int]] = []
        for due_s, rid, source_sid in self._pending_egress_arrivals:
            if self._sim_time_s + 1e-9 < due_s:
                kept_egress.append((due_s, rid, source_sid))
                continue
            self._metrics.on_product_output(rid, self._sim_time_s)
            self._emit(
                "event",
                "ds_6_egress",
                name="product_output",
                pallet_id=rid,
                source_station=source_sid,
            )
        self._pending_egress_arrivals = kept_egress

        # 1) Ingress (Mission 3 -> buffer via DS1)
        for rid in self._ingress.tick(
            self._sim_time_s,
            ds1,
            max_pallets_on_line=self.config.max_pallets_on_line,
            get_pallet_count=self._count_pallets_on_line,
        ):
            self._emit("event", "ds_1", name="raw_batch_ingress", pallet_id=rid)

        # 2) RFID queue read
        if buffer.pallet_at_queue and buffer.pallet_rfid_at_queue and rfid_queue.state == RFIDState.IDLE:
            if rfid_queue.detect(buffer.pallet_rfid_at_queue):
                self._emit("event", "rfid_queue", name="rfid_queue_detect", tag=buffer.pallet_rfid_at_queue)

        # 3) Start pneumatic + conveyor
        if self._sim_time_s == 0.0:
            pneumatic.enable()
            self._emit("event", "pneumatic", name="pneumatic_enable")
        if self._sim_time_s >= 3.0 and not self._did_conveyor_started:
            conveyor.start(speed_percent=50.0)
            self._did_conveyor_started = True
            self._emit("event", "conveyor_motor", name="conveyor_start", speed_percent=50.0)

        # 4) Dispatch from buffer：并行产线 — 任一组装工位 [2,3,5,6] 为 INIT 且无在途指向该站即可发料 / Dispatch when any assembly station [2,3,5,6] is INIT and has no inbound transit
        if (
            buffer.pallet_at_queue
            and getattr(rfid_queue.state, "value", None) == "identified"
            and self._station_route
        ):
            n = len(self._station_route)
            for k in range(n):
                idx = (self._next_station_idx + k) % n
                target_id = self._station_route[idx]
                if any(tid == target_id for _, tid, _ in self._pending_line_arrivals):
                    continue
                target = comps[f"ds_{target_id}"]
                if getattr(target, "state", None).value == "init":
                    rid = buffer.pallet_rfid_at_queue
                    travel_s = conveyor_travel_time_ingress_to_station(cfg, target_id)
                    buffer.pallet_leaves()
                    rfid_queue.clear()
                    self._pending_line_arrivals.append((self._sim_time_s + travel_s, target_id, rid))
                    self._emit(
                        "event",
                        "conveyor_line",
                        name="transit_scheduled",
                        target_station=target_id,
                        seconds=travel_s,
                        pallet_id=rid,
                    )
                    self._next_station_idx = (idx + 1) % n
                    break

        # 5) Elevator choreography：每台组装工位独立升降机（components[f\"elevator_ds{sid}\"]） / Each assembly station uses an independent elevator (components[f\"elevator_ds{sid}\"])
        for sid in list(self._active_by_station.keys()):
            active = comps.get(f"ds_{sid}")
            if active is None:
                continue
            elev = comps.get(f"elevator_ds{sid}")
            if elev is None:
                elev = elevator
            tr = self._elev_track.setdefault(sid, _ElevatorTrack())

            if (
                not tr.did_elevator_receive_ping
                and active.state.value == "receiving"
                and elev.position == ElevatorPosition.DOWN
            ):
                elev.request_down()
                tr.did_elevator_receive_ping = True
                self._emit("event", f"elevator_ds{sid}", name="elevator_down_receive", station=sid)

            if (
                not tr.did_request_up
                and elev.position == ElevatorPosition.DOWN
                and active.state.value == "processing"
            ):
                elev.up_requested = False
                elev.down_requested = False
                elev.request_up()
                tr.did_request_up = True
                self._metrics.on_resource_wait_start(station_id=int(sid), sim_time_s=self._sim_time_s)
                self._emit("event", f"elevator_ds{sid}", name="elevator_up", station=sid)

            if (
                active.state.value == "processing"
                and elev.position == ElevatorPosition.UP
                and not elev.transfer_running
                and tr.transfer_to_ws_started_at is None
                and not tr.did_transfer_to_ws
            ):
                if elev.start_transfer(TransferDirection.TO_WS):
                    self._metrics.on_resource_transfer_started(station_id=int(sid), sim_time_s=self._sim_time_s)
                    tr.transfer_to_ws_started_at = self._sim_time_s
                    self._emit("event", f"elevator_ds{sid}", name="transfer_to_ws_start", station=sid)

            if (
                tr.transfer_to_ws_started_at is not None
                and elev.transfer_running
                and self._sim_time_s - tr.transfer_to_ws_started_at >= elev.transfer_time
            ):
                elev.stop_transfer()
                tr.transfer_to_ws_started_at = None
                tr.did_transfer_to_ws = True
                self._emit("event", f"elevator_ds{sid}", name="transfer_to_ws_stop", station=sid)

            if (
                not tr.did_request_down
                and elev.position == ElevatorPosition.UP
                and active.state.value in ("sending", "cleanup", "init")
                and tr.did_transfer_to_ws
            ):
                elev.up_requested = False
                elev.down_requested = False
                elev.request_down()
                tr.did_request_down = True
                self._metrics.on_resource_wait_start(station_id=int(sid), sim_time_s=self._sim_time_s)
                self._emit("event", f"elevator_ds{sid}", name="elevator_down", station=sid)

            if (
                active.state.value == "sending"
                and elev.position == ElevatorPosition.DOWN
                and not elev.transfer_running
                and tr.transfer_from_ws_started_at is None
                and not tr.did_transfer_from_ws
            ):
                if elev.start_transfer(TransferDirection.FROM_WS):
                    self._metrics.on_resource_transfer_started(station_id=int(sid), sim_time_s=self._sim_time_s)
                    tr.transfer_from_ws_started_at = self._sim_time_s
                    self._emit("event", f"elevator_ds{sid}", name="transfer_from_ws_start", station=sid)

            if (
                tr.transfer_from_ws_started_at is not None
                and elev.transfer_running
                and self._sim_time_s - tr.transfer_from_ws_started_at >= elev.transfer_time
            ):
                elev.stop_transfer()
                tr.transfer_from_ws_started_at = None
                tr.did_transfer_from_ws = True
                self._emit("event", f"elevator_ds{sid}", name="transfer_from_ws_stop", station=sid)

        # 6) Conveyor backpressure
        if buffer.state.value == "full":
            if conveyor.state == ConveyorMotorState.RUNNING:
                conveyor.stop()
                self._emit("event", "conveyor_motor", name="buffer_full_stop")
        else:
            if self._did_conveyor_started and conveyor.state.value == "idle":
                conveyor.start(speed_percent=50.0)
                self._emit("event", "conveyor_motor", name="conveyor_restart", speed_percent=50.0)

        # 7) Release station cycle（并行：每站独立） / Release station cycle (parallel: each station is independent)
        for sid in list(self._active_by_station.keys()):
            st = comps[f"ds_{sid}"]
            pallet_id = self._active_by_station.get(sid)
            if st.state.value == "init" and (not st.pallet_present) and (not st.pallet_at_ws):
                self._emit(
                    "event",
                    f"ds_{sid}",
                    name="station_cycle_done",
                    pallet_id=pallet_id,
                )
                w = self._iface_windows.get(int(sid))
                if w is not None:
                    w.clear()
                    self._emit(
                        "event",
                        f"align_ds_{sid}",
                        name="iface_window",
                        sensor_bits=[0, 0],
                        centered=False,
                    )
                if pallet_id:
                    egress_sid = int(self.config.ws_egress_station)
                    travel_s = conveyor_travel_time_seconds(cfg, int(sid), egress_sid)
                    due_s = self._sim_time_s + max(float(travel_s), 0.0)
                    self._pending_egress_arrivals.append((due_s, pallet_id, int(sid)))
                    self._emit(
                        "event",
                        "conveyor_line",
                        name="egress_transit_scheduled",
                        source_station=int(sid),
                        target_station=egress_sid,
                        seconds=float(travel_s),
                        pallet_id=pallet_id,
                    )
                if pallet_id is not None and rfid_elevator.tag_detected == pallet_id:
                    rfid_elevator.clear()
                del self._active_by_station[sid]
                self._elev_track.pop(sid, None)

    def step(self) -> None:
        self._step_orchestration()
        self.system.update(self._now())
        # WIP / lead-time ingress：在 Buffer 侧 RFID 完成识别后记账（而非 Mission3 刚下发时） / Book WIP/lead-time ingress after Buffer-side RFID is identified (not at Mission 3 dispatch)
        rfid_queue = self.system.components.get("rfid_queue")
        if rfid_queue is not None:
            old_rq = self._prev_states.get("rfid_queue")
            new_rq = getattr(rfid_queue.state, "value", None)
            if old_rq != "identified" and new_rq == "identified":
                tag = getattr(rfid_queue, "tag_detected", None)
                if tag:
                    self._metrics.on_ingress(str(tag), self._sim_time_s)
        self._capture_state_changes()

        buffer = self.system.components["buffer"]
        if self._metrics.maybe_sample(
            self._sim_time_s,
            buffer_count=getattr(buffer, "pallet_count", 0),
            buffer_capacity=getattr(buffer, "max_capacity", 1),
            wip_on_line=self._count_pallets_on_line(),
        ):
            self._emit(
                "performance_metric",
                "system_global",
                name="metrics_snapshot",
                details=self._metrics.snapshot(self._sim_time_s),
            )

        self._sim_time_s += float(self.config.timestep_seconds)

    def run(self) -> None:
        total_seconds = float(self.config.duration_hours) * 3600.0
        steps = int(total_seconds / float(self.config.timestep_seconds))
        for _ in range(steps):
            self.step()
