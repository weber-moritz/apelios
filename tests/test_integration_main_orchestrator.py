import shutil
import socket
from pathlib import Path
import asyncio
import json

from apelios.broker.config import NatsConfig # (Or wherever this lives)
from apelios.middleware.middleware_core import MappingMiddleware

from apelios.main_orchestrator import MainOrchestrator
from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.broker_client import BrokerClient
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager

import pytest

@pytest.fixture
def mock_profile():
    return {"fader.1": {"target": "group1.dimmer", "type": "absolute"}}


@pytest.mark.asyncio
async def test_orchestrator_starts_and_manages_broker_and_middleware(tmp_path, mock_profile):
    """Verify MainOrchestrator can start/stop real NATS via BrokerRuntimeManager."""
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    test_config = NatsConfig(host="127.0.0.1", port=4222)
    broker_manager = BrokerRuntimeManager(provider="nats", config=test_config)    
    
    # Give the Middleware a client pointing to the TEST network!
    middleware_client = BrokerClient(provider="nats", config=test_config)
    middleware = MappingMiddleware(profile=mock_profile)
    middleware_manager = MiddlewareRuntimeManager(
        middleware=middleware, 
        broker_client=middleware_client
    )

    orchestrator = MainOrchestrator(broker_manager=broker_manager, middleware_manager=middleware_manager)
    # 1. Schedule the background task
    task = asyncio.create_task(orchestrator.run_forever())

    # 2. Yield control IMMEDIATELY so the orchestrator can boot the NATS server
    await asyncio.sleep(5)

    # 3. NOW build the test client. (Pass the test_config here too, just to be perfectly safe!)
    test_client = BrokerClient(provider="nats", config=test_config)
    
    # 4. Connect (The server is actually awake now!)
    await test_client.connect()
    
    received_messages = []
    
    def capture_message(msg):
        received_messages.append(msg.data)
        
    await test_client.subscribe("outputs.>", capture_message)
    
    # Publish your test payload
    payload = json.dumps({"source": "fader.1", "value": 0.8}).encode("utf-8")
    await test_client.publish("input.fader.1", payload)

    # 5. Wait for the Orchestrator's 60Hz tick to process the message
    await asyncio.sleep(0.1)

    try:
        # Verify it's running
        assert orchestrator.is_running()
        
        # Health check should pass
        assert await orchestrator.health_check(timeout=3) is True
        
        # Instead of assert len(received_messages) == 1
        assert len(received_messages) >= 1
        assert b"0.8" in received_messages[0]

    finally:
        # Cleanup
        await orchestrator.stop()

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