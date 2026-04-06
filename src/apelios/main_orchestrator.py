import asyncio
import contextlib
from typing import Optional
import logging

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager

logger = logging.getLogger(__name__)

class MainOrchestrator:
    def __init__(self, provider: str = "nats", broker_manager: Optional[BrokerRuntimeManager] = None):
        # Dependency injection keeps this testable.
        self.broker_manager = broker_manager or BrokerRuntimeManager(provider=provider)
        self._running = False
        
    async def start(self) -> None:
        logger.info("Starting orchestrator...")
        if self._running:
            logger.debug("Already running, skipping start")
            return
        await self.broker_manager.start_server()
        logger.info("Broker runtime started")
        self._running = True

    async def stop(self) -> None:
        logger.info("Stopping...")
        if not self._running:
            # Still call stop to be defensive if partial startup happened.
            with contextlib.suppress(Exception):
                await self.broker_manager.stop_server()
            return

        await self.broker_manager.stop_server()
        logger.info("Stopped broker")
        self._running = False

    async def health_check(self, timeout: int = 5) -> bool:
        return await self.broker_manager.health_check(timeout=timeout)

    def is_running(self) -> bool:
        return self.broker_manager.is_running()

    async def run_forever(self) -> None:
        await self.start()
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            await self.stop()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = MainOrchestrator(provider="nats")
    await orchestrator.run_forever()

if __name__ == "__main__":
    asyncio.run(main())