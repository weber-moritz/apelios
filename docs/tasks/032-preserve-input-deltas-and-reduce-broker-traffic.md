---
date: 2026-08-13
state: Todo
priority: High
---

# Task 032: Preserve Input Deltas and Reduce Broker Traffic

## Summary

Mouse input reaches the moving-head fixture, but the current pipeline becomes
slow under load and can distort the relationship between simultaneous X and Y
movement. A circular mouse gesture produces comparable `input.mouse.x` and
`input.mouse.y` events at roughly 60 Hz, yet the resulting DMX stream contains
many more pan updates than tilt updates.

The input adapter is not the source of the asymmetry:

- X and Y both use a scale of `0.002`.
- Both axes publish values of type `delta`.
- Captured input events arrive as paired X/Y samples with comparable values and
  timestamps.
- Disabling the Steam Deck reduces latency substantially, which shows that
  message volume is a major contributor.

The remaining work has two related goals:

1. Preserve the mathematical meaning of queued input events, especially
   `delta` values.
2. Reduce redundant broker traffic so the 60 Hz pipeline does not build a
   multi-second backlog.

## Current Pipeline

```text
MouseAdapter
    -> input.mouse.x / input.mouse.y
    -> RouterRuntimeManager pending outputs
    -> target.lixada-mini-move.pan / tilt
    -> FixtureInputSubscriber inbox
    -> FixtureCore normalized state
    -> 59 DMX channel publications per frame
    -> OutputCore persistent DMX state
    -> ArtNetAdapter sends universe 2 at 40 Hz
```

The Art-Net adapter already owns continuous network refresh. Broker messages
only need to update `OutputCore` when DMX state changes; they do not need to
republish every unchanged channel on every frame.

## Observed Problems

### 1. Delta values can be overwritten

The router currently stores pending output by target using dictionary update:

```python
self._outputs_to_publish.update(outputs)
```

The fixture subscriber stores pending input by source:

```python
self.inbox[source] = payload
```

If more than one event for the same source/target arrives before the next tick,
only the newest payload survives. This is acceptable for a latest-state value,
but incorrect for `delta`: each delta represents motion that must contribute to
the final result.

Under backlog, repeatedly overwriting mouse deltas effectively undersamples the
gesture. Sampling a circular signal at an unfortunate interval can distort one
axis more than the other.

### 2. Every patched DMX channel is published every frame

The complete patch currently contains:

- 7 channels in universe 0;
- 43 channels in universe 1;
- 9 channels in universe 2;
- 59 channels total.

`FixtureCore` produces a complete DMX dictionary each frame and
`FixtureOutputPublisher` republishes all 59 values, even when only pan changed.
At 60 Hz this is up to 3,540 output messages per second before input and target
messages are counted.

### 3. Every NATS publish performs a flush

`NatsClient.publish()` currently calls both `publish()` and `flush()` for each
message. This turns each individual input, target, and DMX value into a separate
broker round trip and prevents efficient batching.

### 4. Zero mouse deltas are published

The mouse backend returns X and Y with `0.0` even when no movement occurred.
Those zero-valued `delta` messages do not change fixture state but still travel
through the full pipeline.

### 5. Development mappings remain active

Default routing still includes `test.*` targets and Steam Deck debug overrides.
They generate unrelated universe 0/1 state and make production behavior harder
to inspect. Art-Net is already restricted to universe 2, but internal broker
traffic is not.

## Required Semantics

Before optimizing, define how multiple pending values are coalesced for the same
`(source, target)` pair:

| Input type | Pending-event behavior | Reason |
|---|---|---|
| `delta` | Sum all pending values | Every relative movement must be preserved |
| `absolute_uni` | Keep newest value | Newest physical position is authoritative |
| `absolute_bi` | Keep newest value | Newest physical position is authoritative |
| `rate` | Keep newest value for the frame | It represents the current velocity |

