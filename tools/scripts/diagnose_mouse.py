"""
Diagnose whether the mouse evdev device is accessible.

Usage:
    python scripts/diagnose_mouse.py
"""
import asyncio
import sys


async def main() -> None:
    print(f"Platform: {sys.platform}\n")

    # 1. Check evdev is importable
    try:
        from evdev import InputDevice, ecodes, list_devices
        print("✓ evdev imported ok")
    except ImportError as e:
        print(f"✗ evdev import failed: {e}")
        return

    # 2. List all input devices
    devices = list_devices()
    if not devices:
        print("✗ No evdev devices found under /dev/input/")
        return

    print(f"\nAll input devices ({len(devices)} found):")
    for path in devices:
        try:
            dev = InputDevice(path)
            print(f"  {path}  →  {dev.name}")
            dev.close()
        except PermissionError:
            print(f"  {path}  →  PERMISSION DENIED")
        except Exception as e:
            print(f"  {path}  →  ERROR: {e}")

    # 3. Try to open the MouseAdapter backend directly
    print("\nAttempting MouseAdapter backend resolution...")
    try:
        from apelios.input.adapters.mouse_adapter import LinuxEvdevMouse
        backend = LinuxEvdevMouse()
        await backend.open()
        print("✓ Mouse device opened successfully")
        await backend.close()
    except FileNotFoundError as e:
        print(f"✗ No mouse device found: {e}")
    except PermissionError as e:
        print(f"✗ Permission denied: {e}")
        print("\nFix:")
        print("  sudo usermod -aG input $USER")
        print("  then log out and back in")
        print("\nQuick one-session fix (no logout needed):")
        print("  sudo chmod a+r <device path shown above>")
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
