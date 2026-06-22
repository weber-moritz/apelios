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

Separation of concerns between the middleware and fixture layer is achieved by having the input layer send type information with each value. The type can be: `absolute_uni`, `absolute_bi`, `rate`, or `delta` so that the fixture layer knows how to process it.

This was needed because:
- If an absolute input like a fader is transformed into a rate value by the middleware, then it gets sent to the fixture layer which would need to convert it back to absolute, causing state desync
- If there is packet loss between the middleware and the fixture layer, the values get out of sync

The fix is to send the type with the value so the fixture layer can apply the appropriate math directly.