"""
Per-Layer Latency Tests for Apelios Performance Testing Framework.

Measures each layer's processing time independently using NATS Broker and 60Hz tick.
Each layer receives all subscribed messages, processes them in the tick, and publishes outputs.

Usage:
    python -m pytest tools/performance/tests/test_layer_latency.py -v
    python -m pytest tools/performance/tests/test_layer_latency.py::TestFixtureLayer::test_fixture_layer_latency[10] -v
"""

import pytest
import asyncio
import time
import csv
import json
import statistics
import socket
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


def is_nats_server_running(port=4222, attempts=10, delay=0.1):
    """Check if NATS server is running on the given port."""
    for _ in range(attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(delay)
                s.connect(('127.0.0.1', port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(delay)
    return False

from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.router.router_runtime_manager import RouterRuntimeManager
from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
from apelios.output.output_runtime_manager import OutputRuntimeManager
from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.config import NatsConfig
from apelios.broker.broker_client import BrokerClient
from apelios.input.adapters.fake_adapter import FakeAdapter
from apelios.output.adapters.fake_output_adapter import FakeOutputAdapter

from .conftest import (
    LAYER_CONFIGS, FIXTURE_LAYER_CONFIGS, TARGET_INTERVAL, FRAMES_PER_CONFIG,
    save_test_metadata, save_csv_results, LAYER_COLORS,
    router_profile_n, fixture_patch_n
)
from .test_e2e_latency import TestE2ELatency


class TestInputLayer:
    """Input layer latency tests: FakeAdapter polling to input.* with NATS."""
    
    @pytest.mark.asyncio
    async def test_input_layer_latency(self, layer_config, results_dir):
        """
        Test input layer latency: FakeAdapter polling to input.* messages.
        
        Measures time from FakeAdapter poll to input.* message publication.
        Uses NATS Broker and 60Hz tick for realistic processing.
        
        Args:
            layer_config: Number of input adapters (1, 10, 25, 50, 100)
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "layer" / "input" / str(layer_config)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup NATS server using BrokerRuntimeManager
        broker_config = NatsConfig(host="127.0.0.1", port=4222)
        broker_runtime = BrokerRuntimeManager(provider="nats", config=broker_config)
        
        # Setup InputRuntimeManager (creates its own BrokerClient)
        # Disable automatic adapter bootstrap for testing
        input_manager = InputRuntimeManager(bootstrap_adapters=False)
        
        # Create a SINGLE FakeAdapter with multiple axes (one per input)
        # This ensures message ordering is preserved
        device_name = "test_input"
        axis_types = {f"value_{i}": "absolute_uni" for i in range(layer_config)}
        adapter = FakeAdapter(
            device=device_name,
            axis_types=axis_types
        )
        input_manager.register_adapter(adapter)
        
        # Start NATS server first (only if not already running)
        server_started_by_us = False
        if not is_nats_server_running(4222):
            await broker_runtime.start_server()
            server_started_by_us = True
        
        # Create a BrokerClient to subscribe to input messages
        broker_client = BrokerClient(provider="nats", config=broker_config)
        await broker_client.connect()
        
        # Track timestamps - will extract from message payload
        message_timestamps = []
        output_timestamps = []
        
        async def on_input(msg):
            """Callback for input messages."""
            import json as json_mod
            try:
                payload = json_mod.loads(msg.data.decode())
                # Extract the timestamp from the message payload (now using perf_counter)
                message_timestamps.append(payload.get('timestamp', time.perf_counter()))
                output_timestamps.append(time.perf_counter())
            except Exception as e:
                print(f"Error parsing message: {e}")
                output_timestamps.append(time.perf_counter())
        
        # Subscribe to all input topics
        await broker_client.subscribe("input.>", on_input)
        await asyncio.sleep(0.1)  # Give subscription time to propagate
        
        # Start input manager after subscription (will not bootstrap adapters due to flag)
        await input_manager.start()
        await input_manager.start_registered_adapters()
        
        # Warmup period
        await asyncio.sleep(1.0)
        message_timestamps.clear()
        output_timestamps.clear()
        
        # Test loop at 60Hz
        for frame in range(FRAMES_PER_CONFIG):
            loop_start = time.perf_counter()
            
            # Tick input manager at 60Hz (triggers adapter to poll and publish)
            await input_manager.tick(dt=TARGET_INTERVAL)
            
            # Maintain 60Hz timing
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, TARGET_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)
        
        # Calculate latencies and save results
        # Single adapter publishes layer_config messages per tick
        self._save_layer_results(
            outputs_dir, layer_config, "input",
            message_timestamps, output_timestamps, FRAMES_PER_CONFIG * layer_config
        )
        
        # Cleanup
        await input_manager.stop_registered_adapters()
        await input_manager.stop()
        await broker_client.disconnect()
        if server_started_by_us:
            await broker_runtime.stop_server()
        
        # Input layer should be very fast (< 1ms)
        median_lat = self._get_median_latency(outputs_dir)
        assert median_lat < 1.0, f"Input latency {median_lat:.4f}ms too high"
        print(f"\nInput Layer Test {layer_config} inputs: median={median_lat:.4f}ms")
    
    def _save_layer_results(self, outputs_dir, config, layer_name, input_ts, output_ts, total_frames):
        """Save layer test results to CSV files."""
        latencies = []
        min_length = min(len(input_ts), len(output_ts))
        
        # Debug: print lengths if they don't match expected
        expected_total = total_frames
        if min_length != expected_total:
            print(f"WARNING: {layer_name} layer - expected {expected_total} pairs, got {min_length} "
                  f"(input_ts={len(input_ts)}, output_ts={len(output_ts)})")
        
        for i in range(min_length):
            latency_ms = (output_ts[i] - input_ts[i]) * 1000
            latencies.append(latency_ms)
        
        drops = len(input_ts) - min_length
        drop_rate = drops / total_frames if total_frames > 0 else 0
        
        # Save raw results
        results_data = []
        for i, lat in enumerate(latencies):
            results_data.append({
                "config_inputs": config,
                "frame_number": i,
                "latency_ms": lat,
                "is_drop": 0
            })
        for i in range(drops):
            results_data.append({
                "config_inputs": config,
                "frame_number": min_length + i,
                "latency_ms": 0.0,
                "is_drop": 1
            })
        
        save_csv_results(
            outputs_dir,
            "results",
            results_data,
            ["config_inputs", "frame_number", "latency_ms", "is_drop"]
        )
        
        # Save statistics
        if latencies:
            stats_data = [{
                "config_inputs": config,
                "count": len(latencies),
                "total_frames": total_frames,
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "mean_ms": statistics.mean(latencies),
                "median_ms": statistics.median(latencies),
                "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                "drops": drops,
                "drop_rate": drop_rate
            }]
        else:
            stats_data = [{
                "config_inputs": config,
                "count": 0,
                "total_frames": total_frames,
                "min_ms": 0,
                "max_ms": 0,
                "mean_ms": 0,
                "median_ms": 0,
                "std_dev_ms": 0,
                "drops": drops,
                "drop_rate": drop_rate
            }]
        
        save_csv_results(
            outputs_dir,
            "statistics",
            stats_data,
            ["config_inputs", "count", "total_frames", "min_ms", "max_ms", 
             "mean_ms", "median_ms", "std_dev_ms", "drops", "drop_rate"]
        )
        
        # Save metadata
        save_test_metadata(
            outputs_dir,
            "layer",
            {"layer": layer_name, "config_inputs": config},
            frames=total_frames
        )
    
    def _get_median_latency(self, outputs_dir):
        """Get median latency from statistics CSV."""
        stats_path = outputs_dir / "statistics.csv"
        if not stats_path.exists():
            return 0
        
        import csv
        with stats_path.open('r') as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            if row:
                return float(row.get("median_ms", 0))
        return 0


class TestRouterLayer:
    """Router layer latency tests: input.* to target.* with NATS."""
    
    @pytest.mark.asyncio
    async def test_router_layer_latency(self, layer_config, results_dir):
        """
        Test router layer latency: input.* to target.* messages.
        
        Measures time from input.* message to target.* message publication.
        Uses NATS Broker and 60Hz tick for realistic processing.
        
        Args:
            layer_config: Number of inputs (1, 10, 25, 50, 100)
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "layer" / "router" / str(layer_config)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup NATS server using BrokerRuntimeManager
        broker_config = NatsConfig(host="127.0.0.1", port=4222)
        broker_runtime = BrokerRuntimeManager(provider="nats", config=broker_config)
        
        # Setup RouterRuntimeManager with shared broker config
        # Use a BrokerClient with the test's config
        router_broker_client = BrokerClient(provider="nats", config=broker_config)
        router_manager = RouterRuntimeManager(broker_client=router_broker_client)
        
        # Set router profile
        profile = router_profile_n(layer_config)
        router_manager.router.profile = profile
        
        # Start NATS server first (only if not already running)
        server_started_by_us = False
        if not is_nats_server_running(4222):
            await broker_runtime.start_server()
            server_started_by_us = True
        
        # Start router manager (this will connect and subscribe to input.>)
        await router_manager.start()
        
        # Create a BrokerClient to publish and subscribe
        broker_client = BrokerClient(provider="nats", config=broker_config)
        await broker_client.connect()
        
        # Track timestamps
        input_timestamps = []
        output_timestamps = []
        
        async def on_target(msg):
            """Callback for target messages."""
            output_timestamps.append(time.perf_counter())
            if len(output_timestamps) <= 5:
                print(f"Router received target message {len(output_timestamps)}: {msg.subject}")
        
        # Subscribe to all target topics
        await broker_client.subscribe("target.>", on_target)
        
        # Warmup period
        await asyncio.sleep(1.0)
        input_timestamps.clear()
        output_timestamps.clear()
        
        # Test loop at 60Hz
        for frame in range(FRAMES_PER_CONFIG):
            loop_start = time.perf_counter()
            
            # Publish directly to input.* topics (simulating input layer output)
            # Record timestamp for each message
            for i in range(layer_config):
                input_timestamps.append(time.perf_counter())
                msg = {
                    "source": f"input.test_{i}.value",
                    "value": 0.5,
                    "type": "absolute_uni",
                    "timestamp": loop_start
                }
                await broker_client.publish(
                    f"input.test_{i}.value",
                    json.dumps(msg).encode()
                )
            
            # Small delay to allow NATS message delivery before ticking
            await asyncio.sleep(0.001)
            
            # Tick router manager at 60Hz
            await router_manager.tick(dt=TARGET_INTERVAL)
            
            # Maintain 60Hz timing
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, TARGET_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)
        
        # Calculate latencies and save results
        input_layer = TestInputLayer()
        input_layer._save_layer_results(
            outputs_dir, layer_config, "router",
            input_timestamps, output_timestamps, FRAMES_PER_CONFIG * layer_config
        )
        
        # Cleanup
        await router_manager.stop()
        await router_broker_client.disconnect()
        await broker_client.disconnect()
        if server_started_by_us:
            await broker_runtime.stop_server()
        
        # Router layer should be fast (< 20ms for 100 inputs, < 15ms for 50, < 10ms for others)
        median_lat = input_layer._get_median_latency(outputs_dir)
        if layer_config >= 100:
            threshold = 20.0
        elif layer_config >= 50:
            threshold = 15.0
        else:
            threshold = 10.0
        assert median_lat < threshold, f"Router latency {median_lat:.4f}ms too high (threshold: {threshold}ms)"
        
        print(f"\nRouter Layer Test {layer_config} inputs: median={median_lat:.4f}ms")


class TestFixtureLayer:
    """Fixture layer latency tests: target.* to output.* with NATS."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("layer_config", FIXTURE_LAYER_CONFIGS)
    async def test_fixture_layer_latency(self, layer_config, results_dir):
        """
        Test fixture layer latency: target.* to output.* messages.
        
        Measures time from target.* message to output.* message publication.
        Uses NATS Broker and 60Hz tick for realistic processing.
        
        Args:
            layer_config: Number of fixtures (1, 10, 25, 50, 100)
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "layer" / "fixture" / str(layer_config)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup NATS server using BrokerRuntimeManager
        broker_config = NatsConfig(host="127.0.0.1", port=4222)
        broker_runtime = BrokerRuntimeManager(provider="nats", config=broker_config)
        
        # Setup FixtureRuntimeManager (creates its own BrokerClient)
        fixture_manager = FixtureRuntimeManager()
        
        # Set fixture patch
        patch = fixture_patch_n(layer_config)
        fixture_manager.core.patch = patch
        
        # Start NATS server first (only if not already running)
        server_started_by_us = False
        if not is_nats_server_running(4222):
            await broker_runtime.start_server()
            server_started_by_us = True
        
        # Then start fixture manager
        await fixture_manager.start()
        
        # Create a BrokerClient to publish and subscribe
        broker_client = BrokerClient(provider="nats", config=broker_config)
        await broker_client.connect()
        
        # Correlate each target input with its stable DMX output subject. Fixture
        # outputs are frame-aligned, so raw list-index pairing is not valid.
        input_timestamps = []
        output_timestamps = []
        pending_inputs = {}
        frame_outputs_received = asyncio.Event()
        
        async def on_output(msg):
            """Callback for output messages."""
            input_timestamp = pending_inputs.pop(msg.subject, None)
            if input_timestamp is None:
                return
            input_timestamps.append(input_timestamp)
            output_timestamps.append(time.perf_counter())
            if not pending_inputs:
                frame_outputs_received.set()
        
        # Subscribe to all output topics
        await broker_client.subscribe("output.>", on_output)
        
        # Warmup period
        await asyncio.sleep(1.0)
        input_timestamps.clear()
        output_timestamps.clear()

        async def wait_for_frame_inputs(expected_sources, timeout=0.1):
            """Wait until NATS has delivered every input for the current frame."""
            async def all_inputs_received():
                while not expected_sources.issubset(fixture_manager.core.inbox):
                    await asyncio.sleep(0)

            await asyncio.wait_for(all_inputs_received(), timeout=timeout)
        
        # Test loop at 60Hz
        for frame in range(FRAMES_PER_CONFIG):
            loop_start = time.perf_counter()
            expected_sources = {f"input.test_{i}.value" for i in range(layer_config)}
            frame_outputs_received.clear()
            
            # Publish directly to target.* topics (simulating router output)
            # Record timestamps by the DMX subject each target must produce.
            for i in range(layer_config):
                pending_inputs[f"output.0.{i}"] = time.perf_counter()
                msg = {
                    "source": f"input.test_{i}.value",
                    "value": 0.5,
                    "type": "absolute_uni",
                    "timestamp": loop_start
                }
                await broker_client.publish(
                    f"target.test_{i}.param",
                    json.dumps(msg).encode()
                )
            
            # Do not tick a partial frame merely because broker delivery took
            # longer than an arbitrary sleep on this machine.
            await wait_for_frame_inputs(expected_sources)
            
            # Tick fixture manager at 60Hz
            await fixture_manager.tick(dt=TARGET_INTERVAL)
            
            # Keep frame correlation intact and fail clearly if any expected DMX
            # key was not published instead of shifting all later samples.
            await asyncio.wait_for(frame_outputs_received.wait(), timeout=0.1)
            
            # Maintain 60Hz timing
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, TARGET_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)
        
        # Calculate latencies and save results
        expected_total = FRAMES_PER_CONFIG * layer_config
        input_layer = TestInputLayer()
        input_layer._save_layer_results(
            outputs_dir, layer_config, "fixture",
            input_timestamps, output_timestamps, expected_total
        )
        
        # Validate output count
        output_count = len(output_timestamps)
        input_count = len(input_timestamps)
        
        # The schema gives every fixture a distinct address, and bounded frame
        # synchronization makes an exact count meaningful.
        expected_outputs = FRAMES_PER_CONFIG * layer_config
        assert output_count == expected_outputs, (
            f"Expected {expected_outputs} distinct fixture outputs, got {output_count}"
        )
        
        # Cleanup
        await fixture_manager.stop()
        await broker_client.disconnect()
        if server_started_by_us:
            await broker_runtime.stop_server()
        
        # Fixture layer should now handle all configs properly
        median_lat = input_layer._get_median_latency(outputs_dir)
        assert median_lat < 50.0, f"Fixture latency {median_lat:.2f}ms too high"
        
        print(f"\nFixture Layer Test {layer_config} inputs: median={median_lat:.2f}ms "
              f"(inputs={input_count}, outputs={output_count})")


class TestOutputLayer:
    """Output layer latency tests: output.* to ArtNet with NATS."""
    
    @pytest.mark.asyncio
    async def test_output_layer_latency(self, layer_config, results_dir):
        """
        Test output layer latency: output.* messages to ArtNet transmission.
        
        Measures time from output.* message to ArtNet packet preparation.
        Uses NATS Broker and 60Hz tick for realistic processing.
        
        Args:
            layer_config: Number of universes (1, 10, 25, 50, 100)
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "layer" / "output" / str(layer_config)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup NATS server using BrokerRuntimeManager
        broker_config = NatsConfig(host="127.0.0.1", port=4222)
        broker_runtime = BrokerRuntimeManager(provider="nats", config=broker_config)
        
        # Setup OutputRuntimeManager (creates its own BrokerClient)
        output_manager = OutputRuntimeManager()
        
        # Create and register FakeOutputAdapter to measure send latency
        # Use test mode to disable automatic loop
        fake_adapter = FakeOutputAdapter(config={"test_mode": True, "output_rate_hz": 60.0}, core=output_manager.core)
        output_manager.core.register_adapter(fake_adapter)
        
        # Start NATS server first (only if not already running)
        server_started_by_us = False
        if not is_nats_server_running(4222):
            await broker_runtime.start_server()
            server_started_by_us = True
        
        # Then start output manager and adapter
        await output_manager.start()
        await fake_adapter.start()
        
        # Create a BrokerClient to publish
        broker_client = BrokerClient(provider="nats", config=broker_config)
        await broker_client.connect()
        
        # Track timestamps - one per message for proper alignment
        input_timestamps = []
        # We'll use fake_adapter.send_timestamps for output timestamps
        
        # Clear any previous timestamps
        fake_adapter.clear_timestamps()
        
        # Warmup period
        await asyncio.sleep(1.0)
        input_timestamps.clear()
        fake_adapter.clear_timestamps()
        
        # Test loop at 60Hz
        for frame in range(FRAMES_PER_CONFIG):
            loop_start = time.perf_counter()
            
            # Publish directly to output.* topics (simulating fixture output)
            # Record timestamp BEFORE each publish for accurate latency
            for i in range(layer_config):
                # One timestamp per message
                input_timestamps.append(time.perf_counter())
                msg = {
                    "universe": i,
                    "address": 0,
                    "value": 128
                }
                await broker_client.publish(
                    f"output.test_{i}",
                    json.dumps(msg).encode()
                )
            
            # Small delay to allow NATS message delivery before ticking
            await asyncio.sleep(0.001)
            
            # Tick output manager at 60Hz
            await output_manager.tick(dt=TARGET_INTERVAL)
            
            # In test mode, manually record send timestamps for each message
            # The adapter's loop is disabled, so we record after processing
            for i in range(layer_config):
                fake_adapter.record_send_timestamp()
            
            # Maintain 60Hz timing
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, TARGET_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)
        
        # Calculate latencies and save results
        # Output timestamps come from the FakeOutputAdapter
        output_timestamps = fake_adapter.get_send_timestamps()
        
        input_layer = TestInputLayer()
        input_layer._save_layer_results(
            outputs_dir, layer_config, "output",
            input_timestamps, output_timestamps, FRAMES_PER_CONFIG * layer_config
        )
        
        # Cleanup
        await fake_adapter.stop()
        await output_manager.stop()
        await broker_client.disconnect()
        if server_started_by_us:
            await broker_runtime.stop_server()
        
        # Output layer should be reasonably fast (< 15ms for NATS-based output)
        median_lat = input_layer._get_median_latency(outputs_dir)
        assert median_lat < 15.0, f"Output latency {median_lat:.4f}ms too high"
        
        print(f"\nOutput Layer Test {layer_config} universes: median={median_lat:.4f}ms")

