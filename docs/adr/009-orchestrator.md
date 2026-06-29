# ADR 009: Orchestrator

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The main orchestrator is the entry point for Apelios. It starts and stops all layers and injects dependencies. It also triggers the tick function to calculate the current frame in each layer. Additionally, the orchestrator performs health checks on each layer.

This makes the orchestrator the central place where all layers are managed and from which they receive global settings and commands.

## Central Instances and Dependency Injection

The orchestrator creates all layer instances in a central location. This guarantees consistent dependencies across all layers.

## Startup Sequence

1. Broker
2. Fixture layer
3. Middleware
4. Input layer

All other layers depend on the broker to communicate. Starting it at a later stage would break the broker clients as they cannot connect.

The startup sequence runs backward relative to the data flow. This prevents messages from being sent to layers that are not yet ready.

The sequence order is less critical as the actual calculation and data flow only begins with the first tick call.

## Shutdown Sequence

1. Input layer
2. Middleware
3. Fixture layer
4. Broker layer

The stop sequence follows the data flow direction to halt new data flow immediately.

The broker is stopped last to avoid breaking broker clients or causing them to unnecessarily search for a disconnected broker.

## 60Hz Tick

This global tick function triggers the tick in each layer. This ensures that each layer stays in sync and does not drift if they calculated ticks independently. For more information, see ADR 003: 60Hz Tick Rate.

The sequence of tick calls follows the data flow direction to ensure all data is sent as close to real-time as possible, as required by the functional requirements.

## Health Check

Each layer exposes a health check function that the orchestrator uses on every tick to verify all layers are running and to catch errors early.

## References
- [ADR-002: Architecture](002-architecture.md) - Overall system architecture
- [ADR-003: 60Hz Tick](003-60hz-tick.md) - Tick rate coordination
- [ADR-004: Stateless Input Adapters](004-stateless-input-adapter.md) - Stateless principle enabled by orchestrator

