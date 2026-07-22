# Apelios Architecture

**Version:** 2.0  
**Last Updated:** 2026-07-06  
**Architecture Style:** Micro-Kernel / Decoupled Event-Driven Pipeline

---

## Table of Contents
1. [System Vision](#1-system-vision)
2. [Project Context](#2-project-context)
3. [Architectural Principles](#3-architectural-principles)
4. [System Architecture](#4-system-architecture)
5. [Payload Schema](#5-payload-schema)
6. [Layer Definitions](#6-layer-definitions)

**Related Documents:**
- [Functional Requirements (FRL)](frl.md)
- [Non-Functional Requirements (NFRL)](non-functional-requirements-list.md)
- [Architecture Changes & Migration](architecture-changes.md)

---

## 1. System Vision

Apelios is a **Micro-Kernel Architecture** centered on a **Decoupled Event-Driven Pipeline** with a central NATS broker. Data flows in a strictly **unidirectional** path:

**Hardware → Input Layer → Router → Fixture Layer → Lights**

Each layer has a single responsibility and communicates exclusively via NATS topics using a **standardized JSON payload schema**. Layers have **zero direct code dependencies** on each other.

The **Main Orchestrator** manages the system lifecycle and injects a shared **Broker Client** instance into each layer's Runtime Manager.

---

## 2. Project Context

### AI Persona & Role
You are acting as a **Senior Software Architect and TDD Coach**. Your goal is to help build a production-grade, high-performance lighting controller.

### Project Stack
- **Language:** Python 3.12+ (Strict typing using `-> None`, `|`, etc. and PEP standards)
- **Concurrency:** `asyncio` (Strictly NO `threading` module)
- **Broker:** NATS (`nats-py`)
- **Testing:** `pytest`, `pytest-asyncio`, `unittest.mock`

### Core Architectural Rules (NEVER VIOLATE)
1. **The Micro-Kernel Pipeline:** The system uses a Decoupled Event-Driven Pipeline. Modules do not import each other. They communicate exclusively via the injected NATS Event Broker.
2. **Stateless Edge, Smart Core:** Input Adapters are DUMB and STATELESS. They read hardware, normalize to `[0.0, 1.0]`, tag the intent (`absolute`, `delta`, `rate`), and publish. The Fixture Core is SMART. It holds the state and calculates time integrations (`dt`).
3. **The 60Hz Heartbeat:** The Orchestrator drives the Core at a locked 60Hz. Time-based math (like joystick rates) relies on the Core's delta-time (`dt`), NOT on network packet arrival times.

### TDD & Workflow Guardrails
When implementing a feature, follow these steps in order:
1. **Rule 1: Logic First.** Explain the architectural "Why" (Control Theory, System Design) before writing any code.
2. **Rule 2: Blueprint over Monolith.** Provide conceptual blueprints, interfaces, or specific method snippets. Encourage writing the glue code.
3. **Rule 3: Test-Driven Discipline.** Do not write implementation code until the testing strategy is defined. Always help write the failing test (The "Red" phase) first.
4. **Rule 4: Mocks.** Use pure Python dictionaries/data classes to test the Domain Core. Use `AsyncMock` to test Adapters. Real NATS servers are only used in Integration tests via `asyncio.create_task()`.

---

## 3. Architectural Principles

### Core Principles
These principles define the architectural boundaries and design philosophy for Apelios.

#### 1. Strict Separation of Concerns
Each layer must own a **single domain** with no overlap:
- **Input Layer:** Physical hardware calibration, normalization, intent tagging
- **Router:** Message routing only (stateless)
- **Fixture Layer:** Mathematical state integration, clamping, protocol translation

> **Why:** Ensures each component can be developed, tested, and modified independently. Prevents domain logic bleed between layers.

#### 2. Stateless Routing
The Router **must not** hold positional state, perform mathematical conversions, or apply hardware compensations. It routes data **blindly** based solely on NATS topic patterns.

> **Why:** Stateless design enables horizontal scaling, simplifies reasoning, and prevents drift between input and output states.

#### 3. Decoupled Communication
Layers **must** communicate exclusively via the NATS broker using a **standardized JSON payload schema**. No layer may have a direct code dependency on another layer.

> **Why:** Enables distributed deployment, supports hot-swapping of components, and maintains clean architectural boundaries.

#### 4. Trust the Intent
Data passed between layers **must** carry an intent tag (`absolute_uni`, `absolute_bi`, `delta`, `rate`). Downstream layers **must** trust and execute this intent without assuming upstream context or second-guessing the type.

> **Why:** Intent is domain knowledge that belongs with the source (Input Layer). Downstream layers should not reinterpret the meaning of data.

---

## 4. System Architecture

### Structural Diagram

See: [system-architecture.drawio](../diagrams/system-architecture.drawio) for the visual representation of the architecture.

For additional context diagrams, see:
- [router-architecture.drawio](../diagrams/router-architecture.drawio)
- [C4 Context Diagrams](../c4/) (c1-apelios.drawio through c4-apelios.drawio)

### Quick Reference: Topic Flow

**Data Flow:**
```
Input: {value: 0.5, type: "rate", timestamp: ...}
    → Router (passthrough, no changes)
    → {value: 0.5, type: "rate", timestamp: ...}
    → Fixture
```

---

## 5. Payload Schema

**ALL** messages between layers use this schema:

```json
{
  "value": 0.05,
  "type": "delta",
  "timestamp": 1685363400.123
}
```

### Valid Types
| Type | Description | Range | Example Use |
|------|-------------|-------|-------------|
| `absolute_uni` | Unipolar absolute | 0.0 to 1.0 | Faders, buttons |
| `absolute_bi` | Bipolar absolute | -1.0 to 1.0 | Joystick axes |
| `delta` | Relative change | Unbounded | Mouse movement |
| `rate` | Velocity | Unbounded | Gyroscope, rate-based control |

### Topic Space
| Layer | Publishes To | Subscribes To | Payload |
|-------|--------------|---------------|---------|
| Input | `input.<device>.<axis>` | - | `{value, type, timestamp}` |
| Input | `input.<device>.manifest` | - | Capabilities manifest |
| Router | `target.<fixture>.<param>` | `input.>` | `{value, type, timestamp}` (unchanged) |
| Fixture | `output.<universe>.<address>` | `target.>` | `{value, type, timestamp}` processed |

---

## 6. Layer Definitions

### A. System Orchestration (Lifecycle Manager)

**Main Orchestrator:** The micro-kernel of the application.
- Boots the NATS server
- Instantiates Broker Client instances
- Injects clients into layer Runtime Managers
- Manages the 60Hz tick loop
- Coordinates startup/shutdown order

### B. Communication Layer (Event Broker)

**NATS Broker:** The absolute center of the data pipeline.
- All inter-layer communication happens via NATS topics
- Modules never talk to each other directly
- Supports distributed deployment across multiple machines

### C. Input Layer (Hardware Abstraction Layer - HAL)

**Role:** Read messy physical hardware, compensate for physical flaws, normalize to mathematical floats, and publish with intent.

#### Responsibilities
- **Hardware Abstraction:** Support multiple input devices (Steam Deck, Mouse, MIDI, etc.)
- **Hardware Compensation:** Apply per-axis scaling and deadzones (scale then deadzone to filter in output units)
- **Normalization:** Convert raw hardware values to standardized floats
- **Intent Tagging:** Determine and publish the `type` for each axis (absolute_uni, absolute_bi, delta, rate)
- **Capabilities Manifest:** Publish available axes and their properties on startup

#### Components
1. **Input Runtime Manager:** Lifecycle, broker connectivity, adapter management
2. **Input Publisher:** Publish normalized events with type to `input.<device>.<axis>`
3. **Base Input Adapter:** Interface contract for all adapters
4. **Device Adapters:** Steam Deck, Mouse, Fake, etc.

### D. Router (Pure Router)

**Role:** A **stateless** switchboard that maps input topics to target topics.

#### Responsibilities
- **Topic Routing:** Map `input.<device>.<axis>` to `target.<fixture>.<parameter>`
- **Capabilities Buffer:** Store input manifests in RAM for validation
- **NO Math:** Must NOT perform any transformations, calculations, or compensations
- **NO State:** Must NOT store any positional or historical data
- **Passthrough:** Republish identical payload (including `type`) to target topic

#### Components
1. **Router Runtime Manager:** Lifecycle, broker connectivity
2. **Router Input Subscriber:** Receive from `input.>` topics
3. **Topic Router:** Lookup routing table, forward messages
4. **Router Output Publisher:** Publish to `target.>` topics

#### Routing Configuration
```json
{
  "mappings": {
    "input.steamdeck.right_stick.x": "target.movinghead01.pan",
    "input.steamdeck.imu.yaw": "target.movinghead01.pan"
  }
}
```

### E. Fixture Layer (State Engine)

**Role:** Maintain the absolute truth of the physical lighting rig. Handle all mathematical integrations, clamping, and protocol output.

#### Responsibilities
- **State Management:** Maintain absolute position for all patched parameters
- **Mathematical Integration:** Apply delta/rate math based on incoming `type`
- **Clamping:** Enforce physical limits after calculations
- **Protocol Translation:** Convert normalized state to DMX/ArtNet values

#### Components
1. **Fixture Runtime Manager:** Lifecycle, broker connectivity, 60Hz loop
2. **Fixture Input Subscriber:** Subscribe to `target.>` topics, populate inbox
3. **Fixture Core:** State engine, math processing, clamping
4. **Fixture Output Publisher:** Publish DMX values to `output.>` topics

#### Configuration (patch.json)
```json
{
  "fixtures": {
    "movinghead01": {
      "type": "robe_robospot",
      "universe": 2,
      "address": 10,
      "parameters": {
        "pan": { "limits": [0.0, 1.0], "width": 16 },
        "tilt": { "limits": [0.0, 1.0], "width": 16 }
      }
    }
  }
}
```

#### Mathematical Operations (by type)
Let $S_{old}$ = current state, $V_{in}$ = incoming value, $L_{min}, L_{max}$ = parameter limits, $\Delta t$ = frame time.

| Type | Formula | Clamping |
|------|---------|----------|
| `absolute_uni` / `absolute_bi` | $S_{new} = V_{in}$ | After assignment |
| `delta` | $S_{new} = \max(L_{min}, \min(L_{max}, S_{old} + V_{in}))$ | After addition |
| `rate` | $S_{new} = \max(L_{min}, \min(L_{max}, S_{old} + (V_{in} \times \Delta t)))$ | After integration |

### F. Output Layer (Protocol Adapters)

**Role:** Translate Fixture Layer output to physical protocols.

- **DMX:** 8-bit (0-255) and 16-bit (0-65535) support
- **ArtNet:** Network-based DMX distribution
- **sACN:** Ethernet lighting protocol
- **NATS Out:** For distributed systems

---

## Terminology

| Term | Definition | Used In |
|------|------------|---------|
| **Intent / Type** | The mathematical meaning of a value: absolute_uni, absolute_bi, delta, or rate | Payload schema |
| **Source** | Identifier for the input device and axis, e.g., `steamdeck.left_stick.x` | NATS topic structure |
| **Target** | Identifier for the fixture parameter, e.g., `movinghead01.pan` | Routing config, target.* topics |
| **Manifest** | JSON document describing an input device's capabilities | Input Layer publishes to NATS |
| **Patch** | JSON document describing the lighting rig configuration | Fixture Layer config |
| **Routing** | JSON document mapping input topics to target topics | Router config |

---

**Document Version:** 1.0  
**Author:** Mistral Vibe (for motzel)  
**Created:** 2026-07-06  
**Status:** Pure vision document

*See the individual source files in this directory for detailed historical context.*
