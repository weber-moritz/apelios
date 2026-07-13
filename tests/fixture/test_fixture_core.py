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
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.1"] = {
        "source": "fader.1",
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5312,
    }

    core.process_frame(dt=0.016)

    # internal_state now stores dict with value, has_first_abs, first_abs_value
    assert core.internal_state["movinghead01.pan"]["value"] == pytest.approx(0.5312)


def test_16bit_output_is_split_into_coarse_and_fine_channels(patch_config):
    core = FixtureCore(patch=patch_config)
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.1"] = {
        "source": "fader.1",
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
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.1"] = {
        "source": "fader.1",
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.75,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"]["value"] == pytest.approx(0.75)


def test_core_uses_type_from_payload_over_patch(patch_config_with_types):
    """Test that payload type overrides patch type."""
    core = FixtureCore(patch=patch_config_with_types)
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.1"] = {
        "source": "fader.1",
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"]["value"] == pytest.approx(0.5)


def test_core_handles_delta_type(patch_config_with_types):
    """Test delta type accumulates values."""
    patch_config_with_types["fixtures"]["movinghead01"]["parameters"]["pan"]["type"] = "delta"
    core = FixtureCore(patch=patch_config_with_types)
    
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.1"] = {
        "source": "fader.1",
        "target": "movinghead01.pan",
        "type": "delta",
        "value": 0.1,
    }
    core.process_frame(dt=0.016)
    
    core.inbox["fader.1"] = {
        "source": "fader.1",
        "target": "movinghead01.pan",
        "type": "delta",
        "value": 0.2,
    }
    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"]["value"] == pytest.approx(0.3)


def test_core_handles_rate_type(patch_config_with_types):
    """Test rate type applies value * dt."""
    patch_config_with_types["fixtures"]["movinghead01"]["parameters"]["pan"]["type"] = "rate"
    core = FixtureCore(patch=patch_config_with_types)
    
    # Inbox keyed by source (Phase 6)
    core.inbox["gyro.1"] = {
        "source": "gyro.1",
        "target": "movinghead01.pan",
        "type": "rate",
        "value": 10.0,
    }
    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"]["value"] == pytest.approx(0.16)


