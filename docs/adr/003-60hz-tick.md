# ADR 003: 60Hz Tick Rate

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The Fixture Core processes inputs at 60Hz, so roughly every 16ms. This provides a stable timing basis for the entire system.

## Considerations
As an alternative to the tick, everything could also be calculated as fast as the system allows. This would slow down the system as it would run as fast as possible without limitations.

As a reference, most other real time applications like game engines use a similar frame system, so each calulcation is frame dependent. In addition, the 60hz limit is considered a good speed as humans struggle to detect 10-30 ms differences.

In addition, most lighting protocols have an upper limit of 60hz or exceeds it even. And ArtNet for example needs an update every 30-60hz anyways before the sender is considered dead.

The default for most protocols is 40-44Hz:

- DMX512: standard is 44 Hz. Most devices support 30-50 Hz, max is roughly 60Hz
- ArtNet (UDP): 40-60 Hz per Universe
- sACN (UDP): 44-50 Hz per universe, supports higher rates

The 60Hz tick rate ensures that time-dependent calculations (especially for `rate`-type inputs) are handled consistently.

## References
- [ADR-002: Architecture](002-architecture.md) - Overall system architecture
- [ADR-008: State Management](008-state-management.md) - Fixture Core statefulness at 60Hz
- https://docs.unity3d.com/6000.4/Documentation/Manual/managing-time-and-frame-rate.html
- https://dl.acm.org/doi/10.1145/3355088.3365170
- https://dev.to/pubnub/how-fast-is-real-time-human-perception-and-technology-1308
- https://dmx-guide.com/
- https://art-net.org.uk/downloads/art-net.pdf
- https://entertainment.sundrax.com/blog/ultimate-guide-sacn-control-lighting-over-network
