from pathlib import Path
import os
import subprocess
import asyncio
import signal
import time
import socket

from .broker_interface import BrokerInterface
from .config import NatsConfig, load_nats_config


class NatsRuntimeManager(BrokerInterface):
    def __init__(self, config: NatsConfig | None = None):
        cfg = config or load_nats_config()

        self.port = cfg.port
        self.host = cfg.host
        self.process = None
        self.log_file = None
        self.log_dir = Path(cfg.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.server_url = f"nats://{self.host}:{self.port}"

    async def start_server(self) -> None:
        if self.process is not None:
            raise RuntimeError("NATS server already running")

        # Kill any stale nats-server processes on our port
        self._kill_stale_nats_servers()

        # Wait for killed processes to release the port
        await asyncio.sleep(0.5)

        # Check if port is already in use before starting
        if self._is_port_in_use(self.port):
            raise RuntimeError(
                f"Port {self.port} is already in use. "
                "Another NATS server may be running, or a previous instance crashed."
            )

        log_path = self.log_dir / "nats-server.log"
        self.log_file = open(log_path, "a", buffering=1)

        self.process = subprocess.Popen(
            ["nats-server", "-p", str(self.port)],
            stdout=self.log_file,
            stderr=self.log_file,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

        try:
            await self.health_check(timeout=5)
        except Exception:
            # Clean up if health check fails
            await self.stop_server()
            raise

    async def stop_server(self) -> None:
        if self.process is None:
            return

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        except ProcessLookupError:
            # Process already dead, still try to clean up
            pass
        finally:
            self.process = None

        if self.log_file is not None:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None

    async def health_check(self, timeout: int = 5) -> bool:
        import nats

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                nc = await nats.connect(self.server_url)
                await nc.close()
                return True
            except Exception:
                await asyncio.sleep(0.2)

        raise RuntimeError(f"NATS server not responding after {timeout}s")

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('0.0.0.0', port))
                return False
            except OSError:
                return True

    def _kill_stale_nats_servers(self) -> None:
        """Kill any existing nats-server processes that might be using our port."""
        try:
            # Find all nats-server processes
            result = subprocess.run(
                ["pgrep", "-f", "nats-server"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                for pid_str in result.stdout.strip().split('\n'):
                    try:
                        pid = int(pid_str.strip())
                        os.kill(pid, signal.SIGTERM)
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        except Exception:
            pass  # Ignore errors, we'll catch them in the port check

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

