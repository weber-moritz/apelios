# ADR 008: State Management

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The system must track accumulated fixture state (e.g., pan/tilt positions) to support features like many-to-one input summation, where multiple inputs (fader + gyro) contribute to the same fixture parameter. We needed to determine where this stateful tracking should occur: distributed across input adapters and router, or centralized in a single layer.

## Decision

We centralize all stateful tracking in the **Fixture Core**. All other layers (Input, Router) remain **stateless** - they normalize, route, and pass through data without retaining any frame-to-frame memory.

The Router is a pure passthrough and does not add or modify fields like `source` or `target`.

Only the Fixture layer is **stateful**, which means it is the only layer that stores input data for more than 1 tick cycle. The Fixture Core tracks per-target state including `value`, `has_first_abs`, and `first_abs_value` to support many-to-one input summation.

This does not mean that each layer cannot have its own configuration files, but those are not created at runtime, so the layer itself has no knowledge about the surrounding layers.

The `source` field originates from the **Input layer** (not Router), ensuring proper separation of concerns where the data producer is self-contained.

## Current Implementation

The inbox format is keyed by `source` (not target) with each entry containing: `{source, target, type, value, timestamp}`. This allows multiple sources to map to the same target via the routing configuration, enabling:

- **Many-to-one summation**: Delta inputs from multiple sources (e.g., fader + gyro) can contribute to the same target
- **First absolute initialization**: The first absolute input to a target sets the base output value
- **Subsequent contributions**: Later inputs (absolute, delta, or rate) contribute changes relative to the current state

The `source` field is required and validated by the fixture_input_subscriber to ensure proper tracking of input origins.

Note: The `target` field is **not** included in the router output payload. The Fixture layer extracts the target from the message topic (`target.<fixture>.<param>`) using wildcard subscriptions. The `source` field is required in the payload to enable many-to-one input summation, where multiple sources can map to the same target and need to be tracked independently. If the broker were to change and no longer support layered or wildcard subscriptions, the `target` field could be added to the payload to allow explicit parsing.

## References
- [ADR-002: Architecture](002-architecture.md) - Overall system architecture and layer separation
- [ADR-003: 60Hz Tick](003-60hz-tick.md) - Fixture Core processing at 60Hz
- [ADR-004: Stateless Input Adapters](004-stateless-input-adapter.md) - Stateless principle applied to input layer
- [ADR-005: Event Contract](005-contract.md) - Payload formats including source field