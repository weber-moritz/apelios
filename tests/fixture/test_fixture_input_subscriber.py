import json
from unittest.mock import MagicMock

import pytest

from apelios.fixture.fixture_input_subscriber import FixtureInputSubscriber


@pytest.fixture
def inbox():
    return {}


@pytest.fixture
def subscriber(inbox):
    return FixtureInputSubscriber(inbox=inbox)


@pytest.mark.asyncio
async def test_subscriber_stores_payload_by_target(subscriber, inbox):
    msg = MagicMock()
    msg.data = json.dumps(
        {
            "target": "movinghead01.pan",
            "intent": "absolute",
            "value": 0.5312,
        }
    ).encode("utf-8")

    # ADD AWAIT HERE
    await subscriber(msg)

    assert inbox["movinghead01.pan"] == {
        "target": "movinghead01.pan",
        "intent": "absolute",
        "value": 0.5312,
    }

@pytest.mark.asyncio
async def test_subscriber_overwrites_latest_payload_for_same_target(subscriber, inbox):
    first_msg = MagicMock()
    first_msg.data = json.dumps(
        {
            "target": "movinghead01.pan",
            "intent": "absolute",
            "value": 0.1,
        }
    ).encode("utf-8")

    second_msg = MagicMock()
    second_msg.data = json.dumps(
        {
            "target": "movinghead01.pan",
            "intent": "absolute",
            "value": 0.8,
        }
    ).encode("utf-8")

    # ADD AWAITS HERE
    await subscriber(first_msg)
    await subscriber(second_msg)

    assert inbox["movinghead01.pan"]["value"] == 0.8
    

@pytest.mark.asyncio
async def test_subscriber_ignores_missing_target(subscriber, inbox):
    msg = MagicMock()
    msg.data = json.dumps(
        {
            "intent": "delta",
            "value": 0.1,
        }
    ).encode("utf-8")

    await subscriber(msg)

    assert inbox == {}

@pytest.mark.asyncio
async def test_subscriber_ignores_malformed_json(subscriber, inbox):
    msg = MagicMock()
    msg.data = b"not valid json"

    await subscriber(msg)

    assert inbox == {}