# Architecture Refactoring Plan: Input, Middleware, and Fixture Layers

## Phase 1: MVP & Immediate Priority List

*Goal: Get the Fixture Layer accurately tracking Steam Deck inputs without drift or hardcoded clamping. Bypass dynamic manifests and routing files for now, and strictly isolate domain responsibilities.*

### 1. Input Layer Modifications (The New Home for Calibration)

* **Keep it Raw (For Now):** For the MVP, just pass the raw hardware values.
* **Future-Proofing:** Acknowledge that any hardware compensation—specifically **deadzones, inversion, and sensitivity curves**—belongs *here*, not in the Middleware. The Input Layer must perfect the signal before it ever hits the broker.

### 2. Middleware Modifications (Strip it down)

* **Remove State:** Delete the "previous" and "current" dictionary stores. The Middleware should no longer remember past values.
* **Remove Math & Compensation:** Delete the delta calculation logic. **Delete the deadzone and sensitivity logic.**
* **Remove Clamping:** Do not force values into a `0.0` to `1.0` range.
* **Add Intent:** Ensure the Middleware passes the raw value *and* its intent `type` (`absolute`, `delta`, or `rate`) downstream to the output topic.

### 3. Fixture Layer Construction (Build the State Engine)

* **Input Module:** Subscribes to the NATS topics coming from the Middleware. Parses the incoming JSON payload (which includes `value` and `type`) and writes it to a high-speed internal buffer/dict.
* **Core Module (The Math Engine):** Runs at 60Hz. Reads the incoming dict, applies the mathematical translation based on the `type` tag (see Math Specs below), and updates the *Internal State Dict*.
* **Output Module:** Reads the Internal State Dict, translates the 0.0-1.0 absolute internal state into physical hardware limits (e.g., 0-255 for 8-bit DMX, or 0-65535 for 16-bit DMX), and sends it out to the physical lighting hardware or network.

---

## Phase 2: Complete Target Architecture

### Overview

The system relies on a microkernel architecture over a central NATS broker. Data flows in a strictly decoupled, unidirectional pipeline: **Hardware -> Input Layer -> Middleware -> Fixture Layer -> Lights**.

### Standardized NATS Payload Schema

All messages passed between the layers must conform to this basic schema:

```json
{
  "value": 0.05, 
  "type": "delta", 
  "timestamp": 1685363400.123 
}

```

*Valid Types:* `absolute_uni` (0 to 1), `absolute_bi` (-1 to 1), `delta` (relative change), `rate` (velocity).

---

### Layer 1: The Input Layer (The Normalizer & Calibrator)

**Role:** Acts as the Hardware Abstraction Layer (HAL). It reads messy physical hardware, compensates for physical flaws, and normalizes data into perfect mathematical floats. It knows nothing about lights.

* **Capabilities Manifest:** On startup, the Input Layer publishes a JSON manifest to NATS describing its available axes and their default `type`.
* **Hardware Compensation:** Handles all physical device flaws. It applies **deadzones**, jitter filtering, and base sensitivity curves so that downstream layers receive pristine data.
* **Configuration:** Subscribes to NATS topics (e.g., `config.input.steamdeck_01.deadzone`) to receive live configuration updates from a central GUI, saving these to a local config file.
* **Execution:** Reads the adapter at 60Hz, applies the math, and publishes standardized payloads to raw input topics (e.g., `input.steamdeck_01.gyro.x`).

---

### Layer 2: The Middleware (The Pure Router)

**Role:** A pure switchboard. It maps `input.>` topics to `target.>` topics. It does **no mathematical conversion, no deadzone compensation, and holds no positional state.**

* **Capabilities Buffer (RAM):** Subscribes to manifest topics and temporarily stores currently connected hardware capabilities in memory.
* **Routing Config (Disk):** Reads `routing.json` on startup. This file contains the user's desired mapping (e.g., map `input.steamdeck_01.gyro.x` to `target.movinghead01.pan`).
* **Execution:** Matches incoming NATS messages against the routing table in memory. When a match is found, it republishes the *identical* payload (including the `type` tag) to the target NATS topic.

---

### Layer 3: The Fixture Layer (The State Engine)

**Role:** Maintains the absolute truth of the physical lighting rig. Handles all mathematical integrations, clamping, and DMX/protocol output.

#### 1. Configuration (`patch.json`)

Reads a local file defining the lighting rig. This is how the Core module knows what NATS topics to listen to and what physical limits to apply.

```json
{
  "fixtures": {
    "movinghead01": {
      "type": "robe_robospot",
      "universe": 2,
      "address": 10,
      "parameters": {
        "pan": { "limits": [0.0, 1.0] },
        "tilt": { "limits": [0.0, 1.0] }
      }
    }
  }
}

```

#### 2. Input Module

Subscribes to all `target.>` topics defined in `patch.json` (e.g., `target.movinghead01.pan`). Validates incoming JSON and writes the newest payload to an inbox dictionary to be processed by the Core.

#### 3. Core Module (State Engine & Math)

Runs a strict 60Hz loop. For every parameter of every patched fixture, it reads the inbox dict, processes the math, and updates the **Internal Output Dict**. It enforces physical limits (clamping) *only* after calculations are complete.

**Mathematical Operations by Type:**
Let $S_{old}$ be the current state, $V_{in}$ be the incoming value, and $L_{min}, L_{max}$ be the parameter's physical limits.

* **If Type is `absolute`:** Overwrite state directly.

$$S_{new} = V_{in}$$


* **If Type is `delta`:** Add change to state, then clamp.

$$S_{new} = \max(L_{min}, \min(L_{max}, S_{old} + V_{in}))$$


* **If Type is `rate`:** Integrate velocity over delta time ($\Delta t$), then clamp.

$$S_{new} = \max(L_{min}, \min(L_{max}, S_{old} + (V_{in} \times \Delta t)))$$



#### 4. Output Module

Reads the finalized **Internal Output Dict** at 60Hz. It translates the normalized state (e.g., `0.5`) into the specific protocol required by the physical light (e.g., converting 0.5 to DMX value 127). It then broadcasts this to the final output network (ArtNet, sACN, NATS out, etc.).