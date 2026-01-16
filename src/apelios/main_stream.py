#!/usr/bin/env python3
"""
Apelios Main Stream Application

This module starts the signaling server and WebRTC video sender to stream camera feed.
To run this module use `python -m apelios.main_stream`
"""
import asyncio
import logging
import sys
import time
from datetime import datetime
from .video_sender import VideoSender, run_sender
from .signaling_server import SignalingServer

# Setup logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for the stream application.
    Starts the video sender with configured settings.
    """
    # Configuration
    HOST = "127.0.0.1" # "192.168.8.144" # "127.0.0.1" #  # Signaling server host
    PORT = 9999         # Signaling server port
    CAMERA_ID = 1       # Camera device ID
    WIDTH = 640         # Video width
    HEIGHT = 480        # Video height
    FPS = 30            # Frames per second
    
    # Print banner
    print("\n" + "=" * 70)
    print("APELIOS VIDEO STREAM SENDER")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    print("Configuration:")
    print(f"   Signaling Server: {HOST}:{PORT}")
    print(f"   Camera ID: {CAMERA_ID}")
    print(f"   Resolution: {WIDTH}x{HEIGHT} @ {FPS} fps")
    print("-" * 70)
    print("Status:")
    print("   • Starting signaling server...")
    
    start_time = time.time()
    
    try:
        # Start the signaling server
        signaling_server = SignalingServer(host=HOST, port=PORT)
        server = await signaling_server.start()
        
        print("   • Signaling server ready")
        print("   • Initializing camera...")
        
        # Start the video sender
        await run_sender(
            host=HOST,
            port=PORT,
            camera_id=CAMERA_ID,
            width=WIDTH,
            height=HEIGHT,
            fps=FPS
        )
    except KeyboardInterrupt:
        print("\n" + "-" * 70)
        elapsed = time.time() - start_time
        minutes, seconds = divmod(int(elapsed), 60)
        hours, minutes = divmod(minutes, 60)
        print(f"Stream Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")
        print("Stream stopped by user")
        print("=" * 70 + "\n")
    except Exception as e:
        print("\n" + "-" * 70)
        print(f"Error occurred: {e}")
        print("=" * 70 + "\n")
        logger.exception("Detailed error information:")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}\n")
        sys.exit(1)
