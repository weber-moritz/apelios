import json
from unittest.mock import AsyncMock, MagicMock
from nats.aio.msg import Msg

import pytest

from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager


@pytest.fixture
def mock_broker():
    broker = MagicMock()
    broker.connect = AsyncMock()
    broker.disconnect = AsyncMock()
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.mark.asyncio
async def test_fixture_runtime_manager_processes_input_to_dmx_output(mock_broker):
    # 1. Define the mock patch matching the FixtureCore's expected nested schema
    mock_patch = {
        "fixtures": {
            "movinghead01": {
                "type": "robe_robospot",
                "universe": 2,
                "address": 10,
                "parameters": {
                    "pan": {
                        "type": "absolute_uni",
                        "width": 16,
                        "limits": [0.0, 1.0]
                    }
                }
            },
            "movinghead02": {
                "type": "robe_robospot",
                "universe": 3,
                "address": 20,
                "parameters": {
                    "dim": {
                        "type": "absolute_uni",
                        "width": 8,
                        "limits": [0.0, 1.0]
                    }
                }
            }
        }
    }

    # 2. Inject the mock_patch so the Core engine doesn't drop the messages
    runtime = FixtureRuntimeManager(broker_client=mock_broker, patch=mock_patch)

    await runtime.start()
    subscriber = mock_broker.subscribe.await_args.args[1]
    
    pan_msg = MagicMock(spec=Msg)
    pan_msg.subject = "target.movinghead01.pan"
    pan_msg.data = json.dumps(
        {
            "value": 0.5,
            "type": "absolute_uni",
            "timestamp": 123.0,
            "source": "fader.1",
        }
    ).encode("utf-8")
    
    await subscriber(pan_msg)

    dim_msg = MagicMock(spec=Msg)
    dim_msg.subject = "target.movinghead02.dim"
    dim_msg.data = json.dumps(
        {
            "value": 0.25,
            "type": "absolute_uni",
            "timestamp": 123.0,
            "source": "fader.2",
        }
    ).encode("utf-8")
    
    await subscriber(dim_msg)

    await runtime.tick(dt=0.016)

    # 3. Assertions will now pass because the core successfully calculated the outputs
    published_subjects = [call.args[0] for call in mock_broker.publish.await_args_list]
    assert "output.2.10" in published_subjects
    assert "output.2.11" in published_subjects
    assert "output.3.20" in published_subjects

    pan_coarse_call = next(call for call in mock_broker.publish.await_args_list if call.args[0] == "output.2.10")
    pan_fine_call = next(call for call in mock_broker.publish.await_args_list if call.args[0] == "output.2.11")
    dim_call = next(call for call in mock_broker.publish.await_args_list if call.args[0] == "output.3.20")

    assert json.loads(pan_coarse_call.args[1].decode("utf-8")) == {
        "universe": 2,
        "address": 10,
        "value": 128,
    }
    assert json.loads(pan_fine_call.args[1].decode("utf-8")) == {
        "universe": 2,
        "address": 11,
        "value": 0,
    }
    assert json.loads(dim_call.args[1].decode("utf-8")) == {
        "universe": 3,
        "address": 20,
        "value": 64,
    }