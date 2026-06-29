import pytest
from unittest.mock import AsyncMock, MagicMock, call

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager
from apelios.main_orchestrator import MainOrchestrator
from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager


@pytest.fixture
def mock_broker():
    mock = MagicMock(spec=BrokerRuntimeManager)
    mock.start_server = AsyncMock()
    mock.stop_server = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_middleware():
    mock = MagicMock(spec=MiddlewareRuntimeManager)
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.tick = AsyncMock()
    mock.is_running = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_input():
    mock = MagicMock(spec=InputRuntimeManager)
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.start_registered_adapters = AsyncMock()
    mock.stop_registered_adapters = AsyncMock()
    mock.tick = AsyncMock()
    mock.is_running = MagicMock(return_value=True)
    return mock

@pytest.fixture
def mock_fixture():
    mock = MagicMock(spec=FixtureRuntimeManager)
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.tick = AsyncMock()
    mock.is_running = MagicMock(return_value=True)
    return mock



@pytest.mark.asyncio
async def test_start_sequence_order(mock_broker, mock_middleware, mock_input, mock_fixture):
    """Test that infrastructure starts BEFORE subsystems, including fixture layer."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware,
        input_manager=mock_input,
        fixture_manager=mock_fixture,
    )

    manager = MagicMock()
    manager.attach_mock(mock_broker.start_server, 'broker_start')
    manager.attach_mock(mock_middleware.start, 'middleware_start')
    manager.attach_mock(mock_input.start, 'input_start')
    manager.attach_mock(mock_input.start_registered_adapters, 'input_start_adapters')
    manager.attach_mock(mock_fixture.start, 'fixture_start')

    await orchestrator.start()

    assert orchestrator.is_running()
    assert manager.mock_calls == [
        call.broker_start(),
        call.fixture_start(),
        call.middleware_start(),
        call.input_start(),
        call.input_start_adapters(),
    ]



@pytest.mark.asyncio
async def test_stop_sequence_order(mock_broker, mock_middleware, mock_input, mock_fixture):
    """Test that subsystems shut down BEFORE infrastructure, including fixture layer."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware,
        input_manager=mock_input,
        fixture_manager=mock_fixture,
    )

    orchestrator._running = True

    manager = MagicMock()
    manager.attach_mock(mock_input.stop_registered_adapters, 'input_stop_adapters')
    manager.attach_mock(mock_input.stop, 'input_stop')
    manager.attach_mock(mock_middleware.stop, 'middleware_stop')
    manager.attach_mock(mock_fixture.stop, 'fixture_stop')
    manager.attach_mock(mock_broker.stop_server, 'broker_stop')

    await orchestrator.stop()

    assert not orchestrator.is_running()
    assert manager.mock_calls == [
        call.input_stop_adapters(),
        call.input_stop(),
        call.middleware_stop(),
        call.fixture_stop(),
        call.broker_stop()
    ]



@pytest.mark.asyncio
async def test_health_check_fails_if_fixture_down(mock_broker, mock_middleware, mock_input, mock_fixture):
    """Test health check logic with fixture layer."""
    mock_broker.health_check.return_value = True
    mock_middleware.is_running.return_value = True
    mock_input.is_running.return_value = True
    mock_fixture.is_running.return_value = False

    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware,
        input_manager=mock_input,
        fixture_manager=mock_fixture,
    )

    is_healthy = await orchestrator.health_check()
    assert is_healthy is False

@pytest.mark.asyncio
async def test_run_forever_executes_tick_and_cleans_up(mock_broker, mock_middleware, mock_input, mock_fixture):
    """Test the infinite loop and graceful shutdown."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker, 
        middleware_manager=mock_middleware,
        input_manager=mock_input,
        fixture_manager=mock_fixture,
    )
    
    # TRICK: Move the crash to the LAST manager in the sequence!
    # This ensures input and middleware get their turn to tick before the loop breaks.
    mock_fixture.tick.side_effect = Exception("Simulated crash to break the loop")
    
    with pytest.raises(Exception, match="Simulated crash"):
        await orchestrator.run_forever()
        
    # Now all three should have exactly one call!
    mock_input.tick.assert_called_once()
    mock_middleware.tick.assert_called_once()
    mock_fixture.tick.assert_called_once()
    
    # Did it successfully call stop() in the finally block?
    mock_input.stop.assert_called_once()
    mock_middleware.stop.assert_called_once()
    mock_fixture.stop.assert_called_once()
    

@pytest.mark.asyncio
async def test_run_forever_yields_when_frame_overruns_target_interval(
    mock_broker,
    mock_middleware,
    mock_input,
    mock_fixture, # <-- Added
    monkeypatch,
):
    """If a frame exceeds 16ms budget, orchestrator should yield with sleep(0)."""
    orchestrator = MainOrchestrator(
        broker_manager=mock_broker,
        middleware_manager=mock_middleware,
        input_manager=mock_input,
        fixture_manager=mock_fixture, # <-- Added
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