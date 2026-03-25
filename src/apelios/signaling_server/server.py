#!/usr/bin/env python3
"""
WebSocket Signaling Server for WebRTC

A persistent signaling server that handles offer/answer exchange
between sender and multiple receivers.
"""

import asyncio
import json
import logging
from websockets.server import serve
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalingServer:
    """WebSocket signaling server for WebRTC connections."""
    
    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port
        self.sender = None
        self.receivers = set()
        
    async def handle_client(self, websocket):
        """Handle a connected client (sender or receiver)."""
        client_type = None
        try:
            # First message identifies client type
            message = await websocket.recv()
            data = json.loads(message)
            client_type = data.get("type")
            
            if client_type == "sender":
                await self.handle_sender(websocket)
            elif client_type == "receiver":
                await self.handle_receiver(websocket)
            else:
                logger.warning(f"Unknown client type: {client_type}")
                
        except websockets.exceptions.ConnectionClosed:
            if client_type == "sender":
                logger.info("Sender disconnected")
                self.sender = None
            elif client_type == "receiver":
                logger.info("Receiver disconnected")
                self.receivers.discard(websocket)
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            
    async def handle_sender(self, websocket):
        """Handle sender connection."""
        logger.info("Sender connected")
        self.sender = websocket
        
        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("message_type")
                
                if msg_type == "offer":
                    # Forward offer to all receivers
                    logger.info(f"Forwarding offer to {len(self.receivers)} receiver(s)")
                    dead_receivers = set()
                    for receiver in self.receivers:
                        try:
                            await receiver.send(message)
                        except:
                            dead_receivers.add(receiver)
                    
                    # Clean up dead connections
                    self.receivers -= dead_receivers
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.sender = None
            logger.info("Sender disconnected")
            
    async def handle_receiver(self, websocket):
        """Handle receiver connection."""
        logger.info("Receiver connected")
        self.receivers.add(websocket)
        
        try:
            # Send current offer if sender is connected
            if self.sender:
                try:
                    # Request fresh offer from sender
                    await self.sender.send(json.dumps({"message_type": "request_offer"}))
                except:
                    logger.warning("Could not request offer from sender")
            
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("message_type")
                
                if msg_type == "answer":
                    # Forward answer to sender
                    if self.sender:
                        try:
                            await self.sender.send(message)
                            logger.info("Forwarded answer to sender")
                        except:
                            logger.warning("Could not forward answer to sender")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.receivers.discard(websocket)
            logger.info("Receiver disconnected")
            
    async def start(self):
        """Start the signaling server."""
        logger.info(f"Starting signaling server on {self.host}:{self.port}")
        server = await serve(self.handle_client, self.host, self.port)
        logger.info("Signaling server ready")
        return server


async def main():
    """Run the signaling server."""
    server = SignalingServer(host="127.0.0.1", port=9999)
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down signaling server")
