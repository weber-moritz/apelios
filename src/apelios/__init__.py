"""
Apelios - Lighting and Streaming Control System

This package provides modules for:
- ArtNet DMX lighting control
- Steam Deck integration
- WebRTC video streaming (sender and receiver)
    - Optional person detection for video streams
- WebSocket signaling server for WebRTC connections
"""

__version__ = '0.1.0'

# Import submodules with optional dependencies
# Only import what's available to avoid ImportErrors
__all__ = []

try:
    from . import artnet
    __all__.append('artnet')
except ImportError as e:
    import logging
    logging.debug(f"artnet module not available: {e}")

try:
    from . import steamdeck
    __all__.append('steamdeck')
except ImportError as e:
    import logging
    logging.debug(f"steamdeck module not available (requires libhidapi): {e}")

try:
    from . import video_receiver
    __all__.append('video_receiver')
except ImportError as e:
    import logging
    logging.debug(f"video_receiver module not available: {e}")

try:
    from . import video_sender
    __all__.append('video_sender')
except ImportError as e:
    import logging
    logging.debug(f"video_sender module not available: {e}")

try:
    from . import signaling_server
    __all__.append('signaling_server')
except ImportError as e:
    import logging
    logging.debug(f"signaling_server module not available: {e}")