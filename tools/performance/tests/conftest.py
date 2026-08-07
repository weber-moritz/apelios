"""
Pytest fixtures for performance testing framework.
Provides NATS Broker setup and shared test configurations.
"""

import pytest
import time
import subprocess
import sys
import os
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


# Pytest hook to add custom command line options
def pytest_addoption(parser):
    """Add custom command line options for performance tests."""
    parser.addoption(
        "--results-dir",
        type=str,
        default=None,
        help="Directory to save test results (defaults to pytest's tmp_path)"
    )


@pytest.fixture
def results_dir(request, tmp_path):
    """
    Fixture providing the results directory.
    
    Priority:
    1. --results-dir command line option
    2. PERF_RESULTS_DIR environment variable
    3. pytest's tmp_path (default)
    
    Returns:
        Path: The directory where test results should be saved.
    """
    # Check command line option first
    custom_dir = request.config.getoption("--results-dir")
    if custom_dir:
        results_path = Path(custom_dir)
        results_path.mkdir(parents=True, exist_ok=True)
        return results_path
    
    # Check environment variable
    env_dir = os.environ.get("PERF_RESULTS_DIR")
    if env_dir:
        results_path = Path(env_dir)
        results_path.mkdir(parents=True, exist_ok=True)
        return results_path
    
    # Fall back to pytest's tmp_path
    return tmp_path


# Test configurations
E2E_CONFIGS = [1, 10, 25, 50, 100]
LAYER_CONFIGS = [1, 10, 25, 50, 100]
FIXTURE_LAYER_CONFIGS = [1, 10, 25, 50, 100]  # All configurations after schema fix
MODULE_CONFIGS = [1, 5, 10, 25, 50, 100]

# Timing constants
TARGET_INTERVAL = 1.0 / 60.0  # 16.67ms per frame (60Hz)
FRAMES_PER_CONFIG = 600  # 10 seconds at 60Hz
MODULE_ITERATIONS = 10000  # High iteration count for module tests

# Color scheme for plots
LAYER_COLORS = {
    "input": "#9b59b6",  # purple
    "router": "#3498db",  # blue
    "fixture": "#e74c3c",  # red
    "output": "#f39c12",  # orange
    "full": "#2ecc71",  # green
    "e2e": "#2ecc71",  # green
}


@pytest.fixture(scope="session")
def nats_server():
    """
    Start NATS server for the test session.
    
    Tries to connect to existing NATS server first.
    If not available, starts a local NATS server via subprocess.
    
    Yields:
        str: NATS server URL (e.g., "localhost:4222")
    """
    import nats
    
    # First, try to connect to existing NATS server (with short timeout)
    try:
        nc = nats.connect(servers=["nats://localhost:4222"], reconnect=False, connect_timeout=2)
        nc.close()
        yield "localhost:4222"
        return
    except Exception:
        pass
    
    # If no existing server, start one via subprocess
    # Try various locations for nats-server binary
    nats_paths = [
        shutil.which("nats-server"),
        str(Path(sys.executable).with_name("nats-server")),
        "/usr/local/bin/nats-server",
        str(Path.home() / "nats-server" / "nats-server"),
        str(Path(__file__).parent.parent.parent.parent / "vendor" / "nats-server" / "nats-server"),
    ]
    
    nats_server_path = None
    for path in nats_paths:
        if path and Path(path).is_file():
            nats_server_path = path
            break
    
    if nats_server_path is None:
        pytest.skip("NATS server binary not found. Please install NATS server.")
    
    # Start NATS server
    proc = subprocess.Popen(
        [nats_server_path, "-p", "4222", "-m", "8223"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    
    # Wait for server to start
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            nc = nats.connect(servers=["nats://localhost:4222"], reconnect=False, connect_timeout=1)
            nc.close()
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        proc.wait(timeout=5)
        pytest.skip("NATS server failed to start within timeout")
    
    yield "localhost:4222"
    
    # Cleanup: terminate NATS server
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture
def nats_client(nats_server):
    """
    Create a NATS client connected to the server.
    
    Args:
        nats_server: NATS server URL from nats_server fixture
        
    Yields:
        nats.Connection: Connected NATS client
    """
    import nats
    
    nc = nats.connect(servers=[f"nats://{nats_server}"])
    yield nc
    nc.close()




# E2E Test Fixtures

@pytest.fixture(params=E2E_CONFIGS)
def e2e_config(request):
    """Pytest fixture providing E2E test input configurations."""
    return request.param


# Per-Layer Test Fixtures

@pytest.fixture(params=LAYER_CONFIGS)
def layer_config(request):
    """Pytest fixture providing per-layer test input configurations."""
    return request.param


@pytest.fixture(params=["input", "router", "fixture", "output", "full"])
def layer_name(request):
    """Pytest fixture for layer selection."""
    return request.param


# Module Test Fixtures

@pytest.fixture(params=MODULE_CONFIGS)
def module_config(request):
    """Pytest fixture providing module test item configurations."""
    return request.param


# Router Profile Fixtures

@pytest.fixture
def router_profile_1():
    """Router profile with 1 input mapping."""
    return {"input.test_0.value": "target.test_0.param"}


# Router Profile Functions (not fixtures - they take n as parameter)
def router_profile_n(n):
    """Router profile with n input mappings."""
    return {f"input.test_{i}.value": f"test_{i}.param" for i in range(n)}


# Fixture Patch Fixtures

@pytest.fixture
def fixture_patch_1():
    """Fixture patch with 1 dimmer fixture."""
    return {
        "fixtures": {
            "test_0": {
                "universe": 0,
                "address": 0,
                "type": "dimmer",
                "parameters": {
                    "param": {"width": 8, "limits": [0.0, 1.0]}
                }
            }
        }
    }


# Fixture Patch Functions (not fixtures - they take n as parameter)
def fixture_patch_n(n):
    """Fixture patch with n dimmer fixtures.
    
    Schema matches the actual fixture patch format:
    - universe and address at the fixture level
    - parameters at the parameter level with width, limits, etc.
    """
    return {
        "fixtures": {
            f"test_{i}": {
                "universe": 0,
                "address": i,  # Each fixture at a unique DMX address
                "type": "dimmer",
                "parameters": {
                    "param": {"width": 8, "limits": [0.0, 1.0]}
                }
            }
            for i in range(n)
        }
    }


# Shared test utilities

def save_test_metadata(outputs_dir, test_type, config, frames=None, iterations=None, **extra):
    """
    Save test metadata to JSON file.
    
    Args:
        outputs_dir: Path to output directory
        test_type: Type of test (e2e, layer, module)
        config: Configuration value
        frames: Number of frames (for E2E/layer tests)
        iterations: Number of iterations (for module tests)
        **extra: Additional metadata fields
    """
    import json
    import socket
    import platform
    
    metadata = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "test_type": test_type,
        **extra
    }
    
    if frames is not None:
        metadata["frames"] = frames
    if iterations is not None:
        metadata["iterations"] = iterations
    if config is not None:
        metadata["config"] = config
    
    metadata["system_info"] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname()
    }
    
    with (outputs_dir / "test_metadata.json").open('w') as f:
        json.dump(metadata, f, indent=2)


def save_csv_results(outputs_dir, filename, data, fieldnames):
    """
    Save test results to CSV file.
    
    Args:
        outputs_dir: Path to output directory
        filename: CSV filename (without extension)
        data: List of dictionaries with data rows
        fieldnames: List of field names for CSV header
    """
    import csv
    
    with (outputs_dir / f"{filename}.csv").open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
