import shutil
import asyncio
import json
import contextlib
from pathlib import Path

import pytest

from apelios.broker.config import NatsConfig # (Or wherever this lives)
from apelios.main_orchestrator import MainOrchestrator
from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.broker_client import BrokerClient
from apelios.router.router_runtime_manager import RouterRuntimeManager
from apelios.router.router_core import MappingRouter
from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
from apelios.input.input_runtime_manager import InputRuntimeManager

@pytest.fixture
def patch_config():
    # 1. UPDATED PATCH CONFIG: Matches the nested schema the FixtureCore expects
    return {
        "fixtures": {
            "group1": {
                "universe": 1,
                "address": 10,
                "parameters": {
                    "dimmer": {
                        "width": 8,
                        "limits": [0.0, 1.0]
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_orchestrator_starts_and_manages_broker_and_fixture(tmp_path, patch_config):
    """Verify MainOrchestrator can process a message completely from Input to Output."""
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    test_config = NatsConfig(host="127.0.0.1", port=4222)
    broker_manager = BrokerRuntimeManager(provider="nats", config=test_config)

    # Router profile: route fader.1 to group1.dimmer (Phase 5 format: source -> target)
    router_profile = {
        "fader.1": "group1.dimmer"
    }
    router_client = BrokerClient(provider="nats", config=test_config)
    router = MappingRouter(profile=router_profile)
    router_manager = RouterRuntimeManager(
        router=router,
        broker_client=router_client
    )

    fixture_client = BrokerClient(provider="nats", config=test_config)
    fixture_manager = FixtureRuntimeManager(broker_client=fixture_client, patch=patch_config)

    input_client = BrokerClient(provider="nats", config=test_config)
    input_manager = InputRuntimeManager(broker_client=input_client)
# ... (Keep all your setup code the same) ...
    orchestrator = MainOrchestrator(
        broker_manager=broker_manager,
        router_manager=router_manager,
        fixture_manager=fixture_manager,
        input_manager=input_manager,
    )

    # 1. START IT DIRECTLY (Not in a background task!)
    # If the broker or any manager fails to connect, Pytest will crash RIGHT HERE 
    # and give us the exact line number and the real error.
    await orchestrator.start()

    # 2. NOW start the infinite tick loop in the background
    # (Since run_forever() calls start(), we will bypass it and just loop)
    async def tick_loop():
        target_interval = 1.0 / 60.0
        while True:
            loop_start = asyncio.get_event_loop().time()
            await orchestrator.input_manager.tick(dt=target_interval)
            await orchestrator.router_manager.tick()
            await orchestrator.fixture_manager.tick(dt=target_interval)
            elapsed = asyncio.get_event_loop().time() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                await asyncio.sleep(0)

    task = asyncio.create_task(tick_loop())

    # 3. CONNECT TEST CLIENT
    test_client = BrokerClient(provider="nats", config=test_config)
    await test_client.connect()
    
    # ... (Keep the rest of your publish and assert logic the same) ...

    received_messages = []

    async def capture_message(msg):
        received_messages.append(msg.data)

    await test_client.subscribe("output.>", capture_message)

    payload = json.dumps({
        "source": "fader.1",
        "value": 0.8,
        "type": "absolute_uni"
    }).encode("utf-8")
    
    await asyncio.sleep(0.2)
        
    await test_client.publish("input.fader.1", payload)
    
    # Wait for the Orchestrator's 60Hz tick to process the messages across layers
    await asyncio.sleep(0.2)

    try:
        # Verify it's running
        assert orchestrator.is_running()

        # Health check should pass
        assert await orchestrator.health_check(timeout=3) is True

        # Verify the pipeline successfully routed and calculated the message
        assert len(received_messages) >= 1
        
        # 4. ASSERT MATH: 0.8 * 255 = 204
        # Check last message (not first) because Task 021 now outputs initialization messages first
        final_data = json.loads(received_messages[-1].decode("utf-8"))
        assert final_data["universe"] == 1
        assert final_data["address"] == 10
        assert final_data["value"] == 204
    
    finally:
        # 1. Close the test client safely to prevent EOF errors
        with contextlib.suppress(Exception):
            await test_client.disconnect()
            
        # 2. Cleanup Orchestrator
        await orchestrator.stop()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    # Verify it stopped
    assert not orchestrator.is_running()


@pytest.mark.asyncio
async def test_orchestrator_stop_without_start_is_safe():
    """Verify stopping orchestrator that never started doesn't crash."""
    broker_manager = BrokerRuntimeManager(provider="nats")
    orchestrator = MainOrchestrator(broker_manager=broker_manager)
    
    # Should not raise
    await orchestrator.stop()
    
    assert not orchestrator.is_running()