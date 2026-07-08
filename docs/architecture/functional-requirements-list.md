# Functional Requirements List (FRL)

**Document Type:** Functional Requirements Specification  
**Purpose:** Define WHAT the system must do — the core capabilities and behaviors that Apelios must deliver to fulfill its mission as a professional lighting controller.  
**Scope:** System-wide functional capabilities  
**Version:** 2.0  
**Last Updated:** 2026-07-06  
**Related Documents:**
- [Non-Functional Requirements (NFRL)](non-functional-requirements-list.md)
- [Architecture Overview](architecture.md)

---

## Overview

The Functional Requirements List (FRL) captures the essential **behaviors** and **capabilities** that Apelios must provide. These are the "what" requirements — the features that must be implemented for the system to be considered complete and functional.

Unlike the architectural principles (which define "how" the system should be structured), the FRL defines the concrete functionality that users and downstream systems depend on.

---

## Requirements

### Core Data Pipeline

- **FR-1.1 Hardware Ingestion:** The system must read physical analog axes, digital buttons, and IMU (gyroscope/accelerometer) data from input devices such as Steam Deck adapters.

- **FR-1.2 Multi-Device Support:** The system must simultaneously process inputs from multiple physical devices (e.g., Steam Deck, MIDI controllers, mouse) without interference or signal degradation.

- **FR-1.3 Signal Normalization:** The system must translate raw hardware data into standardized mathematical signals: unipolar absolute (0.0 to 1.0), bipolar absolute (-1.0 to 1.0), rate (velocity), and delta (relative change).

- **FR-1.4 Intent Tagging:** The system must tag each input value with its mathematical intent type (absolute_uni, absolute_bi, delta, rate) at the source.

### Routing & Mapping

- **FR-2.1 Dynamic Routing:** The system must route a specific hardware input to a specific lighting fixture parameter based on a user-defined routing.json configuration file.

- **FR-2.2 Parameter Mapping:** The system must map logical fixture parameters (pan, tilt, intensity, color) to physical DMX addresses according to fixture profiles defined in patch.json.

- **FR-2.3 Many-to-One Routing:** The system must support multiple input sources contributing to a single fixture parameter (e.g., joystick + gyroscope both controlling pan).

### State Management

- **FR-3.1 State Integration:** The system must maintain an internal absolute position for all patched fixtures, mathematically integrating incoming delta and rate signals into that absolute position using time-based calculations.

### Protocol & Output

- **FR-4.1 Protocol Translation:** The system must translate its internal floating-point state (0.0 to 1.0 for unipolar, -1.0 to 1.0 for bipolar) into the correct physical protocol limits (e.g., 8-bit 0-255, 16-bit 0-65535 DMX values) based on a patch.json profile.

- **FR-4.2 Multi-Protocol Support:** The system must support multiple lighting control protocols including DMX and ArtNet for output to physical lighting fixtures.

