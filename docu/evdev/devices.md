## `ls /dev/input/`
```
by-id    event0  event10  event12  event14  event17  event21  event4  event6  event8  js0  mice    mouse1
by-path  event1  event11  event13  event15  event2   event3   event5  event7  event9  js1  mouse0  mouse2
```

## `ls -l /dev/input/by-id`
```
lrwxrwxrwx 1 root root 10 Oct 15 13:13 usb-Valve_Software_Steam_Controller_123456789ABCDEF-event-if02 -> ../event21
lrwxrwxrwx 1 root root  9 Oct 13 21:06 usb-Valve_Software_Steam_Controller_123456789ABCDEF-event-mouse -> ../event8
lrwxrwxrwx 1 root root 10 Oct 13 21:06 usb-Valve_Software_Steam_Controller_123456789ABCDEF-if01-event-kbd -> ../event14
lrwxrwxrwx 1 root root 10 Oct 15 13:13 usb-Valve_Software_Steam_Controller_123456789ABCDEF-if02-event-joystick -> ../event15
lrwxrwxrwx 1 root root  6 Oct 15 13:13 usb-Valve_Software_Steam_Controller_123456789ABCDEF-if02-joystick -> ../js0
lrwxrwxrwx 1 root root  9 Oct 13 21:06 usb-Valve_Software_Steam_Controller_123456789ABCDEF-mouse -> ../mouse0
```