# Task 026: End-to-End Latency Test

**Related to:** ADR-003 (60Hz Tick Rate), ADR-009 (Orchestrator), NFR-1.1 (Scalability)

---

## Context

Apelios requires **hard real-time behavior** for lighting control (ADR-003), with a target latency of **<30ms** from input event to DMX output. The system processes frames at 60Hz (16.67ms per frame), but the **actual end-to-end latency**—from an input event (e.g., a button press) to the ArtNet packet transmission—has **not been measured empirically**. This gap makes it difficult to:
- Validate the 60Hz tick architecture (ADR-003).
- Determine the **scalability limits** of the system (NFR-1.1).
- Provide **data-driven documentation** for users (e.g., "Apelios supports up to X inputs/outputs with <30ms latency").

---

## Goal

Implement an **automated end-to-end latency test** that measures the time from:
1. **Input event** (simulated via `FakeAdapter`).
2. To **ArtNet output** (broker message on `output.*` topics).

The test will:
- Run with **scaling configurations** (1/1, 10/10, 50/50, 100/100, 200/200, 500/500).
- Use **mixed input types** (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) to reflect realistic usage.
- Measure **latency per frame** (600 frames over 10 seconds).
- Output **statistics** (min, max, median, mean, std dev) and **frame drops**.
- **Avoid hardware dependencies** (use `FakeAdapter` + `MemoryBroker`).

---

## Why?

| **Objective** | **Rationale** | **Reference** |
|---------------|--------------|---------------|
| **Validate real-time capability** | Prove Apelios meets the <30ms latency requirement (ADR-003). | ADR-003 |
| **Determine scalability limits** | Identify at what point latency exceeds acceptable thresholds. | NFR-1.1 |
| **Documentation** | Provide empirical data for the evaluation appendix. | Performance Evaluation Appendix |
| **Regression testing** | Detect performance regressions in future commits. | CI/CD Integration |

---

## Assumptions and Limitations

- **Hardware Independence:** All tests use `FakeAdapter` and `MemoryBroker` to ensure reproducibility without physical hardware or NATS server.
- **Clock Consistency:** All timestamps use `time.perf_counter()` for monotonic, high-resolution timing on the same system clock.
- **Test Environment:** Results may vary based on CPU load, system architecture, and Python implementation. For reproducible results, run on the same hardware configuration.
- **Frame Drop Detection:** A frame is considered dropped if no output message is received within a timeout period (default: 50ms, >3x the 60Hz frame time).
- **Warm-up Period:** Each configuration runs with a 1-second warm-up before measurements begin to allow Python JIT and system caches to stabilize.
- **Adapter-Axis Relationship:** Each `FakeAdapter` provides exactly 1 input axis, so N adapters = N inputs. This matches the configuration labels.

---

## Performance Findings

Initial test results (1 axis per adapter, 10s duration, 60Hz):

| **Inputs** | **Median Latency** | **Max Latency** | **Frame Drops** | **Assessment** |
|-----------|-------------------|----------------|----------------|----------------|
| 1 | 3ms | 12ms | 0% | [OK] Optimal |
| 10 | 3ms | 10ms | 0% | [OK] Optimal |
| 20 | 6ms | 8ms | 0% | [OK] Optimal |
| 30 | 6ms | 9ms | 0% | [OK] Optimal |
| 40 | 6ms | 14ms | 0% | [OK] Optimal |
| 50 | 6ms | 12ms | 0% | [OK] Optimal |
| 60 | 17ms | 32ms | 0% | [WARNING] Boundary |
| 70 | 57ms | 65ms | 12.8% | [FAIL] Overloaded |
| 80 | 57ms | 84ms | 23.7% | [FAIL] Overloaded |

**Key Observation:** The system scales well up to ~50 inputs (<7ms latency), then experiences a sharp degradation at ~60 inputs (17ms) and collapses at 70+ inputs (>57ms, with frame drops).

**Interpretation:** The **scalability limit** for this hardware configuration is approximately **60 inputs at 60Hz**. Beyond this point, the system cannot maintain the target <30ms latency (ADR-003).