Events from different sources targeting the same fixture parameter must remain
separate until `FixtureCore` performs its existing many-to-one summation.

Mixed input types for the same `(source, target)` within one frame are not an
expected normal case. If encountered, retain events in arrival order or use a
clearly documented deterministic rule; do not silently reinterpret a delta as
an absolute value.

## Scope and Constraints

This is a targeted pipeline-correctness and traffic-reduction task.

In scope:

- router pending-event collection;
- fixture pending-event collection;
- mouse zero-delta suppression;
- changed-only fixture output publication;
- NATS publication batching/flush boundaries;
- removal or isolation of obsolete active test mappings;
- focused unit and integration tests;
- manual mouse verification.

Out of scope:

- redesigning the broker abstraction;
- changing the 60 Hz processing model;
- changing fixture patch formats;
- changing Art-Net timing;
- optimizing the Steam Deck backend itself unless measurement after the core
  fixes still shows it blocking;
- changing mouse sensitivity based only on this bug report.

The mouse remains the only default input adapter while this task is developed
and verified. Re-enable the Steam Deck only after the mouse-only path is correct
and responsive.

## Implementation Plan

### Phase 1: Add a failing paired-delta regression test

Create a deterministic test that sends multiple interleaved mouse deltas before
one processing tick:

```text
x: +0.010, +0.020, -0.005  -> expected total +0.025
y: -0.010, -0.020, +0.005  -> expected total -0.025
```

Verify at each relevant boundary:

- router output preserves both cumulative deltas;
- fixture inbox preserves both cumulative deltas;
- final pan and tilt state move by equal and opposite amounts;
- corresponding DMX values move symmetrically around their common start value.

This test must fail against the current overwrite behavior and pass only after
the coalescing fix.

### Phase 2: Correct router pending-event handling

Replace the plain target-to-payload overwrite with a small, explicit pending
event/coalescing structure.

Requirements:

- Key pending state by at least `(target, source)`, not target alone.
- Sum consecutive pending `delta` values.
- Keep the newest absolute/rate value according to the semantics table.
- Preserve timestamps sensibly: the coalesced payload should carry the newest
  contributing timestamp, while tests validate accumulated value rather than
  pretending it was one original event.
- Atomically swap the pending collection at the beginning of `tick()` so events
  arriving while broker publication awaits are collected for the next frame and
  are not erased afterward.

The atomic-swap requirement addresses the current race pattern:

```python
await publisher.publish(self._outputs_to_publish)
self._outputs_to_publish = {}
```

Events arriving during the `await` must not be lost by the later assignment.

### Phase 3: Correct fixture pending-event handling

Apply the same semantic rules before `FixtureCore.process_frame()`:

- Keep sources independent for many-to-one summation.
- Sum pending deltas for the same `(source, target)`.
- Keep newest absolute/rate state.
- Atomically detach the frame inbox before processing so broker callbacks can
  safely populate the next frame.

Prefer one shared, well-tested coalescing helper if it keeps the behavior
obvious. Do not build a general event framework for this task.

### Phase 4: Suppress zero mouse deltas

The mouse adapter should publish movement axes only when the accumulated raw
delta is non-zero.

Important distinction:

- `x`, `y`, `wheel`, and `wheel_h` are `delta`; zero events can be omitted.
- Button release events carry value `0` and must not be dropped.

Adjust the backend/poll snapshot so an idle mouse produces no movement messages
while press and release events remain observable.

### Phase 5: Publish only changed DMX values

Keep `FixtureCore.dmx_output` as a complete frame snapshot to avoid changing its
public behavior and existing calculations. Add changed-value filtering at the
fixture output publication boundary.

`FixtureOutputPublisher` should:

- publish every channel on the first complete frame so `OutputCore` initializes;
- cache the last successfully published value per `(universe, address)`;
- on later frames, publish only channels whose integer DMX value changed;
- update the cache only after successful publication;
- expose/reset cache state appropriately when a new runtime lifecycle begins;
- continue to send explicit zero when a channel changes from non-zero to zero.

