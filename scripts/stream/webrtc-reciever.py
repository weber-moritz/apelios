import asyncio
import cv2
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription
from av import VideoFrame
import numpy as np

SENDER_IP = "192.168.8.144"  # IP of moving head camera
SENDER_PORT = 8080

async def run():
    """Connect to WebRTC sender and display video"""
    
    pc = RTCPeerConnection()
    
    @pc.on("track")
    def on_track(track):
        print(f"Receiving {track.kind} track")
        if track.kind == "video":
            asyncio.create_task(receive_video(track))
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state: {pc.connectionState}")
    
    # Create offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    # Send offer to sender
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"http://{SENDER_IP}:{SENDER_PORT}/offer",
            json={
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            }
        ) as response:
            answer = await response.json()
            await pc.setRemoteDescription(
                RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
            )
    
    print("Connected! Press Ctrl+C to stop")
    
    # Keep connection alive
    try:
        while pc.connectionState != "closed":
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await pc.close()

async def receive_video(track):
    """Receive and display video frames"""
    frame_count = 0
    
    while True:
        try:
            frame = await track.recv()
            
            # Convert to numpy array
            img = frame.to_ndarray(format="bgr24")
            
            # Display
            cv2.imshow('WebRTC Stream', img)
            
            frame_count += 1
            if frame_count % 24 == 0:
                print(f"Received {frame_count} frames", end='\r')
            
            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        except Exception as e:
            print(f"Error receiving frame: {e}")
            break
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nStopped")