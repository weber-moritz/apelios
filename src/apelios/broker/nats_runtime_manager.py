from pathlib import Path
import os
import subprocess
import asyncio
import signal
import socket
import atexit
import ctypes
import shutil
import sys
from functools import partial

from .broker_interface import BrokerInterface
from .config import NatsConfig, load_nats_config


def _set_parent_death_signal(expected_parent_pid: int) -> None:
    """Configure the spawned child, not the parent, to die with Apelios."""
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
        raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG) failed")

    # The parent could have died between Popen() and prctl().
    if os.getppid() != expected_parent_pid:
        os.kill(os.getpid(), signal.SIGTERM)


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

        # Fallback for normal interpreter exit. Ordered application shutdown is
        # owned by MainOrchestrator.
        atexit.register(self._cleanup_on_exit)

    def _find_nats_server(self) -> str | None:
        """Find the nats-server binary in common locations."""
        path_binary = shutil.which("nats-server")
        paths = [
            path_binary,
            str(Path(sys.executable).with_name("nats-server")),
            "/usr/local/bin/nats-server",
            str(Path.home() / "nats-server" / "nats-server"),
            str(Path(__file__).parent.parent.parent.parent / "vendor" / "nats-server" / "nats-server"),
        ]

        for path in paths:
            if path and Path(path).is_file():
                return path
        return None

    async def start_server(self) -> None:
        if self.process is not None:
            raise RuntimeError("NATS server already running")

        # Check if port is already in use before starting - fail fast
        if self._is_port_in_use(self.port):
            raise RuntimeError(
                f"Port {self.port} is already in use. "
                f"Another process may be using it. "
                f"Check with: lsof -i :{self.port} or ss -tlnp | grep {self.port}"
            )

        log_path = self.log_dir / "nats-server.log"
        self.log_file = open(log_path, "a", buffering=1)

        # Try to find nats-server binary
        nats_server_path = self._find_nats_server()
        if not nats_server_path:
            raise RuntimeError(
                "NATS server binary not found. Please install NATS server or set the PATH."
            )

        self.process = subprocess.Popen(
            [nats_server_path, "-p", str(self.port)],
            stdout=self.log_file,
            stderr=self.log_file,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            preexec_fn=self._parent_death_guard(),
        )

        try:
            await self.health_check(timeout=5)
        except Exception:
            # Clean up if health check fails
            await self.stop_server()
            raise

    async def stop_server(self) -> None:
        """Stop the NATS server process and clean up resources.
        
        This method is called explicitly and also registered with atexit
        for automatic cleanup on normal exit.
        """
        self._cleanup_on_exit()

    async def health_check(self, timeout: int = 5) -> bool:
        """Wait until the NATS TCP listener is ready without noisy client logs."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        while loop.time() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(
                    f"NATS server exited with code {self.process.returncode} before becoming ready"
                )

            remaining = deadline - loop.time()
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=min(0.2, remaining),
                )
                del reader
                writer.close()
                await writer.wait_closed()
                return True
            except (OSError, asyncio.TimeoutError):
                await asyncio.sleep(min(0.05, max(0.0, deadline - loop.time())))

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

    def _parent_death_guard(self):
        """Return a Linux child hook that terminates NATS if Apelios disappears."""
        if not sys.platform.startswith("linux"):
            return None
        return partial(_set_parent_death_signal, os.getpid())


    def _cleanup_on_exit(self) -> None:
        """Clean up NATS server process and log file on exit.
        
        Called automatically via atexit and signal handlers.
        Also called by stop_server() for explicit cleanup.
        """
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            except ProcessLookupError:
                # Process already dead
                pass
            except Exception:
                pass
        
        if self.log_file is not None:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None
        
        self.process = None


    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None