**Possible Causes:**
- Broker message overhead (publishing/subcribing for each input event)
- Router mapping processing time
- Fixture layer DMX calculation overhead
- Python asyncio event loop scheduling

**Next Step:** Consider implementing **per-layer latency tests** to isolate which component (input, router, fixture, or output) is the bottleneck.

---

## Implementation (High-Level)

### Hardware Independence
To ensure the test runs **without physical hardware or NATS server**:
- **Input:** `FakeAdapter` (already implemented in Apelios). Simulates button presses with timestamps.
- **Broker:** `MemoryBroker` (from `broker/memory_runtime_manager.py`). No NATS binary required.
- **Output:** Broker subscriber for `output.*` topics. No ArtNet hardware required.
- **Timing:** `time.perf_counter()` (nanosecond precision). No external clock needed.

### Test Configurations
Each adapter provides **1 input axis**, so N adapters = N inputs.

| **Scale** | **Inputs** | **Outputs** | **Input Type Distribution** | **Purpose** |
|-----------|------------|-------------|--------------------------------|-------------|
| Baseline | 1 | 1 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Reference latency (no load) |
| Small Load | 10 | 10 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Typical test environment |
| Load 20 | 20 | 20 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Load 30 | 30 | 30 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Load 40 | 40 | 40 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Medium Load | 50 | 50 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Practical usability limit |
| Load 60 | 60 | 60 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Load 70 | 70 | 70 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Load 80 | 80 | 80 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Load 90 | 90 | 90 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Large Load | 100 | 100 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Upper bound for ADR-003 (<30ms) |
| Load 150 | 150 | 150 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scaling test |
| Stress Test | 200 | 200 | Mixed (1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) | Scalability limit |

### Test Workflow
1. **Setup:**
   - Start Apelios with `N` `FakeAdapter` instances (distributed as 1/3 `absolute_uni`, 1/3 `delta`, 1/3 `rate`) and `M` `ArtNetAdapter` instances.
   - Register a broker subscriber for `output.*` topics.
2. **Test Loop (10 seconds = 600 frames at 60Hz):**
   - `FakeAdapter` publishes an input event with a **randomly selected type** (`absolute_uni`, `delta`, or `rate`) and timestamp (`T_input`).
   - Subscriber waits for `output.*` message and records timestamp (`T_output`).
   - **Latency = `(T_output - T_input) * 1000`** (ms). Both timestamps use `time.perf_counter()` for monotonic clock consistency.
3. **Metrics:**
   - Min/Max/Median/Mean/Standard Deviation of latency.
   - **Frame drops** (input events without corresponding output within the 60Hz frame window).
   - **Input type distribution** (to verify 1/3 split).

### Output Format
**Primary:** CSV (for reproducibility, versioning, and external tools).
**Optional:** Matplotlib plots (for quick local visualization).

| **Format** | **Use Case** | **Pros** | **Cons** |
|------------|--------------|----------|----------|
| **CSV** | Documentation, CI/CD, archiving | Reproducible, versionable, tool-agnostic | No built-in visualization |
| **Matplotlib** | Local development | Immediate feedback, interactive plots | Not versionable, requires `matplotlib` |

**Decision:** Support **both**. Use `--plot` flag to enable Matplotlib output with SVG/PDF export for high-quality figures.

---

## File Location
**Script:** `/scripts/e2e_delay_test.py`

---

## Usage

### Command Line
```bash
# CSV output only (for CI/documentation)
python scripts/e2e_delay_test.py --output-dir results/

# CSV + Matplotlib plots (for local analysis)
python scripts/e2e_delay_test.py --output-dir results/ --plot

# Test specific scaling
python scripts/e2e_delay_test.py --inputs 100 --outputs 100 --duration 10
```

---

## Expected Output

### CSV Format
**File:** `results/e2e_delay_results_<timestamp>.csv`

Each row represents one input event and its corresponding latency measurement.

