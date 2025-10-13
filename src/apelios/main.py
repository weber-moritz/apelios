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
import pygame

def main():
    print("--- Hello there ---")

        # pygame setup
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            # Print all event attributes for debugging
            print(event)

            # If you want to specifically check for joystick (gyro) events:
            if event.type == pygame.JOYAXISMOTION:
                print(f"Joystick {event.joy} axis {event.axis} value: {event.value}")
            if event.type == pygame.QUIT:
                running = False

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("purple")


        # RENDER YOUR GAME HERE

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(60)  # limits FPS to 60


    pygame.quit()


# This special block tells Python to run the main() function
# only when this file is executed directly.
if __name__ == "__main__":
    main()