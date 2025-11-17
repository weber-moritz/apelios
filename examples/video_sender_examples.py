#!/usr/bin/env python3
"""
Example usage of the video-sender module.
"""
import asyncio
import logging
from apelios.video_sender import VideoSender, run_sender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def example_1_simple_function():
    """Example 1: Using the simple run_sender function."""
    print("\n=== Example 1: Simple Function Call ===\n")
    
    # Default settings (640x480 @ 30fps)
    await run_sender(
        host="127.0.0.1",
        port=9999,
        camera_id=0
    )


async def example_2_custom_resolution():
    """Example 2: Custom resolution and FPS."""
    print("\n=== Example 2: Custom Resolution ===\n")
    
    await run_sender(
        host="127.0.0.1",
        port=9999,
        camera_id=0,
        width=1280,
        height=720,
        fps=30
    )


async def example_3_class_usage():
    """Example 3: Using the VideoSender class directly."""
    print("\n=== Example 3: Using VideoSender Class ===\n")
    
    sender = VideoSender(
        camera_id=0,
        width=640,
        height=480,
        fps=30
    )
    
    await sender.start(host="127.0.0.1", port=9999)


async def main():
    """Main entry point."""
    HOST = "127.0.0.1"
    PORT = 9999
    CAMERA_ID = 0
    
    print("Starting video sender...")
    print(f"Host: {HOST}:{PORT}")
    print(f"Camera: {CAMERA_ID}")
    print("Press Ctrl+C to stop\n")
    
    # Basic usage with default settings
    await run_sender(
        host=HOST,
        port=PORT,
        camera_id=CAMERA_ID
    )
    
    # Or with custom resolution
    # await run_sender(
    #     host=HOST,
    #     port=PORT,
    #     camera_id=CAMERA_ID,
    #     width=1280,
    #     height=720,
    #     fps=30
    # )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
