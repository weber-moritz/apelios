# src/apelios/artnet/controller.py
"""Art-Net controller for sending Remote Input to GrandMA."""

import asyncio
import logging
from typing import Optional
from aioartnet import ArtNetClient, ArtNetUniverse

log = logging.getLogger(__name__)


class ArtNetController:
    """
    Art-Net Remote Input sender for GrandMA integration.
    Sends continuous Art-Net stream on specified universe.
    """
    
    def __init__(self, source_ip: str, target_ip: str, 
                 universe: int = 10, output_rate_hz: float = 40):
        """
        Initialize Art-Net controller.
        
        Args:
            source_ip: Steam Deck IP address (e.g., "192.168.8.1")
            target_ip: Network broadcast or target device IP (e.g., "192.168.8.255" or "192.168.8.144")
            universe: Remote Input universe (default 10, must differ from GrandMA output!)
            output_rate_hz: Art-Net output rate in Hz (default 40Hz)
        """
        
        self.source_ip = source_ip
        self.target_ip = target_ip
        
        self.universe = universe
        self.output_rate_hz = output_rate_hz
        
        self.client = ArtNetClient()
        self.universe_obj: Optional[ArtNetUniverse] = None
        
        # Initialize all 512 DMX channels to 0
        self.dmx_data = bytearray(512)
        
        self._running = False
        self._connected = False
    
    async def connect(self):
        """
        Connect to Art-Net network.
        Must be called before sending data.
        """
        if self._connected:
            log.warning("Already connected")
            return
        
        self.client.unicast_ip = self.source_ip            
        self.client.broadcast_ip = self.target_ip
        
        await self.client.connect()
        
        # Configure universe for output
        self.universe_obj = self.client.set_port_config(
            universe=self.universe,
            is_input=True  # Input to network = output from us
        )
        
        self._connected = True
        
        log.info(f"Art-Net connected on {self.source_ip}")
        log.info(f"Sending Remote Input on Universe {self.universe}")
        log.info(f"Configure GrandMA to receive Universe {self.universe} as Remote Input")
    
    def set_channel(self, channel: int, value: int):
        """
        Set a DMX channel value.
        
        Args:
            channel: DMX channel (1-512)
            value: DMX value (0-255)
        
        Returns:
            bool: True if successful, False if invalid parameters
        """
        # Validate channel
        if not (1 <= channel <= 512):
            log.warning(f"Channel {channel} out of range (1-512)")
            return False
        
        # Validate value
        if not (0 <= value <= 255):
            log.warning(f"Value {value} out of range (0-255)")
            return False
        
        # Set channel (convert 1-indexed to 0-indexed)
        self.dmx_data[channel - 1] = value
        return True
    
    def set_16bit(self, channel: int, value: int):
        """
        Set a 16-bit DMX value (for pan/tilt).
        
        Args:
            channel: Start channel for MSB (1-511)
            value: 16-bit value (0-65535)
        
        Returns:
            bool: True if successful
        """
        if not (1 <= channel <= 511):
            log.warning(f"16-bit channel {channel} out of range (1-511)")
            return False
        
        if not (0 <= value <= 65535):
            log.warning(f"16-bit value {value} out of range (0-65535)")
            return False
        
        # Split into MSB and LSB
        msb = (value >> 8) & 0xFF
        lsb = value & 0xFF
        
        self.set_channel(channel, msb)      # MSB
        self.set_channel(channel + 1, lsb)  # LSB
        
        return True
    
    def get_channel(self, channel: int) -> Optional[int]:
        """
        Get current value of a channel.
        
        Args:
            channel: DMX channel (1-512)
        
        Returns:
            Current value (0-255) or None if invalid channel
        """
        if 1 <= channel <= 512:
            return self.dmx_data[channel - 1]
        return None
    
    def clear_all(self):
        """Set all channels to 0."""
        self.dmx_data = bytearray(512)
        log.debug("Cleared all DMX channels to 0")
    
    def send_now(self):
        """
        Immediately send current DMX state (all 512 channels).
        Normally not needed, as start() sends continuously.
        """
        if not self._connected:
            log.error("Not connected! Call connect() first")
            return
        
        if self.universe_obj:
            self.universe_obj.set_dmx(bytes(self.dmx_data))
    
    async def start(self):
        """
        Start continuous Art-Net output.
        Sends all 512 channels repeatedly at configured rate.
        """
        if not self._connected:
            log.error("Not connected! Call connect() first")
            return
        
        if self._running:
            log.warning("Output loop already running")
            return
        
        self._running = True
        interval = 1.0 / self.output_rate_hz
        
        log.info(f"Starting Art-Net output at {self.output_rate_hz}Hz")
        
        try:
            while self._running:
                # Send all 512 channels
                self.send_now()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            log.info("Art-Net output loop cancelled")
        finally:
            self._running = False
    
    def stop(self):
        """Stop continuous Art-Net output."""
        if self._running:
            self._running = False
            log.info("Stopping Art-Net output")
    
    async def close(self):
        """
        Close Art-Net connection.
        Clears all channels and stops output.
        """
        # Clear all channels before closing
        self.clear_all()
        self.send_now()
        await asyncio.sleep(0.1)  # Give time for last packet to send
        
        self.stop()
        
        if self.client.protocol and self.client.protocol.transport:
            self.client.protocol.transport.close()
            log.info("Art-Net connection closed")
        
        self._connected = False
    
    def __repr__(self):
        return f"ArtNetController(universe={self.universe}, connected={self._connected}, running={self._running})"