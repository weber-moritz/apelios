import asyncio
import contextlib
import logging
import time
from typing import Optional

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.broker_client import BrokerClient
from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager

logger = logging.getLogger(__name__)

class MainOrchestrator:
    def __init__(
        self, 
        broker_provider: str = "nats", 
        broker_manager: Optional[BrokerRuntimeManager] = None,
        middleware_manager: Optional[MiddlewareRuntimeManager] = None,
        input_manager: Optional[InputRuntimeManager] = None,
    ):
        # Dependency injection for testability
        self.broker_manager = broker_manager or BrokerRuntimeManager(provider=broker_provider)

        # Each subsystem gets its own broker client connection.
        # Input publishes and middleware subscribes — they must be on separate
        # connections because nats-py does not echo messages back to the same
        # connection that published them (no-echo behaviour).
        self.middleware_manager = middleware_manager or MiddlewareRuntimeManager(
            broker_client=BrokerClient(provider=broker_provider),
        )
        self.input_manager = input_manager or InputRuntimeManager(
            broker_client=BrokerClient(provider=broker_provider),
        )
        
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

        await self.input_manager.start()
        await self.input_manager.start_registered_adapters()
        logger.info("Input runtime started")
        
        self._running = True

    async def stop(self) -> None:
        logger.info("Stopping...")
        if not self._running:
            with contextlib.suppress(Exception):
                await self.input_manager.stop_registered_adapters()
                await self.input_manager.stop()
            with contextlib.suppress(Exception):
                await self.broker_manager.stop_server()
            return

        # 1. Stop gracefully in reverse order (Subsystems first)
        await self.input_manager.stop_registered_adapters()
        await self.input_manager.stop()
        logger.info("Stopped input")

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
        input_healthy = self.input_manager.is_running()
        
        if not middleware_healthy:
            logger.error("Health Check Failed: Middleware is not running.")
        if not input_healthy:
            logger.error("Health Check Failed: Input runtime is not running.")
            
        return broker_healthy and middleware_healthy and input_healthy

    def is_running(self) -> bool:
        return self._running

    async def run_forever(self) -> None:
        await self.start()
        try:
            # The 60Hz Engine (1 second / 60 frames = 0.0166 seconds per frame)
            target_interval = 1.0 / 60.0
            
            while True:
                loop_start = time.monotonic()
                
                # 1. Collect one frame of normalized input events.
                await self.input_manager.tick(dt=target_interval)

                # 2. Process one frame of the lighting universe.
                await self.middleware_manager.tick()
                
                # 3. Calculate how long the math took, and sleep for the exact remainder 
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