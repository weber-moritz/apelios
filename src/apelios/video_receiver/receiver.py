#!/usr/bin/env python3
"""
WebRTC receiver
recieves real-time video stream.
"""

import asyncio
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
from datetime import datetime
import logging
import os

try:
    from ..person_detector import PersonDetector
    from ..signaling_server import WebSocketSignaling
except ImportError:
    # When running as script, use absolute import
    import sys
    from pathlib import Path
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from apelios.person_detector import PersonDetector
    from apelios.signaling_server import WebSocketSignaling

logger = logging.getLogger(__name__)

class VideoReceiver:
    """WebRTC video stream receiver with optional person detection."""
    
    def __init__(self, display=True, save_frames=False, output_dir="frames", 
                 enable_detection=False, detection_method="hog", confidence_threshold=0.5,
                 frame_callback=None):
        """
        Initialize video receiver.
        
        Args:
            display: Show video window (ignored if frame_callback is set)
            save_frames: Save frames to disk
            output_dir: Directory for saved frames
            enable_detection: Enable person detection (optional)
            detection_method: Detection method - "hog" or "haar" (if detection enabled)
            confidence_threshold: Minimum confidence for detections (if detection enabled)
            frame_callback: Optional callback function(frame_array) called for each frame
        """
        self.display = display
        self.save_frames = save_frames
        self.output_dir = output_dir
        self.enable_detection = enable_detection
        self.frame_callback = frame_callback
        self.track = None
        self.frame_count = 0
        self.detection_count = 0
        self.running = True
        
        # Initialize person detector only if enabled
        if self.enable_detection:
            self.detector = PersonDetector(method=detection_method, confidence_threshold=confidence_threshold)
        else:
            self.detector = None
        
        # Create output directory
        if self.save_frames:
            os.makedirs(self.output_dir, exist_ok=True)
    
    async def handle_track(self, track):
        """Handle incoming video track with optional person detection."""
        logger.info(f"Starting to handle {track.kind} track with person detection")
        self.track = track
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.running:
            try:
                # Receive frame with timeout
                frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                
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
                
                # Detect people if detection is enabled
                detections = []
                if self.enable_detection and self.detector:
                    try:
                        detections = self.detector.detect(frame_array)
                    except Exception as e:
                        logger.error(f"Detection error: {e}")
                        detections = []
                
                # Draw detections if enabled, otherwise use original frame
                if self.enable_detection and self.detector:
                    # Draw detections in-place for minimal latency
                    annotated_frame = self.detector.draw_detections(frame_array, detections, in_place=True)
                else:
                    # No copy needed - use frame directly for minimal latency
                    annotated_frame = frame_array
                
                # Add info overlay
                info_text = [
                    f"Frame: {self.frame_count}",
                    datetime.now().strftime("%H:%M:%S.%f")[:-3]
                ]
                
                if self.enable_detection:
                    info_text.insert(1, f"People: {len(detections)}")
                    info_text.insert(2, f"Method: {self.detector.method.upper()}")
                
                y_offset = 30
                for i, text in enumerate(info_text):
                    cv2.putText(
                        annotated_frame,
                        text,
                        (10, y_offset + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA
                    )
                
                # Log detections
                if self.enable_detection and len(detections) > 0:
                    if self.detection_count % 30 == 0:  # Log every 30 detections
                        logger.info(f"Frame {self.frame_count}: Detected {len(detections)} person(s)")
                    self.detection_count += 1
                    
                    # Save frame with detections
                    if self.save_frames:
                        filename = f"{self.output_dir}/detection_{self.frame_count}_{len(detections)}p.jpg"
                        cv2.imwrite(filename, annotated_frame)
                elif self.save_frames and self.frame_count % 30 == 0:
                    # Save every 30th frame if detection is disabled
                    filename = f"{self.output_dir}/frame_{self.frame_count}.jpg"
                    cv2.imwrite(filename, annotated_frame)
                
                # Send frame to callback or display with cv2
                if self.frame_callback:
                    # Call the callback with the frame (for Qt integration)
                    try:
                        self.frame_callback(annotated_frame)
                    except Exception as e:
                        logger.error(f"Frame callback error: {e}")
                elif self.display:
                    # Fallback to cv2.imshow if no callback
                    window_title = "Video Stream - Person Detection" if self.enable_detection else "Video Stream"
                    cv2.imshow(window_title, annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("User requested quit")
                        self.running = False
                        break
                    elif key == ord('s'):
                        # Save frame manually
                        filename = f"{self.output_dir}/manual_{self.frame_count}.jpg"
                        cv2.imwrite(filename, annotated_frame)
                        logger.info(f"Saved frame to {filename}")
                
            except asyncio.TimeoutError:
                consecutive_errors += 1
                logger.warning(f"Timeout ({consecutive_errors}/{max_consecutive_errors})")
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive timeouts")
                    self.running = False
                    break
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                logger.info("Track handling cancelled")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error: {type(e).__name__}: {str(e)}")
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors")
                    self.running = False
                    break
                await asyncio.sleep(0.5)
        
        logger.info(f"Stopped. Frames: {self.frame_count}, Detections: {self.detection_count}")
        
        if self.display:
            cv2.destroyAllWindows()


async def run_receiver(host="127.0.0.1", port=9999, display=True, save_frames=False, 
                       enable_detection=False, detection_method="hog", confidence_threshold=0.5,
                       frame_callback=None):
    """
    Run the WebRTC video stream receiver.
    
    Args:
        host: Signaling server host
        port: Signaling server port
        display: Show video window (ignored if frame_callback is set)
        save_frames: Save frames to disk
        enable_detection: Enable person detection (optional)
        detection_method: Detection method - "hog" or "haar" (if detection enabled)
        confidence_threshold: Minimum confidence for detections (if detection enabled)
        frame_callback: Optional callback function(frame_array) called for each frame
    """
    mode = "with person detection" if enable_detection else "streaming only"
    logger.info(f"Starting WebRTC receiver ({mode}) connecting to {host}:{port}")
    
    signaling = WebSocketSignaling(host, port, client_type="receiver")
    pc = RTCPeerConnection()
    
    video_receiver = VideoReceiver(
        display=display, 
        save_frames=save_frames,
        enable_detection=enable_detection,
        detection_method=detection_method,
        confidence_threshold=confidence_threshold,
        frame_callback=frame_callback
    )
    
    @pc.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack):
            logger.info(f"Received {track.kind} track")
            if track.kind == "video":
                asyncio.ensure_future(video_receiver.handle_track(track))
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            video_receiver.running = False
    
    try:
        await signaling.connect()
        logger.info("Connected to signaling server")
        
        logger.info("Waiting for offer...")
        offer = await signaling.receive()
        
        if not isinstance(offer, RTCSessionDescription):
            raise RuntimeError(f"Expected RTCSessionDescription, got {type(offer)}")
        
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await signaling.send(pc.localDescription)
        logger.info("Handshake complete")
        
        # Wait for connection
        for i in range(300):
            if pc.connectionState == "connected":
                break
            if pc.connectionState in ["failed", "closed"]:
                raise RuntimeError(f"Connection {pc.connectionState}")
            await asyncio.sleep(0.1)
        
        status = "Starting video stream with person detection..." if enable_detection else "Starting video stream..."
        logger.info(f"Connection established! {status}")
        
        while video_receiver.running:
            await asyncio.sleep(0.1)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {str(e)}")
    finally:
        video_receiver.running = False
        await asyncio.sleep(0.5)
        
        try:
            await signaling.close()
            await pc.close()
        except:
            pass
        
        if display:
            cv2.destroyAllWindows()
        
        logger.info("Receiver stopped")


async def main():
    """Main entry point for standalone execution."""
    # Configuration
    HOST = "127.0.0.1"  # Must match sender's HOST
    PORT = 9999
    DISPLAY = True
    SAVE_FRAMES = False
    ENABLE_DETECTION = False  # Set to True to enable person detection (INCREASES LATENCY!)
    DETECTION_METHOD = "hog"  # "hog" or "haar"
    
    await run_receiver(
        host=HOST,
        port=PORT,
        display=DISPLAY,
        save_frames=SAVE_FRAMES,
        enable_detection=ENABLE_DETECTION,
        detection_method=DETECTION_METHOD
    )


if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
