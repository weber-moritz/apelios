import json
from unittest.mock import MagicMock

import pytest
from nats.aio.msg import Msg

from apelios.fixture.fixture_input_subscriber import FixtureInputSubscriber


@pytest.fixture
def inbox():
    return {}


@pytest.fixture
def subscriber(inbox):
    return FixtureInputSubscriber(inbox=inbox)


@pytest.mark.asyncio
async def test_subscriber_stores_payload_by_target(subscriber, inbox):
    msg = MagicMock(spec=Msg)
    msg.subject = "target.movinghead01.pan"
    msg.data = json.dumps(
        {
            "value": 0.5312,
            "type": "absolute_uni",
            "timestamp": 123.0,
        }
    ).encode("utf-8")

    await subscriber(msg)

    assert inbox["movinghead01.pan"] == {
        "target": "movinghead01.pan",
        "type": "absolute_uni",
        "value": 0.5312,
    }

@pytest.mark.asyncio
async def test_subscriber_overwrites_latest_payload_for_same_target(subscriber, inbox):
    first_msg = MagicMock(spec=Msg)
    first_msg.subject = "target.movinghead01.pan"
    first_msg.data = json.dumps(
        {
            "value": 0.1,
            "type": "absolute_uni",
            "timestamp": 123.0,
        }
    ).encode("utf-8")

    second_msg = MagicMock(spec=Msg)
    second_msg.subject = "target.movinghead01.pan"
    second_msg.data = json.dumps(
        {
            "value": 0.8,
            "type": "absolute_uni",
            "timestamp": 124.0,
        }
    ).encode("utf-8")

    await subscriber(first_msg)
    await subscriber(second_msg)

    assert inbox["movinghead01.pan"]["value"] == 0.8
    assert inbox["movinghead01.pan"]["type"] == "absolute_uni"
    

@pytest.mark.asyncio
async def test_subscriber_ignores_missing_target(subscriber, inbox):
    msg = MagicMock(spec=Msg)
    msg.subject = "target"
    msg.data = json.dumps(
        {
            "type": "delta",
            "value": 0.1,
            "timestamp": 123.0,
        }
    ).encode("utf-8")

    await subscriber(msg)

    assert inbox == {}

@pytest.mark.asyncio
async def test_subscriber_ignores_malformed_json(subscriber, inbox):
    msg = MagicMock(spec=Msg)
    msg.subject = "target.test"
    msg.data = b"not valid json"

    await subscriber(msg)

    assert inbox == {}


@pytest.mark.asyncio
async def test_subscriber_parses_type_not_intent(subscriber, inbox):
    msg = MagicMock(spec=Msg)
    msg.subject = "target.test.param"
    msg.data = json.dumps(
        {
            "value": 0.75,
            "type": "absolute_bi",
            "timestamp": 123.0,
        }
    ).encode("utf-8")

    await subscriber(msg)

    assert "test.param" in inbox
    assert inbox["test.param"]["type"] == "absolute_bi"
    assert inbox["test.param"]["value"] == 0.75
    assert "intent" not in inbox["test.param"]


@pytest.mark.asyncio
async def test_subscriber_handles_missing_type(subscriber, inbox):
    msg = MagicMock(spec=Msg)
    msg.subject = "target.test.param"
    msg.data = json.dumps(
        {
            "value": 0.5,
            "timestamp": 123.0,
        }
    ).encode("utf-8")

    await subscriber(msg)

    assert inbox == {}