---
date: 2026-08-07
state: Draft # [Draft | In Progress | Done]
---

# Task 029: Optimize System Latency at 100 I/O

## 0. TDD Contract

- [ ] Write benchmark-correctness and regression tests before production changes.
- [ ] Confirm every new behavioral test fails for the expected reason (Red phase).
- [ ] Implement the smallest change that satisfies the current test (Green phase).
- [ ] Refactor only after the focused and full test suites pass.
- [ ] Record before/after results from the same machine and benchmark configuration.
- [ ] Test files: `tools/performance/tests/test_e2e_latency.py`, `tools/performance/tests/test_layer_latency.py`, `tools/performance/tests/test_module_latency.py`, and focused unit tests under `tests/` for any production component changed.

## 1. Context and Scope

### Objective

Reduce 100-I/O frame-completion and end-to-end latency so Apelios can sustain its intended 60 Hz update rate without unexplained drops, growing backlog, or silently collapsed benchmark samples.

### Verified Baseline

Results from `tools/performance/results/20260807_153010`:

| Measurement at 100 I/O | Median | Frame-completion median | Frames over 16.67 ms |
|---|---:|---:|---:|
| Input layer | 0.15 ms/message | 0.27 ms | 0/600 |
| Router layer | 10.38 ms/message | 11.15 ms | 1/600 |
| Fixture layer | 14.88 ms/message | 29.62 ms | 599/600 |
| Output layer | 5.83 ms/message | 10.48 ms | 1/600 |
| Corrected E2E to `output.*` | 44.11 ms/frame (p95 65.01 ms) | 44.11 ms | — |

The existing combined plot adds per-message medians (~31.24 ms). That number is not directly comparable to E2E frame completion. A comparable isolated-layer estimate to `output.*` is approximately:

```text
input frame completion + router frame completion + fixture frame completion
= 0.27 + 11.15 + 29.62
= 41.04 ms
```

This is close to the measured 44.11 ms E2E median. The primary measured problem is completion of the 100-output fixture batch, not a one-message-per-frame limitation in `FixtureCore`.

### Files in Scope

- `src/apelios/router/`
- `src/apelios/fixture/`
- `src/apelios/output/`
- `src/apelios/broker/` only where profiling proves broker abstraction overhead
- `tools/performance/tests/`
- `tools/performance/scripts/plot_results.py`
- Corresponding unit and integration tests under `tests/`

### Do Not Touch Without Evidence

- Input adapter behavior unrelated to latency
- Fixture value semantics, limits, many-to-one summation, or patch schema
- NATS protocol contracts or output subjects solely to improve a benchmark
- Production tick rate or performance thresholds merely to make tests pass
- Unrelated architectural cleanup

## 2. Strict Constraints

- Preserve externally observable routing, fixture-state, DMX-address, and output-value behavior.
- Do not hide latency with fixed sleeps, relaxed assertions, sample filtering, or larger timeouts.
- Use bounded events/conditions or explicit correlation for asynchronous synchronization.
- Report message latency and frame-completion latency as separate metrics.
- A combined plot must compare like-for-like endpoints and statistics.
- Use `time.perf_counter()` consistently within one process.
- Every expected output must be correlated by a stable identifier or expected subject set.
- Treat missing outputs, unexpected subjects, and timeouts separately from latency samples.
- Measure before choosing an optimization. Do not assume `FixtureCore` computation is the bottleneck when publication may dominate.
- Preserve latest-value/coalescing semantics where they are intentional, but expose coalescing as its own counter under sustained load.
- No new runtime dependency without explicit approval.

## 3. Test Specification

### Phase A: Make the Measurements Comparable

- [ ] `test_router_layer_waits_for_all_correlated_outputs`: all expected target subjects are received before results are saved; the final callback cannot become a false drop.
- [ ] `test_layer_results_separate_message_and_frame_completion_latency`: a 100-message frame produces 100 message samples and one frame-completion sample.
- [ ] `test_combined_plot_uses_frame_completion_statistics`: combined-to-`output.*` uses input + router + fixture frame-completion medians, not per-message medians.
- [ ] `test_combined_plot_labels_output_adapter_endpoint`: full combined latency including the output adapter is distinct from the `output.*` endpoint.
- [ ] `test_negative_latency_file_is_rejected`: corrupted measurements never become a scaling point.
- [ ] `test_drop_rows_are_not_latency_samples`: drops remain visible in statistics but are excluded from latency distributions.

### Phase B: Model Real 60 Hz Operation

- [ ] `test_sustained_e2e_60hz_has_no_unbounded_backlog`: inject frames on absolute 60 Hz deadlines while layer schedulers run independently.
- [ ] `test_sustained_e2e_reports_missed_deadlines`: frames taking longer than 16.67 ms increment an explicit deadline-miss counter.
- [ ] `test_sustained_e2e_reports_coalesced_updates`: overwritten latest-value updates are counted and are not reported as broker drops.
- [ ] `test_sustained_e2e_correlates_output_frames`: outputs cannot be paired with later inputs by raw array index.
- [ ] `test_sustained_e2e_stops_with_bounded_drain`: teardown waits boundedly for in-flight work and reports anything remaining.

### Phase C: Protect Production Semantics

- [ ] Router produces the same target payloads before and after optimization.
- [ ] Fixture core produces identical DMX dictionaries for representative 1/10/25/50/100-fixture patches.
- [ ] Multiple sources targeting one fixture parameter retain the documented summation behavior.
- [ ] Output layer sends identical universe/address/value state to adapters.
- [ ] Message ordering or latest-value behavior is documented and tested wherever batching or concurrency is introduced.