Art-Net remains unaffected: `OutputCore` retains the latest channel values and
`ArtNetAdapter` continues sending the complete whitelisted universe at 40 Hz.

Expected steady-state output counts:

- idle frame: 0 DMX broker messages;
- horizontal mouse movement: normally 1 changed DMX message;
- vertical mouse movement: normally 1 changed DMX message;
- diagonal/circular movement: normally 2 changed DMX messages;
- first frame: one complete initialization snapshot.

### Phase 6: Replace per-message flushes with frame/batch boundaries

Do not simply remove flushing without defining delivery behavior.

Preferred approach:

1. `NatsClient.publish()` queues a publication without immediately flushing.
2. Expose a broker `flush()` operation; the memory implementation is a no-op.
3. Flush once after a logical batch:
   - after the input manager publishes all adapter values for a frame;
   - after the router publishes all pending target values for a frame;
   - after the fixture publishes all changed DMX values for a frame.
4. Ensure integration tests observe messages before proceeding with assertions.
5. Ensure orderly shutdown performs any required final flush before closing, but
   does not reintroduce the cancellation/drain problems fixed in Task 031.

If nats-py's internal flusher provides sufficiently deterministic low-latency
delivery without an explicit frame flush, document and test that decision. The
acceptance criterion is behavior, not a mandatory new abstraction method.

### Phase 7: Isolate obsolete test routing

Review active routing files and remove production-path mappings whose only
purpose is feeding `test.*` fixtures.

At minimum:

- keep mouse X/Y mapped only to `lixada-mini-move.pan` and `.tilt`;
- remove duplicate Steam Deck keys that override intended mappings with
  `test.*` targets;
- decide whether mouse wheel should be unmapped or intentionally mapped to a
  useful moving-head parameter;
- keep test mappings inside test fixtures/configuration rather than active
  runtime configuration.

Do not delete the test fixture patch merely to reduce traffic. Changed-only
publication should solve redundant traffic regardless of how many fixtures are
patched.

### Phase 8: Re-enable and measure the Steam Deck

After the mouse path passes all tests:

1. Temporarily re-enable `steamdeck` alongside `mouse`.
2. Repeat the same responsiveness check.
3. Measure input tick duration and message counts.
4. If the delay returns, distinguish synchronous backend polling from redundant
   publication before changing the Steam Deck adapter.

Input publication may later apply type-aware change suppression:

- `delta`: publish non-zero values;
- absolute types: publish on change;
- `rate`: publish the current non-zero rate every frame, with correct zero/stop
  semantics.

This type-aware optimization is optional for this task unless the preceding
changes are insufficient.

## Test Plan

### Unit tests

- Multiple router deltas for one source/target are summed.
- Router absolute/rate events retain the newest value.
- Different sources targeting one parameter remain independent.
- Events arriving during router publication survive for the next tick.
- Fixture input applies the same delta/latest-value semantics.
- Paired X/Y deltas produce symmetric normalized and DMX changes.
- Idle mouse movement produces no input publications.
- Mouse button release value `0` is still published.
- First fixture frame publishes the complete DMX state.
- Unchanged subsequent frame publishes nothing.
- One changed channel publishes exactly one message.
- Non-zero-to-zero transition is published.
- Failed publication is not incorrectly recorded as successfully cached.
- NATS batches flush at most once per defined frame/batch.

### Integration tests

- Real NATS burst of interleaved X/Y deltas preserves both cumulative totals.
- Input-to-output test confirms pan and tilt update without multi-second backlog.
- OutputCore receives initial state and retains unchanged channels when later
  messages contain only changes.
- Art-Net adapter continues sending only universe 2 at 40 Hz from persistent
  OutputCore state.
- Clean startup and shutdown behavior from Task 031 remains intact.

