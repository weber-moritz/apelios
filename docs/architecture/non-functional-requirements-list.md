# Non-Functional Requirements List (NFRL)

**Document Type:** Non-Functional Requirements Specification  
**Purpose:** Define HOW WELL the system must perform — the quality attributes, constraints, and performance characteristics that Apelios must meet beyond its functional capabilities.  
**Scope:** System-wide quality attributes  
**Version:** 3.0  
**Last Updated:** 2026-07-27  
**Related Documents:**
- [Functional Requirements (FRL)](functional-requirements-list.md)
- [Architecture Overview](architecture.md)

---

## Overview

The Non-Functional Requirements List (NFRL) captures the **quality attributes** and **constraints** that shape how Apelios must operate. These are the "how well" requirements — the performance, reliability, correctness, and extensibility characteristics that make Apelios production-grade.

While the FRL defines *what* the system does, the NFRL defines *how well* it must do it. These requirements are critical for a real-time lighting control system where latency, reliability, and predictability directly impact user experience.

This document describes the target architecture and does not necessarily reflect the current development stage.

---

## Requirements

### Performance

- **NFR-1.1 Real-Time Operation:** The system must target a 60Hz internal tick rate (16.67ms per frame) synchronized across all layers, operating as a soft real-time system.

- **NFR-1.2 Low Latency:** End-to-end latency (from reading a physical input to dispatching the final DMX/ArtNet packet) must remain below 16.6 milliseconds for the 95th percentile of frames under normal operating conditions to maintain real-time responsiveness.

### Reliability & Fault Tolerance

- **NFR-2.1 Device Resilience:** The system must not crash if a physical input device is disconnected mid-operation. Missing or disrupted input sources must be handled gracefully without system failure.

- **NFR-2.2 Connection Recovery:** The system must automatically detect and recover from communication broker disconnections without requiring manual intervention or software restart.

- **NFR-2.3 Stateless Components:** System components responsible for data routing must not maintain internal state that could cause drift or inconsistency between input and output.

### Correctness & Validation

- **NFR-3.1 Input Validation:** All input values must be validated against their mathematical intent ranges (absolute_uni: 0.0-1.0, absolute_bi: -1.0-1.0, delta/rate: must be finite numbers).

- **NFR-3.2 Intent Type Validation:** All messages must carry a valid intent type from the defined set (absolute_uni, absolute_bi, delta, rate).

- **NFR-3.3 Configuration Validation:** All configuration files (routing.json, patch.json) must be validated against their schemas on startup, with clear error messages for invalid data.

- **NFR-3.4 Payload Schema Validation:** All NATS messages must conform to the standardized payload schema (value: float, type: string, timestamp: float).

- **NFR-3.5 Error Reporting:** All errors must produce clear, actionable messages identifying the source, nature, and context of the problem.

- **NFR-3.6 Clamping Enforcement:** All fixture parameter values must be clamped to their defined physical limits before protocol translation to prevent out-of-bounds protocol values.

### Extensibility & Maintainability

- **NFR-4.1 Input Device Extensibility:** The system must support adding support for new physical input device types without requiring modifications to existing code or components.

- **NFR-4.2 Fixture Extensibility:** The system must support defining new lighting fixture types through external configuration, without requiring changes to core functionality.

- **NFR-4.3 Configuration Management:** System configurations must be defined in human-readable, machine-parseable format with documented structure for easy modification and validation.

### Compatibility & Portability

- **NFR-5.1 Cross-Platform Support:** The system must run on Windows, Linux, and macOS with identical functionality and performance characteristics.

- **NFR-5.2 Protocol Compatibility:** The system must support multiple industry-standard lighting control protocols to ensure compatibility with diverse professional lighting equipment.

### Testability & Quality Assurance

- **NFR-6.1 Testability:** The system architecture must support automated unit testing for all core data transformation logic (normalization, routing, integration) without requiring physical hardware or external services.

- **NFR-6.2 Test Coverage:** Core components (Input Adapters, FixtureCore, Router) must maintain comprehensive test coverage to ensure mathematical correctness and data integrity.

### Security

- **NFR-7.1 Local Isolation:** The NATS communication broker must default to loopback-only connections (localhost) to prevent unauthorized network access to the internal data pipeline.