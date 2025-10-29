import hid
import threading
import struct
import pygame
import math

# --- 1. HID Configuration ---
DEVICE_PATH = b"/dev/hidraw2"

# These will store our final, calculated angles
pitch, yaw, roll = 0.0, 0.0, 0.0

# These will store the latest raw "joystick" readings from the gyroscope
gyro_x, gyro_y, gyro_z = 0, 0, 0

def hid_reader():
    """Reads the raw gyroscope data and prints it to the console."""
    global gyro_x, gyro_y, gyro_z
    try:
        with hid.Device(path=DEVICE_PATH) as device:
            print("Listening for raw gyroscope input...")
            while True:
                data = device.read(64)
                if data:
                    # Unpack the bytes for "Sensor B"
                    gyro_x = struct.unpack('<h', bytes(data[30:32]))[0]
                    gyro_y = struct.unpack('<h', bytes(data[32:34]))[0]
                    gyro_z = struct.unpack('<h', bytes(data[34:36]))[0]
                    
                    # --- ADDED BACK IN: Print the raw gyro values ---
                    # The '>6' formats the numbers to be 6 characters wide for alignment.
                    # The 'end="\r"' causes the line to overwrite itself.
                    print(f"Gyro X: {gyro_x:>6}, Gyro Y: {gyro_y:>6}, Gyro Z: {gyro_z:>6}", end='\r')

    except Exception as e:
        print(f"\nHID Error: {e}.") # Added a newline to not overwrite the printout on error

# --- 2. Pygame Visualizer Setup ---
pygame.init()
WIDTH, HEIGHT = 800, 600
BLACK, WHITE = (0, 0, 0), (255, 255, 255)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Direct Gyroscope Visualizer (4x Sensitivity)")
clock = pygame.time.Clock()

# A flat plank shape makes axes easy to identify
points_3d = [
    [-1.5, -0.25, -0.5], [1.5, -0.25, -0.5], [1.5, 0.25, -0.5], [-1.5, 0.25, -0.5],
    [-1.5, -0.25, 0.5], [1.5, -0.25, 0.5], [1.5, 0.25, 0.5], [-1.5, 0.25, 0.5]
]
edges = [
    (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
    (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)
]

# --- 3. Main Application Loop ---
hid_thread = threading.Thread(target=hid_reader, daemon=True)
hid_thread.start()

# --- SENSITIVITY CONTROL ---
GYRO_SENSITIVITY = 0.06

running = True
while running:
    # Get the time that has passed since the last frame (in seconds).
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- THE MAPPING AND INTEGRATION STEP ---
    pitch += gyro_x * GYRO_SENSITIVITY * dt
    yaw   += gyro_y * GYRO_SENSITIVITY * dt
    # roll  += gyro_z * GYRO_SENSITIVITY * dt

    # --- Drawing section (identical to before) ---
    screen.fill(BLACK)
    points_2d = []
    for point in points_3d:
        rad_pitch = math.radians(pitch)
        rad_yaw = math.radians(yaw)
        rad_roll = math.radians(roll)
        x, y, z = point[0], point[1], point[2]
        x, z = x * math.cos(rad_yaw) - z * math.sin(rad_yaw), x * math.sin(rad_yaw) + z * math.cos(rad_yaw)
        y, z = y * math.cos(rad_pitch) - z * math.sin(rad_pitch), y * math.sin(rad_pitch) + z * math.cos(rad_pitch)
        x, y = x * math.cos(rad_roll) - y * math.sin(rad_roll), x * math.sin(rad_roll) + y * math.cos(rad_roll)
        if z + 5 != 0:
            scale = 400 / (z + 5)
            proj_x = int(x * scale + WIDTH / 2)
            proj_y = int(y * scale + HEIGHT / 2)
            points_2d.append((proj_x, proj_y))
        else: points_2d.append((WIDTH/2, HEIGHT/2))
    for edge in edges:
        pygame.draw.line(screen, WHITE, points_2d[edge[0]], points_2d[edge[1]], 2)
    pygame.display.flip()

pygame.quit()