#!/usr/bin/env python3
"""
WebRTC video sender module.
Streams video from a camera using aiortc.
"""
import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import fractions
import logging

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
        self.cap = cv2.VideoCapture(camera_id)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_id}")
        
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
        Start sending video stream.
        
        Args:
            host: Signaling server host
            port: Signaling server port
        """
        logger.info(f"Starting WebRTC sender on {host}:{port}")
        logger.info(f"Using camera ID: {self.camera_id}")
        
        # Create signaling connection
        self.signaling = TcpSocketSignaling(host, port)
        
        # Create peer connection
        self.pc = RTCPeerConnection()
        
        # Add video track
        try:
            self.video_track = VideoTrack(
                camera_id=self.camera_id,
                width=self.width,
                height=self.height,
                fps=self.fps
            )
            self.pc.addTrack(self.video_track)
            logger.info("Video track added")
        except Exception as e:
            logger.error(f"Error opening camera: {e}")
            raise
        
        # Connection state change handler
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state: {self.pc.connectionState}")
        
        try:
            # Connect to signaling server
            await self.signaling.connect()
            logger.info("Connected to signaling server")
            
            # Create and send offer
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            await self.signaling.send(self.pc.localDescription)
            logger.info("Offer sent")
            
            # Wait for answer
            while True:
                obj = await self.signaling.receive()
                
                if isinstance(obj, RTCSessionDescription):
                    await self.pc.setRemoteDescription(obj)
                    logger.info("Answer received and set")
                elif obj is None:
                    logger.info("Signaling ended")
                    break
            
            # Keep connection alive
            logger.info("Streaming... Press Ctrl+C to stop")
            await asyncio.sleep(3600)  # Run for 1 hour or until interrupted
            
        except KeyboardInterrupt:
            logger.info("Stopping sender...")
            raise
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
        finally:
            await self.stop()
    
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
