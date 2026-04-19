# Apelios Architecture Blueprint
**Version:** 1.0  
**Status:** Active / Project Source of Truth

## 1. System Vision
Apelios is a high-performance lighting middleware designed to bridge input devices (e.g., SteamDeck, MIDI controllers) with output targets (e.g., ArtNet/DMX nodes). The core philosophy is a **Hexagonal Architecture** (Ports and Adapters) that ensures mathematical logic is decoupled from network infrastructure.



---

## 2. Structural Design
The system is divided into three distinct layers to maintain a clean separation of concerns.

### A. The Domain Core (Internal Logic)
* **Main Component:** `MappingMiddleware`
* **Responsibility:** Mathematical transformations, scaling, delta calculations, and state management.
* **Constraint:** Must be **100% Pure Python**. No network imports, no I/O, and no external dependencies that require mocks for core testing.

### B. Adapters (External Infrastructure)
* **Input Subscriber:** A passive listener that parses Broker JSON events and updates the Domain Core.
* **Output Publisher:** An active worker that pulls state from the Core, formats it, and publishes to the Broker.
* **Broker Client:** A generic interface (currently NATS) that abstracts the network protocol away from the business logic.

### C. The Orchestrator (System Glue)
* **Component:** `MainOrchestrator`
* **Responsibility:** 1. Lifecycle management (Booting NATS, then Middleware).
    2. Driving the **60Hz Heartbeat** (the `.tick()` loop).
    3. Performing health checks across all subsystems.

---

## 3. Implementation Constraints

### Timing & Performance
* **Heartbeat:** The orchestrator must maintain a consistent **60Hz frequency** (16.67ms per frame).
* **Frequency Logic:** The tick loop must be self-correcting (calculating elapsed time) to prevent drift.

### Concurrency
* **AsyncIO:** Use `asyncio` for all I/O-bound operations. 
* **No Threading:** Avoid the `threading` module to prevent race conditions and memory-sharing complexities between the Core and Adapters.

### Testing Standard (TDD)
* **Unit Tests:** Every class must have a unit test using `unittest.mock`.
* **Integration Tests:** One "Black Box" test per subsystem (Middleware, Broker) to verify plumbing.
* **System Test:** A background task test for the `MainOrchestrator` to verify end-to-end signal flow.

---

## 4. Communication Contract

### Input Format (`input.>`)
Standardized payload for all input devices:
```json
{
  "source": "device.axis_name",
  "value": 0.00
}