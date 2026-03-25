#!/usr/bin/env python3
"""
WebRTC video sender module.
Streams video from a camera using aiortc.
"""
import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import fractions
import logging

try:
    from ..signaling_server import WebSocketSignaling
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from signaling_server import WebSocketSignaling

logger = logging.getLogger(__name__)


class VideoTrack(VideoStreamTrack):
    """Simple video track that captures from camera."""
    
    def __init__(self, camera_id=0, width=640, height=480, fps=30):
        """
        Initialize video track.
        
        Args:
            camera_id: Camera device ID (0 for default camera)
            width: Frame width
            height: Frame height
            fps: Frames per second
        """
        super().__init__()
        self.camera_id = camera_id
        
        logger.info(f"Attempting to open camera {camera_id}...")
        
        # Try multiple backends
        backends = [
            (cv2.CAP_V4L2, "V4L2"),
            (cv2.CAP_ANY, "ANY"),
            (cv2.CAP_GSTREAMER, "GStreamer"),
        ]
        
        self.cap = None
        for backend, name in backends:
            logger.info(f"Trying {name} backend...")
            cap = cv2.VideoCapture(camera_id, backend)
            if cap.isOpened():
                logger.info(f"✓ Camera opened with {name} backend")
                self.cap = cap
                break
            cap.release()
        
        if self.cap is None or not self.cap.isOpened():
            logger.error(f"Failed to open camera {camera_id} with all backends")
            raise RuntimeError(f"Cannot open camera {camera_id}")
        
        logger.info(f"Camera {camera_id} opened successfully")
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_count = 0
        
        logger.info(f"Camera {camera_id} opened: {width}x{height} @ {fps}fps")
    
    async def recv(self):
        """Capture and return a video frame."""
        self.frame_count += 1
        
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Failed to read frame from camera")
            raise RuntimeError("Failed to read frame from camera")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create video frame
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, self.fps)
        
        return video_frame
    
    def __del__(self):
        """Release camera on cleanup."""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            logger.info(f"Camera {self.camera_id} released")


class VideoSender:
    """WebRTC video sender."""
    
    def __init__(self, camera_id=0, width=640, height=480, fps=30):
        """
        Initialize video sender.
        
        Args:
            camera_id: Camera device ID (0 for default camera)
            width: Frame width
            height: Frame height
            fps: Frames per second
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.video_track = None
        self.pc = None
        self.signaling = None
    
    async def start(self, host="127.0.0.1", port=9999):
        """
        Start sending video stream with WebSocket signaling.
        
        Args:
            host: Signaling server host
            port: Signaling server port
        """
        logger.info(f"Starting WebRTC sender connecting to {host}:{port}")
        logger.info(f"Using camera ID: {self.camera_id}")
        
        # Open camera once (reuse for all connections)
        try:
            self.video_track = VideoTrack(
                camera_id=self.camera_id,
                width=self.width,
                height=self.height,
                fps=self.fps
            )
            logger.info("Video track initialized")
        except Exception as e:
            logger.error(f"Error opening camera: {e}")
            raise
        
        # Connect to signaling server once
        self.signaling = WebSocketSignaling(host, port, client_type="sender")
        await self.signaling.connect()
        
        # Handle multiple receiver connections
        connection_count = 0
        active_connections = {}  # Track active peer connections
        
        try:
            while True:
                # Wait for messages from signaling server
                obj = await self.signaling.receive()
                
                if obj is None:
                    logger.info("Signaling connection closed")
                    break
                
                # Handle request for new offer from a receiver
                if isinstance(obj, dict) and obj.get("request_offer"):
                    connection_count += 1
                    logger.info(f"Creating connection #{connection_count} for new receiver")
                    
                    # Create new peer connection for this receiver
                    pc = RTCPeerConnection()
                    pc.addTrack(self.video_track)
                    
                    # Monitor connection state
                    conn_id = connection_count
                    active_connections[conn_id] = pc
                    
                    @pc.on("connectionstatechange")
                    async def on_connectionstatechange(conn_id=conn_id):
                        state = active_connections[conn_id].connectionState
                        logger.info(f"Connection #{conn_id} state: {state}")
                        if state in ["failed", "closed"]:
                            if conn_id in active_connections:
                                del active_connections[conn_id]
                                logger.info(f"Connection #{conn_id} removed")
                    
                    # Create and send offer
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    await self.signaling.send(pc.localDescription)
                    logger.info(f"Offer sent for connection #{conn_id}")
                
                # Handle answer from receiver
                elif isinstance(obj, RTCSessionDescription) and obj.type == "answer":
                    # Find the peer connection waiting for answer (most recent)
                    if active_connections:
                        pc = active_connections[connection_count]
                        await pc.setRemoteDescription(obj)
                        logger.info(f"Answer received for connection #{connection_count}")
                        logger.info(f"Active connections: {len(active_connections)}")
                    else:
                        logger.warning("Received answer but no active peer connection")
                    
        except KeyboardInterrupt:
            logger.info("Stopping sender...")
        finally:
            # Clean up all active connections
            for conn_id, pc in list(active_connections.items()):
                try:
                    await pc.close()
                    logger.debug(f"Closed connection #{conn_id}")
                except:
                    pass
            
            # Clean up signaling
            if self.signaling:
                try:
                    await self.signaling.close()
                except:
                    pass
            
            # Clean up camera
            if self.video_track:
                try:
                    if hasattr(self.video_track, 'cap'):
                        self.video_track.cap.release()
                except:
                    pass
            logger.info("Sender stopped")
    
    async def stop(self):
        """Stop the sender and cleanup resources."""
        logger.info("Cleaning up...")
        
        try:
            if self.signaling:
                await self.signaling.close()
        except Exception as e:
            logger.debug(f"Error closing signaling: {e}")
        
        try:
            if self.pc:
                await self.pc.close()
        except Exception as e:
            logger.debug(f"Error closing peer connection: {e}")
        
        logger.info("Connection closed")


async def run_sender(host="127.0.0.1", port=9999, camera_id=0, width=640, height=480, fps=30):
    """
    Run the WebRTC sender (convenience function).
    
    Args:
        host: Signaling server host
        port: Signaling server port
        camera_id: Camera device ID (0 for default camera)
        width: Frame width
        height: Frame height
        fps: Frames per second
    """
    sender = VideoSender(
        camera_id=camera_id,
        width=width,
        height=height,
        fps=fps
    )
    await sender.start(host=host, port=port)


async def main():
    """Main entry point for standalone execution."""
    # Configuration
    HOST = "127.0.0.1"
    PORT = 9999
    CAMERA_ID = 0
    WIDTH = 640
    HEIGHT = 480
    FPS = 30
    
    await run_sender(
        host=HOST,
        port=PORT,
        camera_id=CAMERA_ID,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS
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
