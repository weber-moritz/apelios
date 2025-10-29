01 00 09 40|fe 6b 12|00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 fd ff f4 30 bd 28 00 00 00 00 01 00 6c 70 cc 34 d6 f2 06 e4 00 00 00 00 3a 01 5c 01 8d 00 6a f9 00 00 00 00 fe ff ff ff
00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63

## `00-03:` date?
## `04-06:` timer?

## `08:`
### abxy
a: `80`
b: `20`
x: `40`
y: `10`

### trigger (L2) press (all the way pressed, binary click)
`02`
### trigger (R2) press (all the way pressed, binary click)
`01`
### shoulder L1 press
`08`
### shoulder R1 press
`04`

## `09:`
### dpad
up: `10`
down: `08`
left: `04`
right: `02`

### save, pause, steam, settings
save: `10`
pause: `40`
steam: `20`
settings: `04`

### back button R lower
`01`
### back button L lower
`80`

## `10:`
### left joysick press
`40`
### L touch pad touch + press
touch: `08`
press: `0a`
### R touch pad touch + press
touch: `10`
press: `14`

## `11:` js r - touch right (js press)
### right joystick press
`04`

## `13:` 
### back button LR upper
L:`02`
R:`04`

## `16-19:` left touch position
### `16-17:` hor
### `18-19:` ver

## `20-23:` right touch position
### `20-21:` hor
### `22-23:` ver

## `24-43:` gyro
### `24-35:` "relative mode" like joystick inputs
#### `24-26:`
### `36-43:` "position mode" like mouse inputs
#### `36-37:` pitch (up down) 
#### `38-39:` yaw (pan left right around z axis)
#### `40-41:` roll (tilt lr, steering)
#### `42-43:` check sum?

## `44-45:`
### left trigger fade (0-100%)

## `46-47:`
### right trigger fade (0-100%)


## `48-51:`
### `48-49:` joystick move lr/hor
### `50-51:` joystick move ud/ver

## `52-55:`
### `52-53:` joystick move lr/hor
### `54-55:` joystick move ud/ver

