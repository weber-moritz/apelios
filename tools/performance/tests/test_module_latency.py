"""
Module Latency Tests for Apelios Performance Testing Framework.

Deep-dive profiling of specific functions identified as slow by per-layer tests.
Uses direct method calls (no NATS Broker, no 60Hz tick) for precise function timing.

Usage:
    python -m pytest tools/performance/tests/test_module_latency.py -v
    python -m pytest tools/performance/tests/test_module_latency.py::TestFixtureModule::test_process_frame_latency[10] -v
"""

import pytest
import time
import csv
import json
import statistics
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from apelios.router.router_core import MappingRouter
from apelios.fixture.fixture_core import FixtureCore
from apelios.fixture.fixture_output_publisher import FixtureOutputPublisher

from .conftest import (
    MODULE_CONFIGS, MODULE_ITERATIONS,
    save_test_metadata, save_csv_results,
    router_profile_n, fixture_patch_n
)


class TestRouterModule:
    """Module-level tests for router layer functions."""
    
    @pytest.mark.parametrize("n_inputs", MODULE_CONFIGS)
    def test_handle_input_latency(self, n_inputs, results_dir):
        """
        Test MappingRouter.handle_input() latency with direct calls.
        
        Measures raw function performance without NATS Broker or tick overhead.
        
        Args:
            n_inputs: Number of inputs to test (1, 5, 10, 25, 50, 100)
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "module" / "router" / "handle_input"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup router with profile
        profile = router_profile_n(n_inputs)
        router = MappingRouter(profile=profile)
        
        # Warmup
        for i in range(n_inputs):
            router.handle_input(f"input.test_{i}.value", 0.5, "absolute_uni")
        
        # Test: Call handle_input for all inputs, measure total time
        latencies = []
        for _ in range(MODULE_ITERATIONS):
            start = time.perf_counter()
            for i in range(n_inputs):
                router.handle_input(f"input.test_{i}.value", 0.5, "absolute_uni")
            latency = (time.perf_counter() - start) * 1000
            # Normalize to per-input latency
            latencies.append(latency / n_inputs)
        
        # Save results
        self._save_module_results(
            outputs_dir, n_inputs, "router", "handle_input", latencies
        )
        
        # Router should be very fast (< 0.1ms per input)
        median_lat = statistics.median(latencies) if latencies else 0
        assert median_lat < 0.1, f"handle_input latency {median_lat:.6f}ms too high"
        
        print(f"\nRouter.handle_input {n_inputs} inputs: median={median_lat:.6f}ms")
    
    def _save_module_results(self, outputs_dir, config, module, function, latencies):
        """Save module test results to CSV files."""
        # Save raw results
        results_data = []
        for i, lat in enumerate(latencies):
            results_data.append({
                "config_inputs": config,
                "iteration": i,
                "latency_ms": lat
            })
        
        save_csv_results(
            outputs_dir,
            "results",
            results_data,
            ["config_inputs", "iteration", "latency_ms"]
        )
        
        # Save statistics
        if latencies:
            stats_data = [{
                "config_inputs": config,
                "count": len(latencies),
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "mean_ms": statistics.mean(latencies),
                "median_ms": statistics.median(latencies),
                "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0
            }]
        else:
            stats_data = [{
                "config_inputs": config,
                "count": 0,
                "min_ms": 0,
                "max_ms": 0,
                "mean_ms": 0,
                "median_ms": 0,
                "std_dev_ms": 0
            }]
        
        save_csv_results(
            outputs_dir,
            "statistics",
            stats_data,
            ["config_inputs", "count", "min_ms", "max_ms", 
             "mean_ms", "median_ms", "std_dev_ms"]
        )
        
        # Save metadata
        save_test_metadata(
            outputs_dir,
            "module",
            {"module": module, "function": function, "config_inputs": config},
            iterations=len(latencies)
        )


class TestFixtureModule:
    """Module-level tests for fixture layer functions."""
    
    @pytest.mark.parametrize("n_fixtures", MODULE_CONFIGS)
    def test_process_frame_latency(self, n_fixtures, results_dir):
        """
        Test FixtureCore.process_frame() latency with direct calls.
        
        Measures raw function performance without NATS Broker or tick overhead.
        
        Args:
            n_fixtures: Number of fixtures to test (1, 5, 10, 25, 50, 100)
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "module" / "fixture" / "process_frame"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup fixture core with patch
        patch = fixture_patch_n(n_fixtures)
        core = FixtureCore(patch=patch)
        
        # Warmup
        for i in range(n_fixtures):
            core.inbox[f"target.test_{i}.param"] = {
                "source": f"input.test_{i}",
                "value": 0.5,
                "type": "absolute_uni",
                "timestamp": time.time()
            }
        core.process_frame(dt=0.016)
        
        # Test: Call process_frame with populated inbox
        latencies = []
        for _ in range(MODULE_ITERATIONS):
            # Re-populate inbox
            for i in range(n_fixtures):
                core.inbox[f"target.test_{i}.param"] = {
                    "source": f"input.test_{i}",
                    "value": 0.5,
                    "type": "absolute_uni",
                    "timestamp": time.time()
                }
            
            start = time.perf_counter()
            core.process_frame(dt=0.016)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
        
        # Save results
        router_test = TestRouterModule()
        router_test._save_module_results(
            outputs_dir, n_fixtures, "fixture", "process_frame", latencies
        )
        
        # Fixture processing is known to be slower
        median_lat = statistics.median(latencies) if latencies else 0
        assert median_lat < 10.0, f"process_frame latency {median_lat:.2f}ms too high"
        
        print(f"\nFixture.process_frame {n_fixtures} fixtures: median={median_lat:.2f}ms")


