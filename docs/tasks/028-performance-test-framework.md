# Task 028: Performance Test Framework

**Related to:** Task-026 (End-to-End Latency Test), Task-027 (Per-Layer Latency Test), ADR-003 (60Hz Tick Rate), NFR-1.1 (Scalability)

**Status:** Draft

---

## Context

Tasks 026 and 027 revealed:
- E2E system scales well to ~50 inputs (<7ms), degrades sharply at 60+ inputs (17ms+)
- Fixture layer is the primary bottleneck (0.66ms → 26ms at 10 inputs)
- Current tests use MemoryBroker which doesn't capture NATS Broker communication overhead
- Per-layer tests need 60Hz tick for realistic processing (receive all messages, process in tick, publish outputs)

**Requirements:**
- Use **NATS Broker** (not MemoryBroker) for E2E and per-layer tests
- Per-layer tests must use **60Hz tick** to simulate real processing
- Module tests use **direct method calls** (no broker, no tick) for deep-dive analysis
- **Linear scale** for all scaling plots (not logarithmic)
- Configurations: **1, 10, 25, 50, 100** inputs for plots
- Each test type gets its own plots directory
- Location: `tools/performance/`

---

## Goal

Create a structured performance testing framework with:
1. **E2E Test**: Full system with NATS Broker + 60Hz tick
2. **Per-Layer Tests**: Individual layers with NATS Broker + 60Hz tick
3. **Module Tests**: Direct core method calls for deep-dive profiling
4. **Standardized Visualization**: Consistent plots (boxplot, scaling) with linear scale
5. **Organized Results**: Clear directory structure with plots per test

---

## Framework Structure

```
tools/performance/
├── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Shared pytest fixtures (NATS Broker)
│   ├── test_e2e_latency.py       # Full system test
│   ├── test_layer_latency.py     # Per-layer tests
│   └── test_module_latency.py    # Module-level direct calls
├── scripts/
│   ├── __init__.py
│   ├── run_all_performance_tests.py  # CLI runner
│   └── plot_results.py           # Standardized plot generation
├── README.md
└── results/                      # Gitignored
    └── .gitignore
```

---

## Test Types

### Test Type Comparison

| **Aspect** | **E2E Test** | **Per-Layer Test** | **Module Test** |
|------------|--------------|-------------------|-----------------|
| **Broker** | NATS Broker | NATS Broker | None |
| **60Hz Tick** | Yes | Yes | No |
| **Communication Overhead** | Included | Included | Excluded |
| **Processing Realism** | Full system | Per-layer | Direct function |
| **Best For** | System validation | Layer isolation | Function profiling |
| **Typical Latency** | 3-100ms | 0.1-50ms | 0.001-10ms |
| **Iterations** | 600 frames (10s) | 600 frames (10s) | 10,000 calls |
| **Use Case** | ADR-003 validation | Bottleneck identification | Optimization target |

---

### 1. E2E Latency Test

**Purpose:** Measure realistic end-to-end latency with all layers active, using NATS Broker.

**Method:**
- Start NATS server (via subprocess or existing container)
- Start all RuntimeManagers (Input, Router, Fixture, Output) with NATS Broker
- Use FakeAdapter instances (1 axis per adapter)
- Subscribe to `output.*` topics
- Measure time from input injection to output message reception
- All managers run at **60Hz tick rate** (dt = 1/60 seconds)

**Configurations:** 1, 10, 25, 50, 100 inputs/outputs, 10s duration (600 frames)

**Output:**
```
results/YYYYMMDD_HHMMSS/e2e/
├── test_metadata.json
├── results.csv              # Raw per-frame data
├── statistics.csv           # Aggregated stats
└── plots/
    ├── boxplot.svg          # Linear scale: 1,10,25,50,100
    ├── boxplot.pdf
    ├── scaling.svg          # Linear scale
    ├── scaling.pdf
    └── histogram.svg
```

**CSV Format (results.csv):**
```csv
frame_number,latency_ms,is_drop
1,2.8,0
2,3.1,0
...
```

**CSV Format (statistics.csv):**
```csv
config_inputs,config_outputs,count,total_events,min_ms,max_ms,mean_ms,median_ms,std_dev_ms,drops,drop_rate
1,1,600,600,1.8,4.2,2.5,2.4,0.2,0,0.0
10,10,6000,6000,2.1,5.6,3.2,3.1,0.3,0,0.0
```

---

