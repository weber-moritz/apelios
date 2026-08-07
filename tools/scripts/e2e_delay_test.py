#!/usr/bin/env python3
"""End-to-End Latency Test for Apelios.

Measures latency from input events (FakeAdapter) to output messages (output.* topics)
across various scaling configurations. Generates CSV data and optionally Matplotlib plots.

Usage:
    python scripts/e2e_delay_test.py --output-dir results/
    python scripts/e2e_delay_test.py --output-dir results/ --plot
    python scripts/e2e_delay_test.py --inputs 100 --outputs 100 --duration 10 --plot

This script uses MemoryBroker to avoid NATS server dependency.
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.input.adapters.fake_adapter import FakeAdapter
from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.router.router_runtime_manager import RouterRuntimeManager
from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
from apelios.output.output_runtime_manager import OutputRuntimeManager


logger = logging.getLogger(__name__)


@dataclass
class LatencyRecord:
    """Single latency measurement record."""
    test_id: str
    timestamp: float
    config_inputs: int
    config_outputs: int
    input_device: str
    input_axis: str
    input_type: str
    frame_number: int
    latency_ms: float
    is_drop: int


@dataclass
class TestConfiguration:
    """Test configuration parameters."""
    inputs: int = 1
    outputs: int = 1
    duration: float = 10.0  # seconds
    warmup: float = 1.0  # seconds
    frame_timeout: float = 0.05  # 50ms timeout for frame drop detection


@dataclass
class TestResult:
    """Aggregated results for one configuration."""
    config: TestConfiguration
    records: list[LatencyRecord] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


class OutputMessageTracker:
    """Tracks output messages and matches them to input events."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.pending_inputs: dict[str, dict] = {}  # input_key -> input_data
        self.received_outputs: list[tuple[float, float, float]] = []  # (timestamp, universe, address)
        self.completed_records: list[LatencyRecord] = []
        self.drop_timeout = config.frame_timeout
        self.frame_counter = 0
        self.test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.input_timestamp_map: dict[str, float] = {}  # source -> timestamp
        
    def add_input(self, source: str, timestamp: float, device: str, axis: str, input_type: str) -> None:
        """Register an input event."""
        self.frame_counter += 1
        input_key = f"{source}_{self.frame_counter}"
        self.pending_inputs[input_key] = {
            "timestamp": timestamp,
            "source": source,
            "device": device,
            "axis": axis,
            "type": input_type,
            "frame": self.frame_counter
        }
        # Also store the latest timestamp for this source
        self.input_timestamp_map[source] = timestamp
        
    def add_output(self, universe: int, address: int, timestamp: float) -> None:
        """Register an output event."""
        self.received_outputs.append((timestamp, universe, address))
        
    def process_matches(self) -> None:
        """Match outputs to inputs and create records."""
        current_time = time.perf_counter()
        
        # Process outputs in order
        for output_ts, universe, address in list(self.received_outputs):
            self.received_outputs.remove((output_ts, universe, address))
            
            # Find the oldest pending input
            if self.pending_inputs:
                oldest_key = min(self.pending_inputs.keys(), 
                                key=lambda k: self.pending_inputs[k]["timestamp"])
                input_data = self.pending_inputs[oldest_key]
                
                latency = (output_ts - input_data["timestamp"]) * 1000  # ms
                
                record = LatencyRecord(
                    test_id=self.test_id,
                    timestamp=input_data["timestamp"],
                    config_inputs=self.config.inputs,
                    config_outputs=self.config.outputs,
                    input_device=input_data["device"],
                    input_axis=input_data["axis"],
                    input_type=input_data["type"],
                    frame_number=input_data["frame"],
                    latency_ms=max(0, latency),
                    is_drop=0
                )
                self.completed_records.append(record)
                del self.pending_inputs[oldest_key]
        
        # Mark timed-out inputs as drops
        drops = []
        for input_key, input_data in self.pending_inputs.items():
            if current_time - input_data["timestamp"] > self.drop_timeout:
                record = LatencyRecord(
                    test_id=self.test_id,
                    timestamp=input_data["timestamp"],
                    config_inputs=self.config.inputs,
                    config_outputs=self.config.outputs,
                    input_device=input_data["device"],
                    input_axis=input_data["axis"],
                    input_type=input_data["type"],
                    frame_number=input_data["frame"],
                    latency_ms=0.0,
                    is_drop=1
                )
                self.completed_records.append(record)
                drops.append(input_key)
        
        for key in drops:
            self.pending_inputs.pop(key, None)
    
    def get_records(self) -> list[LatencyRecord]:
        """Get all completed records."""
        return self.completed_records