def test_core_handles_absolute_bi_type(patch_config_with_types):
    """Test absolute_bi type passes through value directly."""
    core = FixtureCore(patch=patch_config_with_types)
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.2"] = {
        "source": "fader.2",
        "target": "movinghead01.tilt",
        "type": "absolute_bi",
        "value": -0.5,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.tilt"]["value"] == pytest.approx(-0.5)


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
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.1"] = {
        "source": "fader.1",
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5,
    }
    core.inbox["fader.2"] = {
        "source": "fader.2",
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
    
    # Inbox keyed by source (Phase 6)
    core.inbox["fader.1"] = {
        "source": "fader.1",
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


@pytest.fixture
def patch_config_simple():
    """Simple patch config for Phase 6 many-to-one tests."""
    return {
        "fixtures": {
            "group1": {
                "type": "generic",
                "universe": 1,
                "address": 1,
                "parameters": {
                    "dimmer": {
                        "width": 8,
                        "limits": [0.0, 1.0],
                    },
                },
            }
        }
    }


def test_core_initializes_with_first_absolute(patch_config_simple):
    """Test that first absolute input sets base output value (Phase 6.3.7).
    
    When multiple sources map to the same target, the first absolute input
    should set the base output value, and subsequent inputs contribute deltas.
    """
    core = FixtureCore(patch=patch_config_simple)
    
    # Inbox keyed by source (Phase 6 format)
    core.inbox = {
        "fader.1": {
            "source": "fader.1",
            "target": "group1.dimmer",
            "value": 0.5,
            "type": "absolute_uni",
            "timestamp": 100.0,
        }
    }
    
    core.process_frame(dt=0.016)
    
    # Check that dimmer DMX output was written
    assert (1, 1) in core.dmx_output
    # 0.5 normalized * 255 = 127.5 ≈ 128
    assert core.dmx_output[(1, 1)] == pytest.approx(128, abs=1)


def test_core_sums_deltas_from_multiple_sources(patch_config_simple):
    """Test that deltas from multiple sources are summed for same target (Phase 6.3.6).
    
    Multiple sources can map to the same target via routing config.
    Delta inputs should be summed together.
    """
    core = FixtureCore(patch=patch_config_simple)
    
    # Two sources contributing to the same target
    core.inbox = {
        "fader.1": {
            "source": "fader.1",
            "target": "group1.dimmer",
            "value": 0.2,
            "type": "delta",
            "timestamp": 100.0,
        },
        "gyro.1": {
            "source": "gyro.1",
            "target": "group1.dimmer",
            "value": 0.3,
            "type": "delta",
            "timestamp": 100.0,
        },
    }
    
    core.process_frame(dt=0.016)
    
    # Check that dimmer DMX output was written
    assert (1, 1) in core.dmx_output
    # 0.2 + 0.3 = 0.5, normalized * 255 = 127.5 ≈ 128
    assert core.dmx_output[(1, 1)] == pytest.approx(128, abs=1)


@pytest.fixture
def patch_config_with_start_values():
    """Patch config with start values for testing initialization."""
    return {
        "fixtures": {
            "movinghead01": {
                "type": "test",
                "universe": 1,
                "address": 1,
                "parameters": {
                    "pan": {
                        "width": 8,
                        "limits": [0.0, 1.0],
                        "start": 0.5,
                    },
                    "tilt": {
                        "width": 8,
                        "limits": [0.0, 1.0],
                        "start": 0.0,
                    },
                    "dimmer": {
                        "width": 8,
                        "limits": [0.0, 1.0],
                        # No start value, should default to 0.0
                    },
                    "color": {
                        "width": 8,
                        "limits": [-1.0, 1.0],
                        "start": 0.5,
                    },
                },
            }
        }
    }


def test_start_value_initialization(patch_config_with_start_values):
    """Test that parameters initialize with start value when first processed."""
    core = FixtureCore(patch=patch_config_with_start_values)
    
    # Process first frame with no input - parameters should initialize with start values
    core.process_frame(dt=0.016)
    
    # pan has start=0.5
    assert "movinghead01.pan" in core.internal_state
    assert core.internal_state["movinghead01.pan"]["value"] == pytest.approx(0.5)
    assert core.dmx_output[(1, 1)] == pytest.approx(128, abs=1)  # 0.5 * 255 = 127.5
    
    # tilt has start=0.0
    assert "movinghead01.tilt" in core.internal_state
    assert core.internal_state["movinghead01.tilt"]["value"] == pytest.approx(0.0)
    assert core.dmx_output[(1, 2)] == pytest.approx(0)
    
    # dimmer has no start, defaults to 0.0
    assert "movinghead01.dimmer" in core.internal_state
    assert core.internal_state["movinghead01.dimmer"]["value"] == pytest.approx(0.0)
    assert core.dmx_output[(1, 3)] == pytest.approx(0)
    
    # color has start=0.5 with limits [-1.0, 1.0], clamped to [0.0, 1.0]
    assert "movinghead01.color" in core.internal_state
    assert core.internal_state["movinghead01.color"]["value"] == pytest.approx(0.5)


def test_start_value_clamped_to_limits(patch_config_with_start_values):
    """Test that start values are clamped to parameter limits."""
    # Modify config to have start value outside limits
    config = {
        "fixtures": {
            "test": {
                "type": "test",
                "universe": 1,
                "address": 1,
                "parameters": {
                    "value": {
                        "width": 8,
                        "limits": [0.0, 0.5],
                        "start": 1.0,  # Outside upper limit
                    },
                    "value2": {
                        "width": 8,
                        "limits": [0.3, 1.0],
                        "start": 0.1,  # Below lower limit
                    },
                },
            }
        }
    }
    
    core = FixtureCore(patch=config)
    core.process_frame(dt=0.016)
    
    # value with start=1.0 should be clamped to 0.5 (upper limit)
    assert core.internal_state["test.value"]["value"] == pytest.approx(0.5)
    
    # value2 with start=0.1 should be clamped to 0.3 (lower limit)
    assert core.internal_state["test.value2"]["value"] == pytest.approx(0.3)