### 2. Per-Layer Latency Tests

**Purpose:** Measure each layer's processing time independently with NATS Broker and 60Hz tick.

**Layers:**
| **Layer** | **Runtime Manager** | **Input Topic** | **Output Topic** |
|-----------|---------------------|-----------------|------------------|
| Input | InputRuntimeManager | N/A (FakeAdapter) | `input.*` |
| Router | RouterRuntimeManager | `input.*` | `target.*` |
| Fixture | FixtureRuntimeManager | `target.*` | `output.*` |
| Output | OutputRuntimeManager | `output.*` | (ArtNet) |
| Full | All Managers | FakeAdapter | `output.*` |

**Method:**
1. Start NATS server
2. Start only the layer under test's RuntimeManager
3. Subscribe to layer's output topic
4. At 60Hz: publish to input topic → wait for output → calculate latency
5. Layer receives all subscribed messages, processes in tick, publishes outputs

**Configurations:** 1, 10, 25, 50, 100 inputs, 10s duration (600 frames)

**Output:**
```
results/YYYYMMDD_HHMMSS/layer/
├── input/
│   ├── test_metadata.json
│   ├── results.csv
│   ├── statistics.csv
│   └── plots/          # boxplot.svg, scaling.svg (linear)
├── router/
│   ├── ...
│   └── plots/
├── fixture/
│   ├── ...
│   └── plots/
├── output/
│   ├── ...
│   └── plots/
└── full/
    ├── ...
    └── plots/
```

---

### 3. Module Tests

**Purpose:** Deep-dive profiling of specific functions identified as slow by per-layer tests.

**Strategy:**
1. Identify slow functions from per-layer test results
2. Call functions directly with pre-prepared data (no broker, no tick)
3. High iteration count (10,000) for statistical significance
4. Measure raw function performance

**Example Targets:**
- `MappingRouter.handle_input()`
- `MappingRouter._resolve_mapping()`
- `FixtureCore.process_frame()`
- `FixtureCore._calculate_dmx()`
- `OutputPublisher.publish_dmx()`

**Configurations:** 1, 5, 10, 25, 50, 100 items, 10,000 iterations

**Output:**
```
results/YYYYMMDD_HHMMSS/module/
├── router/
│   ├── handle_input/
│   │   ├── test_metadata.json
│   │   ├── results.csv
│   │   ├── statistics.csv
│   │   └── plots/     # boxplot.svg, scaling.svg (linear)
│   └── resolve_mapping/
│       ├── ...
│       └── plots/
├── fixture/
│   ├── process_frame/
│   │   ├── ...
│   │   └── plots/
│   └── calculate_dmx/
│       ├── ...
│       └── plots/
└── output/
    └── publish_dmx/
        ├── ...
        └── plots/
```

---

## Standardized Plots

### Requirements (All Tests)

**General Settings:**
```python
plt.rcParams['figure.figsize'] = [10, 6]
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.titlepad'] = 20
sns.set_style("whitegrid")
```

**1. Boxplot** (`boxplot.svg`, `boxplot.pdf`)
- Configurations: 1, 10, 25, 50, 100 (remove others if crowded)
- X-axis: Number of Inputs (**linear scale**)
- Y-axis: Latency (ms)
- Boxplot showing quartiles, median, whiskers
- Individual datapoints as scatter (alpha=0.3, size=2)
- No outliers hidden
- DPI: 300, bbox_inches: tight

**2. Latency vs Scaling** (`scaling.svg`, `scaling.pdf`)
- X-axis: Number of Inputs (**linear scale** - NOT logarithmic)
- Y-axis: Median Latency (ms)
- Line connecting median values with markers
- Error bars showing standard deviation
- Individual datapoints as scatter (alpha=0.2)
- Horizontal lines: y=30 (red, dotted, "Target <30ms"), y=16.67 (green, dotted, "Frame Time")
- DPI: 300, bbox_inches: tight

### Color Scheme

| **Component** | **Color** |
|--------------|-----------|
| Input layer | `#9b59b6` (purple) |
| Router layer | `#3498db` (blue) |
| Fixture layer | `#e74c3c` (red) |
| Output layer | `#f39c12` (orange) |
| Full/E2E | `#2ecc71` (green) |

---

## Implementation Details

### Shared Infrastructure (conftest.py)

