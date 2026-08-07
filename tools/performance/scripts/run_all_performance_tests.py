#!/usr/bin/env python3
"""
CLI Runner for Apelios Performance Testing Framework.

Runs all performance tests (E2E, per-layer, module) and generates standardized plots.

Usage:
    python tools/performance/scripts/run_all_performance_tests.py --output-dir results/ --plot
    python tools/performance/scripts/run_all_performance_tests.py --e2e --output-dir results/
    python tools/performance/scripts/run_all_performance_tests.py --dry-run
"""

import argparse
import subprocess
import sys
import os
import time
from pathlib import Path
from datetime import datetime
import shutil
import socket


def is_port_in_use(port):
    """Check if a port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(('127.0.0.1', port))
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def start_nats_server():
    """Start NATS server if not already running. Returns the process object."""
    if is_port_in_use(4222):
        print("NATS server already running on port 4222")
        return None
    
    # Try to find nats-server binary
    nats_paths = [
        shutil.which("nats-server"),
        str(Path(sys.executable).with_name("nats-server")),
        "/usr/local/bin/nats-server",
    ]
    
    nats_server_path = None
    for path in nats_paths:
        if not path:
            continue
        p = Path(path)
        if p.is_file():
            nats_server_path = path
            break
    
    if nats_server_path is None:
        print("WARNING: NATS server binary not found at:")
        for p in nats_paths:
            print(f"  - {p}")
        print("Please start NATS server manually: nats-server -p 4222 -m 8223 &")
        return None
    
    try:
        print(f"Starting NATS server from {nats_server_path}...")
        proc = subprocess.Popen(
            [nats_server_path, "-p", "4222", "-m", "8223"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        # Wait for server to start
        max_attempts = 30
        for _ in range(max_attempts):
            if is_port_in_use(4222):
                print("NATS server started on port 4222")
                return proc
            time.sleep(0.1)
        
        # Failed to start
        proc.terminate()
        proc.wait(timeout=5)
        print("WARNING: Failed to start NATS server. Please start it manually.")
        return None
    except Exception as e:
        print(f"WARNING: Error starting NATS server: {e}. Please start it manually.")
        return None


def run_pytest(test_file, verbose=False, dry_run=False, results_dir=None):
    """Run pytest on a test file."""
    cmd = [sys.executable, "-m", "pytest", str(test_file), "--tb=short", "-p", "no:qt"]
    
    if verbose:
        cmd.append("-v")
    
    if results_dir:
        cmd.extend(["--results-dir", str(results_dir)])
    
    if dry_run:
        print("[DRY RUN] " + " ".join(cmd))
        return 0
    
    # Run pytest
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    
    return result.returncode


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Performance Test Runner')
    parser.add_argument('--output-dir', type=str, default='results')
    parser.add_argument('--plot', action='store_true', default=True)
    parser.add_argument('--e2e', action='store_true')
    parser.add_argument('--layer', action='store_true')
    parser.add_argument('--module', action='store_true')
    parser.add_argument('--all', action='store_true', default=True)
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Start NATS server if needed (for E2E and layer tests)
    nats_proc = None
    if args.e2e or args.layer or (args.all and not args.module):
        nats_proc = start_nats_server()
        if nats_proc is None:
            print("\nWARNING: NATS server not available. E2E and layer tests will fail.")
            print("To run these tests, start NATS server manually:")
            print("  nats-server -p 4222 -m 8223 &")
    
    try:
        # Create timestamped results directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path(args.output_dir) / timestamp
        results_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Results directory: {results_dir}")
        
        # Determine which tests to run
        tests_to_run = []
        if args.all or (not args.e2e and not args.layer and not args.module):
            tests_to_run = ['e2e', 'layer', 'module']
        else:
            if args.e2e:
                tests_to_run.append('e2e')
            if args.layer:
                tests_to_run.append('layer')
            if args.module:
                tests_to_run.append('module')
        
        # Define test files
        scripts_dir = Path(__file__).parent
        tests_dir = scripts_dir.parent / "tests"
        
        test_files = {
            'e2e': tests_dir / "test_e2e_latency.py",
            'layer': tests_dir / "test_layer_latency.py",
            'module': tests_dir / "test_module_latency.py"
        }
        
        # Run tests
        any_failed = False
        for test_type in tests_to_run:
            test_file = test_files[test_type]
            if test_file.exists():
                print(f"\n=== Running {test_type} tests ===")
                returncode = run_pytest(
                    test_file,
                    verbose=args.verbose,
                    dry_run=args.dry_run,
                    results_dir=results_dir
                )
                if returncode != 0:
                    print(f"WARNING: {test_type} tests failed with return code {returncode}")
                    any_failed = True
        
        # Generate plots
        if args.plot and not args.dry_run:
            print("\n=== Generating plots ===")
            try:
                from plot_results import generate_all_plots
                generate_all_plots(results_dir)
            except ImportError:
                print("WARNING: plot_results module not found. Plots not generated.")
            except Exception as e:
                print(f"WARNING: Error generating plots: {e}")
        
        # Summary
        if args.dry_run:
            print("\n[DRY RUN] No tests were actually executed")
        elif any_failed:
            print(f"\nSome tests failed. Check output above.")
        else:
            print(f"\nAll tests completed successfully!")
        
        print(f"Results and plots saved to: {results_dir}")
    finally:
        # Cleanup NATS server
        if nats_proc is not None:
            try:
                nats_proc.terminate()
                nats_proc.wait(timeout=5)
                print("\nNATS server stopped")
            except Exception:
                pass


if __name__ == "__main__":
    main()
