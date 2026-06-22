# ADR 001: Broker Selection

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

Apelios needs a way to communicate between layers. A broker was chosen as the most flexible solution. It is fast, proven to work reliably, and can handle large amounts of data.

For this development stage, a basic broker abstraction was chosen to avoid complex refactoring. Currently, only NATS is implemented. Real multi-broker support is intended for future work when necessary.

The abstraction creates minimal overhead, but it was decided that this is less important than the modularity benefits.

## Options Considered

### NATS

NATS is a good broker because a server is available for every OS (Linux, Mac, Windows) and comes as a wrapper Python package. It is very fast and has an ultra-low latency pub/sub system, typically used in cloud-native apps.

NATS allows fire-and-forget, which is good for low latency. By comparison, MQTT has QoS levels 1, 2, and 3 with retained messages. NATS offers JetStream (not used here), which also provides retained messages as a key-value store.

Latency comparison: MQTT offers low latency, while NATS achieves sub-millisecond latency.

NATS needs more RAM for JetStream and is better suited for servers than embedded systems. MQTT has extremely lightweight clients.

MQTT has lighter CPU and RAM usage. Multiple MQTT implementations exist, while NATS has only one first-class implementation.

MQTT could be used as a fallback if NATS does not work on Android.

NATS supports all operating systems (Linux, Windows, Mac) as well as ARM (32/64-bit) and x86 architectures.

NATS is a better choice than Redis because it is platform-native. There is a pip package that directly includes all binaries for all operating systems and can be started from there. This is a good solution for development. For the official release, the actual NATS binary should be included as external data.

It is likely faster. It has subjects (similar to MQTT topics) and supports wildcard subscriptions. For example, you can subscribe to `inputs.*` and receive `inputs.controller.*` and `inputs.mouse.*` with it.

## Alternatives

| Solution | Complexity | Latency | Keep-Alive Method | Pros | Cons | Best For |
|----------|-----------|---------|-------------------|------|------|----------|
| **Redis** | Low-Medium | <1ms | TTL keys + EXPIRE | Very fast, simple API, built-in pub/sub, widely used | Requires separate service, in-memory only (data loss risk) | Low-latency, real-time apps |
| **In-Memory Map** | Very Low | <0.1ms | setTimeout/setInterval | No dependencies, simplest solution, no setup | Not scalable across servers, manual cleanup needed | Single-server apps, prototypes |
| **WebSocket ping/pong** | Low | <5ms | Native WS frames | Built into protocol, no external deps | Manual handling, needs heartbeat logic | Direct client-server connections |
| **Server-Sent Events (SSE)** | Low | <10ms | HTTP keep-alive headers | Browser native, automatic reconnect | One-way only, HTTP overhead | Simple server-to-client updates |
| **PostgreSQL LISTEN/NOTIFY** | Medium | 10-50ms | Custom heartbeat table | Use existing DB, transactional | Higher latency, not designed for real-time | Apps already using PostgreSQL |
| **RabbitMQ** | High | 5-20ms | Heartbeat frames | Guaranteed delivery, robust | Complex setup, overkill for simple cases | Mission-critical messaging |
| **Kafka** | Very High | 10-100ms | Consumer heartbeats | Massive scale, event sourcing | Complex, high latency, resource heavy | Big data, event streaming |
| **Socket.io** | Low | <5ms | Built-in heartbeat | Handles everything, fallbacks | Opinionated, adds overhead | Quick implementation, broad browser support |

### Redis

Redis in redislite Python package:
- What is redislite?
  - Python native implementation of Redis
  - Takes care of cleanup and start and stop

## Decision

NATS is the best choice for real-time applications in this system.

## Consequences

- Flexibility and separation of concerns allow for easy modification
- Broker abstraction enables future multi-broker support
- Minimal overhead is accepted for modularity benefits