class TestOutputModule:
    """Module-level tests for output layer functions."""
    
    @pytest.mark.parametrize("n_universes", [1])  # Test with 1 universe only due to high message count
    def test_publish_dmx_latency(self, n_universes, results_dir):
        """
        Test OutputPublisher.publish_dmx() latency with direct calls.
        
        Measures raw function performance without NATS Broker overhead.
        Uses mock broker for timing.
        
        Args:
            n_universes: Number of DMX universes to test
            results_dir: Directory to save results
        """
        outputs_dir = results_dir / "module" / "output" / "publish_dmx"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock broker that captures publish timing
        from unittest.mock import AsyncMock, MagicMock
        import asyncio
        
        mock_broker = MagicMock()
        mock_broker.publish = AsyncMock()
        
        publisher = FixtureOutputPublisher(broker=mock_broker)
        
        # Create DMX output for n_universes in the format dict[tuple[int, int], int]
        # Each universe has 512 addresses, each with value 128
        dmx_output = {
            (universe, address): 128
            for universe in range(n_universes)
            for address in range(512)
        }
        
        # Use a single event loop for all iterations
        # Reduce iterations for this test (512 messages per call * 100 iterations = 51.2k messages)
        test_iterations = min(MODULE_ITERATIONS, 100)
        
        async def run_test():
            # Warmup
            await publisher.publish_dmx(dmx_output)
            
            # Test
            latencies = []
            for _ in range(test_iterations):
                start = time.perf_counter()
                await publisher.publish_dmx(dmx_output)
                latency = (time.perf_counter() - start) * 1000
                latencies.append(latency)
            return latencies
        
        latencies = asyncio.run(run_test())
        
        # Save results
        router_test = TestRouterModule()
        router_test._save_module_results(
            outputs_dir, n_universes, "output", "publish_dmx", latencies
        )
        
        # Output publishing latency check (512 DMX values per call)
        median_lat = statistics.median(latencies) if latencies else 0
        # Allow higher threshold for DMX publishing (512 addresses per universe)
        assert median_lat < 20.0, f"publish_dmx latency {median_lat:.4f}ms too high"
        
        print(f"\nOutput.publish_dmx {n_universes} universes: median={median_lat:.4f}ms")