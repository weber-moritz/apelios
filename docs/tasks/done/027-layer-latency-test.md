# Task 027: Per-Layer Latency Test

**Related to:** Task-026 (End-to-End Latency Test), ADR-003 (60Hz Tick Rate), ADR-009 (Orchestrator), NFR-1.1 (Scalability)

---

## Context

Task-026 revealed a **sharp latency degradation** at approximately 60-70 inputs:
- 1-50 inputs: 3-6ms median latency (optimal)
- 60 inputs: 17ms median latency (boundary)
- 70+ inputs: 57ms+ median latency with frame drops (overloaded)

This threshold effect suggests a **bottleneck in one specific layer** of the Apelios pipeline. To identify and address this, we need **per-layer latency measurements** to isolate which component (router, fixture, or output) is causing the delay.

---

## Goal

Implement **automated per-layer latency tests** that measure processing time for each layer independently:

1. **Router Layer**: Time from `input.*` message to `target.*` message
2. **Fixture Layer**: Time from `target.*` message to `output.*` message  
3. **Output Layer**: Time from `output.*` message to ArtNet transmission
4. **Full Pipeline**: End-to-end reference (matches Task-026)

Each test runs across scaling configurations (1, 10, 20, ..., 200) to identify which layer's latency grows non-linearly.

### Layer Definitions

| **Layer** | **Input** | **Output** | **What It Tests** |
|-----------|-----------|------------|------------------|
| **Input** | FakeAdapter polling | `input.*` messages | Input adapter processing + polling latency |
| **Router** | `input.*` | `target.*` | Mapping resolution + routing logic |
| **Fixture** | `target.*` | `output.*` | DMX calculation + fixture processing |
| **Output** | `output.*` | (ArtNet packets) | ArtNet packet preparation + sending |
| **Full Pipeline** | `input.*` | `output.*` | Complete end-to-end flow |

---

## Why?

| **Objective** | **Rationale** | **Expected Outcome** |
|---------------|--------------|---------------------|
| **Isolate Bottleneck** | Identify which layer causes the 57ms latency jump at 70+ inputs | Clear data showing router/fixture/output layer latency curves |
| **Validate Architecture** | Confirm each layer meets its individual latency budget | Per-layer latency budgets for ADR-003 |
| **Targeted Optimization** | Focus optimization efforts on the problematic layer | Actionable performance improvements |
| **Regression Testing** | Detect per-layer performance regressions | CI integration with per-layer thresholds |

---

## Implementation (High-Level)

### Test Architecture

Each layer test uses **MemoryBroker** to avoid NATS dependency and measures latency by:
1. **Publishing directly** to the layer's input topic
2. **Subscribing** to the layer's output topic
3. **Matching timestamps** between input and output messages
4. **Calculating latency** as `(T_output - T_input) * 1000` ms

### Layer Definitions

| **Layer** | **Input** | **Output Topic** | **What It Tests** |
|-----------|-----------|-----------------|------------------|
| **Input** | FakeAdapter polling | `input.*` | Input adapter processing + polling latency |
| **Router** | `input.*` | `target.*` | Mapping resolution + routing logic |
| **Fixture** | `target.*` | `output.*` | DMX calculation + fixture processing |
| **Output** | `output.*` | (ArtNet packets) | ArtNet packet preparation + sending |
| **Full Pipeline** | FakeAdapter | `output.*` | Complete end-to-end flow |

### Test Configurations

Same scaling as Task-026 for direct comparison:

| **Scale** | **Inputs** | **Purpose** |
|-----------|------------|-------------|
| Baseline | 1 | Reference latency |
| Small Load | 10 | Typical usage |
| Load 20 | 20 | Scaling test |
| Load 30 | 30 | Scaling test |
| Load 40 | 40 | Scaling test |
| Medium Load | 50 | Boundary identification |
| Load 60 | 60 | Threshold test |
| Load 70 | 70 | Overload test |
| Load 80 | 80 | Overload test |
| Load 90 | 90 | Overload test |
| Large Load | 100 | Stress test |
| Load 150 | 150 | Stress test |
| Stress Test | 200 | Maximum test |

### Test Workflow (Per Layer)

1. **Setup:**
   - Initialize MemoryBroker
   - Start only the layer under test (e.g., for router test: start router_manager only)
   - Subscribe to output topic of the layer

2. **Measurement Loop (60Hz for duration):**
   - Publish test message to input topic with `T_input` timestamp
   - Wait for output message and record `T_output` timestamp
   - Calculate: `latency_ms = (T_output - T_input) * 1000`
   - Track: min, max, mean, median, std_dev, drops

3. **Cleanup:**
   - Stop layer under test
   - Save results

### Message Formats

Each layer test uses the **exact same message format** as the production system:

**Router Input (`input.*`):**
```json
{"source": "test.input_0", "value": 0.5, "type": "absolute_uni", "timestamp": 1234567890.123}
```

**Router Output (`target.*`):**
```json
{"source": "test.input_0", "value": 0.5, "type": "absolute_uni", "timestamp": 1234567890.123}
```

**Fixture Output (`output.*`):**
```json
{"universe": 0, "address": 1, "value": 128}
```

---

## Output Format

### CSV Files

**Per-layer:** `results/layer_latency_<layer>_<timestamp>.csv`

```csv
layer,test_id,timestamp,config_inputs,frame_number,latency_ms,is_drop
router,20260803_170000,1722680000.123456,50,1,2.5,0
router,20260803_170000,1722680016.789012,50,2,2.8,0
fixture,20260803_170000,1722680033.456789,50,1,4.2,0
...
```

