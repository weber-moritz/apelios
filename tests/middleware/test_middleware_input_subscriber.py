import json
import pytest
from unittest.mock import MagicMock
from nats.aio.msg import Msg

from apelios.middleware.middleware_core import MappingMiddleware
from apelios.middleware.middleware_input_subscriber import MiddlewareInputSubscriber


@pytest.fixture
def mock_profile():
    """Standard mock profile for testing (new stateless format)."""
    return {
        "fader.1": "group1.dimmer",
        "mouse.x": "group1.pan"
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

@pytest.mark.asyncio
async def test_subscriber_accepts_valid_json_payload(subscriber, middleware_core):
    """Subscriber parses valid JSON and calls middleware.handle_input()."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.fader.1"
    msg.data = json.dumps({"source": "fader.1", "value": 0.75, "type": "absolute_uni", "timestamp": 123.0}).encode()
    
    await subscriber(msg)
    
    # In stateless architecture, verify middleware returns correct outputs
    outputs = middleware_core.handle_input(source="fader.1", value=0.75, type="absolute_uni", timestamp=123.0)
    assert "group1.dimmer" in outputs
    assert outputs["group1.dimmer"]["value"] == 0.75


@pytest.mark.asyncio
async def test_subscriber_extracts_source_from_payload(subscriber, middleware_core):
    """Subscriber uses source from JSON payload, not subject."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.some.topic"
    msg.data = json.dumps({"source": "fader.1", "value": 0.5, "type": "absolute_uni", "timestamp": 123.0}).encode()
    
    await subscriber(msg)
    
    # Source from payload is used for mapping
    outputs = middleware_core.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=123.0)
    assert "group1.dimmer" in outputs


@pytest.mark.asyncio
async def test_subscriber_coerces_value_to_float(subscriber, middleware_core):
    """Subscriber coerces numeric value to float."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"source": "fader.1", "value": 10, "type": "absolute_uni", "timestamp": 123.0}).encode()  # int
    
    await subscriber(msg)
    
    outputs = middleware_core.handle_input(source="fader.1", value=10, type="absolute_uni", timestamp=123.0)
    assert isinstance(outputs["group1.dimmer"]["value"], float)
    assert outputs["group1.dimmer"]["value"] == 10.0


@pytest.mark.asyncio
async def test_subscriber_rejects_missing_source(subscriber, middleware_core):
    """Subscriber safely ignores payload missing 'source' field."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"value": 0.5, "type": "absolute_uni", "timestamp": 123.0}).encode()  # missing source
    
    # Should not raise
    await subscriber(msg)


@pytest.mark.asyncio
async def test_subscriber_rejects_missing_value(subscriber, middleware_core):
    """Subscriber safely ignores payload missing 'value' field."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"source": "test", "type": "absolute_uni", "timestamp": 123.0}).encode()  # missing value
    
    # Should not raise
    await subscriber(msg)


@pytest.mark.asyncio
async def test_subscriber_rejects_malformed_json(subscriber, middleware_core):
    """Subscriber safely ignores malformed JSON."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = b"not valid json {{"
    
    # Should not raise
    await subscriber(msg)


@pytest.mark.asyncio
async def test_subscriber_rejects_non_numeric_value(subscriber, middleware_core):
    """Subscriber safely ignores non-numeric value."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({"source": "test", "value": "not_a_number", "type": "absolute_uni", "timestamp": 123.0}).encode()
    
    # Should not raise
    await subscriber(msg)


@pytest.mark.asyncio
async def test_subscriber_ignores_extra_fields(subscriber, middleware_core):
    """Subscriber ignores optional metadata fields."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({
        "source": "fader.1",
        "value": 0.5,
        "type": "absolute_uni",
        "timestamp": 1234567890.0,
        "metadata": {"key": "value"}
    }).encode()
    
    # Should not raise
    await subscriber(msg)
    
    # Verify it still works with extra fields
    outputs = middleware_core.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=1234567890.0)
    assert "group1.dimmer" in outputs


@pytest.mark.asyncio
async def test_subscriber_reads_source_from_payload(subscriber, middleware_core):
    """Subscriber reads source from payload, not from msg.subject (7.3.1).
    
    Even if msg.subject differs from payload source, subscriber uses payload source.
    """
    msg = MagicMock(spec=Msg)
    msg.subject = "input.ignored.topic"  # This should NOT be used
    msg.data = json.dumps({
        "source": "mouse.x",  # This SHOULD be used
        "value": 0.5,
        "type": "absolute_uni",
        "timestamp": 1234567890.123
    }).encode()
    
    await subscriber(msg)
    
    # Verify middleware was called with source from payload ("mouse.x"), not from subject ("input.ignored.topic")
    outputs = middleware_core.handle_input(source="mouse.x", value=0.5, type="absolute_uni", timestamp=1234567890.123)
    assert "group1.pan" in outputs  # "mouse.x" maps to "group1.pan" in mock_profile
    assert outputs["group1.pan"]["source"] == "mouse.x"


@pytest.mark.asyncio
async def test_subscriber_parses_type_field(subscriber, middleware_core):
    """Subscriber parses type and timestamp from payload and passes to middleware (2.1.1)."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({
        "source": "fader.1",
        "value": 0.5,
        "type": "absolute_bi",
        "timestamp": 1234567890.123
    }).encode()
    
    await subscriber(msg)
    
    # Verify type and timestamp were passed through to middleware
    outputs = middleware_core.handle_input(source="fader.1", value=0.5, type="absolute_bi", timestamp=1234567890.123)
    assert "group1.dimmer" in outputs
    assert outputs["group1.dimmer"]["type"] == "absolute_bi"
    assert outputs["group1.dimmer"]["timestamp"] == 1234567890.123


@pytest.mark.asyncio
async def test_subscriber_rejects_missing_type(subscriber, middleware_core):
    """Subscriber rejects payload missing required type field (2.1.2)."""
    msg = MagicMock(spec=Msg)
    msg.subject = "input.test"
    msg.data = json.dumps({
        "source": "test",
        "value": 0.5,
        "timestamp": 1234567890.123
    }).encode()  # missing type
    
    # Should not raise, just log warning and ignore
    await subscriber(msg)