import json
import pytest
from unittest.mock import MagicMock
from nats.aio.msg import Msg

from apelios.middleware.middleware_core import MappingMiddleware
from apelios.middleware.middleware_input_subscriber import MiddlewareInputSubscriber


@pytest.fixture
def mock_profile():
    """Standard mock profile for testing."""
    return {
        "fader.1": {"target": "group1.dimmer", "type": "absolute"},
        "mouse.x": {"target": "group1.pan", "type": "absolute_to_delta", "sensitivity": 0.01}
    }


@pytest.fixture
def middleware_core(mock_profile):
    """MappingMiddleware instance."""
    return MappingMiddleware(profile=mock_profile)


@pytest.fixture
def subscriber(middleware_core):
    """MiddlewareInputSubscriber instance."""
    return MiddlewareInputSubscriber(middleware_core)


def test_subscriber_created_with_injected_core(middleware_core):
    """Subscriber accepts injected middleware core."""
    subscriber = MiddlewareInputSubscriber(middleware_core)
    assert subscriber.middleware is middleware_core


def test_subscriber_accepts_valid_json_payload(subscriber, middleware_core):
    """Subscriber parses valid JSON and calls middleware.handle_input()."""
    # Create a mock Msg object
    msg = MagicMock(spec=Msg)
    msg.subject = "input.fader.1"
    msg.data = json.dumps({"source": "fader.1", "value": 0.75}).encode()
    
    # Call the subscriber callback
    subscriber(msg)
    
    # Verify middleware was updated
    assert middleware_core.current_raw_input["fader.1"] == 0.75


def test_subscriber_extracts_source_from_payload(subscriber, middleware_core):
    """Subscriber uses source from JSON payload, not subject."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.some.topic"
    msg.data = json.dumps({"source": "custom.source", "value": 0.5}).encode()
    
    subscriber(msg)
    
    # Should use source from payload, not subject
    assert "custom.source" in middleware_core.current_raw_input
    assert middleware_core.current_raw_input["custom.source"] == 0.5


def test_subscriber_coerces_value_to_float(subscriber, middleware_core):
    """Subscriber coerces numeric value to float."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"source": "test", "value": 10}).encode()  # int
    
    subscriber(msg)
    
    assert isinstance(middleware_core.current_raw_input["test"], float)
    assert middleware_core.current_raw_input["test"] == 10.0


def test_subscriber_rejects_missing_source(subscriber, middleware_core):
    """Subscriber safely ignores payload missing 'source' field."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"value": 0.5}).encode()  # missing source
    
    # Should not raise
    subscriber(msg)
    
    # Should not update middleware
    assert "test" not in middleware_core.current_raw_input


def test_subscriber_rejects_missing_value(subscriber, middleware_core):
    """Subscriber safely ignores payload missing 'value' field."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"source": "test"}).encode()  # missing value
    
    # Should not raise
    subscriber(msg)
    
    # Should not update middleware
    assert "test" not in middleware_core.current_raw_input


def test_subscriber_rejects_malformed_json(subscriber, middleware_core):
    """Subscriber safely ignores malformed JSON."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = b"not valid json {{"
    
    # Should not raise
    subscriber(msg)
    
    # Should not update middleware
    assert len(middleware_core.current_raw_input) == 0


def test_subscriber_rejects_non_numeric_value(subscriber, middleware_core):
    """Subscriber safely ignores non-numeric value."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"source": "test", "value": "not_a_number"}).encode()
    
    # Should not raise
    subscriber(msg)
    
    # Should not update middleware
    assert "test" not in middleware_core.current_raw_input


def test_subscriber_ignores_extra_fields(subscriber, middleware_core):
    """Subscriber ignores optional metadata fields."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({
        "source": "test",
        "value": 0.5,
        "timestamp": 1234567890,
        "metadata": {"key": "value"}
    }).encode()
    
    # Should not raise
    subscriber(msg)
    
    # Should extract and use source and value only
    assert middleware_core.current_raw_input["test"] == 0.5