class MemoryBrokerClient:
    """Simple in-memory broker client for testing without NATS."""
    
    def __init__(self):
        self._subscriptions: dict[str, list] = {}
        self._connected = False
        self._output_callback = None
        
    async def connect(self) -> None:
        self._connected = True
        
    async def disconnect(self) -> None:
        self._connected = False
        self._subscriptions.clear()
        
    async def publish(self, subject: str, message: bytes) -> None:
        if not self._connected:
            raise RuntimeError("Client not connected")
        
        # Notify subscribers
        for subj_pattern, callbacks in self._subscriptions.items():
            # Check for exact match or wildcard match
            if subj_pattern == subject or (subj_pattern.endswith(">") and subject.startswith(subj_pattern[:-1])):
                for callback in callbacks:
                    class MockMsg:
                        def __init__(self, subj, data):
                            self.subject = subj
                            self.data = data
                    msg = MockMsg(subject, message)
                    # Handle both sync and async callbacks
                    result = callback(msg)
                    if asyncio.iscoroutine(result):
                        await result
        
        # Track output messages for latency measurement
        if subject.startswith("output."):
            try:
                data = json.loads(message.decode('utf-8'))
                universe = data.get('universe', 0)
                address = data.get('address', 0)
                # Extract timestamp from message or use current time
                timestamp = data.get('timestamp', time.perf_counter())
                if self._output_callback:
                    self._output_callback(universe, address, timestamp)
            except Exception:
                pass
        
    async def subscribe(self, subject: str, callback) -> None:
        if subject not in self._subscriptions:
            self._subscriptions[subject] = []
        self._subscriptions[subject].append(callback)
        
    def set_output_callback(self, callback):
        """Set callback for output messages (for latency tracking)."""
        self._output_callback = callback


class EnhancedFakeAdapter(FakeAdapter):
    """Enhanced FakeAdapter with configurable axis types for testing."""
    
    def __init__(self, device: str, axis_types: dict[str, str]):
        super().__init__(device=device, axis_types=axis_types)
        self._event_counter = 0
        
    async def poll_once(self, dt: float = 0.016) -> None:
        """Generate fake input values."""
        self._event_counter += 1
        
        # Generate values for all configured axes
        for axis, axis_type in self._axis_types.items():
            if axis_type == "absolute_uni":
                value = (self._event_counter % 100) / 100.0
            elif axis_type == "absolute_bi":
                value = ((self._event_counter % 200) - 100) / 100.0
            elif axis_type == "delta":
                value = 0.1 if self._event_counter % 3 == 0 else 0.0
            elif axis_type == "rate":
                value = 0.5 if self._event_counter % 2 == 0 else -0.5
            else:
                value = 0.5
                
            self.snapshot[axis] = value


