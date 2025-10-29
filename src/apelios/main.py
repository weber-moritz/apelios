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
import evdev
from select import select

def listAcessibleDevices():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        print(device.path, device.name, device.phys)

def listDeviceCapabilities(targetDevice):
    device = evdev.InputDevice(targetDevice)
    print(device)
    
    device.capabilities()
    device.capabilities(verbose=True)
    device.capabilities(absinfo=False)
    
def readDevice(targetDevice):
    device = evdev.InputDevice(targetDevice)
    device.grab()
    
    print(device)
    
    for event in device.read_loop():
        print(evdev.categorize(event))

def readDevices(targetDevices):
    devices = map(evdev.InputDevice, targetDevices)
    devices = {dev.fd: dev for dev in devices}
    
    for dev in devices.values(): print(dev)
    
    while True:
        r, w, x = select(devices, [], [])
        for fd in r:
            for event in devices[fd].read():
                print(event)

    
def main():
    print("--- Hello there ---")
    
    print()
    print("--- accessible devices ---")
    listAcessibleDevices()
    
    targetDevicePaths = ("/dev/input/event15",)
    targetDevicePath = "/dev/input/event9"
    
    # print()
    # print(f"--- capabilities of: {targetDevicePath}---")
    # listDeviceCapabilities(targetDevicePath)
    
    print()
    print(f"--- Inputs of: {targetDevicePath}---")
    readDevice(targetDevicePath)
    

if __name__ == "__main__":
    main()