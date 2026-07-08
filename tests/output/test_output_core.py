"""Tests for OutputCore - TDD Red Phase.

These tests define the expected behavior of the OutputCore
before full implementation exists.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestOutputCoreInitialization:
    """Tests for OutputCore initialization."""

    def test_core_initializes_with_empty_buffer(self):
        """OutputCore should initialize with empty DMX buffer."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        
        assert core.dmx_buffer == {}
        assert core.adapters == []


class TestOutputCoreBuffer:
    """Tests for DMX buffer management."""

    def test_add_to_buffer_stores_value(self):
        """add_to_buffer should store a single channel correctly."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        core.add_to_buffer(universe=1, address=10, value=135)
        
        assert core.dmx_buffer == {(1, 10): 135}

    def test_add_to_buffer_updates_existing_channel(self):
        """add_to_buffer should overwrite existing channel value."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        core.add_to_buffer(universe=1, address=10, value=135)
        core.add_to_buffer(universe=1, address=10, value=200)
        
        assert core.dmx_buffer == {(1, 10): 200}

    def test_add_to_buffer_handles_multiple_universes(self):
        """add_to_buffer should store across different universes."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        core.add_to_buffer(universe=1, address=10, value=135)
        core.add_to_buffer(universe=2, address=20, value=200)
        core.add_to_buffer(universe=1, address=11, value=50)
        
        assert core.dmx_buffer == {
            (1, 10): 135,
            (2, 20): 200,
            (1, 11): 50,
        }

    def test_buffer_is_sparse(self):
        """Buffer should only contain channels that have been set."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        core.add_to_buffer(universe=1, address=10, value=135)
        
        # Channel (1, 11) should not exist
        assert (1, 11) not in core.dmx_buffer
        assert len(core.dmx_buffer) == 1


class TestOutputCoreAdapterRegistration:
    """Tests for adapter registration."""

    def test_register_adapter_adds_to_list(self):
        """register_adapter should add adapter to list."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        mock_adapter = MagicMock()
        
        core.register_adapter(mock_adapter)
        
        assert len(core.adapters) == 1
        assert core.adapters[0] is mock_adapter


class TestOutputCoreProcessFrame:
    """Tests for frame processing."""

    @pytest.mark.asyncio
    async def test_send_to_adapters_calls_all_adapters(self):
        """process_frame should call send_dmx on all registered adapters."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        mock_adapter1 = MagicMock()
        mock_adapter1.send_dmx = AsyncMock()
        mock_adapter2 = MagicMock()
        mock_adapter2.send_dmx = AsyncMock()
        
        core.register_adapter(mock_adapter1)
        core.register_adapter(mock_adapter2)
        core.add_to_buffer(universe=1, address=10, value=135)
        
        await core.process_frame()
        
        mock_adapter1.send_dmx.assert_awaited_once()
        mock_adapter2.send_dmx.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_frame_clears_buffer(self):
        """process_frame should clear buffer after sending."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        mock_adapter = MagicMock()
        mock_adapter.send_dmx = AsyncMock()
        
        core.register_adapter(mock_adapter)
        core.add_to_buffer(universe=1, address=10, value=135)
        core.add_to_buffer(universe=1, address=11, value=200)
        
        await core.process_frame()
        
        assert core.dmx_buffer == {}

    @pytest.mark.asyncio
    async def test_process_frame_with_no_buffer_is_noop(self):
        """process_frame should handle empty buffer without error."""
        from apelios.output.output_core import OutputCore
        
        core = OutputCore()
        
        # Should not raise any errors
        await core.process_frame()
        
        assert core.dmx_buffer == {}
