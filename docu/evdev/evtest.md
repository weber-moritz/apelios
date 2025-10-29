# `sudo evtest /dev/input/eventX`

## `usb-Valve_Software_Steam_Controller_123456789ABCDEF-event-if02 -> ../event21`
```
Input driver version is 1.0.1
Input device ID: bus 0x3 vendor 0x28de product 0x1205 version 0x110
Input device name: "Steam Deck Motion Sensors"
Supported events:
  Event type 0 (EV_SYN)
  Event type 3 (EV_ABS)
    Event code 0 (ABS_X)
      Value      0
      Min   -32768
      Max    32768
      Fuzz      32
      Resolution   16384
    Event code 1 (ABS_Y)
      Value      0
      Min   -32768
      Max    32768
      Fuzz      32
      Resolution   16384
    Event code 2 (ABS_Z)
      Value      0
      Min   -32768
      Max    32768
      Fuzz      32
      Resolution   16384
    Event code 3 (ABS_RX)
      Value      0
      Min   -32768
      Max    32768
      Fuzz       1
      Resolution      16
    Event code 4 (ABS_RY)
      Value      0
      Min   -32768
      Max    32768
      Fuzz       1
      Resolution      16
    Event code 5 (ABS_RZ)
      Value      0
      Min   -32768
      Max    32768
      Fuzz       1
      Resolution      16
  Event type 4 (EV_MSC)
    Event code 5 (MSC_TIMESTAMP)
Properties:
  Property type 6 (INPUT_PROP_ACCELEROMETER)
Testing ... (interrupt to exit)
```

## `usb-Valve_Software_Steam_Controller_123456789ABCDEF-event-mouse -> ../event8`
```
Input driver version is 1.0.1
Input device ID: bus 0x3 vendor 0x28de product 0x1205 version 0x110
Input device name: "Valve Software Steam Controller"
Supported events:
  Event type 0 (EV_SYN)
  Event type 1 (EV_KEY)
    Event code 272 (BTN_LEFT)
    Event code 273 (BTN_RIGHT)
  Event type 2 (EV_REL)
    Event code 0 (REL_X)
    Event code 1 (REL_Y)
    Event code 6 (REL_HWHEEL)
    Event code 8 (REL_WHEEL)
    Event code 11 (REL_WHEEL_HI_RES)
    Event code 12 (REL_HWHEEL_HI_RES)
  Event type 4 (EV_MSC)
    Event code 4 (MSC_SCAN)
Properties:
Testing ... (interrupt to exit)
```