"""Tests for OutputInputSubscriber - TDD Red Phase.

These tests define the expected behavior of the OutputInputSubscriber
before any implementation exists. All tests should fail initially.
"""

import json
from unittest.mock import MagicMock

import pytest

from apelios.output.output_input_subscriber import OutputInputSubscriber


@pytest.fixture
def mock_core():
    """Provide a mocked OutputCore."""
    return MagicMock()


@pytest.fixture
def subscriber(mock_core):
    """Provide an OutputInputSubscriber with mocked core."""
    return OutputInputSubscriber(mock_core)


class TestOutputInputSubscriberParsing:
    """Tests for topic and payload parsing."""

    def test_subscriber_parses_topic_correctly(self, mock_core):
        """Subscriber should parse topic like 'output.1.42' correctly."""
        subscriber = OutputInputSubscriber(mock_core)
        
        # Test valid topic parsing
        payload = json.dumps({"universe": 1, "address": 42, "value": 135}).encode()
        subscriber("output.1.42", payload)
        
        # Verify core was called with correct values
        mock_core.add_to_buffer.assert_called_once_with(
            universe=1, address=42, value=135
        )

    def test_subscriber_parses_payload_correctly(self, mock_core):
        """Subscriber should correctly parse JSON payload."""
        subscriber = OutputInputSubscriber(mock_core)
        
        # Test with different values
        payload = json.dumps({"universe": 2, "address": 100, "value": 255}).encode()
        subscriber("output.2.100", payload)
        
        mock_core.add_to_buffer.assert_called_once_with(
            universe=2, address=100, value=255
        )

    def test_subscriber_calls_core_add_to_buffer(self, mock_core):
        """Subscriber should call core.add_to_buffer() with correct arguments."""
        subscriber = OutputInputSubscriber(mock_core)
        
        payload = json.dumps({"universe": 5, "address": 20, "value": 100}).encode()
        subscriber("output.5.20", payload)
        
        mock_core.add_to_buffer.assert_called_once()
        call_args = mock_core.add_to_buffer.call_args
        assert call_args.kwargs["universe"] == 5
        assert call_args.kwargs["address"] == 20
        assert call_args.kwargs["value"] == 100


class TestOutputInputSubscriberErrorHandling:
    """Tests for error handling."""

    def test_subscriber_handles_invalid_topic(self, mock_core):
        """Subscriber should handle invalid topic formats gracefully."""
        subscriber = OutputInputSubscriber(mock_core)
        
        # Test with invalid topic (not following output.<universe>.<address>)
        payload = json.dumps({"universe": 1, "address": 42, "value": 135}).encode()
        
        # Should not raise an error even with invalid topic
        subscriber("invalid.topic", payload)
        
        # Should still parse payload and call core
        mock_core.add_to_buffer.assert_called_once()

    def test_subscriber_handles_missing_fields(self, mock_core):
        """Subscriber should validate payload structure and handle missing fields."""
        subscriber = OutputInputSubscriber(mock_core)
        
        # Test with missing universe field
        payload = json.dumps({"address": 42, "value": 135}).encode()
        subscriber("output.1.42", payload)
        
        # Should not call core if required fields are missing
        mock_core.add_to_buffer.assert_not_called()

    def test_subscriber_handles_invalid_json(self, mock_core):
        """Subscriber should handle invalid JSON payload gracefully."""
        subscriber = OutputInputSubscriber(mock_core)
        
        # Test with invalid JSON
        subscriber("output.1.42", b"invalid json")
        
        # Should not call core with invalid JSON
        mock_core.add_to_buffer.assert_not_called()

    def test_subscriber_handles_empty_payload(self, mock_core):
        """Subscriber should handle empty payload gracefully."""
        subscriber = OutputInputSubscriber(mock_core)
        
        # Test with empty payload
        subscriber("output.1.42", b"")
        
        # Should not call core with empty payload
        mock_core.add_to_buffer.assert_not_called()

    def test_subscriber_handles_missing_universe(self, mock_core):
        """Subscriber should handle missing universe field."""
        subscriber = OutputInputSubscriber(mock_core)
        
        payload = json.dumps({"address": 42, "value": 135}).encode()
        subscriber("output.1.42", payload)
        
        mock_core.add_to_buffer.assert_not_called()

    def test_subscriber_handles_missing_address(self, mock_core):
        """Subscriber should handle missing address field."""
        subscriber = OutputInputSubscriber(mock_core)
        
        payload = json.dumps({"universe": 1, "value": 135}).encode()
        subscriber("output.1.42", payload)
        
        mock_core.add_to_buffer.assert_not_called()

    def test_subscriber_handles_missing_value(self, mock_core):
        """Subscriber should handle missing value field."""
        subscriber = OutputInputSubscriber(mock_core)
        
        payload = json.dumps({"universe": 1, "address": 42}).encode()
        subscriber("output.1.42", payload)
        
        mock_core.add_to_buffer.assert_not_called()