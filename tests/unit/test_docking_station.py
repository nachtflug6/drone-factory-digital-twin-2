import pytest

from src.mock_up.components import (
    DockingStation,
    DockingStationState,
)


class TestDockingStationTransitions:
    """Test DockingStation SFC-like transitions."""

    def test_mission_2_to_ws_then_operator_complete_then_cleanup_to_init(self):
        """Verify: INIT -> AWAITING_MISSION -> RECEIVING(mission2) -> PROCESSING -> SENDING -> CLEANUP -> INIT"""
        ds = DockingStation(
            id="ds1",
            station_number=1,
            time_wait_at_queue=10.0,
            transfer_time=2.0,
            allow_auto_pass=False,
        )

        # INIT -> AWAITING_MISSION
        ds.pallet_arrived("TAG_001")
        assert ds.state == DockingStationState.AWAITING_MISSION
        assert ds.pallet_present is True
        assert ds.current_mission is None

        # AWAITING_MISSION -> RECEIVING (mission 2)
        ok = ds.accept_mission("2")
        assert ok is True
        assert ds.state == DockingStationState.RECEIVING
        assert ds.current_mission == "2"

        # RECEIVING -> PROCESSING
        ds.update(elapsed_time=2.0)
        assert ds.state == DockingStationState.PROCESSING
        assert ds.pallet_present is False
        assert ds.pallet_at_ws is True
        assert ds.current_mission == "2"

        # PROCESSING -> SENDING (operator complete); internal send-out marker (not Mission 3)
        ds.complete_processing()
        assert ds.state == DockingStationState.SENDING
        assert ds.current_mission == "_ws_sendout"

        # SENDING -> CLEANUP
        ds.update(elapsed_time=2.0)
        assert ds.state == DockingStationState.CLEANUP

        # CLEANUP -> INIT
        ds.update(elapsed_time=0.5)
        assert ds.state == DockingStationState.INIT
        assert ds.current_mission is None

    def test_auto_pass_from_awaiting_mission_to_receiving_mission_1(self):
        """Verify: AWAITING_MISSION 超时触发 accept_mission('1') -> RECEIVING"""
        ds = DockingStation(
            id="ds1",
            station_number=1,
            time_wait_at_queue=1.0,
            transfer_time=2.0,
            allow_auto_pass=True,
        )

        ds.pallet_arrived("TAG_001")
        assert ds.state == DockingStationState.AWAITING_MISSION

        # Enough elapsed time triggers auto accept_mission("1")
        ds.update(elapsed_time=1.1)
        assert ds.state == DockingStationState.RECEIVING
        assert ds.current_mission == "1"

