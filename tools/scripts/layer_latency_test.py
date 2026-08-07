#!/usr/bin/env python3
"""Per-Layer Latency Test for Apelios.

Measures latency for each processing layer independently:
- Router Layer: input.* -> target.*
- Fixture Layer: target.* -> output.*
- Output Layer: output.* -> ArtNet transmission
- Full Pipeline: input.* -> output.* (e2e reference)

Usage:
    python scripts/layer_latency_test.py --output-dir results/
    python scripts/layer_latency_test.py --layer fixture --output-dir results/
    python scripts/layer_latency_test.py --layer all --output-dir results/layer/ --plot

This script uses MemoryBroker to avoid NATS server dependency.
"""

import argparse
import asyncio
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)


@dataclass
class LatencyRecord:
    """Single latency measurement record."""
    layer: str
    test_id: str
    timestamp: float
    config_inputs: int
    frame_number: int
    latency_ms: float
    is_drop: int


@dataclass
class TestConfiguration:
    """Test configuration parameters."""
    layer: str
    inputs: int = 1
    duration: float = 1.0  # seconds per test
    warmup: float = 0.5  # seconds
    frame_timeout: float = 0.05  # 50ms timeout for frame drop detection


@dataclass
class LayerTestResult:
    """Aggregated results for one layer test configuration."""
    config: TestConfiguration
    records: list[LatencyRecord] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