**NATS Broker Fixture:**
```python
@pytest.fixture(scope="session")
def nats_server():
    """Start NATS server for test session."""
    import nats
    try:
        nc = nats.connect(servers=["nats://localhost:4222"])
        nc.close()
        yield "localhost:4222"
        return
    except Exception:
        import subprocess
        proc = subprocess.Popen(
            ["nats-server", "-p", "4222", "-m", "8222"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)
        yield "localhost:4222"
        proc.terminate()
        proc.wait(timeout=5)

@pytest.fixture
def nats_client(nats_server):
    import nats
    nc = nats.connect(servers=[f"nats://{nats_server}"])
    yield nc
    nc.close()
```

**60Hz Tick Constant:**
```python
TARGET_INTERVAL = 1.0 / 60.0  # 16.67ms per frame
```

---

### E2E Test Implementation (test_e2e_latency.py)

```python
import pytest
import asyncio
import time
import csv
import json
import statistics
import socket
import platform

fromapelios.input.input_runtime_manager import InputRuntimeManager
fromapelios.router.router_runtime_manager import RouterRuntimeManager
fromapelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
fromapelios.output.output_runtime_manager import OutputRuntimeManager
fromapelios.broker.broker_runtime_manager import BrokerRuntimeManager
fromapelios.input.adapters.fake_adapter import FakeAdapter

E2E_CONFIGS = [1, 10, 25, 50, 100]
TARGET_INTERVAL = 1.0 / 60.0
FRAMES_PER_CONFIG = 600

@pytest.fixture(params=E2E_CONFIGS)
def input_config(request):
    return request.param

@pytest.mark.asyncio
async def test_e2e_latency(nats_client, input_config, tmp_path):
    outputs_dir = tmp_path / "e2e"
    outputs_dir.mkdir()
    
    # Setup NATS Broker and all managers
    broker_manager = BrokerRuntimeManager(nats_client=nats_client)
    input_manager = InputRuntimeManager(broker_client=broker_manager.client)
    router_manager = RouterRuntimeManager(broker_client=broker_manager.client)
    fixture_manager = FixtureRuntimeManager(broker_client=broker_manager.client)
    output_manager = OutputRuntimeManager(broker_client=broker_manager.client)
    
    # Create FakeAdapters (1 axis each)
    adapters = [
        FakeAdapter(device=f"test_{i}", axis_types={"value": "absolute_uni"})
        for i in range(input_config)
    ]
    for adapter in adapters:
        input_manager.register_adapter(adapter)
    
    # Start all managers
    await broker_manager.start()
    await input_manager.start()
    await input_manager.start_registered_adapters()
    await router_manager.start()
    await fixture_manager.start()
    await output_manager.start()
    
    # Track outputs
    output_timestamps = []
    input_timestamps = []
    
    async def on_output(msg):
        output_timestamps.append(time.perf_counter())
    
    await broker_manager.client.subscribe("output.>", on_output)
    
    # Warmup
    await asyncio.sleep(1.0)
    output_timestamps.clear()
    input_timestamps.clear()
    
    # Test loop at 60Hz
    for frame in range(FRAMES_PER_CONFIG):
        loop_start = time.perf_counter()
        input_timestamps.append(loop_start)
        
        await input_manager.tick(dt=TARGET_INTERVAL)
        await router_manager.tick(dt=TARGET_INTERVAL)
        await fixture_manager.tick(dt=TARGET_INTERVAL)
        await output_manager.tick(dt=TARGET_INTERVAL)
        
        elapsed = time.perf_counter() - loop_start
        sleep_time = max(0, TARGET_INTERVAL - elapsed)
        await asyncio.sleep(sleep_time)
    
    # Calculate latencies and save results
    latencies = []
    min_length = min(len(input_timestamps), len(output_timestamps))
    for i in range(min_length):
        latencies.append((output_timestamps[i] - input_timestamps[i]) * 1000)
    drops = len(input_timestamps) - min_length
    
    # Save results
    with (outputs_dir / "results.csv").open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["frame_number", "latency_ms", "is_drop"])
        for i, lat in enumerate(latencies):
            writer.writerow([i, lat, 0])
        for i in range(drops):
            writer.writerow([min_length + i, 0.0, 1])
    
    stats = {
        "config_inputs": input_config, "config_outputs": input_config,
        "count": len(latencies), "total_events": FRAMES_PER_CONFIG,
        "min_ms": min(latencies) if latencies else 0,
        "max_ms": max(latencies) if latencies else 0,
        "mean_ms": statistics.mean(latencies) if latencies else 0,
        "median_ms": statistics.median(latencies) if latencies else 0,
        "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "drops": drops, "drop_rate": drops / FRAMES_PER_CONFIG
    }
    with (outputs_dir / "statistics.csv").open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=stats.keys())
        writer.writeheader()
        writer.writerow(stats)
    
    metadata = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "test_type": "e2e", "config_inputs": input_config,
        "frames": FRAMES_PER_CONFIG,
        "system_info": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "hostname": socket.gethostname()
        }
    }
    with (outputs_dir / "test_metadata.json").open('w') as f:
        json.dump(metadata, f, indent=2)
    
    # Cleanup
    await input_manager.stop_registered_adapters()
    await input_manager.stop()
    await router_manager.stop()
    await fixture_manager.stop()
    await output_manager.stop()
    await broker_manager.stop()
    
    assert stats["median_ms"] < 100
```

