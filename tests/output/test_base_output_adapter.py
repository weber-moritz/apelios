"""Tests for BaseOutputAdapter - TDD Red Phase.

These tests define the expected behavior of the BaseOutputAdapter
before any implementation exists. All tests should fail initially.
"""

import asyncio
import pytest

from apelios.output.base_output_adapter import BaseOutputAdapter


def _create_test_adapter(config=None):
    """Factory function to create a concrete BaseOutputAdapter for testing."""
    
    class ConcreteTestAdapter(BaseOutputAdapter):
        """Concrete implementation for testing BaseOutputAdapter."""
        
        async def _run_loop(self) -> None:
            """Test implementation of _run_loop - minimal no-op loop."""
            # Minimal implementation that satisfies the abstract method requirement
            # but doesn't actually loop (tests don't need real loop behavior)
            while self._running:
                await asyncio.sleep(0.1)
        
        async def send_dmx(self, dmx_buffer: dict[tuple[int, int], int]) -> None:
            """Test implementation of send_dmx."""
            pass
    
    return ConcreteTestAdapter(config or {})


class TestBaseOutputAdapterInitialization:
    """Tests for BaseOutputAdapter initialization."""

    def test_adapter_initializes_with_config(self):
        """BaseOutputAdapter should store config correctly."""
        config = {"universe": 1, "target_ip": "192.168.1.1"}
        adapter = _create_test_adapter(config)
        
        assert adapter.config == config
        assert adapter.is_running() is False

    def test_adapter_initializes_with_none_config(self):
        """BaseOutputAdapter should handle None config."""
        adapter = _create_test_adapter(None)
        
        assert adapter.config == {}
        assert adapter.is_running() is False

    def test_adapter_initializes_with_empty_config(self):
        """BaseOutputAdapter should handle empty config."""
        adapter = _create_test_adapter({})
        
        assert adapter.config == {}
        assert adapter.is_running() is False


class TestBaseOutputAdapterLifecycle:
    """Tests for BaseOutputAdapter lifecycle methods."""

    @pytest.mark.asyncio
    async def test_adapter_start_sets_running_flag(self):
        """start() should set running flag to True."""
        adapter = _create_test_adapter({})
        
        assert adapter.is_running() is False
        
        await adapter.start()
        
        assert adapter.is_running() is True

    @pytest.mark.asyncio
    async def test_adapter_stop_clears_running_flag(self):
        """stop() should set running flag to False."""
        adapter = _create_test_adapter({})
        await adapter.start()
        
        assert adapter.is_running() is True
        
        await adapter.stop()
        
        assert adapter.is_running() is False

    def test_is_running_returns_correct_state(self):
        """is_running() should return the correct running state."""
        adapter = _create_test_adapter({})
        
        # Initially not running
        assert adapter.is_running() is False


class TestBaseOutputAdapterSendDMX:
    """Tests for BaseOutputAdapter send_dmx method."""

    @pytest.mark.asyncio
    async def test_send_dmx_receives_buffer(self):
        """send_dmx() should accept buffer parameter."""
        adapter = _create_test_adapter({})
        
        dmx_buffer = {(1, 10): 135, (1, 20): 255}
        
        # Should not raise any errors
        await adapter.send_dmx(dmx_buffer)

    @pytest.mark.asyncio
    async def test_send_dmx_with_empty_buffer(self):
        """send_dmx() should handle empty buffer."""
        adapter = _create_test_adapter({})
        
        # Should not raise any errors with empty buffer
        await adapter.send_dmx({})

    @pytest.mark.asyncio
    async def test_send_dmx_with_multiple_universes(self):
        """send_dmx() should handle buffer with multiple universes."""
        adapter = _create_test_adapter({})
        
        dmx_buffer = {
            (1, 10): 135,
            (2, 20): 255,
            (1, 30): 100,
            (3, 5): 0
        }
        
        # Should not raise any errors
        await adapter.send_dmx(dmx_buffer)