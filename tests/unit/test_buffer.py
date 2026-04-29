import pytest

from src.mock_up.components import Buffer, BufferState


class TestBufferTransitions:
    """Test Buffer queue/storage transitions."""

    def test_initial_state_empty(self):
        """Verify: 初始为空状态 EMPTY"""
        buf = Buffer(id="buf1", max_capacity=2, transfer_time=2.0)
        assert buf.state == BufferState.EMPTY
        assert buf.pallet_count == 0
        assert buf.pallet_at_queue is False

    def test_queue_pallet_enters_and_add_to_buffer_in_then_update(self):
        """Verify: pallet_enters -> add_to_buffer(IN) -> update => PARTIAL"""
        buf = Buffer(id="buf1", max_capacity=2, transfer_time=2.0)

        assert buf.pallet_enters("TAG_001") is True
        assert buf.pallet_at_queue is True
        assert buf.pallet_rfid_at_queue == "TAG_001"

        assert buf.add_to_buffer() is True
        assert buf.is_transferring is True
        assert buf.transfer_direction == "in"

        buf.update(elapsed_time=2.0)
        assert buf.is_transferring is False
        assert buf.pallet_count == 1
        assert buf.state == BufferState.PARTIAL
        assert buf.pallet_at_queue is False
        assert buf.pallet_rfid_at_queue is None
        assert buf.stored_rfids == ["TAG_001"]

    def test_buffer_transfer_out_to_queue(self):
        """Verify: remove_from_buffer(OUT) -> update => queue has pallet and EMPTY state"""
        buf = Buffer(id="buf1", max_capacity=2, transfer_time=2.0)
        buf.pallet_enters("TAG_001")
        assert buf.add_to_buffer() is True
        buf.update(elapsed_time=2.0)  # now pallet_count=1 and queue empty

        assert buf.pallet_at_queue is False
        assert buf.pallet_count == 1

        assert buf.remove_from_buffer() is True
        assert buf.is_transferring is True
        assert buf.transfer_direction == "out"

        buf.update(elapsed_time=2.0)
        assert buf.is_transferring is False
        assert buf.pallet_count == 0
        assert buf.state == BufferState.EMPTY
        assert buf.pallet_at_queue is True
        assert buf.pallet_rfid_at_queue == "TAG_001"
        assert buf.stored_rfids == []

    def test_pallet_enters_refused_when_queue_occupied(self):
        """Verify: queue already has pallet => pallet_enters() returns False"""
        buf = Buffer(id="buf1", max_capacity=2, transfer_time=2.0)
        assert buf.pallet_enters("TAG_001") is True
        assert buf.pallet_enters("TAG_002") is False

