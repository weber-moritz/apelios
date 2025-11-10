import argparse
import asyncio
import logging
import time
import threading
from queue import Queue

import cv2
import numpy as np
from aiohttp import ClientSession, ClientTimeout
from aiortc import RTCPeerConnection, RTCSessionDescription


class VideoReceiver:
    """Receives and displays video stream from WebRTC sender"""
    
    def __init__(self, sender_url: str):
        self.sender_url = sender_url
        self.pc = None
        self.frame_count = 0
        self.start_time = None
        self.frame_queue = Queue(maxsize=2)  # Small queue for low latency
        self.running = False
        self.connected = False
        
    async def connect(self):
        """Connect to the sender and start receiving video"""
        print(f"Connecting to {self.sender_url}...")
        
        # Create peer connection
        self.pc = RTCPeerConnection()
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state: {self.pc.connectionState}")
            if self.pc.connectionState == "failed":
                print("Connection failed! Check network and firewall.")
                self.running = False
                self.connected = False
            elif self.pc.connectionState == "connected":
                print("Connected! Receiving video...")
                self.connected = True
        
        @self.pc.on("track")
        def on_track(track):
            print(f"Receiving {track.kind} track")
            if track.kind == "video":
                asyncio.create_task(self.receive_video(track))
            
            @track.on("ended")
            async def on_ended():
                print(f"Track {track.kind} ended")
                self.running = False
        
        # Add transceiver for receiving video only
        self.pc.addTransceiver("video", direction="recvonly")
        
        # Create offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        # Send offer to sender
        try:
            async with ClientSession() as session:
                async with session.post(
                    f"{self.sender_url}/offer",
                    json={
                        "sdp": self.pc.localDescription.sdp,
                        "type": self.pc.localDescription.type
                    },
                    timeout=ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP error {response.status}")
                    
                    answer = await response.json()
                    await self.pc.setRemoteDescription(
                        RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
                    )
        except Exception as e:
            print(f"Failed to connect to sender: {e}")
            await self.close()
            raise
    
    async def receive_video(self, track):
        """Receive video frames and put them in queue"""
        self.running = True
        self.start_time = time.time()
        
        print("Starting video reception...")
        
        try:
            while self.running:
                try:
                    # Receive frame with timeout
                    frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                    
                    # Convert to numpy array
                    img = frame.to_ndarray(format="bgr24")
                    
                    # Put in queue (drop old frames if queue is full)
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except:
                            pass
                    
                    self.frame_queue.put(img)
                    self.frame_count += 1
                        
                except asyncio.TimeoutError:
                    print("\nTimeout receiving frame")
                    self.running = False
                    break
                except Exception as e:
                    print(f"\nError receiving frame: {e}")
                    self.running = False
                    break
                    
        finally:
            print(f"Stopped receiving video. Total frames: {self.frame_count}")
    
    def display_loop(self):
        """Display frames in OpenCV window (runs in main thread)"""
        print("Opening display window...")
        window_name = 'WebRTC Stream'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        fps_time = time.time()
        fps_frames = 0
        current_fps = 0
        
        while self.running or not self.frame_queue.empty():
            try:
                # Get frame from queue with timeout
                img = self.frame_queue.get(timeout=0.1)
                
                # Calculate FPS
                fps_frames += 1
                elapsed = time.time() - fps_time
                if elapsed >= 1.0:
                    current_fps = fps_frames / elapsed
                    fps_frames = 0
                    fps_time = time.time()
                
                # Add info overlay
                info_text = f"FPS: {current_fps:.1f} | Frame: {self.frame_count} | {img.shape[1]}x{img.shape[0]}"
                cv2.putText(img, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Display
                cv2.imshow(window_name, img)
                
                # Check for exit key
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nStopping (pressed 'q')...")
                    self.running = False
                    break
                elif key == ord('s'):
                    # Save screenshot
                    filename = f"screenshot_{int(time.time())}.png"
                    cv2.imwrite(filename, img)
                    print(f"\nScreenshot saved: {filename}")
                    
            except:
                # No frame available, just check keys
                key = cv2.waitKey(10) & 0xFF
                if key == ord('q'):
                    print("\nStopping (pressed 'q')...")
                    self.running = False
                    break
        
        cv2.destroyAllWindows()
        print("Display window closed")
    
    async def close(self):
        """Close the connection"""
        self.running = False
        if self.pc:
            await self.pc.close()
            self.pc = None
        print("Connection closed")
    
    async def run(self):
        """Connect and keep running until stopped"""
        try:
            await self.connect()
            
            # Start display loop in separate thread
            display_thread = threading.Thread(target=self.display_loop, daemon=True)
            display_thread.start()
            
            # Wait for connection
            while not self.connected and self.pc and self.pc.connectionState not in ["closed", "failed"]:
                await asyncio.sleep(0.1)
            
            if not self.connected:
                print("Failed to establish connection")
                return
            
            # Keep running while receiving video or display is active
            while self.running and self.pc and self.pc.connectionState not in ["closed", "failed"]:
                await asyncio.sleep(0.1)
            
            # Wait for display thread to finish
            display_thread.join(timeout=2.0)
                
        except KeyboardInterrupt:
            print("\nStopped by user")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close()


async def main():
    parser = argparse.ArgumentParser(description="WebRTC video receiver (Python window)")
    parser.add_argument(
        "--sender",
        default="http://192.168.8.144:8080",
        help="Sender URL (default: http://192.168.8.144:8080)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("WebRTC Video Receiver")
    print("=" * 60)
    print(f"Sender: {args.sender}")
    print("Press 'q' to quit")
    print("Press 's' to save screenshot")
    print("=" * 60)
    
    receiver = VideoReceiver(args.sender)
    await receiver.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")