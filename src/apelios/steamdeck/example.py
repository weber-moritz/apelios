import time
from bitsteam.deck import SteamDeck

if __name__ == '__main__':
    try:
        # On Linux, you might need to find the correct device path with 'ls /dev/hidraw*'
        deck = SteamDeck(device_path=b"/dev/hidraw2") 
        deck.start()
        
        print("Reading from Steam Deck... Press Ctrl+C to exit.")
        while True:
            # --- Get Button States ---
            a_button = deck.get_button_state('a')
            start_button = deck.get_button_state('start')

            # --- Get Analog Values ---
            analogs = deck.get_analog_values()
            left_stick_x = analogs['left_stick_x']
            right_trigger = analogs['right_trigger']
            
            # --- Get IMU Data ---
            imu_data = deck.get_imu_rates()
            pitch = imu_data['pitch']
            yaw = imu_data['yaw']
            roll = imu_data['roll']

            # --- Print some of the retrieved values ---
            print(f"A Button: {a_button}, Start Button: {start_button}", end=' | ')
            print(f"Left Stick X: {left_stick_x}, Right Trigger: {right_trigger}", end=' | ')
            print(f"Pitch: {pitch:.2f}, Yaw: {yaw:.2f}, Roll: {roll:.2f}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the HID device path is correct and that you have the necessary permissions to read from it.")
    finally:
        if 'deck' in locals() and deck.is_running:
            deck.stop()