from pathlib import Path
import subprocess
import asyncio
import time

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

        log_path = self.log_dir / "nats-server.log"
        self.log_file = open(log_path, "a", buffering=1)

        self.process = subprocess.Popen(
            ["nats-server", "-p", str(self.port)],
            stdout=self.log_file,
            stderr=self.log_file,
        )

        await self.health_check(timeout=5)

    async def stop_server(self) -> None:
        if self.process is None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()

        self.process = None

        if self.log_file is not None:
            self.log_file.close()
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

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