## 4. Investigation and Implementation Steps

### 4.1 Establish a Reproducible Baseline

- [ ] Pin benchmark configuration to 1, 10, 25, 50, and 100 I/O for 600 frames.
- [ ] Record system metadata, Python version, NATS version, and whether NATS was pre-existing or test-started.
- [ ] Run each benchmark at least three times and report median-of-runs plus variance.
- [ ] Save a baseline result directory before production changes.
- [ ] Add frame-completion CSV/statistics to every per-layer benchmark.

### 4.2 Attribute the Fixture Frame Tail

Instrument, without changing behavior, the 100-fixture frame into:

- [ ] NATS delivery from `target.*` to the fixture inbox.
- [ ] `FixtureCore.process_frame()` computation.
- [ ] DMX dictionary construction.
- [ ] `FixtureOutputPublisher.publish_dmx()` total batch publication.
- [ ] First-output and final-output callback arrival.

Use module profiling to determine whether time scales primarily with core processing, JSON serialization, sequential broker publication, callback dispatch, or event-loop contention.

### 4.3 Optimize the Proven Hot Path

Apply these only when profiling supports them, in this order:

- [ ] Remove repeated work or allocations inside fixture processing while preserving output equality.
- [ ] Precompute immutable patch-derived lookup data such as target-to-DMX mappings when patch changes, rather than resolving it every frame.
- [ ] Avoid unnecessary dictionary copies or repeated conversions in the output publication path.
- [ ] Evaluate safe batch serialization/publication within the existing subject contract.
- [ ] Evaluate bounded concurrent publication only if ordering and broker backpressure tests prove it safe.
- [ ] Consider an aggregate universe/frame message only as a separately reviewed protocol change with compatibility tests; do not introduce it solely for benchmark improvement.

### 4.4 Check Router and Output Batch Tails

- [ ] Replace the router benchmark's fixed pre-tick sleep and index pairing with bounded, subject-correlated synchronization.
- [ ] Profile `RouterOutputPublisher` batch publication at 100 mappings.
- [ ] Profile output-layer ingestion and adapter handoff using frame completion, not synthetic per-message timestamp pairing alone.
- [ ] Optimize these layers only after the fixture path meets its target or profiling shows shared publication overhead.

### 4.5 Validate Scheduling and Backpressure

- [ ] Compare the current serially synchronized E2E benchmark with independently scheduled 60 Hz managers.
- [ ] Use absolute deadlines (`next_deadline += interval`) to avoid sleep drift.
- [ ] Define what happens on overrun: backlog, frame skip, or latest-value coalescing.
- [ ] Expose counters for received, processed, published, coalesced, missed-deadline, and timed-out events in benchmark results.
- [ ] Confirm memory use and pending work remain bounded during a 60-second 100-I/O stress run.

### 4.6 Update Reporting

- [ ] Plot per-message latency and per-frame completion separately.
- [ ] Plot measured E2E alongside comparable combined-to-`output.*` frame completion.
- [ ] Plot full combined latency including the output-adapter endpoint as a separate series.
- [ ] Add p50, p95, p99, maximum, deadline misses, drops, and coalesced updates to statistics.
- [ ] Clearly label simulated/summed values versus directly measured values.

## 5. Acceptance Criteria

### Correctness

- [ ] Multi-fixture configurations produce exactly the expected distinct DMX keys.
- [ ] No negative latency samples are generated.
- [ ] No raw index pairing is used where input and output cardinality or alignment can differ.
- [ ] No unexplained drops occur in three consecutive 600-frame runs at any supported configuration.
- [ ] Intentional coalescing is counted separately and matches documented latest-value semantics.
- [ ] All production behavior regression tests pass.

### Performance on the Reference Machine

- [ ] 100-fixture frame-completion median is below 16.67 ms.
- [ ] 100-fixture frame-completion p95 is below 30 ms.
- [ ] Corrected 100-I/O E2E-to-`output.*` median is below 30 ms.
- [ ] Corrected 100-I/O E2E-to-`output.*` p95 is below 50 ms.
- [ ] A 60-second 100-I/O sustained test has bounded pending work and no increasing latency trend.
- [ ] Optimization improves median and p95 across three runs; a single favorable run is insufficient.

### Verification Commands

```bash
venv/bin/python -m pytest tests -q
venv/bin/python -m pytest tools/performance/tests/test_module_latency.py -v
venv/bin/python -m pytest tools/performance/tests/test_layer_latency.py -v
venv/bin/python -m pytest tools/performance/tests/test_e2e_latency.py -v
venv/bin/python tools/performance/scripts/run_all_performance_tests.py --all --plot
```

### Deliverables

- [ ] Before/after result directories with identical configurations.
- [ ] Profiling evidence identifying the optimized hot path.
- [ ] Production changes with focused unit tests.
- [ ] Corrected message-latency, frame-completion, combined-layer, and E2E plots.
- [ ] Short implementation summary documenting trade-offs and any protocol or scheduling decisions.

## 6. Completion Notes

Record final values here when the task is complete:

| Metric at 100 I/O | Before | After | Change |
|---|---:|---:|---:|
| Fixture frame completion p50 | 29.62 ms | — | — |
| Fixture frame completion p95 | 37.51 ms | — | — |
| E2E to `output.*` p50 | 44.11 ms | — | — |
| E2E to `output.*` p95 | 65.01 ms | — | — |
| Deadline misses / 600 frames | — | — | — |
| Drops | 0 E2E; one router teardown artifact | — | — |
| Coalesced updates | Not yet measured | — | — |
