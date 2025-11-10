import cv2
import subprocess
import sys

RTSP_URL = "rtsp://192.168.8.144:8554/stream"
WIDTH, HEIGHT = 640, 480
FPS = 30

# Open camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("Error: Cannot open camera")
    sys.exit(1)

# FFmpeg command
ffmpeg_cmd = [
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f'{WIDTH}x{HEIGHT}',
    '-r', str(FPS),
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-tune', 'zerolatency',
    '-b:v', '500k',
    '-maxrate', '500k',
    '-bufsize', '500k',
    '-g', str(FPS),
    '-pix_fmt', 'yuv420p',
    '-f', 'rtsp',
    RTSP_URL
]

print(f"Streaming to {RTSP_URL}")
print("Press Ctrl+C to stop")

process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame")
            break
        
        if process.stdin:
            process.stdin.write(frame.tobytes())
        else:
            print("Error: FFmpeg stdin closed")
            break
        
except KeyboardInterrupt:
    print("\nStopping...")
except BrokenPipeError:
    print("FFmpeg process died")
finally:
    cap.release()
    if process.stdin:
        process.stdin.close()
    process.terminate()
    process.wait()
    print("Stopped")