import pytest

from src.mock_up.components import RFIDReader, RFIDState


class TestRFIDReaderTransitions:
    """Test RFIDReader detection/clear transitions."""

    def test_detect_idle_to_detecting_and_identified(self):
        """Verify: IDLE -> DETECTING -> IDENTIFIED on detect()+update()"""
        rfid = RFIDReader(id="r1", location="queue", detection_delay=0.5)
        assert rfid.state == RFIDState.IDLE

        assert rfid.detect("TAG_001") is True
        assert rfid.state == RFIDState.DETECTING
        assert rfid.tag_detected == "TAG_001"

        rfid.update(elapsed_time=0.49)
        assert rfid.state == RFIDState.DETECTING

        rfid.update(elapsed_time=0.5)
        assert rfid.state == RFIDState.IDENTIFIED
        assert rfid.detect_start_time is None

    def test_detect_refused_when_not_idle(self):
        """Verify: DETECTING 状态下再次 detect() 返回 False"""
        rfid = RFIDReader(id="r1", location="queue", detection_delay=0.5)
        assert rfid.detect("TAG_001") is True
        assert rfid.detect("TAG_002") is False

    def test_clear_resets_to_idle(self):
        """Verify: clear() -> IDLE and tag cleared"""
        rfid = RFIDReader(id="r1", location="queue", detection_delay=0.5)
        assert rfid.detect("TAG_001") is True
        rfid.update(elapsed_time=0.5)
        assert rfid.state == RFIDState.IDENTIFIED

        rfid.clear()
        assert rfid.state == RFIDState.IDLE
        assert rfid.tag_detected is None
        assert rfid.detect_start_time is None

