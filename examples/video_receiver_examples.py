#!/usr/bin/env python3
"""
Example usage of the video-receiver module.
Shows both streaming-only and streaming with person detection.
"""
import asyncio
import logging
from apelios.video_receiver import VideoReceiver, run_receiver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def example_1_streaming_only():
    """Example 1: Basic video streaming without detection."""
    print("\n=== Example 1: Video Streaming Only ===\n")
    
    receiver = VideoReceiver(
        display=True,
        save_frames=False,
        enable_detection=False  # Detection disabled
    )
    
    await receiver.handle_track(...)  # Track from WebRTC connection


async def example_2_with_detection():
    """Example 2: Video streaming with person detection."""
    print("\n=== Example 2: Video Streaming with Person Detection ===\n")
    
    receiver = VideoReceiver(
        display=True,
        save_frames=True,
        output_dir="detections",
        enable_detection=True,      # Enable detection
        detection_method="hog",      # Use HOG detector
        confidence_threshold=0.5
    )
    
    await receiver.handle_track(...)  # Track from WebRTC connection


async def example_3_simple_function():
    """Example 3: Using the simple run_receiver function."""
    print("\n=== Example 3: Simple Function Call ===\n")
    
    # Without detection (streaming only)
    await run_receiver(
        host="127.0.0.1",
        port=9999,
        display=True,
        enable_detection=False
    )


async def example_4_with_detection_function():
    """Example 4: Using run_receiver with detection."""
    print("\n=== Example 4: Function Call with Detection ===\n")
    
    # With detection
    await run_receiver(
        host="127.0.0.1",
        port=9999,
        display=True,
        save_frames=True,
        enable_detection=True,
        detection_method="hog",
        confidence_threshold=0.5
    )


async def main():
    """Main entry point - run one of the examples."""
    
    # Choose which example to run
    HOST = "127.0.0.1"
    PORT = 9999
    
    # Example: Streaming only (no detection)
    print("Starting video receiver (streaming only)...")
    await run_receiver(
        host=HOST,
        port=PORT,
        display=True,
        enable_detection=False
    )
    
    # Or: Streaming with person detection
    # print("Starting video receiver with person detection...")
    # await run_receiver(
    #     host=HOST,
    #     port=PORT,
    #     display=True,
    #     enable_detection=True,
    #     detection_method="hog"
    # )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
