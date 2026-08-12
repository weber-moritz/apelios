# Latency benchmark snapshot

This directory preserves the reproducible benchmark snapshot captured on
2026-08-07. It contains the raw measurements, per-run metadata, summary
statistics, and representative plots used to establish the optimization
baseline documented in [`docs/tasks/029-optimize-system-latency.md`](../../tasks/029-optimize-system-latency.md).

## Reproducing the snapshot

Install the project with its development and performance dependencies:

```bash
python -m pip install -e '.[dev,performance]'
```

Then run the performance suite from the repository root:

```bash
python tools/performance/scripts/run_all_performance_tests.py \
  --output-dir tools/performance/results/ \
  --plot
```

The framework and result schema are documented in
[`tools/performance/README.md`](../../../tools/performance/README.md).

## Retention policy

The checked-in snapshot intentionally keeps:

- `results.csv` files containing the measurements;
- `statistics.csv` summaries;
- anonymized `test_metadata.json` files;
- PDF plots and reasonably sized SVG plots for review and reuse.

Four layer boxplot SVGs were omitted because each was approximately 12 MB and an
equivalent PDF is retained. Newly generated CSV and JSON output remains ignored
outside this curated snapshot.

Benchmark results are machine- and environment-dependent. Treat this snapshot as
the project baseline, not as a universal performance guarantee.
