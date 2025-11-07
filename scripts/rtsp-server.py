import cv2
import ffmpeg
import numpy as np

RTSP_URL = "rtsp://192.168.8.144:8554/stream"
WIDTH, HEIGHT = 640, 480
FPS = 30

# Open webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)

# Setup FFmpeg process
process = (
    ffmpeg
    .input('pipe:', format='rawvideo', pix_fmt='bgr24', s=f'{WIDTH}x{HEIGHT}', r=FPS)
    .output(RTSP_URL, 
            format='rtsp',
            vcodec='libx264',
            preset='ultrafast',
            tune='zerolatency',
            pix_fmt='yuv420p')
    .overwrite_output()
    .run_async(pipe_stdin=True)
)

print(f"Streaming to {RTSP_URL}")
print("Press Ctrl+C to stop")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Write frame to FFmpeg stdin
        process.stdin.write(frame.tobytes())
        
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    cap.release()
    process.stdin.close()
    process.wait()