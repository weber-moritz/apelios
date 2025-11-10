import cv2
import time
from cyndilib.wrapper.ndi_recv import RecvColorFormat, RecvBandwidth
from cyndilib.video_frame import VideoFrameSync
from cyndilib.receiver import Receiver
from cyndilib.finder import Finder

SENDER_NAME = "Moving Head Camera"  # Name to search for

print("Searching for NDI sources...")

# Create finder and wait for sources
finder = Finder()
finder.open()
finder.wait_for_sources(timeout=10)

# Find our source
source = None
for src in finder:
    if SENDER_NAME in src.name or SENDER_NAME in src.stream_name:
        source = src
        print(f"Found source: {src.name}")
        break

if source is None:
    print(f"Source '{SENDER_NAME}' not found!")
    print(f"Available sources: {finder.get_source_names()}")
    finder.close()
    exit()

# Create receiver with high quality settings
receiver = Receiver(
    color_format=RecvColorFormat.BGRX_BGRA,  # Match OpenCV BGR format
    bandwidth=RecvBandwidth.highest,
)

# Create video frame sync
vf = VideoFrameSync()
receiver.frame_sync.set_video_frame(vf)

# Connect to source
receiver.set_source(source)

print(f"Connecting to '{source.name}'...")
timeout = 30
while not receiver.is_connected() and timeout > 0:
    time.sleep(0.5)
    timeout -= 1

if not receiver.is_connected():
    print("Failed to connect!")
    finder.close()
    exit()

print("Connected! Press 'q' to quit\n")

# Wait for first valid frame
print("Waiting for first frame...")
frame_rate = 30  # Default
while receiver.is_connected():
    receiver.frame_sync.capture_video()
    if vf.xres > 0 and vf.yres > 0:
        frame_rate = vf.get_frame_rate()
        print(f"Receiving {vf.xres}x{vf.yres} @ {frame_rate}fps")
        break
    time.sleep(0.1)

frame_count = 0
start_time = time.time()

try:
    while receiver.is_connected():
        # Capture frame with timing sync
        receiver.frame_sync.capture_video()
        
        if vf.xres == 0 or vf.yres == 0:
            continue
        
        # Get frame data as numpy array
        frame_array = vf.get_array()
        
        # Convert BGRA to BGR for OpenCV display
        if frame_array.shape[2] == 4:  # BGRA
            frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_BGRA2BGR)
        else:
            frame_bgr = frame_array
        
        # Display
        cv2.imshow('NDI Stream', frame_bgr)
        
        # Stats
        frame_count += 1
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            print(f"FPS: {fps:.1f} | Frames: {frame_count}", end='\r')
        
        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
except KeyboardInterrupt:
    print("\n\nStopping receiver...")
finally:
    cv2.destroyAllWindows()
    finder.close()
    print("Receiver stopped")