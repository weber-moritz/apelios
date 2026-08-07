"""
Plot Generation Utility for Apelios Performance Testing Framework.

Generates standardized plots (boxplot, scaling) with linear scale for all test results.

Usage:
    from tools.performance.scripts.plot_results import generate_all_plots
    generate_all_plots(Path("results/YYYYMMDD_HHMMSS"))
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
import json
import csv
import math

# Color scheme for different layers
LAYER_COLORS = {
    "input": "#9b59b6",    # purple
    "router": "#3498db",   # blue
    "fixture": "#e74c3c",   # red
    "output": "#f39c12",   # orange
    "full": "#2ecc71",     # green
    "e2e": "#2ecc71",      # green
}

# Figure settings - standardized across all plots
plt.rcParams['figure.figsize'] = [10, 6]
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.titlepad'] = 20
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 12
sns.set_style("whitegrid")

# Target constants (ms)
TARGET_30MS = 30.0      # Absolute max latency target
TARGET_16_67MS = 16.67  # Frame budget at 60Hz (1/60 seconds)
TARGET_MAX_COLOR = '#c95757'     # muted red
FRAME_BUDGET_COLOR = '#3a8f7b'   # muted teal-green
SAMPLE_COLOR = '#344054'         # soft blue-black


def generate_boxplot(
    data: pd.DataFrame,
    title: str,
    output_path: Path,
    color: str = None,
    x_label: str = 'Number of Inputs',
):
    """
    Generate standardized boxplot with linear scale.
    
    Shows distribution with:
    - Box: quartiles (25%, 50%, 75%)
    - Green line: median (50%)
    - Whiskers: full range (min to max, no outlier hiding)
    - Black dots: individual datapoints (all shown)
    - Red dashed line: 30ms target (absolute max)
    - Green dashed line: 16.67ms target (frame budget)
    
    Args:
        data: DataFrame with 'config_inputs' and 'latency_ms' columns
        title: Plot title
        output_path: Output path (without extension)
        color: Color for the boxplot (optional)
    """
    if data.empty or 'config_inputs' not in data.columns or 'latency_ms' not in data.columns:
        print(f"Skipping boxplot for {title}: missing required columns")
        return
    
    fig, ax = plt.subplots()
    
    # Filter configurations to 1, 10, 25, 50, 100
    valid_configs = [1, 10, 25, 50, 100]
    filtered_data = data[data['config_inputs'].isin(valid_configs)]
    
    # Use consistent color with fallback
    box_color = color if color else '#3498db'  # Default blue
    
    # Create boxplot
    sns.boxplot(
        data=filtered_data, 
        x='config_inputs', 
        y='latency_ms',
        color=box_color, 
        showfliers=False, 
        whis=[0, 100],  # Show full range
        ax=ax,
        linewidth=1.5,
        saturation=0.9,
    )
    
    # Overlay individual datapoints as scatter (all datapoints visible)
    sns.stripplot(
        data=filtered_data, 
        x='config_inputs', 
        y='latency_ms',
        color=SAMPLE_COLOR,
        alpha=0.16,  # Subtle enough to preserve the layer color
        size=1.5,
        ax=ax
    )
    
    # Add target lines (dotted for clear visibility)
    ax.axhline(y=TARGET_30MS, color=TARGET_MAX_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_30MS}ms Target (Max)')
    ax.axhline(y=TARGET_16_67MS, color=FRAME_BUDGET_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_16_67MS}ms (Frame Budget)')
    
    ax.set_title(title, pad=20, fontsize=12, fontweight='bold')
    ax.set_xlabel(x_label, fontsize=10, labelpad=10)
    ax.set_ylabel('Latency (ms)', fontsize=10, labelpad=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right')
    
    # Clean up layout
    fig.tight_layout()
    
    # Save in both SVG and PDF formats
    for ext in ['svg', 'pdf']:
        filepath = output_path.with_suffix(f'.{ext}')
        fig.savefig(filepath, bbox_inches='tight', dpi=300)
    
    plt.close(fig)


def generate_scaling_plot(
    data: pd.DataFrame,
    title: str,
    output_path: Path,
    color: str = None,
    x_label: str = 'Number of Inputs',
    show_p95: bool = False,
):
    """
    Generate standardized scaling plot with linear scale.
    
    Shows scaling behavior:
    - Line with markers: median latency per config
    - Error bars: +/- standard deviation
    - Red dashed line: 30ms target (absolute max)
    - Green dashed line: 16.67ms target (frame budget)
    
    Args:
        data: DataFrame with 'config_inputs' and 'latency_ms' columns
        title: Plot title
        output_path: Output path (without extension)
        color: Color for the line (optional)
    """
    if data.empty or 'config_inputs' not in data.columns or 'latency_ms' not in data.columns:
        print(f"Skipping scaling plot for {title}: missing required columns")
        return
    
    fig, ax = plt.subplots()
    
    # Calculate statistics per configuration
    stats = data.groupby('config_inputs')['latency_ms'].agg(['median', 'std']).reset_index()
    
    # Sort by config_inputs for proper line plotting
    stats = stats.sort_values('config_inputs')
    
    # Use consistent color with fallback
    line_color = color if color else '#3498db'  # Default blue
    
    # Plot with error bars
    ax.errorbar(
        stats['config_inputs'], 
        stats['median'], 
        yerr=stats['std'],
        fmt='-o', 
        capsize=5,
        color=line_color,
        linewidth=2,
        markersize=6,
        label='Median +/- Std Dev'
    )

    if show_p95:
        p95 = (
            data.groupby('config_inputs')['latency_ms']
            .quantile(0.95)
            .sort_index()
        )
        ax.plot(
            p95.index,
            p95.values,
            '--s',
            color=FRAME_BUDGET_COLOR,
            linewidth=2,
            markersize=5,
            label='95th percentile',
        )
    
    # Add target lines (dotted for clear visibility, matching boxplot)
    ax.axhline(y=TARGET_30MS, color=TARGET_MAX_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_30MS}ms Target (Max)')
    ax.axhline(y=TARGET_16_67MS, color=FRAME_BUDGET_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_16_67MS}ms (Frame Budget)')
    
    ax.set_title(title, pad=20, fontsize=12, fontweight='bold')
    ax.set_xlabel(x_label, fontsize=10, labelpad=10)  # Linear scale - NOT logarithmic
    ax.set_ylabel('Median Latency (ms)', fontsize=10, labelpad=10)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Clean up layout
    fig.tight_layout()
    
    # Save in both SVG and PDF formats
    for ext in ['svg', 'pdf']:
        filepath = output_path.with_suffix(f'.{ext}')
        fig.savefig(filepath, bbox_inches='tight', dpi=300)
    
    plt.close(fig)


def generate_histogram(data: pd.DataFrame, title: str, output_path: Path, color: str = None):
    """
    Generate standardized histogram (optional).
    
    Shows latency distribution:
    - Bars: frequency of each latency range
    - Red dashed line: 30ms target
    - Green dashed line: 16.67ms frame budget
    
    Args:
        data: DataFrame with 'latency_ms' column
        title: Plot title
        output_path: Output path (without extension)
        color: Color for histogram bars (optional)
    """
    bar_color = color if color else '#3498db'
    configs = sorted(data['config_inputs'].dropna().unique()) if 'config_inputs' in data else []

    if configs:
        # Thesis-friendly small multiples: use the full text width and compact
        # vertical panels so configurations are easy to compare on one axis.
        all_latencies = data['latency_ms'].dropna()
        latency_min = float(all_latencies.min())
        latency_max = float(all_latencies.max())
        bin_width_ms = 0.5
        bin_start = math.floor(latency_min / bin_width_ms) * bin_width_ms
        bin_end = math.ceil(latency_max / bin_width_ms) * bin_width_ms
        bin_count = max(1, int(round((bin_end - bin_start) / bin_width_ms)))
        common_bins = [bin_start + bin_width_ms * index for index in range(bin_count + 1)]
        fig, axes = plt.subplots(
            len(configs),
            1,
            figsize=(10, 1.75 * len(configs) + 1.25),
            sharex=True,
            sharey=True,
            squeeze=False,
        )
        axes = axes.flatten()
        for ax, config in zip(axes, configs):
            latencies = data.loc[data['config_inputs'] == config, 'latency_ms'].dropna()
            if latencies.empty:
                ax.set_visible(False)
                continue
            p95 = latencies.quantile(0.95)
            ax.hist(latencies, bins=common_bins, alpha=0.78, edgecolor=SAMPLE_COLOR, linewidth=0.6, color=bar_color)
            ax.axvline(p95, color='#6f42c1', linestyle='--', linewidth=2, label=f'p95: {p95:.2f} ms')
            ax.axvline(TARGET_30MS, color=TARGET_MAX_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_30MS} ms target')
            ax.axvline(TARGET_16_67MS, color=FRAME_BUDGET_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_16_67MS} ms budget')
            ax.text(
                0.01,
                0.86,
                f'{int(config)} Inputs / Outputs  |  p95 = {p95:.2f} ms',
                transform=ax.transAxes,
                fontsize=9,
                fontweight='bold',
                va='top',
            )
            ax.set_ylabel('Frames\n/ 0.5 ms')
            ax.grid(True, alpha=0.3)
        axes[-1].set_xlabel('Latency (ms)', fontsize=10, labelpad=8)
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles,
            ['95th percentile', f'{TARGET_30MS} ms target', f'{TARGET_16_67MS} ms frame budget'],
            loc='upper center',
            bbox_to_anchor=(0.5, 0.965),
            ncol=3,
            fontsize=9,
            frameon=False,
        )
        fig.suptitle(title, y=0.995, fontsize=12, fontweight='bold')
        fig.tight_layout(rect=(0, 0, 1, 0.93), h_pad=0.45)
    else:
        fig, ax = plt.subplots()
        latencies = data['latency_ms'].dropna()
        if len(latencies) > 0:
            p95 = latencies.quantile(0.95)
            ax.hist(latencies, bins=50, alpha=0.78, edgecolor=SAMPLE_COLOR, linewidth=0.6, color=bar_color)
            ax.axvline(p95, color='#6f42c1', linestyle='--', linewidth=2, label=f'p95: {p95:.2f} ms')
        ax.axvline(TARGET_30MS, color=TARGET_MAX_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_30MS} ms target')
        ax.axvline(TARGET_16_67MS, color=FRAME_BUDGET_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_16_67MS} ms budget')
        ax.set_title(title, pad=20, fontsize=12, fontweight='bold')
        ax.set_xlabel('Latency (ms)', fontsize=10, labelpad=10)
        ax.set_ylabel('Frequency (Count)', fontsize=10, labelpad=10)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
    
    # Clean up layout
    if not configs:
        fig.tight_layout()
    
    # Save in both SVG and PDF formats
    for ext in ['svg', 'pdf']:
        filepath = output_path.with_suffix(f'.{ext}')
        fig.savefig(filepath, bbox_inches='tight', dpi=300)
    
    plt.close(fig)


def generate_ecdf(data: pd.DataFrame, title: str, output_path: Path):
    """Generate an E2E empirical cumulative distribution for SLO evaluation."""
    required_columns = {'config_inputs', 'latency_ms'}
    if data.empty or not required_columns.issubset(data.columns):
        print(f"Skipping ECDF for {title}: missing required columns")
        return

    configs = sorted(data['config_inputs'].dropna().unique())
    colors = sns.color_palette('viridis', n_colors=len(configs))
    fig, ax = plt.subplots(figsize=(10, 6))

    for color, config in zip(colors, configs):
        latencies = sorted(
            data.loc[data['config_inputs'] == config, 'latency_ms'].dropna()
        )
        if not latencies:
            continue
        cumulative_percent = [
            100.0 * index / len(latencies)
            for index in range(1, len(latencies) + 1)
        ]
        p95 = float(pd.Series(latencies).quantile(0.95))
        ax.step(
            latencies,
            cumulative_percent,
            where='post',
            color=color,
            linewidth=2,
            label=f'{int(config)} I/O (p95 {p95:.2f} ms)',
        )
        ax.scatter([p95], [95], color=color, s=35, zorder=5)

    ax.axhline(
        y=95,
        color='#6f42c1',
        linestyle='--',
        linewidth=1.8,
        label='95% of frames',
    )
    ax.axvline(
        x=TARGET_16_67MS,
        color=FRAME_BUDGET_COLOR,
        linestyle=':',
        linewidth=2,
        label=f'{TARGET_16_67MS} ms frame budget',
    )
    ax.axvline(
        x=TARGET_30MS,
        color=TARGET_MAX_COLOR,
        linestyle=':',
        linewidth=2,
        label=f'{TARGET_30MS} ms target',
    )
    ax.set_xlim(left=0)
    ax.set_ylim(0, 101)
    ax.set_title(title, pad=20, fontsize=12, fontweight='bold')
    ax.set_xlabel('Frame-completion latency (ms)', fontsize=10, labelpad=10)
    ax.set_ylabel('Frames completed (%)', fontsize=10, labelpad=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=9)
    fig.tight_layout()

    for ext in ['svg', 'pdf']:
        fig.savefig(output_path.with_suffix(f'.{ext}'), bbox_inches='tight', dpi=300)

    plt.close(fig)


def generate_p95_requirement_plot(data: pd.DataFrame, output_path: Path):
    """Plot p95 E2E latency by I/O count for direct requirement evaluation."""
    required_columns = {'config_inputs', 'latency_ms'}
    if data.empty or not required_columns.issubset(data.columns):
        print("Skipping p95 requirement plot: missing required columns")
        return

    p95 = (
        data.groupby('config_inputs')['latency_ms']
        .quantile(0.95)
        .sort_index()
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        p95.index,
        p95.values,
        '-o',
        color='#6f42c1',
        linewidth=2.5,
        markersize=7,
        label='95th-percentile frame latency',
    )

    for io_count, latency in p95.items():
        ax.annotate(
            f'{latency:.2f} ms',
            (io_count, latency),
            xytext=(0, 9),
            textcoords='offset points',
            ha='center',
            fontsize=9,
        )

    ax.axhline(
        y=TARGET_16_67MS,
        color=FRAME_BUDGET_COLOR,
        linestyle=':',
        linewidth=2,
        label=f'{TARGET_16_67MS} ms frame budget',
    )
    ax.axhline(
        y=TARGET_30MS,
        color=TARGET_MAX_COLOR,
        linestyle=':',
        linewidth=2,
        label=f'{TARGET_30MS} ms target',
    )
    ax.set_xticks(p95.index)
    ax.set_ylim(bottom=0)
    ax.set_title('E2E p95 Frame Latency by I/O Count', pad=20, fontsize=12, fontweight='bold')
    ax.set_xlabel('Number of Inputs / Outputs', fontsize=10, labelpad=10)
    ax.set_ylabel('95th-percentile frame latency (ms)', fontsize=10, labelpad=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    fig.tight_layout()

    for ext in ['svg', 'pdf']:
        fig.savefig(output_path.with_suffix(f'.{ext}'), bbox_inches='tight', dpi=300)

    plt.close(fig)


def load_csv_to_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load CSV file to DataFrame."""
    try:
        data = pd.read_csv(csv_path)
        if 'latency_ms' in data.columns:
            data['latency_ms'] = pd.to_numeric(data['latency_ms'], errors='coerce')
            negative_count = int((data['latency_ms'] < 0).sum())
            if negative_count:
                print(
                    f"Rejecting corrupted latency results from {csv_path}: "
                    f"{negative_count} negative rows"
                )
                return pd.DataFrame()

            valid = data['latency_ms'].notna()
            if 'is_drop' in data.columns:
                valid &= data['is_drop'] != 1
            invalid_count = int((~valid).sum())
            if invalid_count:
                print(f"Ignoring {invalid_count} invalid/drop latency rows from {csv_path}")
            data = data[valid].copy()
        return data
    except Exception:
        return pd.DataFrame()


