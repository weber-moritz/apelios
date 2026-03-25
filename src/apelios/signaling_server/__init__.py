"""
Signaling Server Module

Provides WebSocket-based signaling server for WebRTC connections.
Handles offer/answer exchange between sender and multiple receivers.
"""

from .server import SignalingServer
from .websocket_signaling import WebSocketSignaling

__all__ = ['SignalingServer', 'WebSocketSignaling']
