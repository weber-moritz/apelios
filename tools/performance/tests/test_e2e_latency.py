"""
E2E Latency Test for Apelios Performance Testing Framework.

Measures realistic end-to-end latency with all layers active using NATS Broker.
All managers run at 60Hz tick rate to simulate real processing behavior.

Usage:
    python -m pytest tools/performance/tests/test_e2e_latency.py -v
    python -m pytest tools/performance/tests/test_e2e_latency.py::test_e2e_latency[10] -v
"""

import pytest
import asyncio
import time
import csv
import json
import statistics
import socket
import platform
import sys
from pathlib import Path


def is_nats_server_running(port=4222):
    """Check if NATS server is running on the given port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(('127.0.0.1', port))
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.router.router_runtime_manager import RouterRuntimeManager
from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
from apelios.output.output_runtime_manager import OutputRuntimeManager
from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.config import NatsConfig
from apelios.broker.broker_client import BrokerClient
from apelios.input.adapters.fake_adapter import FakeAdapter

from .conftest import (
    E2E_CONFIGS, TARGET_INTERVAL, FRAMES_PER_CONFIG,
    save_test_metadata, save_csv_results,
    router_profile_n, fixture_patch_n
)


class TestE2ELatency:
    """E2E latency tests with NATS Broker and 60Hz tick."""
    
    @pytest.fixture(params=E2E_CONFIGS)
    def input_config(self, request):
        """Test configuration: 1, 10, 25, 50, 100 inputs."""
        return request.param
    
    @pytest.mark.asyncio
    async def test_e2e_latency(self, input_config, results_dir):
        """
        End-to-end latency test with all layers active.
        
        Measures time from FakeAdapter input to output.* message reception
        using NATS Broker and 60Hz tick for realistic processing.
        
        Args:
            input_config: Number of input adapters (1, 10, 25, 50, 100)
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "e2e" / str(input_config)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup NATS server using BrokerRuntimeManager (starts the server process)
        broker_config = NatsConfig(host="127.0.0.1", port=4222)
        broker_runtime = BrokerRuntimeManager(provider="nats", config=broker_config)
        
        # Setup all RuntimeManagers (they create their own BrokerClient instances)
        input_manager = InputRuntimeManager()
        router_manager = RouterRuntimeManager()
        fixture_manager = FixtureRuntimeManager()
        output_manager = OutputRuntimeManager()
        
        # Set router profile to route input.test_N.value to target.test_N.param
        router_manager.router.profile = router_profile_n(input_config)
        
        # Set fixture patch
        fixture_manager.core.patch = fixture_patch_n(input_config)
        
        # Create FakeAdapters (1 axis per adapter to match input count)
        adapters = []
        for i in range(input_config):
            device_name = f"test_{i}"
            adapter = FakeAdapter(
                device=device_name,
                axis_types={"value": "absolute_uni"}
            )
            adapters.append(adapter)
            input_manager.register_adapter(adapter)
        
        # Start NATS server first (only if not already running)
        server_started_by_us = False
        if not is_nats_server_running(4222):
            await broker_runtime.start_server()
            server_started_by_us = True
        
        # Then start all managers (they will connect to the running server)
        await input_manager.start()
        await input_manager.start_registered_adapters()
        await router_manager.start()
        await fixture_manager.start()
        await output_manager.start()
        
        # Create a BrokerClient to subscribe to output messages
        broker_client = BrokerClient(provider="nats", config=broker_config)
        await broker_client.connect()
        
        # E2E is measured once per frame: from the start of the input tick until
        # every distinct DMX output expected for that frame has arrived.
        output_timestamps = []
        input_timestamps = []
        pending_output_subjects = set()
        frame_outputs_received = asyncio.Event()
        current_frame_start = None
        
        async def on_output(msg):
            """Callback for output messages."""
            nonlocal current_frame_start
            if msg.subject not in pending_output_subjects:
                return
            pending_output_subjects.remove(msg.subject)
            if not pending_output_subjects and current_frame_start is not None:
                input_timestamps.append(current_frame_start)
                output_timestamps.append(time.perf_counter())
                frame_outputs_received.set()
        
        # Subscribe to all output topics
        await broker_client.subscribe("output.>", on_output)
        
        # Warmup period (1 second) to allow system to stabilize
        await asyncio.sleep(1.0)
        
        # Clear tracking for actual measurement
        output_timestamps.clear()
        input_timestamps.clear()

        async def wait_until(predicate, timeout=0.1):
            """Yield until a broker-driven pipeline stage has completed."""
            async def condition_met():
                while not predicate():
                    await asyncio.sleep(0)

            await asyncio.wait_for(condition_met(), timeout=timeout)
        
        # Test loop: Run for FRAMES_PER_CONFIG frames at 60Hz
        for frame in range(FRAMES_PER_CONFIG):
            loop_start = time.perf_counter()
            current_frame_start = loop_start
            expected_sources = {f"input.test_{i}.value" for i in range(input_config)}
            pending_output_subjects.update(
                f"output.0.{i}" for i in range(input_config)
            )
            frame_outputs_received.clear()
            
            # Advance complete pipeline stages. Bounded waits prevent broker
            # scheduling from turning one logical frame into partial frames.
            await input_manager.tick(dt=TARGET_INTERVAL)
            await wait_until(
                lambda: len(router_manager._outputs_to_publish) == input_config
            )
            await router_manager.tick(dt=TARGET_INTERVAL)
            await wait_until(
                lambda: expected_sources.issubset(fixture_manager.core.inbox)
            )
            await fixture_manager.tick(dt=TARGET_INTERVAL)
            await asyncio.wait_for(frame_outputs_received.wait(), timeout=0.1)
            await output_manager.tick(dt=TARGET_INTERVAL)
            
            # Maintain 60Hz timing
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, TARGET_INTERVAL - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                # Frame overrun - log but continue
                pass
        
        # Calculate latencies
        latencies = []
        min_length = min(len(input_timestamps), len(output_timestamps))
        
        for i in range(min_length):
            latency_ms = (output_timestamps[i] - input_timestamps[i]) * 1000
            latencies.append(latency_ms)
        
        # Calculate drops
        drops = len(input_timestamps) - min_length
        drop_rate = drops / FRAMES_PER_CONFIG if FRAMES_PER_CONFIG > 0 else 0
        
        # Save raw results
        results_data = []
        for i, lat in enumerate(latencies):
            results_data.append({
                "config_inputs": input_config,
                "frame_number": i,
                "latency_ms": lat,
                "is_drop": 0
            })
        for i in range(drops):
            results_data.append({
                "config_inputs": input_config,
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
        
        # Calculate and save statistics
        if latencies:
            stats_data = [{
                "config_inputs": input_config,
                "config_outputs": input_config,
                "count": len(latencies),
                "total_events": FRAMES_PER_CONFIG,
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "mean_ms": statistics.mean(latencies),
                "median_ms": statistics.median(latencies),
                "p95_ms": statistics.quantiles(latencies, n=100)[94] if len(latencies) > 1 else latencies[0],
                "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                "drops": drops,
                "drop_rate": drop_rate
            }]
        else:
            stats_data = [{
                "config_inputs": input_config,
                "config_outputs": input_config,
                "count": 0,
                "total_events": FRAMES_PER_CONFIG,
                "min_ms": 0,
                "max_ms": 0,
                "mean_ms": 0,
                "median_ms": 0,
                "p95_ms": 0,
                "std_dev_ms": 0,
                "drops": drops,
                "drop_rate": drop_rate
            }]
        
        save_csv_results(
            outputs_dir,
            "statistics",
            stats_data,
            ["config_inputs", "config_outputs", "count", "total_events", 
             "min_ms", "max_ms", "mean_ms", "median_ms", "p95_ms", "std_dev_ms", 
             "drops", "drop_rate"]
        )
        
        # Save metadata
        save_test_metadata(
            outputs_dir,
            "e2e",
            {"config_inputs": input_config, "config_outputs": input_config},
            frames=FRAMES_PER_CONFIG
        )
        
        # Cleanup - stop managers first, then broker client, then broker server
        await input_manager.stop_registered_adapters()
        await input_manager.stop()
        await router_manager.stop()
        await fixture_manager.stop()
        await output_manager.stop()
        await broker_client.disconnect()
        if server_started_by_us:
            await broker_runtime.stop_server()
        
        # Assert reasonable latency (allow higher for stress tests)
        if input_config <= 50:
            assert stats_data[0]["median_ms"] < 50, \
                f"E2E latency {stats_data[0]['median_ms']:.2f}ms exceeds threshold for {input_config} inputs"
        else:
            assert stats_data[0]["median_ms"] < 100, \
                f"E2E latency {stats_data[0]['median_ms']:.2f}ms exceeds threshold for {input_config} inputs"
        
        # Print summary
        print(f"\nE2E Test {input_config} inputs: median={stats_data[0]['median_ms']:.2f}ms, "
              f"max={stats_data[0]['max_ms']:.2f}ms, drops={drops} ({drop_rate*100:.1f}%)")
