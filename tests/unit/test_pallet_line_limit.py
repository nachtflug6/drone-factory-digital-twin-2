"""Tests for max pallets on line (count + ingress gate)."""

from src.mock_up.components import DockingStationState, create_ws_conveyor_system
from src.mock_up.config import SimulationConfig
from src.mock_up.logic import RawMaterialIngressScheduler, count_pallets_on_line


def test_count_pallets_on_line_includes_buffer_and_pending():
    cfg = SimulationConfig()
    comps = create_ws_conveyor_system(cfg)
    assert count_pallets_on_line(comps, [], cfg.station_numbers) == 0
    assert count_pallets_on_line(comps, [object(), object()], cfg.station_numbers) == 2


def test_ingress_no_new_batch_when_line_full_and_ds_blocked():
    """满场时不再按间隔追加 pending；DS1 无法接收时仅验证批次追加被跳过。"""

    class FakeDS1:
        state = DockingStationState.INIT

        def accept_mission(self, *args, **kwargs):
            return False

    ingress = RawMaterialIngressScheduler(1.0, pallets_per_batch=1)
    ds1 = FakeDS1()

    ingress.tick(0.0, ds1, max_pallets_on_line=2, get_pallet_count=lambda: 0)
    assert len(ingress.pending_rfids) == 1

    ingress.tick(1.0, ds1, max_pallets_on_line=2, get_pallet_count=lambda: 2)
    assert len(ingress.pending_rfids) == 1


def test_ingress_inner_loop_skips_accept_when_at_max():
    class FakeDS1:
        state = DockingStationState.INIT
        accepts = 0

        def accept_mission(self, *args, **kwargs):
            self.accepts += 1
            return True

    ingress = RawMaterialIngressScheduler(1000.0, pallets_per_batch=1)
    ingress.pending_rfids.append("RAW_000001")
    ds1 = FakeDS1()

    ingress.tick(
        0.0,
        ds1,
        max_pallets_on_line=1,
        get_pallet_count=lambda: 1,
    )
    assert ds1.accepts == 0
    assert ingress.pending_rfids  # still queued
