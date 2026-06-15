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