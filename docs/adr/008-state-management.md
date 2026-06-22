# ADR 008: State Management

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The functional requirements require the system to be modular, which also means information-independence and separation of concerns. The layers only follow the defined contract and just pass the data through to the next layer without knowing about the previous or next layer.

## Decision

To achieve this, the stateless requirement was developed. The reason is that assuming information about how the next layer works would violate the modular and information independence requirements.

All layers pass all required information along to the next layer, so that each layer can be refactored or changed without touching the information that the previous layer sends.

Only the Fixture layer is **stateful**, which means it is the only layer that stores input data for more than 1 tick cycle. The Fixture Core tracks per-target state including `value`, `has_first_abs`, and `first_abs_value` to support many-to-one input summation.

This does not mean that each layer cannot have its own configuration files, but those are not created at runtime, so the layer itself has no knowledge about the surrounding layers.

## Current Implementation (Phase 6)

The inbox format is keyed by `source` (not target) with each entry containing: `{source, target, type, value, timestamp}`. This allows multiple sources to map to the same target via the routing configuration, enabling:

- **Many-to-one summation**: Delta inputs from multiple sources (e.g., fader + gyro) can contribute to the same target
- **First absolute initialization**: The first absolute input to a target sets the base output value
- **Subsequent contributions**: Later inputs (absolute, delta, or rate) contribute changes relative to the current state

The `source` field is required and validated by the fixture_input_subscriber to ensure proper tracking of input origins.