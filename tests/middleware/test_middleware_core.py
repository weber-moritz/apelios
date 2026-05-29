import pytest
from apelios.middleware.middleware_core import MappingMiddleware


@pytest.fixture
def middleware():
    """Fixture with passthrough mapping (no math applied)."""
    mock_profile = {
        "fader.1": {
            "target": "group1.dimmer",
            "intent": "absolute",
        },
        "mouse.x": {
            "target": "group1.pan",
            "intent": "delta",
            "sensitivity": 0.01,  # Ignored in MVP
        },
        "joystick.1": {
            "target": "group1.tilt",
            "intent": "rate",
            "sensitivity": 0.4,  # Ignored in MVP
            "deadzone": 0.05,  # Ignored in MVP
        },
    }
    return MappingMiddleware(profile=mock_profile)


def test_core_absolute_passthrough(middleware):
    """Test that absolute intent values are passed through unchanged."""
    middleware.handle_input(source="fader.1", value=0.75)
    assert "group1.dimmer" not in middleware.enriched_outputs

    middleware.process_frame(dt=0.016)
    
    # Check that enriched payload is created
    assert "group1.dimmer" in middleware.enriched_outputs
    enriched = middleware.enriched_outputs["group1.dimmer"]
    
    # Verify payload structure
    assert enriched["target"] == "group1.dimmer"
    assert enriched["value"] == 0.75  # Raw value, no processing
    assert enriched["intent"] == "absolute"
    assert "timestamp" in enriched


def test_core_delta_passthrough_no_math(middleware):
    """Test that delta intent values are passed through without delta math."""
    # Middleware should NOT apply delta math. That's the fixture layer's job.
    middleware.handle_input(source="mouse.x", value=0.5)
    middleware.process_frame(dt=0.016)
    
    enriched = middleware.enriched_outputs.get("group1.pan")
    assert enriched is not None
    assert enriched["target"] == "group1.pan"
    assert enriched["value"] == 0.5  # Raw passthrough, no delta calculation
    assert enriched["intent"] == "delta"


def test_core_rate_passthrough_no_integration(middleware):
    """Test that rate intent values are passed through without time integration."""
    # Middleware should NOT apply rate/time math. That's the fixture layer's job.
    middleware.handle_input(source="joystick.1", value=0.8)
    middleware.process_frame(dt=0.016)
    
    enriched = middleware.enriched_outputs.get("group1.tilt")
    assert enriched is not None
    assert enriched["target"] == "group1.tilt"
    assert enriched["value"] == 0.8  # Raw passthrough, no time integration
    assert enriched["intent"] == "rate"


def test_core_multiple_sources_in_one_frame(middleware):
    """Test that multiple sources are all mapped in one frame."""
    middleware.handle_input(source="fader.1", value=0.5)
    middleware.handle_input(source="mouse.x", value=0.3)
    middleware.handle_input(source="joystick.1", value=-0.2)
    
    middleware.process_frame(dt=0.016)
    
    # All three should be enriched
    assert len(middleware.enriched_outputs) == 3
    assert middleware.enriched_outputs["group1.dimmer"]["value"] == 0.5
    assert middleware.enriched_outputs["group1.pan"]["value"] == 0.3
    assert middleware.enriched_outputs["group1.tilt"]["value"] == -0.2


def test_core_backward_compat_virtual_output_state(middleware):
    """Test that virtual_output_state still receives raw values for backward compatibility."""
    middleware.handle_input(source="fader.1", value=0.75)
    middleware.process_frame(dt=0.016)
    
    # Old code may still rely on virtual_output_state containing raw values
    assert middleware.virtual_output_state["group1.dimmer"] == 0.75


def test_core_transient_input_buffer_cleared_each_frame(middleware):
    """Test that the input buffer is cleared after each frame."""
    middleware.handle_input(source="fader.1", value=0.5)
    middleware.process_frame(dt=0.016)
    
    # Buffer should be empty after process_frame
    assert len(middleware.current_raw_input) == 0
    
    # Next frame with no new input should produce no enriched outputs
    middleware.process_frame(dt=0.016)
    assert len(middleware.enriched_outputs) == 0


def test_core_no_clamping_in_middleware(middleware):
    """Test that middleware does NOT clamp values."""
    # Middleware passes raw values through unchanged, even if out of 0-1 range
    middleware.handle_input(source="mouse.x", value=5.0)  # Way outside [0, 1]
    middleware.process_frame(dt=0.016)
    
    enriched = middleware.enriched_outputs["group1.pan"]
    assert enriched["value"] == 5.0  # No clamping in middleware


def test_core_unmapped_sources_ignored(middleware):
    """Test that sources without a mapping are ignored."""
    middleware.handle_input(source="fader.1", value=0.5)
    middleware.handle_input(source="unmapped.source", value=0.9)  # Not in profile
    middleware.process_frame(dt=0.016)
    
    # Only the mapped source should be in enriched_outputs
    assert len(middleware.enriched_outputs) == 1
    assert "group1.dimmer" in middleware.enriched_outputs
    # unmapped source should not create output