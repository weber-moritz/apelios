# ADR 003: 60Hz Tick Rate

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The Fixture Core processes inputs at 60Hz, or every 16ms. This provides a stable timing basis for the entire system.

## Decision

60Hz is a good choice because it is fast and exceeds the refresh rate of common lighting protocols. The default for most protocols is 40-44Hz:

- DMX512: standard is 44 Hz. Most devices support 30-50 Hz, max is roughly 60Hz
- ArtNet (UDP over Ethernet): 40-60 Hz per Universe
- sACN (UDP): 40-60 Hz per universe, supports higher rates

The 60Hz tick rate ensures that time-dependent calculations (especially for `rate`-type inputs) are handled consistently.