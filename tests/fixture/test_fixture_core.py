import pytest

from apelios.fixture.fixture_core import FixtureCore


@pytest.fixture
def patch_config():
    return {
        "fixtures": {
            "movinghead01": {
                "type": "robe_robospot",
                "universe": 2,
                "address": 10,
                "parameters": {
                    "pan": {
                        "type": "absolute_uni",
                        "width": 16,
                        "limits": [0.0, 1.0],
                    },
                    "tilt": {
                        "type": "delta",
                        "width": 8,
                        "limits": [0.0, 1.0],
                    },
                },
            }
        }
    }


@pytest.fixture
def patch_config_with_types():
    """Patch config using type field for Phase 3."""
    return {
        "fixtures": {
            "movinghead01": {
                "type": "robe_robospot",
                "universe": 2,
                "address": 10,
                "parameters": {
                    "pan": {
                        "type": "absolute_uni",
                        "width": 16,
                        "limits": [0.0, 1.0],
                    },
                    "tilt": {
                        "type": "absolute_bi",
                        "width": 8,
                        "limits": [-1.0, 1.0],
                    },
                },
            }
        }
    }


def test_absolute_math_updates_state_without_hidden_math(patch_config):
    core = FixtureCore(patch=patch_config)
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5312,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"] == pytest.approx(0.5312)


def test_16bit_output_is_split_into_coarse_and_fine_channels(patch_config):
    core = FixtureCore(patch=patch_config)
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5,
    }

    core.process_frame(dt=0.016)

    assert core.dmx_output[(2, 10)] == 128
    assert core.dmx_output[(2, 11)] == 0


def test_core_uses_type_field(patch_config_with_types):
    """Test that core uses type field from payload (3.2.1)."""
    core = FixtureCore(patch=patch_config_with_types)
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.75,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"] == pytest.approx(0.75)


def test_core_uses_type_from_payload_over_patch(patch_config_with_types):
    """Test that payload type overrides patch type."""
    core = FixtureCore(patch=patch_config_with_types)
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"] == pytest.approx(0.5)


def test_core_handles_delta_type(patch_config_with_types):
    """Test delta type accumulates values."""
    patch_config_with_types["fixtures"]["movinghead01"]["parameters"]["pan"]["type"] = "delta"
    core = FixtureCore(patch=patch_config_with_types)
    
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "delta",
        "value": 0.1,
    }
    core.process_frame(dt=0.016)
    
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "delta",
        "value": 0.2,
    }
    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"] == pytest.approx(0.3)


def test_core_handles_rate_type(patch_config_with_types):
    """Test rate type applies value * dt."""
    patch_config_with_types["fixtures"]["movinghead01"]["parameters"]["pan"]["type"] = "rate"
    core = FixtureCore(patch=patch_config_with_types)
    
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "rate",
        "value": 10.0,
    }
    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"] == pytest.approx(0.16)


def test_core_handles_absolute_bi_type(patch_config_with_types):
    """Test absolute_bi type passes through value directly."""
    core = FixtureCore(patch=patch_config_with_types)
    core.inbox["movinghead01.tilt"] = {
        "target": "movinghead01.tilt",
        "type": "absolute_bi",
        "value": -0.5,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.tilt"] == pytest.approx(-0.5)


@pytest.fixture
def patch_config_offset_based():
    """Patch config using offset-based addressing (Phase 4.2)."""
    return {
        "fixtures": {
            "movinghead01": {
                "type": "robe_robospot",
                "universe": 2,
                "address": 10,
                "parameters": {
                    "pan": {
                        "type": "absolute_uni",
                        "width": 16,
                        "limits": [0.0, 1.0],
                    },
                    "tilt": {
                        "type": "absolute_uni", 
                        "address": 2,
                        "width": 8,
                        "limits": [0.0, 1.0],
                    },
                },
            }
        }
    }


def test_patch_offset_based_auto_sequential(patch_config_offset_based):
    """Test that parameters without address get sequential offsets (4.2.3)."""
    core = FixtureCore(patch=patch_config_offset_based)
    
    # pan has no address → offset 0 → channels 10-11
    # tilt has explicit address: 2 → offset 2 → channel 12
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5,
    }
    core.inbox["movinghead01.tilt"] = {
        "target": "movinghead01.tilt",
        "type": "absolute_uni",
        "value": 0.75,
    }
    core.process_frame(dt=0.016)
    
    # pan (16-bit, auto offset 0) should write to channels (2, 10) and (2, 11)
    assert (2, 10) in core.dmx_output
    assert (2, 11) in core.dmx_output
    
    # tilt (8-bit, explicit offset 2) should write to channel (2, 12) = 10 + 2
    assert (2, 12) in core.dmx_output
    assert core.dmx_output[(2, 12)] == pytest.approx(191)  # 0.75 * 255


def test_patch_offset_based_explicit_address(patch_config_offset_based):
    """Test that parameters with explicit address use that offset (4.2.2)."""
    core = FixtureCore(patch=patch_config_offset_based)
    
    core.inbox["movinghead01.tilt"] = {
        "target": "movinghead01.tilt",
        "type": "absolute_uni",
        "value": 0.75,
    }
    core.process_frame(dt=0.016)
    
    # tilt has address: 2, so offset = 2, channel = 10 + 2 = 12
    assert (2, 12) in core.dmx_output
    assert core.dmx_output[(2, 12)] == pytest.approx(191)  # 0.75 * 255


def test_patch_object_format(patch_config_offset_based):
    """Test that patch uses object format, not array (4.2.1)."""
    core = FixtureCore(patch=patch_config_offset_based)
    
    # Verify fixtures is a dict, not a list
    assert isinstance(core.patch.get("fixtures"), dict)
    
    # Verify movinghead01 is a fixture dict
    fixture = core.patch["fixtures"]["movinghead01"]
    assert isinstance(fixture, dict)
    assert fixture["type"] == "robe_robospot"
    assert fixture["address"] == 10
    
    # Verify parameters is a dict
    params = fixture["parameters"]
    assert isinstance(params, dict)
    assert "pan" in params
    assert "tilt" in params