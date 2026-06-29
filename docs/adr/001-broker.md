# ADR 001: Broker Selection

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

Apelios needs a way to communicate between layers. A broker was chosen as the most flexible solution. It is fast, proven to work reliably, and can handle large amounts of data.

For this development stage, a basic broker abstraction was chosen to avoid complex refactoring in the future. That means all other layers use an abstracted broker client. Currently, only NATS is implemented. Real multi-broker support is intended for future work when necessary.

The abstraction creates minimal overhead, but it was decided that this is less important than the modularity benefits.

## Options Considered

| Solution | Complexity | Latency | Keep-Alive Method | Pros | Cons | Best For |
|----------|-----------|---------|-------------------|------|------|----------|
| **NATS** | Low | <350µs p99 (Core), 10-30ms p99 (JetStream) | Heartbeat (ping/pong) | Ultra-low latency, lightweight (~20MB), cross-platform, wildcard subscriptions, built-in request-reply, clustering, JetStream persistence | JetStream needs more RAM, smaller ecosystem than Kafka | Cloud-native microservices, IoT, real-time service communication |
| **MQTT** | Low | 1-50ms (QoS dependent) | PINGREQ/PINGRESP | ISO standard, QoS 0/1/2, retained messages, hierarchical topics (+, #), extremely lightweight clients, works on unreliable networks | Clustering vendor-specific, no native request-reply, no standardized multi-site federation | IoT, industrial IoT, OT environments, resource-constrained devices |
| **Redis** | Low-Medium | <1ms | TTL keys + EXPIRE | Very fast, simple API, built-in pub/sub, widely used | Requires separate service, in-memory only (data loss risk) | Low-latency, real-time apps |
| **In-Memory Map** | Very Low | <0.1ms | setTimeout/setInterval | No dependencies, simplest solution, no setup | Not scalable across servers, manual cleanup needed | Single-server apps, prototypes |
| **WebSocket ping/pong** | Low | <5ms | Native WS frames | Built into protocol, no external deps | Manual handling, needs heartbeat logic | Direct client-server connections |
| **Server-Sent Events (SSE)** | Low | <10ms | HTTP keep-alive headers | Browser native, automatic reconnect | One-way only, HTTP overhead | Simple server-to-client updates |
| **PostgreSQL LISTEN/NOTIFY** | Medium | 10-50ms | Custom heartbeat table | Use existing DB, transactional | Higher latency, not designed for real-time | Apps already using PostgreSQL |
| **RabbitMQ** | High | 5-20ms | Heartbeat frames | Guaranteed delivery, robust | Complex setup, overkill for simple cases | Mission-critical messaging |
| **Kafka** | Very High | 10-100ms | Consumer heartbeats | Massive scale, event sourcing | Complex, high latency, resource heavy | Big data, event streaming |
| **Socket.io** | Low | <5ms | Built-in heartbeat | Handles everything, fallbacks | Opinionated, adds overhead | Quick implementation, broad browser support |

NATS wins due to its sub-millisecond latency, and cross-platform support—ideal for Apelios' real-time, high-performance layer communication.


## Decision

NATS is the best choice for real-time applications in this system.

## Consequences

- Flexibility and separation of concerns allow for easy modification
- Broker abstraction enables future multi-broker support
- Minimal overhead is accepted for modularity benefits

## References

- [NATS vs MQTT comparison](https://i-flow.io/en/ressources/nats-vs-mqtt-comparison-for-the-uns-application/)
- [Message queue comparison](https://backendbytes.com/articles/message-queue-comparison/)
- [NATS official docs](https://docs.nats.io/nats-concepts/overview/compare-nats)
- [NATS vs Redis vs Kafka](https://www.index.dev/skill-vs-skill/nats-vs-redis-vs-kafka)

