# Apelios Performance Testing Framework

A structured performance testing framework for measuring Apelios system latency with NATS Broker and 60Hz tick.

## Quick Start

### 1. Install Dependencies

```bash
# Python packages - using requirements.txt
pip install -r requirements.txt

# Or install manually:
pip install pytest pytest-asyncio matplotlib seaborn pandas nats-py

# NATS Server (required for E2E and per-layer tests)
# Ubuntu/Debian:
sudo apt-get install nats-server

# Or download manually from https://nats.io/download/
nats-server -p 4222 &
```

### 2. Run Tests

```bash
# Run ALL tests with plots
python scripts/run_all_performance_tests.py --output-dir results/ --plot

# Run only E2E tests
python scripts/run_all_performance_tests.py --e2e --output-dir results/

# Run only per-layer tests
python scripts/run_all_performance_tests.py --layer --output-dir results/ --plot

# Run only module tests
python scripts/run_all_performance_tests.py --module --output-dir results/

# Dry run (show commands without executing)
python scripts/run_all_performance_tests.py --dry-run
```

### 3. Run via pytest Directly

```bash
# All E2E tests
python -m pytest tests/test_e2e_latency.py -v

# Specific configuration
python -m pytest tests/test_e2e_latency.py::TestE2ELatency::test_e2e_latency[10] -v

# All per-layer tests
python -m pytest tests/test_layer_latency.py -v

# All module tests
python -m pytest tests/test_module_latency.py -v
```

## Framework Structure

```
tools/performance/
├── tests/
│   ├── test_e2e_latency.py       # Full system test with NATS Broker + 60Hz tick
│   ├── test_layer_latency.py     # Per-layer tests (input, router, fixture, output, full)
│   └── test_module_latency.py    # Module-level direct function calls
├── scripts/
│   ├── plot_results.py           # Generate standardized plots (linear scale)
│   └── run_all_performance_tests.py  # CLI runner
└── results/                      # Generated output (gitignored)
    └── YYYYMMDD_HHMMSS/
        ├── e2e/
        ├── layer/
        └── module/
```

## Test Types

| Test | Broker | 60Hz Tick | Purpose | Typical Latency |
|------|--------|-----------|---------|-----------------|
| **E2E** | NATS | Yes | Full system validation | 3-15ms |
| **Per-Layer** | NATS | Yes | Layer isolation | 0.1-50ms |
| **Module** | None | No | Function profiling | 0.001-10ms |

### E2E Test (`test_e2e_latency.py`)
- Tests full system with all layers active
- Uses NATS Broker for realistic communication overhead
- 60Hz tick rate for realistic processing
- Configurations: **1, 10, 25, 50, 100** inputs
- Output: CSV data + plots (boxplot, scaling, histogram)

### Per-Layer Tests (`test_layer_latency.py`)
- Tests each layer independently: **input, router, fixture, output, full**
- Uses NATS Broker + 60Hz tick
- Each layer receives all messages, processes in tick, publishes outputs
- Configurations: **1, 10, 25, 50, 100** inputs
- Output: CSV data + plots per layer

### Module Tests (`test_module_latency.py`)
- Direct function calls (no broker, no tick)
- High iteration count: **10,000** for statistical significance
- Targets slow functions identified by layer tests
- Configurations: **1, 5, 10, 25, 50, 100** items
- Output: CSV data + plots per function

## Results Structure

```
results/YYYYMMDD_HHMMSS/
├── e2e/
│   ├── test_metadata.json
│   ├── results.csv
│   ├── statistics.csv
│   └── plots/
│       ├── boxplot.svg      # Linear scale: 1,10,25,50,100 inputs
│       ├── boxplot.pdf
│       ├── scaling.svg      # Linear scale (NOT logarithmic)
│       ├── scaling.pdf
│       └── histogram.svg
├── layer/
│   ├── input/
│   │   ├── ...
│   │   └── plots/
│   ├── router/
│   ├── fixture/
│   ├── output/
│   └── full/
└── module/
    ├── router/
    │   ├── handle_input/
    │   └── resolve_mapping/
    ├── fixture/
    │   ├── process_frame/
    │   └── calculate_dmx/
    └── output/
        └── publish_dmx/
```

## Plot Standards

All plots use **linear scale** (not logarithmic) and include:

- **Boxplot**: Shows distribution with quartiles, median, whiskers, individual datapoints
- **Scaling Plot**: Line with markers, error bars (std dev), target lines at 30ms and 16.67ms
- **Formats**: SVG + PDF, 300 DPI, tight bbox
- **Colors**: Per-layer color scheme (input=purple, router=blue, fixture=red, output=orange, full=green)

## Expected Results

Based on previous findings:

| Inputs | E2E | Input Layer | Router Layer | Fixture Layer | Output Layer |
|--------|-----|-------------|--------------|---------------|--------------|
| 1 | ~3ms | <1ms | <1ms | ~1ms | <1ms |
| 10 | ~6ms | <1ms | <1ms | ~5ms | <1ms |
| 25 | ~7ms | <1ms | <1ms | ~10ms | <1ms |
| 50 | ~10ms | <1ms | <1ms | ~20ms | <1ms |
| 100 | ~15ms | <1ms | <1ms | ~25ms | <1ms |

## Troubleshooting

### NATS Server Issues
```bash
# Check if NATS is running
nats-server -p 4222 &

# Check port
netstat -tlnp | grep 4222
```

### Missing Dependencies
```bash
pip install pytest pytest-asyncio matplotlib seaborn pandas nats-py
```

### Permission Issues
```bash
mkdir -p results
chmod 755 results
```

## Key Features

- NATS Broker for realistic communication overhead
- 60Hz tick for realistic processing simulation
- Linear scale for all scaling plots (not logarithmic)
- Per-test plots with standardized formatting
- Organized results with metadata and CSV output
- Module tests for deep-dive function profiling

## More Information

- See `docs/tasks/028-performance-test-framework.md` for detailed implementation
- See `docs/tasks/done/026-e2e-delay-test.md` for baseline E2E test
- See `docs/tasks/done/027-layer-latency-test.md` for previous layer test findings