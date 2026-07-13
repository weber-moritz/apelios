"""Tests for ArtNetAdapter - Complete implementation tests.

These tests verify the full ArtNet adapter implementation including
aioartnet integration, config usage, rate limiting, and DMX formatting.
"""

from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from apelios.output.adapters.artnet_adapter import ArtNetAdapter


class MockArtNetUniverse:
    """Mock ArtNet universe for testing."""
    
    def __init__(self):
        self.sent_dmx_data = []
    
    def set_dmx(self, dmx_data: bytes) -> None:
        """Mock set_dmx method."""
        self.sent_dmx_data.append(dmx_data)


class MockArtNetClient:
    """Mock aioartnet client for testing."""
    
    def __init__(self):
        self.unicast_ip = None
        self.broadcast_ip = None
        self.connected = False
        self.universe_objs = {}
    
    async def connect(self) -> None:
        """Mock connect method."""
        self.connected = True
    
    def set_port_config(self, universe: int, is_input: bool):
        """Mock set_port_config method."""
        if universe not in self.universe_objs:
            self.universe_objs[universe] = MockArtNetUniverse()
        return self.universe_objs[universe]
    
    @property
    def protocol(self):
        """Mock protocol property."""
        class MockProtocol:
            transport = MagicMock()
        return MockProtocol()


@pytest.fixture
def mock_artnet_client():
    """Provide a mocked aioartnet client."""
    return MockArtNetClient()


@pytest.fixture
def artnet_adapter():
    """Provide an ArtNetAdapter with test config."""
    config = {
        "source_ip": "127.0.0.1",
        "target_ip": "127.0.0.1",
        "universe": 1,
        "output_rate_hz": 40
    }
    return ArtNetAdapter(config)


@pytest.fixture
def artnet_adapter_universe_2():
    """Provide an ArtNetAdapter configured for universe 2."""
    config = {
        "source_ip": "127.0.0.1",
        "target_ip": "127.0.0.1", 
        "universe": 2,
        "output_rate_hz": 40
    }
    return ArtNetAdapter(config)


class TestArtNetAdapterInitialization:
    """Tests for ArtNetAdapter initialization."""

    def test_artnet_adapter_initializes_with_config(self):
        """ArtNetAdapter should initialize with config."""
        config = {
            "source_ip": "192.168.1.1",
            "target_ip": "192.168.1.255",
            "universe": 10,
            "output_rate_hz": 40
        }
        adapter = ArtNetAdapter(config)
        
        assert adapter.config == config
        assert adapter.universe == 10
        assert adapter.source_ip == "192.168.1.1"
        assert adapter.target_ip == "192.168.1.255"
        assert adapter.output_rate_hz == 40
        assert adapter.is_running() is False

    def test_artnet_adapter_initializes_with_partial_config(self):
        """ArtNetAdapter should handle partial config with defaults."""
        config = {"universe": 5}
        adapter = ArtNetAdapter(config)
        
        assert adapter.universe == 5
        assert adapter.source_ip == "127.0.0.1"  # default
        assert adapter.target_ip == "127.0.0.1"  # default
        assert adapter.output_rate_hz == 40  # default
        assert adapter.config == config

    def test_artnet_adapter_initializes_with_empty_config(self):
        """ArtNetAdapter should handle empty config."""
        adapter = ArtNetAdapter({})
        
        # Should default to universe 0
        assert adapter.universe == 0
        assert adapter.source_ip == "127.0.0.1"
        assert adapter.target_ip == "127.0.0.1"
        assert adapter.output_rate_hz == 40

    def test_artnet_adapter_initializes_with_none_config(self):
        """ArtNetAdapter should handle None config."""
        adapter = ArtNetAdapter(None)
        
        # Should default to universe 0
        assert adapter.universe == 0
        assert adapter.source_ip == "127.0.0.1"
        assert adapter.target_ip == "127.0.0.1"
        assert adapter.output_rate_hz == 40