class E2EDelayTest:
    """Main test class for end-to-end latency measurement."""
    
    # Standard scaling configurations
    # Tests with finer granularity to identify the exact scaling limit
    SCALING_CONFIGS = [
        {"inputs": 1, "outputs": 1, "name": "Baseline"},
        {"inputs": 10, "outputs": 10, "name": "Small Load"},
        {"inputs": 20, "outputs": 20, "name": "Load 20"},
        {"inputs": 30, "outputs": 30, "name": "Load 30"},
        {"inputs": 40, "outputs": 40, "name": "Load 40"},
        {"inputs": 50, "outputs": 50, "name": "Medium Load"},
        {"inputs": 60, "outputs": 60, "name": "Load 60"},
        {"inputs": 70, "outputs": 70, "name": "Load 70"},
        {"inputs": 80, "outputs": 80, "name": "Load 80"},
        {"inputs": 90, "outputs": 90, "name": "Load 90"},
        {"inputs": 100, "outputs": 100, "name": "Large Load"},
        {"inputs": 150, "outputs": 150, "name": "Load 150"},
        {"inputs": 200, "outputs": 200, "name": "Stress Test"},
    ]
    
    # Input type distribution (1/3 each)
    INPUT_TYPES = ["absolute_uni", "delta", "rate"]
    
    def __init__(self, args):
        self.args = args
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._generate_plots_flag = args.plot
        self.test_configs = []
        
        # Use specific config if provided, otherwise use all standard configs
        if args.inputs is not None and args.outputs is not None:
            self.test_configs.append(TestConfiguration(
                inputs=args.inputs,
                outputs=args.outputs,
                duration=args.duration,
                warmup=args.warmup or 1.0,
                frame_timeout=args.frame_timeout or 0.05
            ))
        else:
            for config_dict in self.SCALING_CONFIGS:
                self.test_configs.append(TestConfiguration(
                    inputs=config_dict["inputs"],
                    outputs=config_dict["outputs"],
                    duration=args.duration,
                    warmup=args.warmup or 1.0,
                    frame_timeout=args.frame_timeout or 0.05
                ))
        
        self.all_records: list[LatencyRecord] = []
        self.test_results: list[TestResult] = []
        
    def _create_input_type_for_axis(self, index: int) -> str:
        """Distribute input types evenly (1/3 each)."""
        return self.INPUT_TYPES[index % len(self.INPUT_TYPES)]
    
    async def _run_test(self, config: TestConfiguration) -> TestResult:
        """Run the latency test for a specific configuration."""
        logger.info(f"Starting test for {config.inputs} inputs, {config.outputs} outputs (1 axis per adapter)")
        
        # Setup tracking
        tracker = OutputMessageTracker(config)
        
        # Create memory broker client with output callback
        broker_client = MemoryBrokerClient()
        broker_client.set_output_callback(tracker.add_output)
        
        # Create runtime managers
        input_manager = InputRuntimeManager(broker_client=broker_client)
        router_manager = RouterRuntimeManager(broker_client=broker_client)
        fixture_manager = FixtureRuntimeManager(broker_client=broker_client)
        output_manager = OutputRuntimeManager(broker_client=broker_client)
        
        # Create and register FakeAdapters
        # Each adapter has 1 axis to match the configuration count
        adapters = []
        for i in range(config.inputs):
            device_name = f"fake_{i}"
            axis_name = "value"
            axis_type = self._create_input_type_for_axis(i)
            axis_types = {axis_name: axis_type}
            
            adapter = EnhancedFakeAdapter(
                device=device_name,
                axis_types=axis_types
            )
            adapters.append(adapter)
            input_manager.register_adapter(adapter)
        
        # Start the system
        logger.info("Starting runtime managers...")
        
        # For memory broker, we don't need to start a server
        # Just initialize the managers
        await input_manager.start()
        await input_manager.start_registered_adapters()
        await router_manager.start()
        await fixture_manager.start()
        await output_manager.start()
        
        logger.info("System started, beginning warm-up...")
        
        # Warm-up period
        warmup_start = time.perf_counter()
        while time.perf_counter() - warmup_start < config.warmup:
            await asyncio.sleep(0.1)
        
        logger.info("Warm-up complete, starting measurement...")
        
        # Reset tracker for actual measurement
        tracker = OutputMessageTracker(config)
        broker_client.set_output_callback(tracker.add_output)
        
        # Run the test
        target_interval = 1.0 / 60.0
        frames_to_run = int(config.duration * 60)
        frame_count = 0
        
        test_start = time.perf_counter()
        
        while frame_count < frames_to_run:
            loop_start = time.perf_counter()
            
            # Record input timestamps before processing
            current_time = time.perf_counter()
            for adapter in adapters:
                for axis in adapter._axis_types.keys():
                    input_type = adapter.get_axis_type(axis)
                    tracker.add_input(
                        source=f"{adapter.device}.{axis}",
                        timestamp=current_time,
                        device=adapter.device,
                        axis=axis,
                        input_type=input_type
                    )
            
            # Tick all managers
            await input_manager.tick(dt=target_interval)
            await router_manager.tick(dt=target_interval)
            await fixture_manager.tick(dt=target_interval)
            await output_manager.tick(dt=target_interval)
            
            # Process any matches
            tracker.process_matches()
            
            frame_count += 1
            
            # Sleep to maintain 60Hz
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                logger.debug(f"Dropped frame in test loop: took {elapsed:.4f}s")
        
        # Process any remaining matches
        tracker.process_matches()
        
        test_end = time.perf_counter()
        logger.info(f"Completed {frame_count} frames in {test_end - test_start:.2f}s")
        
        # Cleanup
        logger.info("Stopping runtime managers...")
        await input_manager.stop_registered_adapters()
        await input_manager.stop()
        await router_manager.stop()
        await fixture_manager.stop()
        await output_manager.stop()
        await broker_client.disconnect()
        
        # Create result
        result = TestResult(config=config, records=tracker.get_records())
        result.statistics = self._calculate_statistics(result.records)
        
        logger.info(f"Test complete: {result.statistics}")
        return result
    
    def _calculate_statistics(self, records: list[LatencyRecord]) -> dict[str, Any]:
        """Calculate statistics from latency records."""
        if not records:
            return {
                "count": 0,
                "total_events": 0,
                "min_ms": 0,
                "max_ms": 0,
                "mean_ms": 0,
                "median_ms": 0,
                "std_dev_ms": 0,
                "drops": 0,
                "drop_rate": 0
            }
        
        latencies = [r.latency_ms for r in records if r.is_drop == 0]
        drops = [r for r in records if r.is_drop == 1]
        total = len(records)
        
        if latencies:
            latencies_sorted = sorted(latencies)
            count = len(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
            mean_lat = sum(latencies) / count
            
            # Median
            mid = count // 2
            if count % 2 == 0:
                median_lat = (latencies_sorted[mid - 1] + latencies_sorted[mid]) / 2
            else:
                median_lat = latencies_sorted[mid]
            
            # Standard deviation
            if count > 1:
                variance = sum((x - mean_lat) ** 2 for x in latencies) / (count - 1)
                std_dev = variance ** 0.5
            else:
                std_dev = 0
        else:
            count = 0
            min_lat = 0
            max_lat = 0
            mean_lat = 0
            median_lat = 0
            std_dev = 0
        
        return {
            "count": count,
            "total_events": total,
            "min_ms": min_lat,
            "max_ms": max_lat,
            "mean_ms": mean_lat,
            "median_ms": median_lat,
            "std_dev_ms": std_dev,
            "drops": len(drops),
            "drop_rate": len(drops) / total if total > 0 else 0
        }
    
    async def run_all_tests(self) -> None:
        """Run all configured tests."""
        logger.info(f"Starting e2e delay tests with {len(self.test_configs)} configurations")
        
        for config in self.test_configs:
            logger.info(f"\n=== Testing {config.inputs} inputs / {config.outputs} outputs ===")
            result = await self._run_test(config)
            self.test_results.append(result)
            self.all_records.extend(result.records)
            
            logger.info(f"Results: {result.statistics}")
        
        logger.info(f"\nAll tests completed. Total records: {len(self.all_records)}")
    
    def save_csv(self) -> Path:
        """Save all records to CSV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self.output_dir / f"e2e_delay_results_{timestamp}.csv"
        
        fieldnames = [
            "test_id", "timestamp", "config_inputs", "config_outputs",
            "input_device", "input_axis", "input_type", "frame_number",
            "latency_ms", "is_drop"
        ]
        
        with csv_path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in self.all_records:
                row = {
                    "test_id": record.test_id,
                    "timestamp": f"{record.timestamp:.6f}",
                    "config_inputs": record.config_inputs,
                    "config_outputs": record.config_outputs,
                    "input_device": record.input_device,
                    "input_axis": record.input_axis,
                    "input_type": record.input_type,
                    "frame_number": record.frame_number,
                    "latency_ms": f"{record.latency_ms:.3f}",
                    "is_drop": record.is_drop
                }
                writer.writerow(row)
        
        logger.info(f"CSV saved to: {csv_path}")
        return csv_path
    
    def save_statistics(self) -> Path:
        """Save aggregated statistics to a separate CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stats_path = self.output_dir / f"e2e_delay_statistics_{timestamp}.csv"
        
        fieldnames = [
            "config_inputs", "config_outputs", "count", "total_events",
            "min_ms", "max_ms", "mean_ms", "median_ms", "std_dev_ms",
            "drops", "drop_rate"
        ]
        
        with stats_path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.test_results:
                row = {
                    "config_inputs": result.config.inputs,
                    "config_outputs": result.config.outputs,
                    **result.statistics
                }
                writer.writerow(row)
        
        logger.info(f"Statistics saved to: {stats_path}")
        return stats_path
    
    def generate_plots(self) -> list[Path]:
        """Generate Matplotlib plots from the collected data."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError as e:
            logger.error(f"Matplotlib or Seaborn not available: {e}")
            return []
        
        generated_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = [12, 8]
        plt.rcParams['font.size'] = 12
        
        # 1. Boxplot per Configuration
        if len(self.test_results) > 0:
            fig, ax = plt.subplots()
            
            data_to_plot = []
            labels = []
            
            for result in self.test_results:
                latencies = [r.latency_ms for r in result.records if r.is_drop == 0]
                if latencies:
                    data_to_plot.append(latencies)
                    labels.append(f"{result.config.inputs}/{result.config.outputs}")
            
            if data_to_plot:
                ax.boxplot(data_to_plot, tick_labels=labels)
                ax.set_title('Latency Distribution by Configuration')
                ax.set_xlabel('Configuration (Inputs/Outputs)')
                ax.set_ylabel('Latency (ms)')
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, alpha=0.3)
                
                for ext in ['svg', 'pdf']:
                    filepath = self.output_dir / f"e2e_latency_boxplot_{timestamp}.{ext}"
                    fig.savefig(filepath, bbox_inches='tight', dpi=300)
                    generated_files.append(filepath)
                
                plt.close(fig)
        
        # 2. Line Plot: Latency vs Scaling
        if len(self.test_results) > 0:
            fig, ax = plt.subplots()
            
            x_values = [r.config.inputs for r in self.test_results]
            y_median = [r.statistics['median_ms'] for r in self.test_results]
            y_std = [r.statistics['std_dev_ms'] for r in self.test_results]
            y_mean = [r.statistics['mean_ms'] for r in self.test_results]
            
            ax.errorbar(x_values, y_median, yerr=y_std, 
                       fmt='-o', capsize=5, label='Median +/- Std Dev')
            ax.plot(x_values, y_mean, '--s', label='Mean')
            
            # Add target line
            ax.axhline(y=30, color='r', linestyle=':', label='Target (<30ms)')
            ax.axhline(y=16.67, color='g', linestyle=':', label='Frame Time (16.67ms)')
            
            ax.set_xscale('log')
            ax.set_title('Latency vs Scaling')
            ax.set_xlabel('Number of Inputs/Outputs (log scale)')
            ax.set_ylabel('Latency (ms)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Annotate each point
            for i, result in enumerate(self.test_results):
                ax.annotate(f"{result.config.inputs}/{result.config.outputs}",
                           (x_values[i], y_median[i]),
                           textcoords="offset points", xytext=(0,10), ha='center')
            
            for ext in ['svg', 'pdf']:
                filepath = self.output_dir / f"e2e_latency_scaling_{timestamp}.{ext}"
                fig.savefig(filepath, bbox_inches='tight', dpi=300)
                generated_files.append(filepath)
            
            plt.close(fig)
        
        # 3. Histogram
        if len(self.all_records) > 0:
            fig, ax = plt.subplots()
            
            latencies = [r.latency_ms for r in self.all_records if r.is_drop == 0]
            if latencies:
                ax.hist(latencies, bins=50, alpha=0.7, edgecolor='black')
                ax.set_title('Latency Distribution Histogram')
                ax.set_xlabel('Latency (ms)')
                ax.set_ylabel('Frequency')
                ax.grid(True, alpha=0.3)
                
                for ext in ['svg', 'pdf']:
                    filepath = self.output_dir / f"e2e_latency_histogram_{timestamp}.{ext}"
                    fig.savefig(filepath, bbox_inches='tight', dpi=300)
                    generated_files.append(filepath)
                
                plt.close(fig)
        
        # 4. Violin Plot
        if len(self.test_results) > 0:
            fig, ax = plt.subplots()
            
            data_to_plot = []
            labels = []
            
            for result in self.test_results:
                latencies = [r.latency_ms for r in result.records if r.is_drop == 0]
                if latencies:
                    data_to_plot.append(latencies)
                    labels.append(f"{result.config.inputs}/{result.config.outputs}")
            
            if data_to_plot:
                positions = list(range(1, len(data_to_plot) + 1))
                ax.violinplot(data_to_plot, positions=positions, showmeans=True, showmedians=True)
                ax.set_title('Latency Distribution Violin Plot')
                ax.set_xlabel('Configuration (Inputs/Outputs)')
                ax.set_ylabel('Latency (ms)')
                ax.set_xticks(positions)
                ax.set_xticklabels(labels)
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, alpha=0.3)
                
                for ext in ['svg', 'pdf']:
                    filepath = self.output_dir / f"e2e_latency_violin_{timestamp}.{ext}"
                    fig.savefig(filepath, bbox_inches='tight', dpi=300)
                    generated_files.append(filepath)
                
                plt.close(fig)
        
        logger.info(f"Generated {len(generated_files)} plot files")
        return generated_files
    
    def print_summary(self) -> None:
        """Print a summary of test results to console."""
        print("\n" + "=" * 80)
        print("E2E LATENCY TEST SUMMARY")
        print("=" * 80)
        
        for result in self.test_results:
            stats = result.statistics
            config = result.config
            
            assessment = "[OK] Optimal"
            if stats["median_ms"] > 30:
                assessment = "[FAIL] Overloaded"
            elif stats["median_ms"] > 15:
                assessment = "[WARNING] Boundary"
            
            print(f"\n{config.inputs}/{config.outputs}:")
            print(f"  Median: {stats['median_ms']:.2f}ms, Max: {stats['max_ms']:.2f}ms")
            print(f"  Mean: {stats['mean_ms']:.2f}ms +/- {stats['std_dev_ms']:.2f}ms")
            print(f"  Frame Drops: {stats['drops']} ({stats['drop_rate']*100:.1f}%)")
            print(f"  Assessment: {assessment}")
        
        print("\n" + "=" * 80)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='End-to-End Latency Test for Apelios',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python scripts/e2e_delay_test.py --output-dir results/
  python scripts/e2e_delay_test.py --output-dir results/ --plot
  python scripts/e2e_delay_test.py --inputs 100 --outputs 100 --duration 10 --plot
        """
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='results',
        help='Directory to save CSV and plot files (default: results)'
    )
    
    parser.add_argument(
        '--plot',
        action='store_true',
        help='Generate Matplotlib plots (requires matplotlib and seaborn)'
    )
    
    parser.add_argument(
        '--inputs',
        type=int,
        default=None,
        help='Number of input adapters (overrides standard configurations)'
    )
    
    parser.add_argument(
        '--outputs',
        type=int,
        default=None,
        help='Number of outputs (overrides standard configurations)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=10.0,
        help='Test duration in seconds (default: 10)'
    )
    
    parser.add_argument(
        '--warmup',
        type=float,
        default=1.0,
        help='Warm-up duration in seconds (default: 1)'
    )
    
    parser.add_argument(
        '--frame-timeout',
        type=float,
        default=0.05,
        help='Timeout for frame drop detection in seconds (default: 0.05)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    # Create and run test
    test = E2EDelayTest(args)
    await test.run_all_tests()
    
    # Save results
    csv_path = test.save_csv()
    stats_path = test.save_statistics()
    
    # Generate plots if requested
    if args.plot:
        test.generate_plots()
    
    # Print summary
    test.print_summary()
    
    logger.info(f"Test complete. Results saved to: {csv_path}")
    if args.plot:
        logger.info("Plots generated in SVG and PDF formats")


if __name__ == "__main__":
    asyncio.run(main())
