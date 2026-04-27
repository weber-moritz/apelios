import pytest
from unittest.mock import AsyncMock, MagicMock, call

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager
from apelios.main_orchestrator import MainOrchestrator  # Adjust import path if needed


@pytest.fixture
def mock_broker():
    """Mock the network infrastructure."""
    mock = MagicMock(spec=BrokerRuntimeManager)
    mock.start_server = AsyncMock()
    mock.stop_server = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_middleware():
    """Mock the 60Hz math engine."""
    mock = MagicMock(spec=MiddlewareRuntimeManager)
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.tick = AsyncMock()
    mock.is_running = MagicMock(return_value=True)
    return mock


@pytest.mark.asyncio
async def test_start_sequence_order(mock_broker, mock_middleware):
    """Test that infrastructure starts BEFORE subsystems."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware
    )
    
    # We use a parent mock to track the exact order of calls across different objects
    manager = MagicMock()
    manager.attach_mock(mock_broker.start_server, 'broker_start')
    manager.attach_mock(mock_middleware.start, 'middleware_start')

    await orchestrator.start()
    
    assert orchestrator.is_running()
    # Verify the broker started first!
    assert manager.mock_calls == [
        call.broker_start(),
        call.middleware_start()
    ]


@pytest.mark.asyncio
async def test_stop_sequence_order(mock_broker, mock_middleware):
    """Test that subsystems shut down BEFORE infrastructure."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware
    )
    
    # Force it into a running state
    orchestrator._running = True
    
    manager = MagicMock()
    manager.attach_mock(mock_middleware.stop, 'middleware_stop')
    manager.attach_mock(mock_broker.stop_server, 'broker_stop')

    await orchestrator.stop()
    
    assert not orchestrator.is_running()
    # Verify the middleware stopped first!
    assert manager.mock_calls == [
        call.middleware_stop(),
        call.broker_stop()
    ]


@pytest.mark.asyncio
async def test_health_check_fails_if_middleware_down(mock_broker, mock_middleware):
    """Test health check logic."""
    # Broker is healthy, but middleware crashed
    mock_broker.health_check.return_value = True
    mock_middleware.is_running.return_value = False
    
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware
    )
    
    is_healthy = await orchestrator.health_check()
    assert is_healthy is False


@pytest.mark.asyncio
async def test_run_forever_executes_tick_and_cleans_up(mock_broker, mock_middleware):
    """Test the infinite loop and graceful shutdown."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware
    )
    
    # TRICK: How do you test a `while True` loop without hanging Pytest forever?
    # We force the `tick()` method to throw an Exception the first time it runs.
    # This breaks the loop, allowing us to verify the `finally: await self.stop()` block executes.
    mock_middleware.tick.side_effect = Exception("Simulated crash to break the loop")
    
    with pytest.raises(Exception, match="Simulated crash"):
        await orchestrator.run_forever()
        
    # Did it try to run a frame?
    mock_middleware.tick.assert_called_once()
    
    # Did it successfully call stop() in the finally block?
    mock_middleware.stop.assert_called_once()


@pytest.mark.asyncio
async def test_run_forever_yields_when_frame_overruns_target_interval(
    mock_broker,
    mock_middleware,
    monkeypatch,
):
    """If a frame exceeds 16ms budget, orchestrator should yield with sleep(0)."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker,
        middleware_manager=mock_middleware,
    )

    # First tick succeeds so the timing branch runs; second tick stops the loop.
    mock_middleware.tick.side_effect = [None, Exception("Stop loop")]

    monotonic_values = iter([0.0, 0.020, 0.021])

    def fake_monotonic() -> float:
        try:
            return next(monotonic_values)
        except StopIteration:
            return 0.021

    monkeypatch.setattr(
        "apelios.main_orchestrator.time.monotonic",
        fake_monotonic,
    )

    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr("apelios.main_orchestrator.asyncio.sleep", fake_sleep)

    with pytest.raises(Exception, match="Stop loop"):
        await orchestrator.run_forever()

    assert any(delay == 0 for delay in sleep_calls)