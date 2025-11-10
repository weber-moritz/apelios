import asyncio
import cv2
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import json

WIDTH, HEIGHT = 1280, 720
FPS = 24

class CameraTrack(VideoStreamTrack):
    """Video track from OpenCV camera"""
    
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, FPS)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create video frame
        new_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        new_frame.pts = pts
        new_frame.time_base = time_base
        
        return new_frame
    
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()


# WebRTC peer connection
pcs = set()

async def offer(request):
    """Handle WebRTC offer from client"""
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state: {pc.connectionState}")
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            await pc.close()
            pcs.discard(pc)

    # Add camera track
    camera = CameraTrack()
    pc.addTrack(camera)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    )

async def on_shutdown(app):
    """Close all peer connections"""
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/offer", offer)
    app.on_shutdown.append(on_shutdown)
    
    print("WebRTC server starting on http://0.0.0.0:8080")
    print("Sender ready for connections")
    
    web.run_app(app, host="0.0.0.0", port=8080)