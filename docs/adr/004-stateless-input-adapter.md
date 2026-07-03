# ADR 0004: Stateless Input Adapters and Centralized State Accumulation

**Date:** April 19, 2026  
**Status:** Accepted  

## 1. Context
Apelios must process hardware inputs from diverse sources with fundamentally different electrical/software behaviors:
* **Absolute Unipolar:** Faders, Buttons (e.g., 0.0 to 1.0)
* **Absolute Bipolar:** Joysticks, Analog Sticks (e.g., -1.0 to 1.0)
* **Rate:** Gyros, IMU (Angular velocity / deflection rate)
* **Delta:** Mouse, Trackpad (Raw relative movement)

These inputs ultimately need to be mapped to a unified output (e.g., the Pan/Tilt of a moving head). We needed to determine where the "Source of Truth" (the Virtual Canvas or Accumulator) for the lighting rig's position should live: in the Input Adapter at the edge, in the Middleware Core, or in the Fixture Core?

## 2. Options Considered

### Option 1: Edge State (Smart Input Modules)
The Input Module keeps track of the "Virtual Canvas". When a joystick is moved, the module calculates the new absolute position and publishes it (e.g., `0.60`, then `0.61`, then `0.62`).
* **Pros:** The Middleware Core and Fixture Core are simple; they only process absolute positions.
* **Cons:** Highly vulnerable to state desync. If an input device loses power, restarts, or reconnects, its local state resets to zero. Upon the first touch, it will send `0.01`, causing the lighting fixture to violently snap back to the start position.

### Option 2: Core State (Stateless Input Modules)
The Input Module is "dumb". It holds no memory. It reads hardware, normalizes the data, tags it with a `type` (`absolute_uni`, `absolute_bi`, `delta`, or `rate`), and publishes it with a timestamp. The Fixture Core holds the single Virtual Canvas and applies mathematical accumulation at a locked 60Hz.
* **Pros:** Perfect state retention during disconnects. Hardware nodes can drop in and out of the network seamlessly. Time-dependent math ($\Delta t$ for joysticks) is handled by the stable 60Hz core loop rather than jittery network edge nodes.
* **Cons:** The Fixture Core must be aware of multiple input types and apply different mathematical formulas (`value`, `+= value`, or `+= value * dt`) depending on the type.

## 3. Decision
We will proceed with **Option 2 (Core State / Stateless Adapters)**. 

The Input Adapters will be restricted to translating hardware-specific SDK/HID data into a single broker payload shape:
`{"value": X, "type": "absolute_uni", "timestamp": T, "source": "input.device.axis"}`

The Middleware is a pure passthrough, forwarding the input payload unchanged to the target topic. The `FixtureCore` will act as the central Accumulator. 

## 4. Consequences
* **Separation of Concerns:** The boundary is firmly established. Edge adapters handle *Hardware Normalization*. The Fixture Core handles *Time, Memory, and Integration*.
* **Implementation Requirement:** The Fixture Core's `process_frame()` method must resolve input behavior and calculate $\Delta t$ for `rate`-based inputs. The Middleware is stateless and does not have a `process_frame()` method.
* **Payload Contract:** Input adapters publish normalized `value`, `type`, `timestamp`, and `source`. The `value`, `type`, `timestamp`, and `source` fields flow through the entire pipeline unchanged.
* **Future Proofing:** This explicitly separates the Input Accumulation problem from the Output Priority problem. Because the Fixture Core centralizes all state, downstream priority policies (Additive/Stacking vs. LTP) can be applied reliably in memory.

## References:
- [ADR-002: Architecture](002-architecture.md) - Overall system architecture
- [ADR-005: Event Contract](005-contract.md) - Payload formats and topic structure
- [ADR-008: State Management](008-state-management.md) - Centralized state in Fixture Core
