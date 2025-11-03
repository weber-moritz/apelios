import hid
import threading
import struct
import pygame
from scipy.spatial.transform import Rotation as R
import pygame_widgets
from pygame_widgets.slider import Slider

# --- 1. HID Configuration ---
DEVICE_PATH = b"/dev/hidraw2"

# Global variables for our final, STABLE, local angular velocity
_stable_local_pitch_rate = 0.0
_stable_local_yaw_rate   = 0.0
_stable_local_roll_rate  = 0.0
_data_lock = threading.Lock()

def hid_reader_thread():
    """Derives a STABLE local angular velocity (a 'Synthetic Gyro') from the quaternion stream."""
    global _stable_local_pitch_rate, _stable_local_yaw_rate, _stable_local_roll_rate
    
    previous_device_orientation = R.identity()
    is_first_frame = True
    
    try:
        with hid.Device(path=DEVICE_PATH) as device:
            print("--- Stable Local Angular Velocity Monitor (MVP) ---")
            while True:
                data = device.read(64)
                if not data: continue

                raw_x, raw_y, raw_z, raw_w = [struct.unpack('<h', bytes(data[i:i+2]))[0] for i in range(36, 44, 2)]
                scaling_factor = 16384.0
                q_x, q_y, q_z, q_w = raw_x/scaling_factor, raw_y/scaling_factor, raw_z/scaling_factor, raw_w/scaling_factor
                
                try:
                    input_quat_map = [q_z, q_y, q_x, q_w]
                    current_device_orientation = R.from_quat(input_quat_map)

                    if is_first_frame:
                        previous_device_orientation = current_device_orientation
                        is_first_frame = False
                    else:
                        delta_local = previous_device_orientation.inv() * current_device_orientation
                        delta_angles = delta_local.as_euler('zyx', degrees=True)
                        
                        SENSITIVITY_MULTIPLIER = 1.0 # Your calibrated value goes here
                        
                        with _data_lock:
                            _stable_local_roll_rate, _stable_local_yaw_rate, _stable_local_pitch_rate = (
                                delta_angles[0] * SENSITIVITY_MULTIPLIER,
                                delta_angles[1] * SENSITIVITY_MULTIPLIER,
                                delta_angles[2] * SENSITIVITY_MULTIPLIER
                            )
                        
                        previous_device_orientation = current_device_orientation
                        
                except Exception:
                    is_first_frame = True

    except Exception as e:
        print(f"\nHID Error: {e}.")

def get_local_rotation_rates():
    """Safely reads the latest rotation rates."""
    with _data_lock:
        return (_stable_local_pitch_rate, _stable_local_yaw_rate, _stable_local_roll_rate)

# --- Pygame Setup ---
pygame.init()
WIDTH, HEIGHT = 1000, 800 # Increased window size
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("MVP: Stable Local Velocity Monitor")
clock = pygame.time.Clock()

# --- SCALED DOWN UI ---
# Fonts are now smaller
font_title = pygame.font.SysFont('Arial', 24)
font_text = pygame.font.SysFont('Arial', 18)

WHITE, RED, GREEN, BLUE = (240, 240, 240), (255, 50, 50), (50, 255, 50), (50, 50, 255)

# Sliders are now smaller and repositioned
slider_width, slider_height = 200, 10
slider_x, slider_y = 50, 80
slider_spacing = 40 # Space between sliders

pitch_slider = Slider(screen, slider_x, slider_y, slider_width, slider_height, min=-5, max=5, handleColour=RED)
yaw_slider   = Slider(screen, slider_x, slider_y + slider_spacing, slider_width, slider_height, min=-5, max=5, handleColour=GREEN)
roll_slider  = Slider(screen, slider_x, slider_y + slider_spacing * 2, slider_width, slider_height, min=-5, max=5, handleColour=BLUE)

# --- Main Loop ---
hid_thread = threading.Thread(target=hid_reader_thread, daemon=True)
hid_thread.start()
running = True
while running:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
    
    # Get the clean, local "joystick" rates
    pitch_rate, yaw_rate, roll_rate = get_local_rotation_rates()
    deadzone = 0.05
    display_pitch = pitch_rate if abs(pitch_rate) > deadzone else 0
    display_yaw   = yaw_rate   if abs(yaw_rate)   > deadzone else 0
    display_roll  = roll_rate  if abs(roll_rate)  > deadzone else 0

    # Update slider values
    pitch_slider.setValue(display_pitch)
    yaw_slider.setValue(display_yaw)
    roll_slider.setValue(display_roll)
    
    # --- Drawing ---
    screen.fill((20,20,30))
    pygame_widgets.update(events) # Draw the sliders
    
    # Draw titles and labels with the smaller font
    title = font_title.render("Stable Local Angular Velocity (Device Space)", True, WHITE)
    screen.blit(title, (slider_x, 30))
    
    pitch_text = font_text.render(f"Pitch Rate: {display_pitch:5.2f}°/frame", True, WHITE)
    yaw_text   = font_text.render(f"Yaw Rate:   {display_yaw:5.2f}°/frame", True, WHITE)
    roll_text  = font_text.render(f"Roll Rate:  {display_roll:5.2f}°/frame", True, WHITE)
    
    screen.blit(pitch_text, (slider_x + slider_width + 20, slider_y - 2))
    screen.blit(yaw_text,   (slider_x + slider_width + 20, slider_y + slider_spacing - 2))
    screen.blit(roll_text,  (slider_x + slider_width + 20, slider_y + slider_spacing * 2 - 2))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()