---

### Per-Layer Test Example (test_layer_latency.py)

```python
@pytest.mark.asyncio
async def test_fixture_layer_latency(nats_client, layer_config, tmp_path):
    outputs_dir = tmp_path / "layer" / "fixture"
    outputs_dir.mkdir(parents=True)
    
    broker_manager = BrokerRuntimeManager(nats_client=nats_client)
    fixture_manager = FixtureRuntimeManager(broker_client=broker_manager.client)
    
    await broker_manager.start()
    await fixture_manager.start()
    
    input_timestamps = []
    output_timestamps = []
    
    async def on_output(msg):
        output_timestamps.append(time.perf_counter())
    
    await broker_manager.client.subscribe("output.>", on_output)
    
    # Warmup
    await asyncio.sleep(1.0)
    input_timestamps.clear()
    output_timestamps.clear()
    
    # Test loop at 60Hz
    for frame in range(FRAMES_PER_CONFIG):
        loop_start = time.perf_counter()
        input_timestamps.append(loop_start)
        
        # Publish to target.* topics
        for i in range(layer_config):
            msg = {
                "source": f"test_{i}.value",
                "value": 0.5,
                "type": "absolute_uni",
                "timestamp": loop_start
            }
            await broker_manager.client.publish(
                f"target.test_{i}.param",
                json.dumps(msg).encode()
            )
        
        # Fixture processes all subscribed messages in tick
        await fixture_manager.tick(dt=TARGET_INTERVAL)
        
        elapsed = time.perf_counter() - loop_start
        sleep_time = max(0, TARGET_INTERVAL - elapsed)
        await asyncio.sleep(sleep_time)
    
    # Calculate latencies and save results
    # ... (similar to E2E test)
    
    await fixture_manager.stop()
    await broker_manager.stop()
    
    assert stats["median_ms"] < 50  # Fixture layer known bottleneck
```

---

### Module Test Example (test_module_latency.py)

