# ADR 0004: Stateless Input Adapters and Centralized State Accumulation

**Date:** April 19, 2026  
**Status:** Accepted  

## 1. Context
Apelios must process hardware inputs from diverse sources with fundamentally different electrical/software behaviors:
* **Absolute (No Wrap):** Faders (e.g., 0.0 to 1.0)
* **Absolute (Wrap):** Gyros, Jogwheels (e.g., 0 to 360 degrees)
* **Continuous / Rate:** Joysticks, Triggers (Deflection from a center deadzone)
* **Relative / Speed:** Mouse, Trackpad (Raw delta values)

These inputs ultimately need to be mapped to a unified output (e.g., the Pan/Tilt of a moving head). We needed to determine where the "Source of Truth" (the Virtual Canvas or Accumulator) for the lighting rig's position should live: in the Input Adapter at the edge, or in the Middleware Core?

## 2. Options Considered

### Option 1: Edge State (Smart Input Modules)
The Input Module keeps track of the "Virtual Canvas". When a joystick is moved, the module calculates the new absolute position and publishes it (e.g., `0.60`, then `0.61`, then `0.62`).
* **Pros:** The Middleware Core is extremely simple; it only processes absolute positions.
* **Cons:** Highly vulnerable to state desync. If an input device loses power, restarts, or reconnects, its local state resets to zero. Upon the first touch, it will send `0.01`, causing the lighting fixture to violently snap back to the start position. It also complicates "multiplayer" (multiple controllers editing the same value).

### Option 2: Core State (Stateless Input Modules)
The Input Module is "dumb". It holds no memory. It reads hardware, normalizes the data, tags it with an "Intent Type" (`absolute`, `delta`, or `rate`), and publishes it. The Middleware Core holds the single Virtual Canvas and applies mathematical accumulation at a locked 60Hz.
* **Pros:** Perfect state retention during disconnects. Hardware nodes can drop in and out of the network seamlessly. Time-dependent math ($\Delta t$ for joysticks) is handled by the stable 60Hz core loop rather than jittery network edge nodes.
* **Cons:** The Middleware Core must be aware of multiple input types and apply different mathematical formulas (`value`, `+= value`, or `+= value * dt`) depending on the type.

## 3. Decision
We will proceed with **Option 2 (Core State / Stateless Adapters)**. 

The Input Adapters will be restricted to translating hardware-specific SDK/HID data into one of three normalized JSON intents:
1. `{"type": "absolute", "value": X}`
2. `{"type": "delta", "value": X}`
3. `{"type": "rate", "value": X}`

The `MappingMiddleware` core will act as the central Accumulator. 

## 4. Consequences
* **Separation of Concerns:** The boundary is firmly established. Edge adapters handle *Hardware Normalization*. The Core handles *Time, Memory, and Integration*.
* **Implementation Requirement:** The Core's `process_frame()` method must be expanded to parse the `type` tag and calculate $\Delta t$ for `rate`-based inputs.
* **Future Proofing:** This explicitly separates the Input Accumulation problem from the Output Priority problem. Because the Core centralizes all deltas, downstream priority policies (Additive/Stacking vs. LTP) can be applied reliably in memory.