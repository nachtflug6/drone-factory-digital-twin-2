import pytest

from src.mock_up.components import PneumaticSystem, PneumaticState


class TestPneumaticSystemTransitions:
    """Test PneumaticSystem key transitions."""

    def test_enable_stabilizing_to_normal(self):
        """Verify: OFF -> STABILIZING -> NORMAL"""
        pneu = PneumaticSystem(
            id="p1",
            target_pressure_bar=6.0,
            min_pressure_bar=5.5,
            max_pressure_bar=7.0,
            max_flow_nm3h=15.0,
            stabilization_time=2.0,
        )
        assert pneu.state == PneumaticState.OFF
        assert pneu.is_enabled is False

        pneu.enable()
        assert pneu.is_enabled is True
        assert pneu.state == PneumaticState.STABILIZING

        pneu.update(elapsed_time=2.0)
        assert pneu.state == PneumaticState.NORMAL
        assert pneu.current_pressure_bar == pneu.target_pressure_bar

    def test_enable_and_disable_resets_pressure(self):
        """Verify: disable() -> OFF 且压力/流量归零"""
        pneu = PneumaticSystem(
            id="p1",
            target_pressure_bar=6.0,
            min_pressure_bar=5.5,
            max_pressure_bar=7.0,
            max_flow_nm3h=15.0,
            stabilization_time=2.0,
        )
        pneu.enable()
        pneu.update(elapsed_time=2.0)
        assert pneu.state == PneumaticState.NORMAL

        pneu.disable()
        assert pneu.state == PneumaticState.OFF
        assert pneu.current_pressure_bar == 0.0
        assert pneu.current_flow_nm3h == 0.0

    def test_fault_flow_causes_leak_detected(self):
        """Verify: NORMAL 中流量超限 -> LEAK_DETECTED（分两步 update）"""
        pneu = PneumaticSystem(
            id="p1",
            target_pressure_bar=6.0,
            min_pressure_bar=5.5,
            max_pressure_bar=7.0,
            max_flow_nm3h=0.1,  # normal flow becomes 0.5 => trigger leak
            stabilization_time=2.0,
        )
        pneu.enable()
        pneu.update(elapsed_time=2.0)
        # After stabilization, state becomes NORMAL in this call.
        assert pneu.state == PneumaticState.NORMAL

        # Next update cycle should check faults in NORMAL branch.
        pneu.update(elapsed_time=0.0)
        assert pneu.state == PneumaticState.LEAK_DETECTED