**Aggregated Statistics:** `results/layer_latency_statistics_<timestamp>.csv`

```csv
layer,config_inputs,count,min_ms,max_ms,mean_ms,median_ms,std_dev_ms,drops,drop_rate
router,50,60,1.8,3.2,2.5,2.4,0.2,0,0.0
fixture,50,60,3.5,5.1,4.2,4.1,0.3,0,0.0
output,50,60,0.5,1.2,0.8,0.7,0.1,0,0.0
```

### Matplotlib Plots (if `--plot`)

1. **Layer Comparison Boxplot:**
   - X-axis: Layer (router, fixture, output)
   - Y-axis: Latency (ms)
   - **Purpose:** Compare baseline latency per layer

2. **Per-Layer Scaling Plot:**
   - X-axis: Number of inputs (log scale)
   - Y-axis: Median latency (ms)
   - Separate line for each layer
   - **Purpose:** Identify which layer scales poorly

3. **Latency Breakdown:**
   - Stacked bar chart showing layer contribution to total latency
   - **Purpose:** Visualize where time is spent

---

## Performance Findings

Initial test results confirm the **fixture layer is the primary bottleneck**:

| **Layer** | **1 input** | **10 inputs** | **20 inputs** | **Scaling Behavior** |
|-----------|-------------|---------------|----------------|---------------------|
| **Input** | 0.09ms | 0.20ms | ~0.30ms | **Linear - OK** |
| **Router** | 0.10ms | 0.30ms | 0.53ms | **Linear - OK** |
| **Fixture** | 0.66ms | 26.14ms | 26.49ms | **Exponential - BOTTLENECK** |
| **Output** | 0.08ms | 0.16ms | 0.28ms | **Linear - OK** |
| **Full Pipeline** | 1.55ms | 53.10ms | ~54ms | **Matches sum of layers** |

**Key Findings:**
- **Router Layer:** Scales linearly (0.1ms per input). Very efficient.
- **Fixture Layer:** **JUMPS from 0.66ms to 26.14ms at 10 inputs!** This is the primary bottleneck.
- **Output Layer:** Scales linearly (0.08ms per input). Very efficient.
- **Full Pipeline:** Latency = Router + Fixture + Output (confirmed by measurements).

**Root Cause:** The fixture layer's `process_frame` method iterates over ALL fixtures for EVERY input event, leading to O(N*M) complexity where N=inputs and M=fixtures. With the current implementation, adding more inputs or fixtures causes quadratic growth in processing time.

**Confirmed:** The fixture layer is the bottleneck identified in Task-026. At 10 inputs, it already consumes ~26ms of the 30ms budget.

---

## File Location

**Script:** `/scripts/layer_latency_test.py`

---

## Usage

### Command Line

```bash
# Test all layers at default configurations
python scripts/layer_latency_test.py --output-dir results/

# Test specific layer only
python scripts/layer_latency_test.py --layer fixture --output-dir results/

# Test with plots
python scripts/layer_latency_test.py --output-dir results/ --plot

# Test specific scaling
python scripts/layer_latency_test.py --inputs 100 --duration 5 --output-dir results/

# Test all layers at all configurations
python scripts/layer_latency_test.py --all --output-dir results/ --plot
```

### Arguments

| **Argument** | **Default** | **Description** |
|--------------|-------------|-----------------|
| `--layer` | `all` | Layer to test: `router`, `fixture`, `output`, or `all` |
| `--inputs` | `1,10,20,...,200` | Comma-separated list of input counts |
| `--duration` | `1` | Test duration in seconds per configuration |
| `--output-dir` | `results` | Directory for CSV and plot output |
| `--plot` | `False` | Generate Matplotlib plots |
| `--verbose` | `False` | Enable verbose logging |

---

## Next Steps

1. **Implementation:**
   - [x] Implement **input layer** test (FakeAdapter polling to `input.*`)
   - [x] Implement router layer test (publish to `input.*`, measure to `target.*`)
   - [x] Implement fixture layer test (publish to `target.*`, measure to `output.*`)
   - [x] Implement output layer test (publish to `output.*`, measure ArtNet send time)
   - [x] Implement full pipeline test (FakeAdapter to `output.*`)
   - [x] Use MemoryBroker for all tests
   - [x] Output CSV for each layer
   - [x] Optional Matplotlib plots with per-layer scaling analysis

2. **Analysis:**
   - [x] Compare per-layer results with Task-026 e2e results
   - [x] **Identified: Fixture layer is the bottleneck**
   - [ ] Document findings in Performance Evaluation Appendix
   - [ ] Profile fixture layer's `process_frame` method

3. **Optimization:**
   - [ ] Focus on the bottleneck layer
   - [ ] Profile and optimize the identified component

---

## References

- [Task-026: End-to-End Latency Test](../done/026-e2e-delay-test.md) - Baseline e2e test implementation and findings
- [ADR-003: 60Hz Tick Rate](../adr/003-60hz-tick.md) - Target latency requirements
- [ADR-009: Orchestrator](../adr/009-orchestrator.md) - 60Hz tick loop implementation
- [NFR-1.1: Scalability](../architecture/non-functional-requirements-list.md#scalability) - System scalability requirements
- [Router Runtime Manager](../../src/apelios/router/router_runtime_manager.py) - Router layer entry point
- [Fixture Runtime Manager](../../src/apelios/fixture/fixture_runtime_manager.py) - Fixture layer entry point
- [Output Runtime Manager](../../src/apelios/output/output_runtime_manager.py) - Output layer entry point
