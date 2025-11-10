import cv2
import time
import numpy as np
from cyndilib.finder import Finder
from cyndilib.receiver import Receiver
from cyndilib.wrapper.ndi_recv import RecvColorFormat, RecvBandwidth
from cyndilib.video_frame import VideoFrameSync

# Configuration
SOURCE_NAME = "Moving Head Camera"

print("Searching for NDI sources...")

# Create finder and wait for sources
finder = Finder()

try:
    finder.open()
    
    print("Waiting for sources (this may take a few seconds)...")
    # Try multiple times to find sources
    for attempt in range(3):
        found = finder.wait_for_sources(timeout=5)
        if found:
            break
        print(f"Attempt {attempt + 1}/3: No sources found yet...")
        time.sleep(1)
    
    # Get source names
    source_names = finder.get_source_names()
    print(f"\nAvailable sources: {source_names}")
    
    if not source_names:
        print("\nNo NDI sources detected!")
        print("Make sure the sender is running and both devices are on the same network.")
        exit()
    
    # Find matching source
    target_source = None
    for source_name in source_names:
        if SOURCE_NAME.lower() in source_name.lower():
            target_source = finder.get_source(source_name)
            break
    
    # If exact match not found, use first available
    if not target_source:
        print(f"\nSource '{SOURCE_NAME}' not found!")
        if source_names:
            print(f"Using first available source: {source_names[0]}")
            target_source = finder.get_source(source_names[0])
        else:
            exit()
    
    print(f"\nConnecting to '{target_source.name}'...")
    
    # Create receiver with proper frame sync setup
    receiver = Receiver(
        color_format=RecvColorFormat.BGRX_BGRA,
        bandwidth=RecvBandwidth.highest
    )
    
    # Create and attach video frame to frame_sync
    vf = VideoFrameSync()
    receiver.frame_sync.set_video_frame(vf)
    
    # Set source
    receiver.set_source(target_source)
    
    # Wait for connection
    print("Waiting for connection...")
    for i in range(50):
        if receiver.is_connected():
            break
        time.sleep(0.1)
        if i % 10 == 0:
            print(f"Still waiting... ({i/10:.0f}s)")
    
    if not receiver.is_connected():
        print("Failed to connect!")
        exit()
    
    print("Connected! Press 'q' to quit\n")
    
    frame_count = 0
    start_time = None
    
    print("Waiting for frames...")
    while receiver.is_connected():
        # Capture frame
        receiver.frame_sync.capture_video()
        
        # Check if we have valid frame data
        if min(vf.xres, vf.yres) > 0 and vf.get_data_size() > 0:
            # Get frame as numpy array
            frame_array = vf.get_array()
            
            # Convert BGRA to BGR
            frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_BGRA2BGR)
            
            # Display
            cv2.imshow('NDI Stream', frame_bgr)
            
            frame_count += 1
            if frame_count == 1:
                print(f"Receiving {vf.xres}x{vf.yres}")
                start_time = time.time()
            
            if frame_count % 30 == 0 and start_time:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"Received {frame_count} frames | FPS: {fps:.1f}", end='\r')
            
            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            # Wait a bit if no valid frame received yet
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            time.sleep(0.01)

except KeyboardInterrupt:
    print("\n\nStopping receiver...")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
finally:
    finder.close()
    cv2.destroyAllWindows()
    print("Receiver stopped")