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
                        "intent": "absolute",
                        "width": 16,
                        "limits": [0.0, 1.0],
                    },
                    "tilt": {
                        "intent": "delta",
                        "width": 8,
                        "limits": [0.0, 1.0],
                    },
                },
            }
        }
    }


def test_absolute_math_updates_state_without_hidden_math(patch_config):
    core = FixtureCore(patch=patch_config)
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "intent": "absolute",
        "value": 0.5312,
    }

    core.process_frame(dt=0.016)

    assert core.internal_state["movinghead01.pan"] == pytest.approx(0.5312)


def test_16bit_output_is_split_into_coarse_and_fine_channels(patch_config):
    core = FixtureCore(patch=patch_config)
    core.inbox["movinghead01.pan"] = {
        "target": "movinghead01.pan",
        "intent": "absolute",
        "value": 0.5,
    }

    core.process_frame(dt=0.016)

    assert core.dmx_output[(2, 10)] == 128
    assert core.dmx_output[(2, 11)] == 0