#!/usr/bin/env python3
"""
Robust WebRTC receiver for Linux localhost testing.
Receives video stream using aiortc with improved error handling.
"""
import asyncio
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RobustVideoReceiver:
    """Robust video receiver with error handling and recovery."""
    
    def __init__(self, display=True, save_frames=False, output_dir="imgs"):
        self.display = display
        self.save_frames = save_frames
        self.output_dir = output_dir
        self.track = None
        self.frame_count = 0
        self.error_count = 0
        self.max_consecutive_errors = 10
        self.running = True
        
        # Create output directory if saving frames
        if self.save_frames:
            import os
            os.makedirs(self.output_dir, exist_ok=True)
    
    async def handle_track(self, track):
        """
        Handle incoming video track with robust error handling.
        
        Args:
            track: MediaStreamTrack to receive frames from
        """
        logger.info(f"Starting to handle {track.kind} track")
        self.track = track
        consecutive_errors = 0
        
        while self.running:
            try:
                # Receive frame with timeout
                frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                
                # Reset error counter on successful frame receive
                consecutive_errors = 0
                self.frame_count += 1
                
                # Convert frame to numpy array
                if isinstance(frame, VideoFrame):
                    frame_array = frame.to_ndarray(format="bgr24")
                elif isinstance(frame, np.ndarray):
                    frame_array = frame
                else:
                    logger.warning(f"Unexpected frame type: {type(frame)}")
                    continue
                
                # Log every 30th frame to avoid spam
                if self.frame_count % 30 == 0:
                    logger.info(f"Received frame {self.frame_count} (shape: {frame_array.shape})")
                
                # Add timestamp overlay
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                cv2.putText(
                    frame_array, 
                    timestamp, 
                    (10, frame_array.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, 
                    (0, 255, 0), 
                    2, 
                    cv2.LINE_AA
                )
                
                # Add frame counter
                cv2.putText(
                    frame_array,
                    f"Frame: {self.frame_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA
                )
                
                # Display frame
                if self.display:
                    cv2.imshow("WebRTC Receiver", frame_array)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("User requested quit")
                        self.running = False
                        break
                    elif key == ord('s'):
                        # Save frame on 's' key
                        filename = f"{self.output_dir}/manual_frame_{self.frame_count}.jpg"
                        cv2.imwrite(filename, frame_array)
                        logger.info(f"Manually saved frame to {filename}")
                
                # Save frame if enabled
                if self.save_frames and self.frame_count % 30 == 0:  # Save every 30th frame
                    filename = f"{self.output_dir}/received_frame_{self.frame_count}.jpg"
                    cv2.imwrite(filename, frame_array)
                    logger.debug(f"Saved frame to {filename}")
                
            except asyncio.TimeoutError:
                consecutive_errors += 1
                logger.warning(f"Timeout waiting for frame (consecutive: {consecutive_errors}/{self.max_consecutive_errors})")
                
                if consecutive_errors >= self.max_consecutive_errors:
                    logger.error("Too many consecutive timeouts, stopping")
                    self.running = False
                    break
                
                # Wait a bit before retrying
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                logger.info("Track handling cancelled")
                break
                
            except Exception as e:
                consecutive_errors += 1
                self.error_count += 1
                logger.error(f"Error receiving frame: {type(e).__name__}: {str(e)}")
                
                if consecutive_errors >= self.max_consecutive_errors:
                    logger.error("Too many consecutive errors, stopping")
                    self.running = False
                    break
                
                # Check if it's a connection error
                if "Connection" in str(e) or "closed" in str(e).lower():
                    logger.error("Connection error detected, stopping")
                    self.running = False
                    break
                
                # Wait before retrying
                await asyncio.sleep(0.5)
        
        logger.info(f"Track handling stopped. Total frames: {self.frame_count}, Errors: {self.error_count}")
        
        # Cleanup
        if self.display:
            cv2.destroyAllWindows()


async def run_receiver(host="127.0.0.1", port=9999, display=True, save_frames=False):
    """
    Run the WebRTC receiver.
    
    Args:
        host: Signaling server host
        port: Signaling server port
        display: Whether to display video window
        save_frames: Whether to save frames to disk
    """
    logger.info(f"Starting WebRTC receiver connecting to {host}:{port}")
    
    # Create signaling and peer connection
    signaling = TcpSocketSignaling(host, port)
    pc = RTCPeerConnection()
    
    # Create video receiver
    video_receiver = RobustVideoReceiver(display=display, save_frames=save_frames)
    
    # Track handler
    @pc.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack):
            logger.info(f"Received {track.kind} track")
            if track.kind == "video":
                asyncio.ensure_future(video_receiver.handle_track(track))
            else:
                logger.warning(f"Ignoring non-video track: {track.kind}")
    
    # Connection state handler
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState == "failed":
            logger.error("Connection failed")
            video_receiver.running = False
        elif pc.connectionState == "closed":
            logger.info("Connection closed")
            video_receiver.running = False
    
    try:
        # Connect to signaling server
        await signaling.connect()
        logger.info("Connected to signaling server")
        
        # Wait for offer
        logger.info("Waiting for offer...")
        offer = await signaling.receive()
        
        if not isinstance(offer, RTCSessionDescription):
            raise RuntimeError(f"Expected RTCSessionDescription, got {type(offer)}")
        
        logger.info("Offer received")
        
        # Set remote description
        await pc.setRemoteDescription(offer)
        logger.info("Remote description set")
        
        # Create and send answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await signaling.send(pc.localDescription)
        logger.info("Answer sent")
        
        # Wait for connection
        logger.info("Waiting for connection...")
        timeout = 30  # 30 seconds timeout
        for i in range(timeout * 10):
            if pc.connectionState == "connected":
                break
            if pc.connectionState in ["failed", "closed"]:
                raise RuntimeError(f"Connection {pc.connectionState}")
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("Connection timeout")
        
        logger.info("Connection established successfully!")
        
        # Keep running while receiver is active
        while video_receiver.running:
            await asyncio.sleep(0.1)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {str(e)}")
    finally:
        # Cleanup
        video_receiver.running = False
        await asyncio.sleep(0.5)  # Give time for cleanup
        
        try:
            await signaling.close()
        except Exception as e:
            logger.debug(f"Error closing signaling: {e}")
        
        try:
            await pc.close()
        except Exception as e:
            logger.debug(f"Error closing peer connection: {e}")
        
        if display:
            cv2.destroyAllWindows()
        
        logger.info("Receiver stopped")


async def main():
    """Main entry point."""
    # Configuration
    HOST = "127.0.0.1"  # localhost
    PORT = 9999
    DISPLAY = True  # Show video window
    SAVE_FRAMES = False  # Set to True to save frames
    
    await run_receiver(HOST, PORT, DISPLAY, SAVE_FRAMES)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