def load_all_results_for_test(test_dir: Path) -> pd.DataFrame:
    """
    Load all results CSV files from a test directory.
    
    For E2E and layer tests with config subdirectories (e2e/1/, e2e/10/, etc.):
    loads all results.csv from subdirectories and combines them.
    
    For tests with single results.csv: loads that directly.
    
    Args:
        test_dir: Directory containing results.csv files
        
    Returns:
        Combined DataFrame with all results
    """
    all_data = []
    
    # First, try to load results.csv directly from test_dir
    results_path = test_dir / "results.csv"
    if results_path.exists():
        df = load_csv_to_dataframe(results_path)
        if not df.empty:
            # Add config information from directory name if not present
            if 'config_inputs' not in df.columns and 'config_items' not in df.columns:
                # Try to extract config from directory structure
                if test_dir.name.isdigit():
                    df['config_inputs'] = int(test_dir.name)
            all_data.append(df)
    
    # Also check for config subdirectories (for E2E and layer tests)
    for config_dir in test_dir.iterdir():
        if config_dir.is_dir() and config_dir.name.isdigit():
            config_results_path = config_dir / "results.csv"
            if config_results_path.exists():
                df = load_csv_to_dataframe(config_results_path)
                if not df.empty:
                    # Add config if not already present
                    if 'config_inputs' not in df.columns and 'config_items' not in df.columns:
                        df['config_inputs'] = int(config_dir.name)
                    all_data.append(df)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


