import cv2
import time
import numpy as np
from fractions import Fraction
from cyndilib.wrapper.ndi_recv import RecvColorFormat
from cyndilib.wrapper.ndi_structs import FourCC
from cyndilib.video_frame import VideoSendFrame
from cyndilib.sender import Sender

# Configuration
SENDER_NAME = "Moving Head Camera"
WIDTH, HEIGHT = 1280, 720
FPS = 30

# Create sender
sender = Sender(SENDER_NAME)

# Create video frame
vf = VideoSendFrame()
vf.set_resolution(WIDTH, HEIGHT)
vf.set_frame_rate(Fraction(FPS, 1))
vf.set_fourcc(FourCC.BGRX)

# Set video frame on sender
sender.set_video_frame(vf)

# Open camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("Failed to open camera")
    exit()

print(f"NDI Sender '{SENDER_NAME}' started")
print(f"Streaming at {WIDTH}x{HEIGHT} @ {FPS}fps")
print("Press Ctrl+C to stop")
print("\nWaiting 3 seconds for NDI registration...")

frame_count = 0
start_time = time.time()

try:
    # Keep sender open with context manager
    sender.open()
    
    # Give NDI time to register on the network
    time.sleep(3)
    print("Now sending frames...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break
        
        # Convert BGR to BGRX (add alpha channel)
        frame_bgrx = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        
        # Send the frame
        sender.write_video_async(frame_bgrx.ravel())
        
        frame_count += 1
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            print(f"Sent {frame_count} frames | FPS: {fps:.1f}", end='\r')

except KeyboardInterrupt:
    print("\n\nStopping sender...")
finally:
    sender.close()
    cap.release()
    print("Sender stopped")