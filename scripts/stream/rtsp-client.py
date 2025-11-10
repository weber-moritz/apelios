import cv2

# RTSP stream URL (replace with your stream)
RTSP_URL = "rtsp://localhost:8554/stream"

# Create video capture object with options
cap = cv2.VideoCapture(RTSP_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer for lower latency


# Try to force TCP transport (more reliable than UDP)
cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

if not cap.isOpened():
    print(f"Error: Cannot open RTSP stream {RTSP_URL}")
    exit()

print(f"Connected to {RTSP_URL}")
print("Press 'q' to quit")

# Main loop
while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Error: Failed to receive frame")
        break
    
    # Display the frame
    cv2.imshow('RTSP Stream', frame)
    
    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()