def generate_plots_for_test_type(test_dir: Path, test_type: str, layer_name: str = None):
    """
    Generate all plots for a specific test type directory.
    
    Args:
        test_dir: Directory containing test results
        test_type: Type of test ('e2e', 'layer', 'module')
        layer_name: Name of layer (for layer tests)
    """
    plots_dir = test_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    
    # Load all results
    data = load_all_results_for_test(test_dir)
    
    if data.empty or len(data) == 0:
        print(f"No data found for {test_dir}")
        return
    
    # Determine color based on layer or test type
    color = None
    if layer_name:
        color = LAYER_COLORS.get(layer_name)
    elif test_type in LAYER_COLORS:
        color = LAYER_COLORS.get(test_type)
    
    # Determine base title based on layer or test type
    if layer_name:
        base_title = f"{layer_name.capitalize()} Layer"
    elif test_type == "e2e":
        base_title = "E2E"
    elif test_type == "module":
        # Extract module and function from path
        parts = test_dir.relative_to(test_dir.parent.parent.parent).parts
        if len(parts) >= 2:
            base_title = f"{parts[0]}.{parts[1]}"
        else:
            base_title = "Module"
    else:
        base_title = "Test"

    x_label = 'Number of Inputs / Outputs' if test_type == 'e2e' else 'Workload Size'
    
    # Generate boxplot
    boxplot_title = f"{base_title} Latency Distribution by Configuration"
    generate_boxplot(data, boxplot_title, plots_dir / "boxplot", color, x_label)
    
    # Generate scaling plot
    scaling_title = f"{base_title} Latency vs Input Count"
    generate_scaling_plot(
        data,
        scaling_title,
        plots_dir / "scaling",
        color,
        x_label,
        show_p95=(test_type == 'e2e'),
    )
    
    # Generate histogram for E2E tests (optional)
    if test_type == "e2e" and len(data) > 100:
        histogram_title = f"{base_title} Latency Distribution Histogram"
        generate_histogram(data, histogram_title, plots_dir / "histogram", color)
        ecdf_title = f"{base_title} Frame-Completion Latency Distribution"
        generate_ecdf(data, ecdf_title, plots_dir / "ecdf")
        generate_p95_requirement_plot(data, plots_dir / "p95_latency")
    
    print(f"Generated plots for {test_dir}")