class LayerLatencyTracker:
    """Tracks latency for a specific layer."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.pending_inputs: dict[str, dict] = {}
        self.test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.frame_counter = 0
        self.completed_records: list[LatencyRecord] = []
        self.drop_timeout = config.frame_timeout
        
    def add_input(self, timestamp: float) -> str:
        """Register an input event. Returns input_key for matching."""
        self.frame_counter += 1
        input_key = f"{self.config.layer}_{self.frame_counter}"
        self.pending_inputs[input_key] = {
            "timestamp": timestamp,
            "frame": self.frame_counter
        }
        return input_key
        
    def add_output(self, input_key: str, timestamp: float) -> None:
        """Register an output event and match to input."""
        if input_key in self.pending_inputs:
            input_data = self.pending_inputs[input_key]
            latency = (timestamp - input_data["timestamp"]) * 1000  # ms
            
            record = LatencyRecord(
                layer=self.config.layer,
                test_id=self.test_id,
                timestamp=input_data["timestamp"],
                config_inputs=self.config.inputs,
                frame_number=input_data["frame"],
                latency_ms=max(0, latency),
                is_drop=0
            )
            self.completed_records.append(record)
            del self.pending_inputs[input_key]
            
    def mark_drop(self, input_key: str) -> None:
        """Mark an input as dropped."""
        if input_key in self.pending_inputs:
            input_data = self.pending_inputs[input_key]
            record = LatencyRecord(
                layer=self.config.layer,
                test_id=self.test_id,
                timestamp=input_data["timestamp"],
                config_inputs=self.config.inputs,
                frame_number=input_data["frame"],
                latency_ms=0.0,
                is_drop=1
            )
            self.completed_records.append(record)
            del self.pending_inputs[input_key]
            
    def process_drops(self) -> None:
        """Mark all pending inputs as drops."""
        current_time = time.perf_counter()
        drops = []
        for input_key, input_data in self.pending_inputs.items():
            if current_time - input_data["timestamp"] > self.drop_timeout:
                drops.append(input_key)
        for key in drops:
            self.mark_drop(key)
            
    def get_records(self) -> list[LatencyRecord]:
        """Get all completed records."""
        return self.completed_records


class MemoryBrokerClient:
    """Simple in-memory broker client for testing without NATS."""
    
    def __init__(self):
        self._subscriptions: dict[str, list] = {}
        self._connected = False
        
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
            if subj_pattern == subject or (subj_pattern.endswith(">") and subject.startswith(subj_pattern[:-1])):
                for callback in callbacks:
                    class MockMsg:
                        def __init__(self, subj, data):
                            self.subject = subj
                            self.data = data
                    msg = MockMsg(subject, message)
                    result = callback(msg)
                    if asyncio.iscoroutine(result):
                        await result
                        
    async def subscribe(self, subject: str, callback) -> None:
        if subject not in self._subscriptions:
            self._subscriptions[subject] = []
        self._subscriptions[subject].append(callback)


class LayerLatencyTest:
    """Main test class for per-layer latency measurement."""
    
    LAYERS = ["input", "router", "fixture", "output", "full"]
    
    # Test configurations - same as e2e test for comparison
    SCALING_CONFIGS = [
        1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200
    ]
    
    def __init__(self, args):
        self.args = args
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generate_plots_flag = args.plot
        self.verbose = args.verbose
        
        # Determine which layer(s) to test
        if args.layer == "all":
            self.layers_to_test = self.LAYERS
        else:
            self.layers_to_test = [args.layer]
            
        # Determine which input counts to test
        if args.inputs:
            self.input_counts = [int(x.strip()) for x in args.inputs.split(",")]
        else:
            self.input_counts = self.SCALING_CONFIGS
            
        self.test_results: list[LayerTestResult] = []
        self.all_records: list[LatencyRecord] = []
        
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
    
    async def _test_input_layer(self, config: TestConfiguration) -> LayerTestResult:
        """Test input layer latency: FakeAdapter polling -> input.* messages"""
        logger.info(f"  Testing input layer with {config.inputs} inputs")
        
        from apelios.input.input_runtime_manager import InputRuntimeManager
        from apelios.input.adapters.fake_adapter import FakeAdapter
        
        tracker = LayerLatencyTracker(config)
        broker_client = MemoryBrokerClient()
        await broker_client.connect()
        
        # Create and start input manager only
        input_manager = InputRuntimeManager(broker_client=broker_client)
        
        # Create FakeAdapters
        adapters = []
        for i in range(config.inputs):
            adapter = FakeAdapter(device=f"layer_test_{i}", axis_types={"value": "absolute_uni"})
            adapters.append(adapter)
            input_manager.register_adapter(adapter)
        
        await input_manager.start()
        await input_manager.start_registered_adapters()
        
        # Track input keys for matching - use a queue for FIFO matching
        pending_input_keys = []
        output_count = [0]
        
        # Subscribe to input.* messages
        async def on_input_message(msg):
            try:
                # Simple FIFO matching - each input message matches the next pending input
                if pending_input_keys:
                    input_key = pending_input_keys.pop(0)
                    tracker.add_output(input_key, time.perf_counter())
                    output_count[0] += 1
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error processing input message: {e}")
        
        await broker_client.subscribe("input.>", on_input_message)
        
        # Warm-up
        warmup_start = time.perf_counter()
        while time.perf_counter() - warmup_start < config.warmup:
            await asyncio.sleep(0.1)
        
        # Reset tracker for actual test
        tracker = LayerLatencyTracker(config)
        pending_input_keys.clear()
        output_count[0] = 0
        
        # Run test
        target_interval = 1.0 / 60.0
        frames_to_run = int(config.duration * 60)
        frame_count = 0
        
        while frame_count < frames_to_run:
            loop_start = time.perf_counter()
            
            # Record input timestamps before processing
            current_time = time.perf_counter()
            for adapter in adapters:
                input_key = tracker.add_input(current_time)
                pending_input_keys.append(input_key)
            
            # Tick input manager
            await input_manager.tick(dt=target_interval)
            
            # Process drops
            tracker.process_drops()
            
            frame_count += 1
            
            # Sleep to maintain 60Hz
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Process remaining drops
        tracker.process_drops()
        
        # Cleanup
        await input_manager.stop_registered_adapters()
        await input_manager.stop()
        await broker_client.disconnect()
        
        result = LayerTestResult(config=config, records=tracker.get_records())
        result.statistics = self._calculate_statistics(result.records)
        logger.info(f"    Input: got {output_count[0]} outputs, {len(result.records)} records")
        return result
    
    async def _test_router_layer(self, config: TestConfiguration) -> LayerTestResult:
        """Test router layer latency: input.* -> target.*"""
        logger.info(f"  Testing router layer with {config.inputs} inputs")
        
        from apelios.router.router_runtime_manager import RouterRuntimeManager
        from apelios.router.router_core import MappingRouter
        
        tracker = LayerLatencyTracker(config)
        broker_client = MemoryBrokerClient()
        await broker_client.connect()
        
        # Create router with test mappings
        # Map test input sources to test targets
        test_profile = {}
        for i in range(max(config.inputs, 200)):  # Pre-create enough mappings
            test_profile[f"layer_test.input_{i}"] = f"target.layer_test_{i}"
        
        router_core = MappingRouter(profile=test_profile)
        router_manager = RouterRuntimeManager(
            router=router_core,
            broker_client=broker_client
        )
        await router_manager.start()
        
        # Track input keys for matching - use a queue for FIFO matching
        pending_input_keys = []
        output_count = [0]
        
        # Subscribe to target.* messages
        async def on_target_message(msg):
            try:
                # Simple FIFO matching - each output matches the next pending input
                if pending_input_keys:
                    input_key = pending_input_keys.pop(0)
                    tracker.add_output(input_key, time.perf_counter())
                    output_count[0] += 1
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error processing target message: {e}")
        
        await broker_client.subscribe("target.>", on_target_message)
        
        # Warm-up
        warmup_start = time.perf_counter()
        while time.perf_counter() - warmup_start < config.warmup:
            await asyncio.sleep(0.1)
        
        # Reset tracker for actual test
        tracker = LayerLatencyTracker(config)
        pending_input_keys.clear()
        output_count[0] = 0
        
        # Run test
        target_interval = 1.0 / 60.0
        frames_to_run = int(config.duration * 60)
        frame_count = 0
        
        while frame_count < frames_to_run:
            loop_start = time.perf_counter()
            
            # Publish input messages directly
            current_time = time.perf_counter()
            for i in range(config.inputs):
                input_key = tracker.add_input(current_time)
                pending_input_keys.append(input_key)
                input_msg = {
                    "source": f"layer_test.input_{i}",
                    "value": 0.5,
                    "type": "absolute_uni",
                    "timestamp": current_time
                }
                await broker_client.publish(f"input.layer_test", json.dumps(input_msg).encode('utf-8'))
            
            # Tick router
            await router_manager.tick(dt=target_interval)
            
            # Process drops
            tracker.process_drops()
            
            frame_count += 1
            
            # Sleep to maintain 60Hz
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Process remaining drops
        tracker.process_drops()
        
        # Cleanup
        await router_manager.stop()
        await broker_client.disconnect()
        
        result = LayerTestResult(config=config, records=tracker.get_records())
        result.statistics = self._calculate_statistics(result.records)
        logger.info(f"    Router: got {output_count[0]} outputs, {len(result.records)} records")
        return result
    
    async def _test_fixture_layer(self, config: TestConfiguration) -> LayerTestResult:
        """Test fixture layer latency: target.* -> output.*"""
        logger.info(f"  Testing fixture layer with {config.inputs} inputs")
        
        from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
        
        tracker = LayerLatencyTracker(config)
        broker_client = MemoryBrokerClient()
        await broker_client.connect()
        
        # Create fixture core with test patch
        # The patch defines fixtures and their parameters
        test_patch = {
            "fixtures": {}
        }
        for i in range(max(config.inputs, 200)):
            test_patch["fixtures"][f"test_fixture_{i}"] = {
                "type": "dimmer",
                "parameters": {
                    f"param_{i}": {
                        "dmx_address": i,
                        "dmx_universe": 0
                    }
                }
            }
        
        from apelios.fixture.fixture_core import FixtureCore
        fixture_core = FixtureCore(patch=test_patch)
        fixture_manager = FixtureRuntimeManager(
            core=fixture_core,
            broker_client=broker_client
        )
        await fixture_manager.start()
        
        # Track input keys for matching - use a queue for FIFO matching
        pending_input_keys = []
        output_count = [0]
        
        # Subscribe to output.* messages
        async def on_output_message(msg):
            try:
                # Simple FIFO matching - each output matches the next pending input
                if pending_input_keys:
                    input_key = pending_input_keys.pop(0)
                    tracker.add_output(input_key, time.perf_counter())
                    output_count[0] += 1
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error processing output message: {e}")
        
        await broker_client.subscribe("output.>", on_output_message)
        
        # Warm-up
        warmup_start = time.perf_counter()
        while time.perf_counter() - warmup_start < config.warmup:
            await asyncio.sleep(0.1)
        
        # Reset tracker for actual test
        tracker = LayerLatencyTracker(config)
        pending_input_keys.clear()
        output_count[0] = 0
        
        # Run test
        target_interval = 1.0 / 60.0
        frames_to_run = int(config.duration * 60)
        frame_count = 0
        
        while frame_count < frames_to_run:
            loop_start = time.perf_counter()
            
            # Publish target messages directly
            current_time = time.perf_counter()
            for i in range(config.inputs):
                input_key = tracker.add_input(current_time)
                pending_input_keys.append(input_key)
                target_msg = {
                    "source": f"layer_test.{i}",
                    "value": 0.5,
                    "type": "absolute_uni",
                    "timestamp": current_time
                }
                # Publish to target.test_fixture_i.param_i to match our test patch
                await broker_client.publish(f"target.test_fixture_{i}.param_{i}", json.dumps(target_msg).encode('utf-8'))
            
            # Tick fixture
            await fixture_manager.tick(dt=target_interval)
            
            # Process drops
            tracker.process_drops()
            
            frame_count += 1
            
            # Sleep to maintain 60Hz
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Process remaining drops
        tracker.process_drops()
        
        # Cleanup
        await fixture_manager.stop()
        await broker_client.disconnect()
        
        result = LayerTestResult(config=config, records=tracker.get_records())
        result.statistics = self._calculate_statistics(result.records)
        logger.info(f"    Fixture: got {output_count[0]} outputs, {len(result.records)} records")
        return result
    
    async def _test_output_layer(self, config: TestConfiguration) -> LayerTestResult:
        """Test output layer: measures processing time of output manager."""
        logger.info(f"  Testing output layer with {config.inputs} outputs")
        
        from apelios.output.output_runtime_manager import OutputRuntimeManager
        
        tracker = LayerLatencyTracker(config)
        broker_client = MemoryBrokerClient()
        await broker_client.connect()
        
        # Create and start output manager only
        output_manager = OutputRuntimeManager(broker_client=broker_client)
        await output_manager.start()
        
        # Track input keys for matching - use a queue for FIFO matching
        pending_input_keys = []
        output_count = [0]
        
        # For output layer, we measure the time from publishing to output.*
        # until the output manager processes and "sends" it
        # We'll subscribe to catch when messages are published by output manager
        
        original_publish = broker_client.publish
        
        async def tracked_publish(subject: str, message: bytes):
            await original_publish(subject, message)
            # When output manager publishes, record the time
            if subject.startswith("output."):
                try:
                    # Simple FIFO matching
                    if pending_input_keys:
                        key = pending_input_keys.pop(0)
                        tracker.add_output(key, time.perf_counter())
                        output_count[0] += 1
                except:
                    pass
        
        broker_client.publish = tracked_publish
        
        # Warm-up
        warmup_start = time.perf_counter()
        while time.perf_counter() - warmup_start < config.warmup:
            await asyncio.sleep(0.1)
        
        # Reset tracker for actual test
        tracker = LayerLatencyTracker(config)
        pending_input_keys.clear()
        output_count[0] = 0
        
        # Run test
        target_interval = 1.0 / 60.0
        frames_to_run = int(config.duration * 60)
        frame_count = 0
        
        while frame_count < frames_to_run:
            loop_start = time.perf_counter()
            
            # Publish output messages directly to the internal queue
            current_time = time.perf_counter()
            for i in range(config.inputs):
                input_key = tracker.add_input(current_time)
                pending_input_keys.append(input_key)
                output_msg = {
                    "universe": 0,
                    "address": i,
                    "value": 128,
                    "timestamp": current_time
                }
                # Publish to the internal input of output manager
                # The output manager listens on output.* topics
                await broker_client.publish(f"output.universe_0", json.dumps(output_msg).encode('utf-8'))
            
            # Tick output manager
            await output_manager.tick(dt=target_interval)
            
            # Process drops
            tracker.process_drops()
            
            frame_count += 1
            
            # Sleep to maintain 60Hz
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Process remaining drops
        tracker.process_drops()
        
        # Cleanup
        await output_manager.stop()
        await broker_client.disconnect()
        
        result = LayerTestResult(config=config, records=tracker.get_records())
        result.statistics = self._calculate_statistics(result.records)
        logger.info(f"    Output: got {output_count[0]} outputs, {len(result.records)} records")
        return result
    
    async def _test_full_pipeline(self, config: TestConfiguration) -> LayerTestResult:
        """Test full pipeline latency: input.* -> output.*"""
        logger.info(f"  Testing full pipeline with {config.inputs} inputs")
        
        from apelios.input.input_runtime_manager import InputRuntimeManager
        from apelios.input.adapters.fake_adapter import FakeAdapter
        from apelios.router.router_runtime_manager import RouterRuntimeManager
        from apelios.router.router_core import MappingRouter
        from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
        from apelios.fixture.fixture_core import FixtureCore
        from apelios.output.output_runtime_manager import OutputRuntimeManager
        
        tracker = LayerLatencyTracker(config)
        broker_client = MemoryBrokerClient()
        await broker_client.connect()
        
        # Use default profiles (same as e2e test) for fair comparison
        # This ensures we're testing the actual system, not custom test configs
        
        # Start all managers with default configurations
        input_manager = InputRuntimeManager(broker_client=broker_client)
        router_manager = RouterRuntimeManager(broker_client=broker_client)
        fixture_manager = FixtureRuntimeManager(broker_client=broker_client)
        output_manager = OutputRuntimeManager(broker_client=broker_client)
        
        # Create FakeAdapters
        adapters = []
        for i in range(config.inputs):
            adapter = FakeAdapter(device=f"layer_test_{i}", axis_types={"value": "absolute_uni"})
            adapters.append(adapter)
            input_manager.register_adapter(adapter)
        
        # Start managers
        await input_manager.start()
        await input_manager.start_registered_adapters()
        await router_manager.start()
        await fixture_manager.start()
        await output_manager.start()
        
        # Track for matching
        output_count = [0]
        
        # Subscribe to output.*
        async def on_output_message(msg):
            try:
                # Match outputs to inputs - simple round-robin matching
                if tracker.pending_inputs:
                    # Get oldest pending input
                    oldest_key = min(tracker.pending_inputs.keys(),
                                    key=lambda k: tracker.pending_inputs[k]["timestamp"])
                    tracker.add_output(oldest_key, time.perf_counter())
                    output_count[0] += 1
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error processing output: {e}")
        
        await broker_client.subscribe("output.>", on_output_message)
        
        # Warm-up
        warmup_start = time.perf_counter()
        while time.perf_counter() - warmup_start < config.warmup:
            await asyncio.sleep(0.1)
        
        # Reset tracker for actual test
        tracker = LayerLatencyTracker(config)
        output_count[0] = 0
        
        # Run test
        target_interval = 1.0 / 60.0
        frames_to_run = int(config.duration * 60)
        frame_count = 0
        
        while frame_count < frames_to_run:
            loop_start = time.perf_counter()
            
            # Record input timestamps
            current_time = time.perf_counter()
            for adapter in adapters:
                tracker.add_input(current_time)
            
            # Tick all managers
            await input_manager.tick(dt=target_interval)
            await router_manager.tick(dt=target_interval)
            await fixture_manager.tick(dt=target_interval)
            await output_manager.tick(dt=target_interval)
            
            # Process drops
            tracker.process_drops()
            
            frame_count += 1
            
            # Sleep to maintain 60Hz
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Process remaining drops
        tracker.process_drops()
        
        # Cleanup
        await input_manager.stop_registered_adapters()
        await input_manager.stop()
        await router_manager.stop()
        await fixture_manager.stop()
        await output_manager.stop()
        await broker_client.disconnect()
        
        result = LayerTestResult(config=config, records=tracker.get_records())
        result.statistics = self._calculate_statistics(result.records)
        logger.info(f"    Full: got {output_count[0]} outputs, {len(result.records)} records")
        return result
    
    async def _run_layer_test(self, layer: str, inputs: int) -> LayerTestResult:
        """Run a test for a specific layer and input count."""
        config = TestConfiguration(
            layer=layer,
            inputs=inputs,
            duration=self.args.duration,
            warmup=self.args.warmup,
            frame_timeout=self.args.frame_timeout
        )
        
        if layer == "input":
            return await self._test_input_layer(config)
        elif layer == "router":
            return await self._test_router_layer(config)
        elif layer == "fixture":
            return await self._test_fixture_layer(config)
        elif layer == "output":
            return await self._test_output_layer(config)
        elif layer == "full":
            return await self._test_full_pipeline(config)
        else:
            raise ValueError(f"Unknown layer: {layer}")
    
    async def run_all_tests(self) -> None:
        """Run all configured tests."""
        logger.info(f"Starting per-layer latency tests")
        logger.info(f"  Layers: {self.layers_to_test}")
        logger.info(f"  Input counts: {self.input_counts}")
        
        for layer in self.layers_to_test:
            logger.info(f"\n=== Testing {layer.upper()} Layer ===")
            
            for inputs in self.input_counts:
                logger.info(f"  {inputs} inputs...")
                try:
                    result = await self._run_layer_test(layer, inputs)
                    self.test_results.append(result)
                    self.all_records.extend(result.records)
                    
                    stats = result.statistics
                    logger.info(f"    {inputs:3d} inputs: median={stats['median_ms']:6.2f}ms, "
                               f"drops={stats['drops']:3d} ({stats['drop_rate']*100:5.1f}%)")
                except Exception as e:
                    logger.error(f"    Error testing {layer} with {inputs} inputs: {e}")
                    import traceback
                    traceback.print_exc()
    
    def save_csv(self) -> list[Path]:
        """Save all records to CSV files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []
        
        # Save per-layer CSV files
        layers = set(r.config.layer for r in self.test_results)
        for layer in layers:
            layer_records = [r for r in self.all_records if r.layer == layer]
            csv_path = self.output_dir / f"layer_latency_{layer}_{timestamp}.csv"
            
            fieldnames = [
                "layer", "test_id", "timestamp", "config_inputs",
                "frame_number", "latency_ms", "is_drop"
            ]
            
            with csv_path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in layer_records:
                    row = {
                        "layer": record.layer,
                        "test_id": record.test_id,
                        "timestamp": f"{record.timestamp:.6f}",
                        "config_inputs": record.config_inputs,
                        "frame_number": record.frame_number,
                        "latency_ms": f"{record.latency_ms:.3f}",
                        "is_drop": record.is_drop
                    }
                    writer.writerow(row)
            
            logger.info(f"CSV saved to: {csv_path}")
            saved_files.append(csv_path)
        
        # Save aggregated statistics
        stats_path = self.output_dir / f"layer_latency_statistics_{timestamp}.csv"
        
        fieldnames = [
            "layer", "config_inputs", "count", "total_events",
            "min_ms", "max_ms", "mean_ms", "median_ms", "std_dev_ms",
            "drops", "drop_rate"
        ]
        
        with stats_path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.test_results:
                row = {
                    "layer": result.config.layer,
                    "config_inputs": result.config.inputs,
                    **result.statistics
                }
                writer.writerow(row)
        
        logger.info(f"Statistics saved to: {stats_path}")
        saved_files.append(stats_path)
        
        return saved_files
    
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
        
        # 1. Layer Comparison Boxplot (baseline: 1 input)
        baseline_results = {}
        for result in self.test_results:
            if result.config.inputs == 1:
                baseline_results[result.config.layer] = result
        
        if len(baseline_results) > 0:
            fig, ax = plt.subplots()
            
            data_to_plot = []
            labels = []
            
            for layer in self.LAYERS:
                if layer in baseline_results:
                    result = baseline_results[layer]
                    latencies = [r.latency_ms for r in result.records if r.is_drop == 0]
                    if latencies:
                        data_to_plot.append(latencies)
                        labels.append(layer.capitalize())
            
            if data_to_plot:
                ax.boxplot(data_to_plot, tick_labels=labels)
                ax.set_title('Baseline Layer Latency Comparison (1 input)')
                ax.set_xlabel('Layer')
                ax.set_ylabel('Latency (ms)')
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, alpha=0.3)
                
                for ext in ['svg', 'pdf']:
                    filepath = self.output_dir / f"layer_baseline_boxplot_{timestamp}.{ext}"
                    fig.savefig(filepath, bbox_inches='tight', dpi=300)
                    generated_files.append(filepath)
                
                plt.close(fig)
        
        # 2. Per-Layer Scaling Plot
        if len(self.test_results) > 0:
            fig, ax = plt.subplots()
            
            colors = {'input': 'purple', 'router': 'blue', 'fixture': 'green', 'output': 'orange', 'full': 'red'}
            
            for layer in self.LAYERS:
                layer_results = [r for r in self.test_results if r.config.layer == layer]
                if layer_results:
                    # Sort by input count
                    layer_results.sort(key=lambda x: x.config.inputs)
                    x_values = [r.config.inputs for r in layer_results]
                    y_median = [r.statistics['median_ms'] for r in layer_results]
                    y_std = [r.statistics['std_dev_ms'] for r in layer_results]
                    
                    color = colors.get(layer, 'gray')
                    ax.errorbar(x_values, y_median, yerr=y_std,
                               fmt='-o', capsize=5, label=layer.capitalize(),
                               color=color, alpha=0.7)
            
            # Add target line
            ax.axhline(y=30, color='r', linestyle=':', label='Target (<30ms)')
            ax.axhline(y=16.67, color='g', linestyle=':', label='Frame Time (16.67ms)')
            
            # Use linear scale for better visibility of the bottleneck at ~10 inputs
            # ax.set_xscale('log')  # Commented out - using linear scale
            ax.set_title('Per-Layer Latency vs Scaling')
            ax.set_xlabel('Number of Inputs')
            ax.set_ylabel('Median Latency (ms)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            for ext in ['svg', 'pdf']:
                filepath = self.output_dir / f"layer_scaling_{timestamp}.{ext}"
                fig.savefig(filepath, bbox_inches='tight', dpi=300)
                generated_files.append(filepath)
            
            plt.close(fig)
        
        # 3. Latency Breakdown at key points
        for breakdown_inputs in [1, 50, 100]:
            breakdown_data = {}
            for result in self.test_results:
                if result.config.inputs == breakdown_inputs:
                    breakdown_data[result.config.layer] = result.statistics['median_ms']
            
            if len(breakdown_data) > 0:
                fig, ax = plt.subplots()
                
                layers_ordered = ['input', 'router', 'fixture', 'output', 'full']
                values = [breakdown_data.get(l, 0) for l in layers_ordered if l in breakdown_data]
                labels_ordered = [l.capitalize() for l in layers_ordered if l in breakdown_data]
                
                if values:
                    bars = ax.bar(labels_ordered, values, alpha=0.7, edgecolor='black')
                    ax.set_title(f'Latency Breakdown at {breakdown_inputs} Inputs')
                    ax.set_xlabel('Layer')
                    ax.set_ylabel('Median Latency (ms)')
                    ax.grid(True, alpha=0.3, axis='y')
                    
                    # Add value labels on bars
                    for bar, value in zip(bars, values):
                        if value > 0.1:  # Only label if visible
                            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                                   f'{value:.1f}', ha='center', va='bottom')
                    
                    for ext in ['svg', 'pdf']:
                        filepath = self.output_dir / f"layer_breakdown_{breakdown_inputs}_{timestamp}.{ext}"
                        fig.savefig(filepath, bbox_inches='tight', dpi=300)
                        generated_files.append(filepath)
                    
                    plt.close(fig)
        
        logger.info(f"Generated {len(generated_files)} plot files")
        return generated_files
    
    def print_summary(self) -> None:
        """Print a summary of test results to console."""
        print("\n" + "=" * 80)
        print("PER-LAYER LATENCY TEST SUMMARY")
        print("=" * 80)
        
        # Group results by layer
        layer_results = {}
        for result in self.test_results:
            layer = result.config.layer
            if layer not in layer_results:
                layer_results[layer] = []
            layer_results[layer].append(result)
        
        # Print per-layer summary
        for layer, results in layer_results.items():
            print(f"\n{layer.upper()} LAYER:")
            print("-" * 40)
            
            # Sort by input count
            results.sort(key=lambda x: x.config.inputs)
            
            for result in results:
                stats = result.statistics
                config = result.config
                
                assessment = "[OK]"
                if stats["median_ms"] > 30:
                    assessment = "[FAIL]"
                elif stats["median_ms"] > 15:
                    assessment = "[WARN]"
                
                print(f"  {config.inputs:3d} inputs: median={stats['median_ms']:6.2f}ms, "
                      f"max={stats['max_ms']:6.2f}ms, drops={stats['drops']:3d} "
                      f"({stats['drop_rate']*100:5.1f}%) {assessment}")
        
        print("\n" + "=" * 80)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Per-Layer Latency Test for Apelios',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python scripts/layer_latency_test.py --output-dir results/
  python scripts/layer_latency_test.py --layer fixture --output-dir results/
  python scripts/layer_latency_test.py --layer all --output-dir results/ --plot
  python scripts/layer_latency_test.py --inputs 1,10,50,100 --output-dir results/
        """
    )
    
    parser.add_argument(
        '--layer',
        type=str,
        default='all',
        choices=['input', 'router', 'fixture', 'output', 'full', 'all'],
        help='Layer to test: input, router, fixture, output, full, or all (default: all)'
    )
    
    parser.add_argument(
        '--inputs',
        type=str,
        default=None,
        help='Comma-separated list of input counts to test (default: 1,10,20,...,200)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=1.0,
        help='Test duration in seconds per configuration (default: 1)'
    )
    
    parser.add_argument(
        '--warmup',
        type=float,
        default=0.5,
        help='Warm-up duration in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--frame-timeout',
        type=float,
        default=0.05,
        help='Timeout for frame drop detection in seconds (default: 0.05)'
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
    test = LayerLatencyTest(args)
    await test.run_all_tests()
    
    # Save results
    test.save_csv()
    
    # Generate plots if requested
    if args.plot:
        test.generate_plots()
    
    # Print summary
    test.print_summary()
    
    logger.info("Test complete. Results saved.")
    if args.plot:
        logger.info("Plots generated in SVG and PDF formats")


if __name__ == "__main__":
    asyncio.run(main())
