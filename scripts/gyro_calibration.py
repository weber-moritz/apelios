import hid
import threading
import struct
import pygame
from scipy.spatial.transform import Rotation as R
import pygame_widgets
from pygame_widgets.slider import Slider

# --- 1. HID Configuration ---
DEVICE_PATH = b"/dev/hidraw2"

# Global variable to store the stable, local roll rate we are calibrating
stable_local_roll_rate = 0.0

# We still need the full quaternion logic to produce the stable data
previous_device_orientation = R.identity()
is_first_frame = True

def hid_reader():
    """Derives a STABLE local angular velocity from the quaternion stream."""
    global previous_device_orientation, is_first_frame, stable_local_roll_rate
    
    try:
        with hid.Device(path=DEVICE_PATH) as device:
            print("--- Stable Velocity Calibration (Roll Axis) ---")
            while True:
                data = device.read(64)
                if data:
                    raw_x, raw_y, raw_z, raw_w = [struct.unpack('<h', bytes(data[i:i+2]))[0] for i in range(36, 44, 2)]
                    scaling_factor = 16384.0
                    q_x, q_y, q_z, q_w = raw_x/scaling_factor, raw_y/scaling_factor, raw_z/scaling_factor, raw_w/scaling_factor
                    
                    try:
                        # This is our established mapping for the device's axes
                        input_quat_map = [q_z, q_y, q_x, q_w]
                        current_device_orientation = R.from_quat(input_quat_map)

                        if is_first_frame:
                            previous_device_orientation = current_device_orientation
                            is_first_frame = False
                        else:
                            # Calculate the LOCAL delta rotation
                            delta_local = previous_device_orientation.inv() * current_device_orientation
                            
                            # Convert the delta to its Euler angles to get the rates
                            delta_angles = delta_local.as_euler('zyx', degrees=True)
                            
                            # We only care about the ROLL component for this test
                            stable_local_roll_rate = delta_angles[0]
                            
                            previous_device_orientation = current_device_orientation
                            
                    except Exception:
                        is_first_frame = True
                        stable_local_roll_rate = 0.0

    except Exception as e:
        print(f"\nHID Error: {e}.")

# --- 2. Pygame Calibration Tool ---
pygame.init()
WIDTH, HEIGHT = 800, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stable Velocity Calibration (Roll Axis)")
clock = pygame.time.Clock()
font = pygame.font.SysFont('Arial', 24)
WHITE, BLUE = (240, 240, 240), (50, 50, 255)

# --- THE MOST IMPORTANT VARIABLE: THIS IS WHAT YOU WILL TUNE ---
# This value is now a MULTIPLIER for our stable, calculated rates.
# It should be close to 1.0. If the rotation is too slow, make it bigger (e.g., 1.5).
# If too fast, make it smaller (e.g., 0.8).
SENSITIVITY_MULTIPLIER = 3.95

# The slider will show the total accumulated angle.
slider_width, slider_x, slider_y = 250, 50, 150
roll_slider = Slider(screen, slider_x, slider_y, slider_width, 40, min=-360, max=360, handleColour=BLUE)

# --- 3. Main Application Loop ---
hid_thread = threading.Thread(target=hid_reader, daemon=True)
hid_thread.start()

accumulated_roll = 0.0
running = True
while running:
    # No need for dt here, because the delta_angles are already "per frame"
    clock.tick(60)
    
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: # Use ENTER key
                print("Angle reset to zero.")
                accumulated_roll = 0.0

    # Apply a deadzone to the calculated rate
    deadzone = 0.01
    current_velocity = stable_local_roll_rate if abs(stable_local_roll_rate) > deadzone else 0
    
    # --- INTEGRATION STEP ---
    # We add the scaled, stable velocity to our total.
    # The rate is already "degrees per frame", so we don't need to multiply by dt.
    accumulated_roll += current_velocity * SENSITIVITY_MULTIPLIER

    # Update the slider
    roll_slider.setValue(accumulated_roll)

    # --- Drawing ---
    screen.fill((20,20,30))
    pygame_widgets.update(events)
    
    # Instructions and labels
    title = font.render(f"Current Multiplier: {SENSITIVITY_MULTIPLIER}", True, WHITE)
    instructions1 = font.render("1. Lay Deck flat, press ENTER to reset angle to 0.", True, WHITE)
    instructions2 = font.render("2. Physically roll the Deck 90 degrees.", True, WHITE)
    instructions3 = font.render("3. Adjust multiplier until the text shows ~90°.", True, WHITE)
    roll_text = font.render(f"Accumulated Roll: {accumulated_roll:.1f}°", True, WHITE)
    
    screen.blit(title, (50, 20))
    screen.blit(instructions1, (50, 50))
    screen.blit(instructions2, (50, 80))
    screen.blit(instructions3, (50, 110))
    screen.blit(roll_text, (slider_x + slider_width + 20, slider_y + 5))
    
    pygame.display.flip()

pygame.quit()