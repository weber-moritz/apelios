Of course. It's an excellent practice to document your progress. Capturing the journey from a problem to a solution is incredibly valuable.

Here is a documentation file summarizing the findings, along with a well-structured prompt to continue your work in a new chat.

---

### **Project Documentation: Analysis of a 3D HID Motion Controller**

**Version:** 1.0
**Date:** 2025-10-27

#### **1. Project Objective**

The goal of this project was to read data from a 64-byte HID device and create a real-time 3D visualization that accurately reflects its physical orientation.

#### **2. Investigation & Findings**

The analysis progressed through several key phases of discovery:

**Phase 1: Initial Analysis of Pre-Calculated Euler Angles**

*   **Data Source:** Bytes `36-43` of the HID data packet.
*   **Initial Assumption:** These bytes represented the final, calculated `pitch`, `yaw`, and `roll` of the device (known as Euler angles).
*   **Problem Encountered:** The visualization showed that rotating the device on a single physical axis caused multiple on-screen axes to rotate simultaneously. This "coupling" of axes is a classic symptom of **Gimbal Lock**, an inherent mathematical limitation of Euler angles.
*   **Conclusion:** The device's pre-calculated orientation is unreliable for precise tracking. A more robust solution using raw sensor data was required.

**Phase 2: Identification of Raw Sensor Data**

*   **Data Source:** Bytes `24-35` of the HID data packet.
*   **Hypothesis:** This 12-byte block contained raw data from two separate 3-axis sensors (likely an accelerometer and a gyroscope).
*   **Methodology:** An experiment was conducted to differentiate the sensors:
    1.  **Accelerometer (Sensor A):** Identified as the sensor that measures a constant, non-zero force even when the device is stationary (this is the force of gravity). Its output changes based on its tilt relative to the ground.
    2.  **Gyroscope (Sensor B):** Identified as the sensor that measures the *rate of rotation*. Its output is near-zero when the device is stationary and produces values only during physical movement.
*   **Conclusion:** The raw sensor data was successfully identified and mapped.

**Phase 3: Implementation of Gyroscope-Only Tracking**

*   **Methodology:** The raw gyroscope data (angular velocity) was integrated over time to calculate the device's orientation.
*   **Problem Encountered:** While responsive, this method suffered from significant **gyroscope drift**. Fast movements caused an accumulation of small errors, resulting in the virtual object's orientation drifting away from the real physical orientation over time.
*   **Conclusion:** The gyroscope is excellent for measuring fast, instantaneous rotation but is unreliable for long-term orientation stability.

**Phase 4: Final Solution with Sensor Fusion (Complementary Filter)**

*   **Methodology:** A **Complementary Filter** was implemented to fuse the data from both the accelerometer and the gyroscope, leveraging the strengths of each.
    *   The **gyroscope** provides the primary, high-frequency rotation data.
    *   The **accelerometer** provides a stable, drift-free reference of "down" (gravity) to constantly correct the gyroscope's accumulated drift for the pitch and roll axes.
*   **Result:** This approach produced a stable, responsive, and accurate visualization that correctly tracks fast movements without significant long-term drift on the pitch and roll axes.

#### **3. Final Byte Mapping**

| Byte Range | Sensor            | Data Type                   | Description                                             |
| :--------- | :---------------- | :-------------------------- | :------------------------------------------------------ |
| `24-29`    | **Accelerometer** | 3x 2-byte Signed Integers   | Measures static forces (gravity). Used for drift correction. |
| `30-35`    | **Gyroscope**     | 3x 2-byte Signed Integers   | Measures angular velocity. Used for instantaneous rotation. |
| `36-43`    | **Euler Angles**  | 3x 2-byte Signed Integers   | Device's internal, pre-calculated orientation. **(Deprecated)** |

#### **4. Current Known Limitations**

*   **Yaw Drift:** The current solution does not correct for drift on the yaw axis (rotation around the vertical axis). This is because the accelerometer can only measure the direction of gravity and cannot provide a reference for a compass heading (e.g., "north"). To solve this, a third sensor (a magnetometer) would be required.

---

### **Prompt for a New LLM Chat**