class TestArtNetAdapterLifecycle:
    """Tests for ArtNetAdapter lifecycle methods."""

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_start_sets_running_flag(self, mock_client_class):
        """start() should set running flag to True and configure client with correct IPs."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        config = {"source_ip": "192.168.1.1", "target_ip": "192.168.1.255", "universe": 1}
        adapter = ArtNetAdapter(config)
        
        assert adapter.is_running() is False
        
        await adapter.start()
        
        assert adapter.is_running() is True
        # Verify client was configured with correct IPs
        assert mock_client.unicast_ip == "192.168.1.1"
        assert mock_client.broadcast_ip == "192.168.1.255"
        assert mock_client.connected is True
        # Verify universe was configured
        assert 1 in mock_client.universe_objs

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_stop_clears_running_flag(self, mock_client_class):
        """stop() should set running flag to False and clean up."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({})
        await adapter.start()
        
        assert adapter.is_running() is True
        
        await adapter.stop()
        
        assert adapter.is_running() is False
        assert adapter.client is None
        assert adapter.universe_obj is None

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_start_is_idempotent(self, mock_client_class):
        """start() should be idempotent - multiple calls don't cause issues."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({})
        
        await adapter.start()
        await adapter.start()  # Second call
        
        assert adapter.is_running() is True
        # Should only connect once
        assert mock_client.connected is True

    @pytest.mark.asyncio
    async def test_artnet_adapter_stop_is_idempotent(self):
        """stop() should be idempotent - multiple calls don't cause issues."""
        adapter = ArtNetAdapter({})
        
        await adapter.stop()  # Stop when not running
        await adapter.stop()  # Stop again
        
        assert adapter.is_running() is False


class TestArtNetAdapterUniverseFilter:
    """Tests for ArtNetAdapter universe filtering functionality (Task 017)."""

    def test_universe_filter_single_int(self):
        """universe config as int should create single-universe filter."""
        adapter = ArtNetAdapter({"universe": 5})
        assert adapter.universe_filter == [5]

    def test_universe_filter_list_of_ints(self):
        """universe config as list should create multi-universe filter."""
        adapter = ArtNetAdapter({"universe": [0, 1, 2]})
        assert adapter.universe_filter == [0, 1, 2]

    def test_universe_filter_empty_list(self):
        """universe config as empty list should send all universes."""
        adapter = ArtNetAdapter({"universe": []})
        assert adapter.universe_filter == []

    def test_universe_filter_missing(self):
        """Missing universe config should default to [0]."""
        adapter = ArtNetAdapter({})
        assert adapter.universe_filter == [0]

    def test_universe_filter_none(self):
        """None universe config should default to [0]."""
        adapter = ArtNetAdapter(None)
        assert adapter.universe_filter == [0]