Avoid a tight absolute timing assertion in normal CI. Use a generous timeout to
detect seconds-long backlog while preventing load-related flakes. Record actual
latency as diagnostic output where useful.

### Full verification

- Run focused router, fixture, output, broker, and input tests.
- Run the complete application test suite.
- Run the complete repository collection if focused/application tests pass.
- Confirm no NATS child or port 4222 listener remains afterward.

## Manual Verification

Use the mouse-only bootstrap initially.

1. Start Apelios.
2. Start `watch_inputs.py` and make a small circular gesture.
3. Confirm paired X/Y input values appear immediately.
4. Start `watch_targets.py` and confirm paired pan/tilt target changes.
5. Start `watch_outputs.py` with its default universe-2 filter.
6. Make horizontal, vertical, diagonal, and circular gestures.
7. Confirm:
   - channel 1 responds to horizontal movement;
   - channel 2 responds to vertical movement;
   - diagonal/circular movement updates both without obvious imbalance;
   - idle periods produce no repeated changed-value output;
   - observed response is immediate rather than seconds behind.
8. Connect the moving head and confirm Art-Net motion matches the watcher.
9. Stop with one `Ctrl+C` and verify clean lifecycle behavior.
10. Repeat after temporarily re-enabling the Steam Deck.

## Instrumentation and Success Metrics

Add temporary or test-only counters rather than permanent noisy logging:

- input messages per frame;
- target messages per frame;
- DMX broker messages per frame;
- tick duration per layer;
- end-to-end timestamp from input payload to observed output message.

Expected qualitative improvement:

- no seconds-long queue;
- circular X/Y input remains recognizably balanced at output;
- idle output publication approaches zero after initialization;
- mouse-only runtime remains comfortably within the 16.67 ms frame budget.

Do not claim a hard real-time guarantee from this manual check.

## Risks and Mitigations

### Risk: Changed-only output leaves a channel stale

Mitigation: publish a full initial snapshot, explicitly publish transitions to
zero, and test OutputCore persistence.

### Risk: Removing per-message flush loses messages at shutdown

Mitigation: define batch flush boundaries and test immediate shutdown after a
publication burst.

### Risk: Coalescing changes many-to-one behavior

Mitigation: key by `(source, target)` and retain separate contributions until
FixtureCore combines them.

### Risk: Rate inputs stop behaving continuously

Mitigation: do not sum rate events as deltas. Keep the newest rate for the frame
and retain existing repeated-rate semantics.

### Risk: Scope expands before the project snapshot

Mitigation: implement phases 1-6 first. Phase 7 is configuration cleanup and
Phase 8 is validation. Stop once correctness, responsiveness, tests, and clean
shutdown pass; defer unrelated performance work.

## Acceptance Criteria

- [ ] Paired X/Y delta bursts are preserved through router and fixture layers.
- [ ] Circular mouse movement produces reasonably balanced pan/tilt updates.
- [ ] No pending event is erased because it arrived during an awaited publish.
- [ ] Idle mouse axes do not emit zero-delta traffic.
- [ ] Complete DMX state is published once at initialization.
- [ ] Unchanged DMX channels are not republished every frame.
- [ ] Art-Net still continuously sends the complete universe-2 state at 40 Hz.
- [ ] NATS no longer performs one flush round trip per individual value.
- [ ] Mouse-only control has no visible multi-second backlog.
- [ ] Obsolete active `test.*` routing is removed or isolated.
- [ ] Task 031 startup and shutdown behavior remains clean.
- [ ] Focused, application, and full repository tests pass.
- [ ] Manual horizontal, vertical, diagonal, and circular mouse tests pass.
- [ ] Steam Deck impact is measured before it is restored as a default adapter.

## Release Boundary

Commit this work separately from the earlier repository cleanup. Create the
neutral project snapshot tag only after this task and Task 031 are committed,
pushed, and verified from a clean checkout or synchronized working tree.
