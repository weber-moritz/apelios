import pytest
from apelios.router.router_core import MappingRouter


@pytest.fixture
def router():
    """Fixture with pure passthrough routing (stateless, no intent in config)."""
    mock_profile = {
        "fader.1": "group1.dimmer",
        "mouse.x": "group1.pan",
        "joystick.1": "group1.tilt",
    }
    return MappingRouter(profile=mock_profile)


def test_core_passes_type_unchanged(router):
    """Test that type from input layer flows through unchanged (Phase 5/6)."""
    outputs = router.handle_input(source="fader.1", value=0.75, type="absolute_uni", timestamp=123.0)
    assert outputs == {"group1.dimmer": {"value": 0.75, "type": "absolute_uni", "timestamp": 123.0, "source": "fader.1"}}


def test_core_has_no_state_dicts(router):
    """Test that router has NO state dictionaries."""
    assert not hasattr(router, 'current_raw_input')
    assert not hasattr(router, 'virtual_output_state')
    assert not hasattr(router, 'enriched_outputs')


def test_core_processes_immediately(router):
    """Test that inputs are processed immediately, not batched in process_frame."""
    outputs = router.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=100.0)
    assert "group1.dimmer" in outputs
    assert outputs["group1.dimmer"]["value"] == 0.5


def test_core_absolute_passthrough(router):
    """Test that absolute type values are passed through unchanged."""
    outputs = router.handle_input(source="fader.1", value=0.75, type="absolute_uni", timestamp=123.0)
    assert "group1.dimmer" in outputs
    assert outputs["group1.dimmer"]["value"] == 0.75
    assert outputs["group1.dimmer"]["type"] == "absolute_uni"


def test_core_delta_passthrough_no_math(router):
    """Test that delta type values are passed through without delta math."""
    outputs = router.handle_input(source="mouse.x", value=0.5, type="delta", timestamp=124.0)
    assert "group1.pan" in outputs
    assert outputs["group1.pan"]["value"] == 0.5
    assert outputs["group1.pan"]["type"] == "delta"


def test_core_rate_passthrough_no_integration(router):
    """Test that rate type values are passed through without time integration."""
    outputs = router.handle_input(source="joystick.1", value=0.8, type="rate", timestamp=125.0)
    assert "group1.tilt" in outputs
    assert outputs["group1.tilt"]["value"] == 0.8
    assert outputs["group1.tilt"]["type"] == "rate"


def test_core_multiple_sources_in_one_call(router):
    """Test that multiple sources can be handled independently."""
    out1 = router.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=100.0)
    out2 = router.handle_input(source="mouse.x", value=0.3, type="delta", timestamp=101.0)
    out3 = router.handle_input(source="joystick.1", value=-0.2, type="rate", timestamp=102.0)
    
    assert "group1.dimmer" in out1
    assert "group1.pan" in out2
    assert "group1.tilt" in out3


def test_core_no_clamping_in_router(router):
    """Test that router does NOT clamp values."""
    outputs = router.handle_input(source="mouse.x", value=5.0, type="delta", timestamp=100.0)
    assert outputs["group1.pan"]["value"] == 5.0


def test_core_unmapped_sources_ignored(router):
    """Test that sources without a mapping are ignored."""
    outputs = router.handle_input(source="unmapped.source", value=0.9, type="absolute_uni", timestamp=100.0)
    assert outputs == {}


def test_core_profile_only_has_source_to_target(router):
    """Test that profile only contains source->target mapping, no intent/sensitivity."""
    assert router.profile == {
        "fader.1": "group1.dimmer",
        "mouse.x": "group1.pan",
        "joystick.1": "group1.tilt",
    }


def test_core_returns_outputs_dict(router):
    """Test that handle_input returns a dict of outputs."""
    outputs = router.handle_input(source="fader.1", value=0.5, type="absolute_uni", timestamp=100.0)
    assert isinstance(outputs, dict)


def test_core_no_process_frame_method(router):
    """Test that there is no process_frame method."""
    assert not hasattr(router, 'process_frame')


def test_core_includes_source_in_output(router):
    """Test that source field is included in output payload (Phase 6.1.1).
    
    For many-to-one input summation, the fixture layer needs to track which source
    contributed to which target. The router must include the source in the output.
    """
    outputs = router.handle_input(source="fader.1", value=0.75, type="absolute_uni", timestamp=123.0)
    
    assert "group1.dimmer" in outputs
    payload = outputs["group1.dimmer"]
    
    # Verify all expected fields are present
    assert payload["value"] == 0.75
    assert payload["type"] == "absolute_uni"
    assert payload["timestamp"] == 123.0
    # Phase 6: source must be included
    assert payload["source"] == "fader.1"


def test_core_passes_source_unchanged():
    """Router passes source from input layer unchanged (7.4.2).
    
    For Phase 7, when payload is passed directly, router forwards it unchanged.
    """
    router = MappingRouter(profile={"input.fader.1": "group1.pan"})
    
    # Full payload from input layer with source
    payload = {
        "value": 0.5,
        "type": "absolute_uni",
        "timestamp": 100.0,
        "source": "input.fader.1"
    }
    
    outputs = router.handle_input(
        source="input.fader.1",
        value=0.5,
        type="absolute_uni",
        timestamp=100.0,
        payload=payload  # Full payload for pure passthrough
    )
    
    assert "group1.pan" in outputs
    # Verify the full payload was passed through unchanged
    assert outputs["group1.pan"] == payload
    assert outputs["group1.pan"]["source"] == "input.fader.1"
