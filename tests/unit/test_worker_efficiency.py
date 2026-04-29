from src.mock_up.components import DockingStation
from src.mock_up.config import SimulationConfig


class TestWorkerEfficiency:
    def test_shift_efficiency_lookup_supports_cross_midnight(self):
        cfg = SimulationConfig(
            worker_efficiency_base=1.0,
            worker_efficiency_shifts=[
                (6.0, 14.0, 1.10),   # morning shift
                (14.0, 22.0, 1.00),  # evening shift
                (22.0, 6.0, 0.85),   # night shift (cross-midnight)
            ],
        )
        assert cfg.worker_efficiency_at_sim_time_seconds(7 * 3600) == 1.10
        assert cfg.worker_efficiency_at_sim_time_seconds(15 * 3600) == 1.00
        assert cfg.worker_efficiency_at_sim_time_seconds(23 * 3600) == 0.85
        assert cfg.worker_efficiency_at_sim_time_seconds(2 * 3600) == 0.85

    def test_worker_efficiency_scales_assembly_duration(self):
        ds = DockingStation(
            id="ds_eff",
            station_number=2,
            assembly_time_min_seconds=120.0,
            assembly_time_max_seconds=900.0,
            assembly_duration_distribution="deterministic",
            worker_efficiency=1.25,
        )
        # deterministic base = (120 + 900) / 2 = 510s, then divided by efficiency
        assert ds._sample_assembly_duration_seconds() == 408.0

    def test_uniform_distribution_respects_range(self):
        ds = DockingStation(
            id="ds_uniform",
            station_number=3,
            assembly_time_min_seconds=180.0,
            assembly_time_max_seconds=600.0,
            assembly_duration_distribution="uniform",
            worker_efficiency=1.0,
        )
        for _ in range(100):
            val = ds._sample_assembly_duration_seconds()
            assert 180.0 <= val <= 600.0