Here is a prompt designed to be a perfect continuation of this project. Just copy and paste it into a new chat.

Hello! I'm working on a project to track the 3D orientation of a HID device using Python. I have successfully implemented a sensor fusion algorithm (a Complementary Filter) to combine accelerometer and gyroscope data, which gives me a very stable reading for pitch and roll.

My current challenge is that the raw sensor values are not perfectly calibrated. When the device is lying perfectly still on my desk, the gyroscope values are not exactly zero, and the accelerometer doesn't report a perfectly clean gravity vector. This introduces a small, constant error into my calculations.

I would like to implement a simple, on-demand calibration routine. Here is the plan:

1.  When the user presses the 'c' key in the Pygame window, the program should capture the current accelerometer and gyroscope readings.
2.  These captured readings will be stored as "offsets" or "biases."
3.  In the main loop, these offsets should be subtracted from every subsequent raw sensor reading before they are used in the sensor fusion calculations.

Could you please modify my current script to include this calibration functionality?

Here is my complete, working code:

```python
import hid
import threading
import struct
import pygame
import math

# --- 1. HID Configuration ---
DEVICE_PATH = b"/dev/hidraw2"

# Our final, fused angles
pitch, yaw, roll = 0.0, 0.0, 0.0

# Raw sensor values
accel_x, accel_y, accel_z = 0, 0, 0
gyro_x, gyro_y, gyro_z = 0, 0, 0

def hid_reader():
    """Reads BOTH raw accelerometer and gyroscope data."""
    global accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z
    try:
        with hid.Device(path=DEVICE_PATH) as device:
            print("Listening for raw sensor input...")
            while True:
                data = device.read(64)
                if data:
                    accel_x = struct.unpack('<h', bytes(data[24:26]))[0]
                    accel_y = struct.unpack('<h', bytes(data[26:28]))[0]
                    accel_z = struct.unpack('<h', bytes(data[28:30]))[0]
                    gyro_x = struct.unpack('<h', bytes(data[30:32]))[0]
                    gyro_y = struct.unpack('<h', bytes(data[32:34]))[0]
                    gyro_z = struct.unpack('<h', bytes(data[34:36]))[0]
    except Exception as e:
        print(f"\nHID Error: {e}.")

# --- 2. Pygame Visualizer (Setup is the same) ---
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sensor Fusion Visualizer (Complementary Filter)")
clock = pygame.time.Clock()
points_3d = [[-1.5,-0.25,-0.5],[1.5,-0.25,-0.5],[1.5,0.25,-0.5],[-1.5,0.25,-0.5],[-1.5,-0.25,0.5],[1.5,-0.25,0.5],[1.5,0.25,0.5],[-1.5,0.25,0.5]]
edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]

# --- 3. Main Application Loop ---
hid_thread = threading.Thread(target=hid_reader, daemon=True)
hid_thread.start()

GYRO_SENSITIVITY = 0.04
FILTER_WEIGHT = 0.98

running = True
while running:
    dt = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # The new part will go here...

    # --- SENSOR FUSION LOGIC ---
    pitch_gyro = pitch + gyro_x * GYRO_SENSITIVITY * dt
    roll_gyro  = roll - gyro_z * GYRO_SENSITIVITY * dt
    
    try:
        pitch_accel = math.degrees(math.atan2(accel_y, math.sqrt(accel_x**2 + accel_z**2)))
        roll_accel  = math.degrees(math.atan2(-accel_x, accel_z))
    except ZeroDivisionError:
        pitch_accel = 0
        roll_accel = 0

    pitch = FILTER_WEIGHT * pitch_gyro + (1 - FILTER_WEIGHT) * pitch_accel
    roll  = FILTER_WEIGHT * roll_gyro  + (1 - FILTER_WEIGHT) * roll_accel
    yaw += gyro_y * GYRO_SENSITIVITY * dt

    # --- Drawing section (identical to before) ---
    screen.fill((0,0,0))
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
        pygame.draw.line(screen, (255,255,255), points_2d[edge[0]], points_2d[edge[1]], 2)
    pygame.display.flip()

pygame.quit()
```