```python
import pytest
import time
import csv
import json
import statistics

fromapelios.fixture.fixture_core import FixtureCore

MODULE_CONFIGS = [1, 5, 10, 25, 50, 100]
MODULE_ITERATIONS = 10000

@pytest.fixture
def fixture_patch_n(n):
    return {
        "fixtures": {
            f"test_{i}": {
                "type": "dimmer",
                "parameters": {f"param": {"dmx_address": i, "dmx_universe": 0}}
            }
            for i in range(n)
        }
    }

@pytest.mark.parametrize("n_fixtures", MODULE_CONFIGS)
def test_process_frame_latency(n_fixtures, tmp_path, fixture_patch_n):
    outputs_dir = tmp_path / "module" / "fixture" / "process_frame"
    outputs_dir.mkdir(parents=True)
    
    patch = fixture_patch_n(n_fixtures)
    core = FixtureCore(patch=patch)
    
    # Warmup
    for i in range(n_fixtures):
        core.inbox[f"target.test_{i}.param"] = {
            "source": f"input.test_{i}", "value": 0.5,
            "type": "absolute_uni", "timestamp": time.time()
        }
    core.process_frame(dt=0.016)
    
    # Test - direct function calls, no broker, no tick
    latencies = []
    for _ in range(MODULE_ITERATIONS):
        for i in range(n_fixtures):
            core.inbox[f"target.test_{i}.param"] = {
                "source": f"input.test_{i}", "value": 0.5,
                "type": "absolute_uni", "timestamp": time.time()
            }
        
        start = time.perf_counter()
        core.process_frame(dt=0.016)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    # Save results
    with (outputs_dir / "results.csv").open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["config_items", "iteration", "latency_ms"])
        for i, lat in enumerate(latencies):
            writer.writerow([n_fixtures, i, lat])
    
    stats = {
        "config_items": n_fixtures, "count": len(latencies),
        "min_ms": min(latencies), "max_ms": max(latencies),
        "mean_ms": statistics.mean(latencies),
        "median_ms": statistics.median(latencies),
        "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0
    }
    with (outputs_dir / "statistics.csv").open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=stats.keys())
        writer.writeheader()
        writer.writerow(stats)
    
    metadata = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "test_type": "module", "module": "fixture",
        "function": "process_frame", "config_items": n_fixtures,
        "iterations": len(latencies)
    }
    with (outputs_dir / "test_metadata.json").open('w') as f:
        json.dump(metadata, f, indent=2)
    
    assert stats["median_ms"] < 10

---

### Plot Generation (plot_results.py)

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path

LAYER_COLORS = {
    "input": "#9b59b6", "router": "#3498db",
    "fixture": "#e74c3c", "output": "#f39c12",
    "full": "#2ecc71", "e2e": "#2ecc71"
}

plt.rcParams['figure.figsize'] = [10, 6]
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.titlepad'] = 20
sns.set_style("whitegrid")


def generate_boxplot(data, title, output_path, color=None):
    fig, ax = plt.subplots()
    if color:
        sns.boxplot(data=data, x='config_inputs', y='latency_ms',
                    color=color, showfliers=False, whis=[0, 100], ax=ax)
    else:
        sns.boxplot(data=data, x='config_inputs', y='latency_ms',
                    showfliers=False, whis=[0, 100], ax=ax)
    sns.stripplot(data=data, x='config_inputs', y='latency_ms',
                  color='black', alpha=0.3, size=2, ax=ax)
    ax.set_title(title)
    ax.set_xlabel('Inputs')
    ax.set_ylabel('Latency (ms)')
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path.with_suffix('.svg'), bbox_inches='tight', dpi=300)
    fig.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight', dpi=300)
    plt.close(fig)


def generate_scaling_plot(data, title, output_path, color=None):
    fig, ax = plt.subplots()
    stats = data.groupby('config_inputs')['latency_ms'].agg(['median', 'std']).reset_index()
    label = 'Median +/- Std Dev'
    if color:
        ax.errorbar(stats['config_inputs'], stats['median'], yerr=stats['std'],
                   fmt='-o', capsize=5, color=color, label=label)
    else:
        ax.errorbar(stats['config_inputs'], stats['median'], yerr=stats['std'],
                   fmt='-o', capsize=5, label=label)
    ax.axhline(y=30, color='r', linestyle=':', label='Target (<30ms)')
    ax.axhline(y=16.67, color='g', linestyle=':', label='Frame Time (16.67ms)')
    ax.set_title(title)
    ax.set_xlabel('Number of Inputs')  # Linear scale
    ax.set_ylabel('Median Latency (ms)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path.with_suffix('.svg'), bbox_inches='tight', dpi=300)
    fig.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight', dpi=300)
    plt.close(fig)
```

---

### CLI Runner (run_all_performance_tests.py)

```python
#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Performance Test Runner')
    parser.add_argument('--output-dir', type=str, default='results')
    parser.add_argument('--plot', action='store_true', default=True)
    parser.add_argument('--e2e', action='store_true')
    parser.add_argument('--layer', action='store_true')
    parser.add_argument('--module', action='store_true')
    parser.add_argument('--all', action='store_true', default=True)
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(args.output_dir) / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)
    
    tests_to_run = []
    if args.all or (not args.e2e and not args.layer and not args.module):
        tests_to_run = ['e2e', 'layer', 'module']
    else:
        if args.e2e: tests_to_run.append('e2e')
        if args.layer: tests_to_run.append('layer')
        if args.module: tests_to_run.append('module')
    
    test_files = {
        'e2e': 'tools/performance/tests/test_e2e_latency.py',
        'layer': 'tools/performance/tests/test_layer_latency.py',
        'module': 'tools/performance/tests/test_module_latency.py'
    }
    
    for test_type in tests_to_run:
        test_file = Path(test_files[test_type])
        if test_file.exists():
            cmd = [sys.executable, "-m", "pytest", str(test_file), "--tb=short"]
            if args.verbose: cmd.append("-v")
            if not args.dry_run:
                result = subprocess.run(cmd, capture_output=True, text=True)
                print(result.stdout)
            else:
                print("[DRY RUN]", " ".join(cmd))
    
    if args.plot:
        from tools.performance.scripts.plot_results import generate_all_plots
        generate_all_plots(results_dir)
    
    print(f"Results saved to: {results_dir}")

if __name__ == "__main__":
    main()
```

