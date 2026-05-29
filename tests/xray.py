import shutil
import asyncio
import json
import contextlib
from pathlib import Path

import pytest

from apelios.broker.config import NatsConfig 
from apelios.main_orchestrator import MainOrchestrator
from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.broker_client import BrokerClient
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager
from apelios.middleware.middleware_core import MappingMiddleware
from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
from apelios.input.input_runtime_manager import InputRuntimeManager

@pytest.fixture
def patch_config():
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
async def test_orchestrator_pipeline_xray(tmp_path, patch_config):
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    test_config = NatsConfig(host="127.0.0.1", port=4222)
    
    # 1. Start Server manually FIRST, and give it time to breathe!
    broker_manager = BrokerRuntimeManager(provider="nats", config=test_config)
    await broker_manager.start_server()
    await asyncio.sleep(1) # <--- THIS PREVENTS THE ZOMBIE CONNECTION BUG!

    # 2. Setup Managers
    middleware_profile = {"fader.1": {"target": "group1.dimmer", "intent": "absolute"}}
    middleware_client = BrokerClient(provider="nats", config=test_config)
    middleware_manager = MiddlewareRuntimeManager(
        middleware=MappingMiddleware(profile=middleware_profile),
        broker_client=middleware_client
    )

    fixture_client = BrokerClient(provider="nats", config=test_config)
    fixture_manager = FixtureRuntimeManager(broker_client=fixture_client, patch=patch_config)

    input_client = BrokerClient(provider="nats", config=test_config)
    input_manager = InputRuntimeManager(broker_client=input_client)

    orchestrator = MainOrchestrator(
        broker_manager=broker_manager,
        middleware_manager=middleware_manager,
        fixture_manager=fixture_manager,
        input_manager=input_manager,
    )

    # 3. Start subsystems (NATS is definitely awake now)
    await orchestrator.middleware_manager.start()
    await orchestrator.fixture_manager.start()
    await orchestrator.input_manager.start()
    orchestrator._running = True 

    # 4. Tick loop
    async def tick_loop():
        target_interval = 1.0 / 60.0
        while True:
            loop_start = asyncio.get_event_loop().time()
            await orchestrator.input_manager.tick(dt=target_interval)
            await orchestrator.middleware_manager.tick()
            await orchestrator.fixture_manager.tick(dt=target_interval)
            elapsed = asyncio.get_event_loop().time() - loop_start
            await asyncio.sleep(max(0, target_interval - elapsed))

    task = asyncio.create_task(tick_loop())

    # 5. Connect X-Ray Test Client
    test_client = BrokerClient(provider="nats", config=test_config)
    await test_client.connect()

    # X-RAY TRACKERS
    xray_input = []
    xray_target = []
    xray_output = []

    async def cap_in(m): xray_input.append(m.data)
    async def cap_mid(m): xray_target.append(m.data)
    async def cap_out(m): xray_output.append(m.data)

    await test_client.subscribe("input.>", cap_in)
    await test_client.subscribe("target.>", cap_mid)
    await test_client.subscribe("output.>", cap_out)

    # 6. Fire Payload
    payload = json.dumps({"source": "fader.1", "value": 0.8}).encode("utf-8")
    await test_client.publish("input.fader.1", payload)
    
    # Let the 60Hz loop process the message across the pipeline
    await asyncio.sleep(0.5)

    try:
        # PRINT THE DIAGNOSTICS BEFORE ASSERTING!
        print("\n\n" + "="*40)
        print("🔍 PIPELINE X-RAY REPORT 🔍")
        print(f"1. NATS Received Input:    {'✅ YES' if xray_input else '❌ NO (NATS is dead)'}")
        print(f"2. Middleware Outputted:   {'✅ YES' if xray_target else '❌ NO (Middleware dropped it)'}")
        print(f"3. Fixture Core Outputted: {'✅ YES' if xray_output else '❌ NO (Fixture Core dropped it)'}")
        if xray_target:
            print(f"   -> Middleware payload was: {xray_target[0]}")
        print("="*40 + "\n")

        assert len(xray_output) >= 1, "The pipeline broke. Check the X-Ray report above!"
        
        final_data = json.loads(xray_output[0].decode("utf-8"))
        assert final_data["universe"] == 1
        assert final_data["value"] == 204

    finally:
        await test_client.disconnect()
        await orchestrator.stop()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task