```csv
test_id,timestamp,config_inputs,config_outputs,input_device,input_axis,input_type,frame_number,latency_ms,is_drop
20260803_140000,1722680000.123456,1,1,fake_0,axis_0,absolute_uni,1,2.8,0
20260803_140000,1722680016.789012,1,1,fake_0,axis_1,delta,2,3.1,0
20260803_140000,1722680033.456789,1,1,fake_0,axis_2,rate,3,2.9,0
...
```

**Fields:**
- `test_id`: Unique identifier for the test run
- `timestamp`: System timestamp when the input event was generated
- `config_inputs`: Number of input adapters in this configuration
- `config_outputs`: Number of output universes/addresses
- `input_device`: Device identifier for the input source
- `input_axis`: Axis/control identifier
- `input_type`: Input type (`absolute_uni`, `delta`, or `rate`)
- `frame_number`: Sequential frame counter (1-600 for 10s at 60Hz)
- `latency_ms`: Measured latency in milliseconds
- `is_drop`: 1 if frame was dropped, 0 otherwise

### Matplotlib Output (if `--plot`)
Plots are exported as **SVG and PDF** for vector quality, suitable for both screen and print.

1. **Boxplot per Configuration:**
   - Shows median, quartiles, and outliers across all frames.
   - **Purpose:** Compare latency distributions across configurations.
2. **Line Plot: Latency vs. Scaling:**
   - X-axis: Number of inputs/outputs (logarithmic scale for better visualization).
   - Y-axis: Median latency (ms) with error bars showing standard deviation.
   - **Purpose:** Scalability analysis and trend identification.
3. **Histogram:**
   - Frequency of latency values across all tests.
   - **Purpose:** Jitter analysis and outlier detection.
4. **Violin Plot:**
   - Shows the full distribution density of latency per configuration.
   - **Purpose:** Detailed distribution analysis beyond boxplot.

---

## Example Results

| **Scaling** | **Median (ms)** | **Max (ms)** | **Frame Drops** | **Assessment** |
|-------------|-----------------|--------------|-----------------|----------------|
| 1/1 | 2.8 | 4.2 | 0 | [OK] Optimal |
| 10/10 | 3.1 | 5.6 | 0 | [OK] Optimal |
| 50/50 | 4.5 | 9.8 | 0 | [OK] Acceptable |
| 100/100 | 6.8 | 15.2 | 2 | [OK] Acceptable |
| 200/200 | 12.4 | 32.1 | 15 | [WARNING] Boundary |
| 500/500 | 45.2 | 120.4 | 120 | [FAIL] Overloaded |

**Interpretation:**
- **[OK] ADR-003 Validated:** At ≤100 inputs/outputs, median latency remains **<10ms** (target: <30ms).
- **[WARNING] Scalability Limit:** At 200+ I/O, latency exceeds **30ms** → Optimization needed (broker tuning, Cython, etc.).
- **[FAIL] System Breaking Point:** At 500 I/O, **120 frame drops** occur → System is overloaded.

---

## Next Steps

1. **Implementation:**
   - [ ] Use `FakeAdapter` for input simulation.
   - [ ] Use `MemoryBroker` to avoid NATS dependency.
   - [ ] Implement CSV output (mandatory).
   - [ ] Add `--plot` flag for Matplotlib integration (optional).
2. **Documentation:**
   - [ ] Document results in **Appendix A: Performance Evaluation** (tables + diagrams).
   - [ ] Add **summary** to Basic Concepts Chapter (§2.1.3) and ADR-003.
3. **CI Integration:**
   - [ ] Add test to **GitHub Actions** or **GitLab CI** (CSV output only).
   - [ ] **Regression check:** Fail if latency exceeds previous results by >10%.

---

## References
- [ADR-003: 60Hz Tick Rate](../adr/003-60hz-tick.md) - Target latency and timing requirements.
- [ADR-009: Orchestrator](../adr/009-orchestrator.md) - 60Hz tick loop implementation.
- [NFR-1.1: Scalability](../architecture/non-functional-requirements-list.md#scalability) - System scalability requirements.
- [FakeAdapter Implementation](../../src/apelios/input/adapters/fake_adapter.py) - Input simulation.
- [MemoryBroker Implementation](../../src/apelios/broker/memory_runtime_manager.py) - Broker without NATS.