---

## Setup and Usage

### Requirements
```
pytest>=7.0
pytest-asyncio>=0.21
matplotlib>=3.7
seaborn>=0.12
pandas>=2.0
nats-py>=2.0
```

### Directory Setup
```bash
mkdir -p tools/performance/{tests,scripts,results}
touch tools/performance/__init__.py
touch tools/performance/tests/__init__.py
touch tools/performance/scripts/__init__.py
echo -e "# Ignore all generated results\n*\n!.gitignore" > tools/performance/results/.gitignore
```

### Usage Examples
```bash
# Run all tests with plots
python tools/performance/scripts/run_all_performance_tests.py --output-dir results/ --plot

# Run only E2E tests
python tools/performance/scripts/run_all_performance_tests.py --e2e --output-dir results/

# Run via pytest directly
python -m pytest tools/performance/tests/test_e2e_latency.py -v

# Dry run
python tools/performance/scripts/run_all_performance_tests.py --dry-run
```

---

## Module Test Strategy

The **module test strategy** is designed for deep-dive profiling after per-layer tests identify bottlenecks:

**Process:**
1. **Identify:** Run per-layer tests to find which layer has high latency
2. **Isolate:** Examine the layer's source code to identify candidate functions
3. **Profile:** Create module tests that call these functions directly
4. **Analyze:** Module tests reveal raw function performance without broker/tick overhead
5. **Optimize:** Focus optimization efforts on the slowest functions

**Example Workflow:**
- Per-layer test shows Fixture layer has 26ms latency at 10 inputs
- Module test on `FixtureCore.process_frame()` shows 25ms of that latency
- Module test on `FixtureCore._calculate_dmx()` shows 24ms
- Conclusion: DMX calculation is the bottleneck
- Action: Optimize `_calculate_dmx()` method

**Key Differences:**
- **No NATS Broker:** Tests direct function calls only
- **No 60Hz Tick:** Functions called directly, not through runtime managers
- **High Iterations:** 10,000 calls for statistical significance
- **Precision:** Measures raw computation time, excluding all external factors

---

## Expected Outcomes

1. **E2E Test:** Confirms Task-026 findings with NATS Broker overhead
2. **Per-Layer Tests:** Isolates fixture layer bottleneck with realistic 60Hz tick processing
3. **Module Tests:** Enables deep-dive into slow functions
4. **Standardized Plots:** Consistent linear scale visualization for thesis
5. **Reproducible Results:** Clear organization, metadata tracking

---

## Next Steps

1. [ ] Create `tools/performance/` directory structure
2. [ ] Implement `conftest.py` with NATS Broker fixtures
3. [ ] Implement `test_e2e_latency.py` with NATS Broker + 60Hz tick
4. [ ] Implement `test_layer_latency.py` with NATS Broker + 60Hz tick
5. [ ] Implement `test_module_latency.py` for deep-dive profiling
6. [ ] Create `plot_results.py` with standardized linear scale plots
7. [ ] Create `run_all_performance_tests.py` CLI runner
8. [ ] Add README with usage documentation
9. [ ] Test and validate results
10. [ ] Move Task-027 to done/ once validated

---

## References

- [Task-026: End-to-End Latency Test](../done/026-e2e-delay-test.md)
- [Task-027: Per-Layer Latency Test](../done/027-layer-latency-test.md)
- [ADR-003: 60Hz Tick Rate](../adr/003-60hz-tick.md)
- [ADR-009: Orchestrator](../adr/009-orchestrator.md)
- [NFR-1.1: Scalability](../architecture/non-functional-requirements-list.md#scalability)
- [Broker Runtime Manager](../src/apelios/broker/broker_runtime_manager.py)
- [Router Runtime Manager](../src/apelios/router/router_runtime_manager.py)
- [Fixture Runtime Manager](../src/apelios/fixture/fixture_runtime_manager.py)
- [Output Runtime Manager](../src/apelios/output/output_runtime_manager.py)
- [FakeAdapter Implementation](../src/apelios/input/adapters/fake_adapter.py)
```
