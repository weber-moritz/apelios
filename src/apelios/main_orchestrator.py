import asyncio
import contextlib
import logging
import time
from typing import Optional

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager

logger = logging.getLogger(__name__)

class MainOrchestrator:
    def __init__(
        self, 
        broker_provider: str = "nats", 
        broker_manager: Optional[BrokerRuntimeManager] = None,
        middleware_manager: Optional[MiddlewareRuntimeManager] = None
    ):
        # Dependency injection for testability
        self.broker_manager = broker_manager or BrokerRuntimeManager(provider=broker_provider)
        
        # pass a broker client here to have all dependecies clear in the main orchestrator
        self.middleware_manager = middleware_manager or MiddlewareRuntimeManager()
        
        self._running = False
        
    async def start(self) -> None:
        logger.info("Starting orchestrator...")
        if self._running:
            logger.debug("Already running, skipping start")
            return
            
        # 1. Start the Infrastructure FIRST (The NATS Server)
        await self.broker_manager.start_server()
        logger.info("Broker runtime started")

        # 2. Start the Subsystems SECOND (Middleware connects to the server)
        await self.middleware_manager.start()
        logger.info("Middleware runtime started")
        
        self._running = True

    async def stop(self) -> None:
        logger.info("Stopping...")
        if not self._running:
            with contextlib.suppress(Exception):
                await self.broker_manager.stop_server()
            return

        # 1. Stop gracefully in reverse order (Subsystems first)
        await self.middleware_manager.stop()
        logger.info("Stopped middleware")

        # 2. Stop Infrastructure last
        await self.broker_manager.stop_server()
        logger.info("Stopped broker")
        
        self._running = False

    async def health_check(self, timeout: int = 5) -> bool:
        """Verify all critical subsystems are alive."""
        broker_healthy = await self.broker_manager.health_check(timeout=timeout)
        
        # We use the is_running() method you already wrote as a basic health check!
        middleware_healthy = self.middleware_manager.is_running()
        
        if not middleware_healthy:
            logger.error("Health Check Failed: Middleware is not running.")
            
        return broker_healthy and middleware_healthy

    def is_running(self) -> bool:
        return self._running

    async def run_forever(self) -> None:
        await self.start()
        try:
            # The 60Hz Engine (1 second / 60 frames = 0.0166 seconds per frame)
            target_interval = 1.0 / 60.0
            
            while True:
                loop_start = time.monotonic()
                
                # 1. Process one frame of the lighting universe
                await self.middleware_manager.tick()
                
                # 2. Calculate how long the math took, and sleep for the exact remainder 
                #    to maintain a perfect 60Hz frequency without drifting.
                elapsed = time.monotonic() - loop_start
                sleep_time = target_interval - elapsed
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    # If math took longer than 16ms, we dropped a frame! 
                    # Yield to the async event loop anyway to prevent the program from locking up.
                    logger.debug("Dropped frame: tick took too long")
                    await asyncio.sleep(0)
                    
        finally:
            await self.stop()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    orchestrator = MainOrchestrator(broker_provider="nats")
    await orchestrator.run_forever()

if __name__ == "__main__":
    asyncio.run(main())