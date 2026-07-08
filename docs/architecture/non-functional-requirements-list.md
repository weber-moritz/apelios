# Non-Functional Requirements List (NFRL)

**Document Type:** Non-Functional Requirements Specification  
**Purpose:** Define HOW WELL the system must perform — the quality attributes, constraints, and performance characteristics that Apelios must meet beyond its functional capabilities.  
**Scope:** System-wide quality attributes  
**Version:** 2.0  
**Last Updated:** 2026-07-06  
**Related Documents:**
- [Functional Requirements (FRL)](functional-requirements-list.md)
- [Architecture Overview](architecture.md)

---

## Overview

The Non-Functional Requirements List (NFRL) captures the **quality attributes** and **constraints** that shape how Apelios must operate. These are the "how well" requirements — the performance, reliability, scalability, and maintainability characteristics that make Apelios production-grade.

While the FRL defines *what* the system does, the NFRL defines *how well* it must do it. These requirements are critical for a real-time lighting control system where latency, reliability, and extensibility directly impact user experience.

This document describes the target architecture and does not necesarrily reflext the current development stage. 

---

## Requirements

### Performance

- **NFR-1.1 Real-Time Operation:** The system must operate on a strict 60Hz internal tick rate (16.67ms per frame) synchronized across all layers.

- **NFR-1.2 Low Latency:** End-to-end latency (from reading a physical input to dispatching the final DMX/ArtNet packet) must not exceed 16.6 milliseconds to maintain real-time responsiveness.

### Reliability & Fault Tolerance

- **NFR-2.1 Device Resilience:** The system must not crash if a physical input device is disconnected mid-operation. Missing or disrupted input sources must be handled gracefully without system failure.

- **NFR-2.2 Connection Recovery:** The system must automatically detect and recover from communication broker disconnections without requiring manual intervention or software restart.

- **NFR-2.3 Stateless Components:** System components responsible for data routing must not maintain internal state that could cause drift or inconsistency between input and output.

### Extensibility & Maintainability

- **NFR-3.1 Input Device Extensibility:** The system must support adding support for new physical input device types without requiring modifications to existing code or components.

- **NFR-3.2 Fixture Extensibility:** The system must support defining new lighting fixture types through external configuration, without requiring changes to core functionality.

- **NFR-3.3 Configuration Management:** System configurations must be defined in human-readable, machine-parseable format with documented structure for easy modification and validation.

### Compatibility & Portability

- **NFR-4.1 Cross-Platform Support:** The system must run on Windows, Linux, and macOS with identical functionality and performance characteristics.

- **NFR-4.2 Protocol Compatibility:** The system must support multiple industry-standard lighting control protocols to ensure compatibility with diverse professional lighting equipment.