class TestArtNetAdapterSendDMX:
    """Tests for ArtNetAdapter send_dmx method."""

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_send_dmx_filters_by_universe(self, mock_client_class):
        """send_dmx() should only send DMX for configured universe."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({"universe": 1})
        await adapter.start()
        
        # Buffer contains data for universe 1 and 2
        dmx_buffer = {
            (1, 10): 135,    # Should be sent
            (1, 20): 255,    # Should be sent
            (2, 5): 100,     # Should be ignored
            (3, 15): 50      # Should be ignored
        }
        
        await adapter.send_dmx(dmx_buffer)
        
        # Get the universe object for universe 1
        universe_obj = mock_client.universe_objs[1]
        assert len(universe_obj.sent_dmx_data) == 1
        
        # Verify only channels 10 and 20 were set (others are 0)
        sent_data = universe_obj.sent_dmx_data[0]
        assert sent_data[9] == 135   # Channel 10 (0-indexed)
        assert sent_data[19] == 255  # Channel 20 (0-indexed)
        assert sent_data[4] == 0     # Channel 5 (0-indexed) - from universe 2, should be 0

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_send_dmx_handles_sparse_buffer(self, mock_client_class):
        """send_dmx() should handle sparse buffer (only some channels)."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({"universe": 1})
        await adapter.start()
        
        # Sparse buffer with only a few channels
        dmx_buffer = {
            (1, 1): 100,
            (1, 10): 150,
            (1, 100): 200
        }
        
        await adapter.send_dmx(dmx_buffer)
        
        universe_obj = mock_client.universe_objs[1]
        assert len(universe_obj.sent_dmx_data) == 1
        
        sent_data = universe_obj.sent_dmx_data[0]
        assert sent_data[0] == 100   # Channel 1
        assert sent_data[9] == 150   # Channel 10
        assert sent_data[99] == 200  # Channel 100

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_send_dmx_formats_correctly(self, mock_client_class):
        """send_dmx() should format DMX data correctly with all zeros for other channels."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({"universe": 1})
        await adapter.start()
        
        # Single channel
        dmx_buffer = {(1, 1): 135}
        
        await adapter.send_dmx(dmx_buffer)
        
        universe_obj = mock_client.universe_objs[1]
        sent_data = universe_obj.sent_dmx_data[0]
        assert sent_data[0] == 135
        # All other channels should be 0
        assert all(v == 0 for i, v in enumerate(sent_data) if i != 0)

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_handles_16bit_values(self, mock_client_class):
        """send_dmx() should handle 16-bit DMX values by splitting into MSB/LSB."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({"universe": 1})
        await adapter.start()
        
        # 16-bit values (0-65535)
        dmx_buffer = {
            (1, 1): 65535,  # Max 16-bit value: MSB=255, LSB=255
            (1, 3): 32768,   # Mid-range: MSB=128, LSB=0
            (1, 5): 256,     # MSB=1, LSB=0
        }
        
        await adapter.send_dmx(dmx_buffer)
        
        universe_obj = mock_client.universe_objs[1]
        sent_data = universe_obj.sent_dmx_data[0]
        
        # Channel 1 (MSB) and 2 (LSB) for value 65535
        assert sent_data[0] == 255  # MSB of 65535
        assert sent_data[1] == 255  # LSB of 65535
        
        # Channel 3 (MSB) and 4 (LSB) for value 32768
        assert sent_data[2] == 128  # MSB of 32768
        assert sent_data[3] == 0    # LSB of 32768
        
        # Channel 5 (MSB) and 6 (LSB) for value 256
        assert sent_data[4] == 1    # MSB of 256
        assert sent_data[5] == 0    # LSB of 256

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_send_dmx_with_empty_buffer(self, mock_client_class):
        """send_dmx() should handle empty buffer by sending all zeros."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({"universe": 1})
        await adapter.start()
        
        await adapter.send_dmx({})
        
        # Should still send (all zeros)
        universe_obj = mock_client.universe_objs[1]
        assert len(universe_obj.sent_dmx_data) == 1
        assert all(v == 0 for v in universe_obj.sent_dmx_data[0])

    @pytest.mark.asyncio
    async def test_artnet_adapter_send_dmx_does_not_send_when_not_running(self):
        """send_dmx() should not send when adapter is not running."""
        adapter = ArtNetAdapter({"universe": 1})
        # Don't call start()
        
        dmx_buffer = {(1, 1): 135}
        await adapter.send_dmx(dmx_buffer)
        
        # Should not have tried to send
        assert adapter.client is None

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_artnet_adapter_send_dmx_does_not_send_when_client_failed_to_connect(self, mock_client_class):
        """send_dmx() should not send when client connection failed."""
        # Mock client that fails to connect
        mock_client = MockArtNetClient()
        mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client_class.return_value = mock_client
        
        adapter = ArtNetAdapter({"universe": 1})
        await adapter.start()  # Will fail to connect but still mark as running
        
        dmx_buffer = {(1, 1): 135}
        await adapter.send_dmx(dmx_buffer)
        
        # Should not have sent anything because client is None
        assert adapter.client is None


class TestArtNetAdapterUniverseFilterSending:
    """Tests for ArtNetAdapter universe filter behavior during send_dmx (Task 017)."""

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_send_dmx_with_multiple_universes_in_filter(self, mock_client_class):
        """send_dmx() should create and send to multiple universes in filter."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        # Configure adapter with multiple universes
        adapter = ArtNetAdapter({"universe": [0, 2]})
        await adapter.start()
        
        # Verify both universes were created
        assert 0 in mock_client.universe_objs
        assert 2 in mock_client.universe_objs
        assert 1 not in mock_client.universe_objs  # Not in filter
        
        # Send DMX with data for universes 0, 1, 2
        dmx_buffer = {
            (0, 1): 100,
            (1, 1): 150,  # Should be ignored (not in filter)
            (2, 1): 200,
        }
        await adapter.send_dmx(dmx_buffer)
        
        # Verify only universes 0 and 2 received data
        assert len(mock_client.universe_objs[0].sent_dmx_data) == 1
        assert len(mock_client.universe_objs[2].sent_dmx_data) == 1

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_send_dmx_with_empty_filter_sends_all_universes_with_data(self, mock_client_class):
        """send_dmx() with empty filter should send all universes that have data."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        # Configure adapter with empty filter (send all)
        adapter = ArtNetAdapter({"universe": []})
        await adapter.start()
        
        # With empty filter, should default to creating universe 0
        assert 0 in mock_client.universe_objs
        
        # Send DMX with data for universes 0, 1, 2
        dmx_buffer = {
            (0, 1): 100,
            (1, 1): 150,
            (2, 1): 200,
        }
        await adapter.send_dmx(dmx_buffer)
        
        # With empty filter, all universes with data should be sent
        # But only universe 0 was created during start (default for empty filter)
        # So only universe 0 should receive data
        assert len(mock_client.universe_objs[0].sent_dmx_data) == 1

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_send_dmx_with_filter_sends_whitelisted_universes_only(self, mock_client_class):
        """send_dmx() should send only whitelisted universes, even if others have data."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        # Configure adapter with specific universes
        adapter = ArtNetAdapter({"universe": [0, 2]})
        await adapter.start()
        
        # Send DMX with data for universe 1 only (not in filter)
        dmx_buffer = {
            (1, 1): 150,
        }
        await adapter.send_dmx(dmx_buffer)
        
        # Universe 0 and 2 should still send (even with no data for those universes)
        assert len(mock_client.universe_objs[0].sent_dmx_data) == 1
        assert len(mock_client.universe_objs[2].sent_dmx_data) == 1
        # Universe 1 was not created, so no data sent there
        assert 1 not in mock_client.universe_objs

    @pytest.mark.asyncio
    @patch("apelios.output.adapters.artnet_adapter.ArtNetClient")
    async def test_send_dmx_with_empty_filter_dynamically_creates_universes(self, mock_client_class):
        """send_dmx() with empty filter should dynamically create universes for any universe with data."""
        mock_client = MockArtNetClient()
        mock_client_class.return_value = mock_client
        
        # Configure adapter with empty filter (send all universes with data)
        adapter = ArtNetAdapter({"universe": []})
        await adapter.start()
        
        # With empty filter, only universe 0 should be created during start
        assert 0 in mock_client.universe_objs
        assert 1 not in mock_client.universe_objs
        assert 2 not in mock_client.universe_objs
        
        # Send DMX with data for universes 0, 1, and 2
        dmx_buffer = {
            (0, 1): 100,
            (1, 1): 150,
            (2, 1): 200,
        }
        await adapter.send_dmx(dmx_buffer)
        
        # All three universes should now have universe objects created
        # and all should have sent data
        assert 0 in mock_client.universe_objs
        assert 1 in mock_client.universe_objs
        assert 2 in mock_client.universe_objs
        
        # Verify data was sent for all universes
        assert len(mock_client.universe_objs[0].sent_dmx_data) == 1
        assert len(mock_client.universe_objs[1].sent_dmx_data) == 1
        assert len(mock_client.universe_objs[2].sent_dmx_data) == 1

