import hid

# Specify the HID device path
DEVICE_PATH = b"/dev/hidraw2"  # Note the b prefix for bytes

def read_hid_device():
    try:
        # Open the HID device
        with hid.Device(path=DEVICE_PATH) as device:
            print("Listening for HID input...\n")
            while True:
                # Read input from the HID device
                data = device.read(64)  # Read 64 bytes
                if data:
                    # Convert byte data to a readable format
                    # print("Data received:", data)i 
                    # If you want to decode it further
                    hex_data = ' '.join(format(x, '02x') for x in data)
                    print()
                    print("00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63")
                    print(hex_data)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    read_hid_device()