def generate_plots_for_layer_test(layer_dir: Path):
    """
    Generate plots for a per-layer test directory.
    
    Args:
        layer_dir: Directory containing layer-specific test results
    """
    layer_name = layer_dir.name
    
    # Load all results using the common function
    data = load_all_results_for_test(layer_dir)
    
    if data.empty:
        print(f"No data found for layer {layer_name}")
        return
    
    # Create plots directory
    plots_dir = layer_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    
    color = LAYER_COLORS.get(layer_name)
    base_title = f"{layer_name.capitalize()} Layer"
    x_labels = {
        'input': 'Number of Input Axes / Published Messages per Frame',
        'router': 'Number of Routed Messages per Frame',
        'fixture': 'Number of Fixtures / DMX Outputs per Frame',
        'output': 'Number of Output Universes per Frame',
        'full': 'Number of Inputs / Outputs',
    }
    x_label = x_labels.get(layer_name, 'Workload Size')
    
    # Generate boxplot
    boxplot_title = f"{base_title} Latency Distribution by Configuration"
    generate_boxplot(data, boxplot_title, plots_dir / "boxplot", color, x_label)
    
    # Generate scaling plot
    scaling_title = f"{base_title} Latency vs Input Count"
    generate_scaling_plot(data, scaling_title, plots_dir / "scaling", color, x_label)
    
    print(f"Generated plots for layer {layer_name}")


