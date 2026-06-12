# Architectural Principles

## Core Principles

These principles define the architectural boundaries and design philosophy for Apelios.

### 1. Strict Separation of Concerns
Each layer must own a **single domain** with no overlap:
- **Input Layer:** Physical hardware calibration, normalization, intent tagging
- **Middleware:** Message routing only (stateless)
- **Fixture Layer:** Mathematical state integration, clamping, protocol translation

> **Why:** Ensures each component can be developed, tested, and modified independently. Prevents domain logic bleed between layers.

### 2. Stateless Routing
The Middleware **must not** hold positional state, perform mathematical conversions, or apply hardware compensations. It routes data **blindly** based solely on NATS topic patterns.

> **Why:** Stateless design enables horizontal scaling, simplifies reasoning, and prevents drift between input and output states.

### 3. Decoupled Communication
Layers **must** communicate exclusively via the NATS broker using a **standardized JSON payload schema**. No layer may have a direct code dependency on another layer.

> **Why:** Enables distributed deployment, supports hot-swapping of components, and maintains clean architectural boundaries.

### 4. Trust the Intent
Data passed between layers **must** carry an intent tag (`absolute_uni`, `absolute_bi`, `delta`, `rate`). Downstream layers **must** trust and execute this intent without assuming upstream context or second-guessing the type.

> **Why:** Intent is domain knowledge that belongs with the source (Input Layer). Downstream layers should not reinterpret the meaning of data.

---

## Current Violations & Fixes

The current implementation (commit 60da486) has architectural violations that need to be addressed.

### 🚨 Principle 1 Violation: Separation of Concerns

**Violation:** Middleware performs intent resolution (domain logic)

| Current Behavior | Problem | Fix |
|------------------|---------|-----|
| Middleware reads `intent` from mapping config and adds it to payload | Middleware is doing Input Layer's job | Move intent/type definition to Input Layer adapters |
| Middleware maintains `current_raw_input` and `virtual_output_state` | Middleware holds state (Fixture's job) | Remove all state from Middleware |

**Impact:** Middleware is currently doing both routing AND domain logic (intent resolution). This violates separation of concerns and makes the system harder to reason about.

### 🚨 Principle 2 Violation: Stateless Routing

**Violation:** Middleware has state

| Current Code | Problem | Fix |
|--------------|---------|-----|
| `MappingMiddleware.current_raw_input` | Stores input values between frames | Remove this dict, process messages immediately |
| `MappingMiddleware.virtual_output_state` | Stores output values | Remove this dict, it's Fixture Layer's responsibility |
| `MappingMiddleware.process_frame(dt)` | Batch processing with state | Change to stateless passthrough |

**Impact:** Stateful Middleware can lose messages if timing is off, and violates the pure router principle.

### 🚨 Principle 3 Violation: Decoupled Communication

**Violation:** Payload schema is inconsistent

| Current Schema | Target Schema | Problem |
|----------------|----------------|---------|
| `{source: "device.axis", value: 0.5}` | `{value: 0.5, type: "delta", timestamp: 123.456}` | Missing type and timestamp fields |

**Impact:** Without `type` in the payload, intent information is lost between layers. Middleware currently compensates by adding intent from config, which violates decoupling.

**Fix:** All layers must use the standardized schema with `value`, `type`, and `timestamp` fields.

### 🚨 Principle 4 Violation: Trust the Intent

**Violation:** Middleware second-guesses intent

| Current Flow | Problem | Target Flow |
|--------------|---------|-------------|
| Input publishes `{source, value}` | No intent in payload | Input publishes `{value, type, timestamp}` |
| Middleware looks up intent in mapping config | Middleware reinterpret intent | Middleware passes through type unchanged |
| Middleware adds intent to payload | Intent is derived, not inherent | Fixture receives type from Input via Middleware |

**Impact:** Intent is not trusted - it's reconstructed by Middleware from external config. This means the data's meaning can change based on config, not based on the source's actual intent.

**Fix:** Input Layer must publish with `type` field. Middleware must pass it through unchanged. Fixture must trust the `type` from the payload.

---

## Terminology

| Term | Definition | Used In |
|------|------------|---------|
| **Intent / Type** | The mathematical meaning of a value: absolute_uni, absolute_bi, delta, or rate | Payload schema |
| **Source** | Identifier for the input device and axis, e.g., `steamdeck.left_stick.x` | Current payload (to be removed) |
| **Target** | Identifier for the fixture parameter, e.g., `movinghead01.pan` | Routing config, target.* topics |
| **Manifest** | JSON document describing an input device's capabilities | Input Layer publishes to NATS |
| **Patch** | JSON document describing the lighting rig configuration | Fixture Layer config |
| **Routing** | JSON document mapping input topics to target topics | Middleware config |

---

## How We're Fixing It

### Step 1: Fix Payload Schema (Input Layer)
- Update `InputPublisher` to publish `{value, type, timestamp}`
- Update all adapters to specify `type` for each axis
- Remove `source` field (replaced by NATS topic structure)

### Step 2: Make Middleware Stateless (Middleware)
- Remove `current_raw_input` dict
- Remove `virtual_output_state` dict
- Remove `process_frame(dt)` batch processing
- Change to immediate passthrough per message
- Remove intent resolution from mapping config

### Step 3: Update Subscribers (Fixture Layer)
- Update `FixtureInputSubscriber` to expect `type` field
- Change field name from `intent` to `type` throughout
- Keep math engine unchanged (it already works correctly)

### Step 4: Clean Up Config (All Layers)
- Remove `intent` and `sensitivity` from mapping files
- Update patch.json to match spec format
- Rename mapping files to routing.json

### Verification
After changes, verify:
- [ ] Input → Middleware → Fixture flow works end-to-end
- [ ] All 127 tests pass (may need updates)
- [ ] Middleware has zero state
- [ ] Middleware does zero math
- [ ] Fixture Layer receives `type` from Input via Middleware
