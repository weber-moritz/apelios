# ADR 002: Architecture

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

This architecture is a microkernel/hexagonal architecture.

A microkernel means that every module has its own manager (`runtime_manager`) class. It routes information inside the module and has start, stop, and tick functions that are called by the `main_orchestrator`.

The architecture in each module is not identical. The middleware has a very simple hexagonal architecture. The broker has 2 modules: the `broker_runtime_manager` and the `broker_client`. The runtime manager gets started/stopped by the main orchestrator. The client is imported by all modules that require communication.

It would also be possible to use a single client for all modules and pass the reference from the main orchestrator to the modules, but that would conflict with the modularization targeted by this project.

## Decision

This architecture fulfills the non-technical requirements (NTR):

**Modularization:** Each module can be exchanged or changed with minimal changes to other modules. Only the orchestrator knows about the other modules; the modules themselves do not know what other modules exist.

**Stability:** Is achieved through independent modules. Should one module stop working, that would not affect the other modules.

## Layers

### Fixture and Middleware Separation

Separation of concerns between the middleware and fixture layer is achieved by having **input adapters** include type information (`absolute_uni`, `absolute_bi`, `rate`, `delta`) with each value. The fixture layer reads this type directly and applies the appropriate math, while middleware acts as a pure passthrough—eliminating the state desync and packet loss issues that occurred when middleware performed transformations.

## References

- [ADR-004: Stateless Input Adapters](004-stateless-input-adapter.md) - Stateless principle applied to input layer
- [ADR-005: Event Contract](005-contract.md) - Payload formats and topic structure
- [ADR-008: State Management](008-state-management.md) - Centralized state in Fixture Core
- [Software Architecture Patterns](https://www.geeksforgeeks.org/software-engineering/types-of-software-architecture-patterns/)
- [Design Patterns in System Architecture](https://www.geeksforgeeks.org/system-design/design-patterns-architecture/)
- [Microsoft Azure Architecture Styles](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/)
