# ADR 010: Output Layer Independent Adapter Timing

**Date:** 2026-07-10  
**Status:** Accepted  
**Related:** ADR-002 (Architecture), ADR-003 (60Hz Tick), ADR-004 (Stateless Adapters), ADR-008 (State Management), ADR-009 (Orchestrator)

---

## Context

The Apelios system uses a 60Hz orchestrator tick (per ADR-003 and ADR-009) to drive the Input, Router, and Fixture layers at a consistent rate. This synchronized timing prevents drift and ensures predictable behavior for time-dependent calculations, particularly for `rate`-type inputs.

The Output Layer presents a different challenge. While lighting protocols specify rate ranges rather than fixed values (per ADR-003: DMX 30-50Hz, ArtNet 40-60Hz, sACN 44-50Hz), the 60Hz orchestrator tick cannot produce consistent timing for these rates due to alignment issues.

With a 60Hz orchestrator generating ticks at 0ms, 16.67ms, 33.33ms, 50ms, 66.67ms:

Attempting a 40Hz rate (25ms interval) with relative time checks results in effective intervals of 33.33ms, producing an actual rate of approximately 30Hz rather than the intended 40Hz.

Even with absolute time checks, the constraint remains: sends can only occur when the orchestrator invokes the adapter. Since 25ms is not a multiple of 16.67ms, consistent 40Hz or 44Hz timing cannot be achieved within the tick-based model.

The previous architecture had OutputCore calling `adapter.send_dmx()` on each tick, with adapters implementing rate limiting internally. This approach tied adapter timing to the orchestrator's 60Hz rhythm, making consistent protocol-specific rates impossible.

## Decision

Output Layer adapters run independent timing loops, decoupled from the orchestrator's 60Hz tick. The OutputCore continues to be updated by the orchestrator at 60Hz, but adapters read from this state and transmit at their configured rates using their own loops.

This creates a hybrid timing model:
- **Input/Router/Fixture**: Driven by orchestrator at 60Hz (unchanged, per ADR-003, ADR-009)
- **OutputCore**: Updated by orchestrator at 60Hz (state management only)
- **Output Adapters**: Run independent loops at configured rates (timing control)

The key insight is **architectural independence**. While protocols have tolerance ranges, the critical requirements are that each adapter maintains a consistent rate within its supported range, and that the Output Layer timing is independent of the orchestrator's 60Hz timing.

## Consequences

We centralize DMX state in OutputCore while giving each adapter control over its transmission timing. This separation ensures that state management remains centralized (per ADR-008) while timing control is delegated to the adapters.

The orchestrator continues to drive the overall system at 60Hz, maintaining synchronization for Input, Router, and Fixture layers. OutputCore receives state updates at this rate, but adapters consume this state at their own cadence.

- Timing independence allows each adapter to maintain consistent intervals within its protocol's supported range, eliminating jitter and drift caused by orchestrator alignment.

- Multiple adapters can operate at different rates simultaneously without interference, enabling ArtNet at 40Hz, sACN at 44Hz, and DMX at 44Hz to coexist seamlessly.

- Absolute time scheduling (`next_send = now + interval`) ensures consistent intervals between transmissions.

- The separation of concerns is maintained: OutputCore handles state, adapters handle timing and transmission, RuntimeManager handles lifecycle.

- Adapters remain stateless (per ADR-004), reading from OutputCore rather than maintaining their own DMX state.

This approach introduces two exceptions to existing ADRs:

- **ADR-003**: Output adapters are not driven by the 60Hz orchestrator tick, as protocol rates cannot be consistently achieved within the 60Hz tick constraints. This exception is limited to Output Layer adapters; all other layers continue to use the 60Hz tick.

- **ADR-009**: Output adapters have independent timing loops. However, the principle of preventing drift is maintained through independent absolute scheduling, while Input/Router/Fixture layers continue to be driven by the global tick function.

## References

- [ADR-002: Architecture](002-architecture.md) - Micro-kernel architecture with manager classes
- [ADR-003: 60Hz Tick](003-60hz-tick.md) - Fixture Core processing at 60Hz; protocol rate ranges
- [ADR-004: Stateless Input Adapters](004-stateless-input-adapter.md) - Stateless principle applied to input layer
- [ADR-008: State Management](008-state-management.md) - Centralized state in Fixture Core
- [ADR-009: Orchestrator](009-orchestrator.md) - Orchestrator as central timing master
- [Art-Net Specification](https://art-net.org.uk/downloads/art-net.pdf) - Protocol timing requirements
- [sACN Guide](https://entertainment.sundrax.com/blog/ultimate-guide-sacn-control-lighting-over-network) - Streaming ACN timing
- [DMX Guide](https://dmx-guide.com/) - DMX512 protocol timing standards

---

*Document Version: 1.0*  
*Author: Mistral Vibe*  
*Created: 2026-07-10*
