import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from apelios.fixture.fixture_output_publisher import FixtureOutputPublisher


@pytest.fixture
def mock_broker():
    broker = MagicMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def output_module(mock_broker):
    return FixtureOutputPublisher(broker=mock_broker)


@pytest.mark.asyncio
async def test_output_module_publishes_dmx_values(output_module, mock_broker):
    dmx_output = {
        (2, 10): 135,
    }

    await output_module.publish_dmx(dmx_output)

    mock_broker.publish.assert_awaited_once_with(
        "output.2.10",
        json.dumps({"universe": 2, "address": 10, "value": 135}).encode("utf-8"),
    )


@pytest.mark.asyncio
async def test_output_module_publishes_multiple_dmx_values(output_module, mock_broker):
    dmx_output = {
        (2, 10): 135,
        (2, 11): 42,
    }

    await output_module.publish_dmx(dmx_output)

    assert mock_broker.publish.await_count == 2
    mock_broker.publish.assert_any_await(
        "output.2.10",
        json.dumps({"universe": 2, "address": 10, "value": 135}).encode("utf-8"),
    )
    mock_broker.publish.assert_any_await(
        "output.2.11",
        json.dumps({"universe": 2, "address": 11, "value": 42}).encode("utf-8"),
    )


@pytest.mark.asyncio
async def test_output_module_prints_state(output_module, capsys):
    dmx_output = {
        (2, 10): 135,
    }

    await output_module.publish_dmx(dmx_output)

    captured = capsys.readouterr()
    assert "2:10=135" in captured.out