# apelios/main.py

# valve input0  = mouse button left (track pad)
# keyboard      = vol up / down
# valve input1  = 
# xbox pad      = 

# https://python-evdev.readthedocs.io/en/latest/tutorial.html

# /dev/input/event4 Valve Software Steam Controller usb-0000:04:00.4-3/input0
# /dev/input/event5 AT Translated Set 2 keyboard isa0060/serio0/input0
# /dev/input/event9 Valve Software Steam Controller usb-0000:04:00.4-3/input1
# /dev/input/event11 Microsoft X-Box 360 pad 0 

import time
import asyncio
import evdev

def listDevices():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
            print(device.path, device.name, device.phys)

def listEvents(dev):
    for event in dev.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            print(evdev.categorize(event))

def main():
    print("--- Hello there ---")

    listDevices()

    # We will use try...except to handle errors gracefully
    try:
        # NOTE: Make sure '/dev/input/event13' is correct for your X-Box pad right now
        dev = evdev.InputDevice('/dev/input/event13') 
        print(f"--- Listening to: {dev.name} ---")

        # NO MORE while(1) loop! 
        # We just call listEvents once and it will run forever by itself.
        listEvents(dev)

    except PermissionError:
        print("[ERROR] Permission denied. You need to run this script with 'sudo'.")
        print("Example: 'sudo python main.py'")
    except FileNotFoundError:
        print("[ERROR] Device not found. Did the event number change?")
    


# This special block tells Python to run the main() function
# only when this file is executed directly.
if __name__ == "__main__":
    main()