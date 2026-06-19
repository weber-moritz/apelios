import pytest
from apelios.middleware.middleware_core import MappingMiddleware


@pytest.fixture
def middleware():
    """Fixture with pure passthrough routing (stateless, no intent in config)."""
    mock_profile = {
        "fader.1": "group1.dimmer",
        "mouse.x": "group1.pan",
        "joystick.1": "group1.tilt",
    }
    return MappingMiddleware(profile=mock_profile)


def test_core_passes_type_unchanged(middleware):
    """Test that type from input layer flows through unchanged (Phase 5/6)."""
    outputs = middleware.handle_input(source="fader.1", value=0.75, type="absolute_uni", timestamp=123.0)
    assert outputs == {"group1.dimmer": {"value": 0.75, "type": "absolute_uni", "timestamp": 123.0, "source": "fader.1"}}


def test_core_has_no_state_dicts(middleware):
    """Test that middleware has NO state dictionaries."""
    assert not hasattr(middleware, 'current_raw_input')
    assert not hasattr(middleware, 'virtual_output_state')
    assert not hasattr(middleware, 'enriched_outputs')


def test_core_processes_immediately(middleware):
    """Test that inputs are processed immediately, not batched in process_frame."""
    outputs = middleware.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=100.0)
    assert "group1.dimmer" in outputs
    assert outputs["group1.dimmer"]["value"] == 0.5


def test_core_absolute_passthrough(middleware):
    """Test that absolute type values are passed through unchanged."""
    outputs = middleware.handle_input(source="fader.1", value=0.75, type="absolute_uni", timestamp=123.0)
    assert "group1.dimmer" in outputs
    assert outputs["group1.dimmer"]["value"] == 0.75
    assert outputs["group1.dimmer"]["type"] == "absolute_uni"


def test_core_delta_passthrough_no_math(middleware):
    """Test that delta type values are passed through without delta math."""
    outputs = middleware.handle_input(source="mouse.x", value=0.5, type="delta", timestamp=124.0)
    assert "group1.pan" in outputs
    assert outputs["group1.pan"]["value"] == 0.5
    assert outputs["group1.pan"]["type"] == "delta"


def test_core_rate_passthrough_no_integration(middleware):
    """Test that rate type values are passed through without time integration."""
    outputs = middleware.handle_input(source="joystick.1", value=0.8, type="rate", timestamp=125.0)
    assert "group1.tilt" in outputs
    assert outputs["group1.tilt"]["value"] == 0.8
    assert outputs["group1.tilt"]["type"] == "rate"


def test_core_multiple_sources_in_one_call(middleware):
    """Test that multiple sources can be handled independently."""
    out1 = middleware.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=100.0)
    out2 = middleware.handle_input(source="mouse.x", value=0.3, type="delta", timestamp=101.0)
    out3 = middleware.handle_input(source="joystick.1", value=-0.2, type="rate", timestamp=102.0)
    
    assert "group1.dimmer" in out1
    assert "group1.pan" in out2
    assert "group1.tilt" in out3


def test_core_no_clamping_in_middleware(middleware):
    """Test that middleware does NOT clamp values."""
    outputs = middleware.handle_input(source="mouse.x", value=5.0, type="delta", timestamp=100.0)
    assert outputs["group1.pan"]["value"] == 5.0


def test_core_unmapped_sources_ignored(middleware):
    """Test that sources without a mapping are ignored."""
    outputs = middleware.handle_input(source="unmapped.source", value=0.9, type="absolute_uni", timestamp=100.0)
    assert outputs == {}


def test_core_profile_only_has_source_to_target(middleware):
    """Test that profile only contains source->target mapping, no intent/sensitivity."""
    assert middleware.profile == {
        "fader.1": "group1.dimmer",
        "mouse.x": "group1.pan",
        "joystick.1": "group1.tilt",
    }


def test_core_returns_outputs_dict(middleware):
    """Test that handle_input returns a dict of outputs."""
    outputs = middleware.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=100.0)
    assert isinstance(outputs, dict)


def test_core_no_process_frame_method(middleware):
    """Test that there is no process_frame method."""
    assert not hasattr(middleware, 'process_frame')


def test_core_includes_source_in_output(middleware):
    """Test that source field is included in output payload (Phase 6.1.1).
    
    For many-to-one input summation, the fixture layer needs to track which source
    contributed to which target. The middleware must include the source in the output.
    """
    outputs = middleware.handle_input(source="fader.1", value=0.75, type="absolute_uni", timestamp=123.0)
    
    assert "group1.dimmer" in outputs
    payload = outputs["group1.dimmer"]
    
    # Verify all expected fields are present
    assert payload["value"] == 0.75
    assert payload["type"] == "absolute_uni"
    assert payload["timestamp"] == 123.0
    # Phase 6: source must be included
    assert payload["source"] == "fader.1"