def generate_combined_layer_plot(layer_dir: Path):
    """Plot each layer's median latency and their summed median by config."""
    layer_names = ["input", "router", "fixture", "output"]
    median_series = {}

    for layer_name in layer_names:
        data = load_all_results_for_test(layer_dir / layer_name)
        if data.empty:
            continue
        median_series[layer_name] = data.groupby('config_inputs')['latency_ms'].median()

    if not median_series:
        print(f"No layer data found for combined plot in {layer_dir}")
        return

    medians = pd.DataFrame(median_series).sort_index()
    complete = medians.dropna(subset=layer_names) if all(
        name in medians.columns for name in layer_names
    ) else pd.DataFrame()

    plots_dir = layer_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    fig, ax = plt.subplots()

    for layer_name in layer_names:
        if layer_name not in medians:
            continue
        ax.plot(
            medians.index,
            medians[layer_name],
            '-o',
            color=LAYER_COLORS[layer_name],
            linewidth=2,
            markersize=6,
            label=f"{layer_name.capitalize()} median",
        )

    if not complete.empty:
        combined = complete[layer_names].sum(axis=1)
        ax.plot(
            combined.index,
            combined,
            '-o',
            color=LAYER_COLORS['full'],
            linewidth=3,
            markersize=7,
            label='Combined (sum of layer medians)',
        )

    ax.axhline(y=TARGET_30MS, color=TARGET_MAX_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_30MS}ms Target (Max)')
    ax.axhline(y=TARGET_16_67MS, color=FRAME_BUDGET_COLOR, linestyle=':', linewidth=2, label=f'{TARGET_16_67MS}ms (Frame Budget)')
    ax.set_title('Individual and Combined Layer Latency', pad=20, fontsize=12, fontweight='bold')
    ax.set_xlabel('Workload Size (Items per Frame)', fontsize=10, labelpad=10)
    ax.set_ylabel('Median Latency (ms)', fontsize=10, labelpad=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    fig.tight_layout()

    for ext in ['svg', 'pdf']:
        fig.savefig(plots_dir / f"combined_latency.{ext}", bbox_inches='tight', dpi=300)

    plt.close(fig)
    print(f"Generated combined layer plot in {plots_dir}")


def generate_plots_for_module_test(module_dir: Path):
    """
    Generate plots for a module test directory.
    
    Args:
        module_dir: Directory containing module-specific test results
    """
    # Module tests are organized as module/layers/function/
    # Load all results from function subdirectories
    all_data = []
    
    for function_dir in module_dir.iterdir():
        if function_dir.is_dir():
            # Load results from this function directory (which may have config subdirs)
            df = load_all_results_for_test(function_dir)
            if not df.empty:
                # Add function name
                df['function'] = function_dir.name
                all_data.append(df)
    
    if not all_data:
        print(f"No data found for module {module_dir.name}")
        return
    
    combined_data = pd.concat(all_data, ignore_index=True)
    
    # Determine module name and color
    module_name = module_dir.name
    color = LAYER_COLORS.get(module_name)
    
    # Create plots directory
    plots_dir = module_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    
    base_title = f"{module_name.capitalize()} Module"
    
    # Generate boxplot
    boxplot_title = f"{base_title} Latency Distribution by Configuration"
    generate_boxplot(combined_data, boxplot_title, plots_dir / "boxplot", color, 'Number of Items')
    
    # Generate scaling plot
    scaling_title = f"{base_title} Latency vs Input Count"
    generate_scaling_plot(combined_data, scaling_title, plots_dir / "scaling", color, 'Number of Items')
    
    print(f"Generated plots for module {module_name}")


def generate_all_plots(results_dir: Path):
    """
    Generate all plots for a complete test run.
    
    Walks through the results directory structure and generates
    plots for each test type (e2e, layer, module).
    
    Args:
        results_dir: Root results directory (e.g., results/YYYYMMDD_HHMMSS)
    """
    if not results_dir.exists():
        print(f"Results directory {results_dir} does not exist")
        return
    
    print(f"Generating plots for {results_dir}")
    
    # Process E2E tests
    e2e_dir = results_dir / "e2e"
    if e2e_dir.exists():
        generate_plots_for_test_type(e2e_dir, "e2e")
    
    # Process per-layer tests
    layer_dir = results_dir / "layer"
    if layer_dir.exists():
        for layer_name in ["input", "router", "fixture", "output", "full"]:
            layer_subdir = layer_dir / layer_name
            if layer_subdir.is_dir():
                generate_plots_for_layer_test(layer_subdir)
        generate_combined_layer_plot(layer_dir)
    
    # Process module tests
    module_dir = results_dir / "module"
    if module_dir.exists():
        for module_subdir in module_dir.iterdir():
            if module_subdir.is_dir():
                generate_plots_for_module_test(module_subdir)
    
    print(f"All plots generated for {results_dir}")


def collect_results_for_comparison(results_dir: Path) -> dict:
    """
    Collect all results from a test run for cross-test comparison.
    
    Args:
        results_dir: Root results directory
        
    Returns:
        Dictionary with collected data per test type
    """
    results = {}
    
    # Collect E2E results
    e2e_dir = results_dir / "e2e"
    if e2e_dir.exists():
        results["e2e"] = load_all_results_for_test(e2e_dir)
    
    # Collect layer results
    layer_dir = results_dir / "layer"
    if layer_dir.exists():
        results["layer"] = {}
        for layer_subdir in layer_dir.iterdir():
            if layer_subdir.is_dir():
                layer_name = layer_subdir.name
                results["layer"][layer_name] = load_all_results_for_test(layer_subdir)
    
    # Collect module results
    module_dir = results_dir / "module"
    if module_dir.exists():
        results["module"] = {}
        for module_subdir in module_dir.iterdir():
            if module_subdir.is_dir():
                module_name = module_subdir.name
                results["module"][module_name] = {}
                for function_dir in module_subdir.iterdir():
                    if function_dir.is_dir():
                        function_name = function_dir.name
                        results["module"][module_name][function_name] = \
                            load_all_results_for_test(function_dir)
    
    return results


if __name__ == "__main__":
    # Allow running this script directly
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate plots from performance test results')
    parser.add_argument('--results-dir', type=str, required=True, 
                        help='Path to results directory (e.g., results/YYYYMMDD_HHMMSS)')
    parser.add_argument('--test-type', type=str, default='all',
                        choices=['all', 'e2e', 'layer', 'module'],
                        help='Specific test type to process (default: all)')
    
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    
    if args.test_type == 'all':
        generate_all_plots(results_dir)
    elif args.test_type == 'e2e':
        e2e_dir = results_dir / "e2e"
        if e2e_dir.exists():
            generate_plots_for_test_type(e2e_dir, "e2e")
    elif args.test_type == 'layer':
        layer_dir = results_dir / "layer"
        if layer_dir.exists():
            for layer_name in ["input", "router", "fixture", "output", "full"]:
                layer_subdir = layer_dir / layer_name
                if layer_subdir.is_dir():
                    generate_plots_for_layer_test(layer_subdir)
            generate_combined_layer_plot(layer_dir)
    elif args.test_type == 'module':
        module_dir = results_dir / "module"
        if module_dir.exists():
            for module_subdir in module_dir.iterdir():
                if module_subdir.is_dir():
                    generate_plots_for_module_test(module_subdir)
