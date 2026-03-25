"""
WebSocket signaling client for WebRTC connections.
"""
import asyncio
import json
import logging
from aiortc import RTCSessionDescription
import websockets

logger = logging.getLogger(__name__)


class WebSocketSignaling:
    """WebSocket-based signaling for WebRTC connections."""
    
    def __init__(self, host="127.0.0.1", port=9999, client_type="receiver"):
        """
        Initialize WebSocket signaling.
        
        Args:
            host: WebSocket server host
            port: WebSocket server port
            client_type: "sender" or "receiver"
        """
        self.uri = f"ws://{host}:{port}"
        self.client_type = client_type
        self.websocket = None
        self._receive_queue = asyncio.Queue()
        self._receive_task = None
        
    async def connect(self):
        """Connect to the signaling server."""
        logger.info(f"Connecting to signaling server at {self.uri} as {self.client_type}")
        self.websocket = await websockets.connect(self.uri)
        
        # Send client type identification
        await self.websocket.send(json.dumps({"type": self.client_type}))
        logger.info(f"Connected as {self.client_type}")
        
        # Start receiving messages
        self._receive_task = asyncio.create_task(self._receive_loop())
        
    async def _receive_loop(self):
        """Background task to receive messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("message_type")
                
                if msg_type in ["offer", "answer"]:
                    # Reconstruct RTCSessionDescription
                    # Use message_type (offer/answer) not the client type field
                    obj = RTCSessionDescription(
                        sdp=data["sdp"],
                        type=msg_type  # Use message_type, not data["type"]
                    )
                    await self._receive_queue.put(obj)
                elif msg_type == "request_offer":
                    # Signal to sender to create new offer
                    await self._receive_queue.put({"request_offer": True})
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            await self._receive_queue.put(None)
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            await self._receive_queue.put(None)
    
    async def send(self, description):
        """
        Send an offer or answer.
        
        Args:
            description: RTCSessionDescription
        """
        if not self.websocket:
            raise RuntimeError("Not connected to signaling server")
        
        message = {
            "type": self.client_type,
            "message_type": description.type,
            "sdp": description.sdp,
        }
        
        await self.websocket.send(json.dumps(message))
        logger.debug(f"Sent {description.type}")
    
    async def receive(self):
        """
        Receive an offer or answer.
        
        Returns:
            RTCSessionDescription or None if connection closed
        """
        obj = await self._receive_queue.get()
        return obj
    
    async def close(self):
        """Close the signaling connection."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket signaling closed")
