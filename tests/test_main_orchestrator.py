import pytest
from unittest.mock import AsyncMock, MagicMock

from apelios.main_orchestrator import MainOrchestrator


@pytest.mark.asyncio
async def test_start_delegates_to_broker_manager():
    fake_broker = MagicMock()
    fake_broker.start_server = AsyncMock()
    fake_broker.is_running.return_value = True
    
    orchestrator = MainOrchestrator(broker_manager=fake_broker)
    await orchestrator.start()
    
    fake_broker.start_server.assert_awaited_once()
    assert orchestrator.is_running() is True


@pytest.mark.asyncio
async def test_start_is_idempotent():
    fake_broker = MagicMock()
    fake_broker.start_server = AsyncMock()
    fake_broker.is_running.return_value = True
    
    orchestrator = MainOrchestrator(broker_manager=fake_broker)
    
    await orchestrator.start()
    await orchestrator.start()  # Call twice
    
    # start_server should only be called once
    fake_broker.start_server.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_delegates_to_broker_manager():
    fake_broker = MagicMock()
    fake_broker.start_server = AsyncMock()
    fake_broker.stop_server = AsyncMock()
    fake_broker.is_running.return_value = False
    
    orchestrator = MainOrchestrator(broker_manager=fake_broker)
    await orchestrator.start()
    await orchestrator.stop()
    
    fake_broker.stop_server.assert_awaited_once()
    assert orchestrator.is_running() is False


@pytest.mark.asyncio
async def test_health_check_delegates_and_returns_value():
    fake_broker = MagicMock()
    fake_broker.health_check = AsyncMock(return_value=True)
    
    orchestrator = MainOrchestrator(broker_manager=fake_broker)
    result = await orchestrator.health_check(timeout=3)
    
    fake_broker.health_check.assert_awaited_once_with(timeout=3)
    assert result is True


def test_is_running_delegates():
    fake_broker = MagicMock()
    fake_broker.is_running.return_value = True
    
    orchestrator = MainOrchestrator(broker_manager=fake_broker)
    assert orchestrator.is_running() is True
    fake_broker.is_running.assert_called_once()


@pytest.mark.asyncio
async def test_stop_without_start_is_safe():
    fake_broker = MagicMock()
    fake_broker.stop_server = AsyncMock()
    fake_broker.is_running.return_value = False
    
    orchestrator = MainOrchestrator(broker_manager=fake_broker)
    
    # Should not raise even though never started
    await orchestrator.stop()
    
    assert orchestrator.is_running() is False