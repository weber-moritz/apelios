the main logic in the middleware runs at 60hz, or every 16ms

60hz is a good choice as it is rather fast, and faster than the common protocols. default for most protocols is 40-44Hz:

- DMX512: standard is 44 Hz. most devices support 30-50 hz, max is roughly 60hz?
- artnet (udp over ethernet): 40-60 Hz per Universe
- sACN(udp): 40-60 Hz per universe. supports higher rates