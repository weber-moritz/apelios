from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class NatsConfig:
    host: str = "127.0.0.1"
    port: int = 4222
    log_dir: Path = Path("logs")


def load_nats_config() -> NatsConfig:
    host = os.getenv("APELIOS_NATS_HOST", "127.0.0.1")
    port = int(os.getenv("APELIOS_NATS_PORT", "4222"))
    log_dir = Path(os.getenv("APELIOS_NATS_LOG_DIR", "logs"))
    return NatsConfig(host=host, port=port, log_dir=log_dir)