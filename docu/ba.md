# currently plan:
- keep the 3 dash button pressed to switch to gamepad mode
- in steam set the game pad mode to:
    - gyro to none 
    - enable gyro buttons to none (always active) in the settings next to this
- in desktop mode start the python add and switch to the game pad mode
- gui help lib ref cite: https://www.pythonguis.com/tutorials/pyside6-layouts/

# gui elements:
## top (whole width, maybe 7% screen height?)
- left aligned: video tab
- left aligned: settings tab (next to it)
- (right aligned: toggle between input)
- (right aligned: ip address/latency etc?)

## video stream:
- centered back: video stream, scaled to fit
- right side: vertical brighness slider
- left side: vertical zoom slider
- top right: gizmo/view cube / orientation cube
- bottom: settings for overlay (circle, crosshair, person detection)

## settings:
- EXIT PORGRAM
- camera ip address/port
- artnet destination ip address
- fixture type (from dropdown?)
- sensitivity for gyro?

## changes to video stream:
- took appart the reciever so now there is an optional person_detector module
- fixed the bug of the sender not offering a new stream, now one can disconnect, sender restart signaling server, and then reconnect
- the tcp socket thing did not work propperly. better solution anyways is to use a websocket.