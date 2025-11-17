#!/usr/bin/env python3
"""
Minimal WebRTC sender for Linux localhost testing.
Streams video from a camera using aiortc.
"""
import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import fractions


class VideoTrack(VideoStreamTrack):
    """Simple video track that captures from camera."""
    
    def __init__(self, camera_id=0):
        super().__init__()
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_id}")
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.frame_count = 0
    
    async def recv(self):
        """Capture and return a video frame."""
        self.frame_count += 1
        
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame from camera")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create video frame
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, 30)
        
        return video_frame
    
    def __del__(self):
        """Release camera on cleanup."""
        if hasattr(self, 'cap'):
            self.cap.release()


async def run_sender(host="127.0.0.1", port=9999, camera_id=0):
    """
    Run the WebRTC sender.
    
    Args:
        host: Signaling server host (default: localhost)
        port: Signaling server port
        camera_id: Camera device ID (0 for default camera)
    """
    print(f"Starting WebRTC sender on {host}:{port}")
    print(f"Using camera ID: {camera_id}")
    
    # Create signaling connection
    signaling = TcpSocketSignaling(host, port)
    
    # Create peer connection
    pc = RTCPeerConnection()
    
    # Add video track
    try:
        video_track = VideoTrack(camera_id)
        pc.addTrack(video_track)
        print("Video track added")
    except Exception as e:
        print(f"Error opening camera: {e}")
        return
    
    # Connection state change handler
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state: {pc.connectionState}")
    
    try:
        # Connect to signaling server
        await signaling.connect()
        print("Connected to signaling server")
        
        # Create and send offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send(pc.localDescription)
        print("Offer sent")
        
        # Wait for answer
        while True:
            obj = await signaling.receive()
            
            if isinstance(obj, RTCSessionDescription):
                await pc.setRemoteDescription(obj)
                print("Answer received and set")
            elif obj is None:
                print("Signaling ended")
                break
        
        # Keep connection alive
        print("Streaming... Press Ctrl+C to stop")
        await asyncio.sleep(3600)  # Run for 1 hour or until interrupted
        
    except KeyboardInterrupt:
        print("\nStopping sender...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        await signaling.close()
        await pc.close()
        print("Connection closed")


async def main():
    """Main entry point."""
    # Configuration
    HOST = "192.168.8.144"  # localhost
    PORT = 9999
    CAMERA_ID = 0  # Default camera
    
    await run_sender(HOST, PORT, CAMERA_ID)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
