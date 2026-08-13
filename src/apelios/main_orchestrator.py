import asyncio
import logging
import signal
import time
from typing import Optional

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.broker_client import BrokerClient
from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.router.router_runtime_manager import RouterRuntimeManager

logger = logging.getLogger(__name__)

from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager
from apelios.output.output_runtime_manager import OutputRuntimeManager

class MainOrchestrator:
    def __init__(
        self, 
        broker_provider: str = "nats", 
        broker_manager: Optional[BrokerRuntimeManager] = None,
        router_manager: Optional[RouterRuntimeManager] = None,
        input_manager: Optional[InputRuntimeManager] = None,
        fixture_manager: Optional[FixtureRuntimeManager] = None,
        output_manager: Optional[OutputRuntimeManager] = None,
    ):
        # Dependency injection for testability
        self.broker_manager = broker_manager or BrokerRuntimeManager(provider=broker_provider)

        self.router_manager = router_manager or RouterRuntimeManager(
            broker_client=BrokerClient(provider=broker_provider),
        )
        self.input_manager = input_manager or InputRuntimeManager(
            broker_client=BrokerClient(provider=broker_provider),
        )
        self.fixture_manager = fixture_manager or FixtureRuntimeManager(
            broker_client=BrokerClient(provider=broker_provider),
        )
        self.output_manager = output_manager or OutputRuntimeManager(
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

        # 2. Layers: starting in reverse dataflow sequence
        await self.output_manager.start()
        logger.info("Output runtime started")

        await self.fixture_manager.start()
        logger.info("Fixture runtime started")

        await self.router_manager.start()
        logger.info("Router runtime started")

        await self.input_manager.start()
        await self.input_manager.start_registered_adapters()
        logger.info("Input runtime started")

        self._running = True

    async def stop(self) -> None:
        logger.info("Stopping...")
        cleanup_errors = []

        async def cleanup(label: str, operation) -> None:
            try:
                await operation()
                logger.info("Stopped %s", label)
            except Exception as exc:
                logger.exception("Failed to stop %s", label)
                cleanup_errors.append(exc)

        # Stop clients before infrastructure. Run every cleanup step even if an
        # earlier layer fails so the owned NATS process cannot be orphaned.
        await cleanup("input adapters", self.input_manager.stop_registered_adapters)
        await cleanup("input", self.input_manager.stop)
        await cleanup("router", self.router_manager.stop)
        await cleanup("fixture layer", self.fixture_manager.stop)
        await cleanup("output layer", self.output_manager.stop)
        await cleanup("broker", self.broker_manager.stop_server)

        self._running = False
        if cleanup_errors:
            raise cleanup_errors[0]

    async def health_check(self, timeout: int = 5) -> bool:
        """Verify all critical subsystems are alive."""
        broker_healthy = await self.broker_manager.health_check(timeout=timeout)

        router_healthy = self.router_manager.is_running()
        input_healthy = self.input_manager.is_running()
        fixture_healthy = self.fixture_manager.is_running()
        output_healthy = self.output_manager.is_running()

        if not router_healthy:
            logger.error("Health Check Failed: Router is not running.")
        if not input_healthy:
            logger.error("Health Check Failed: Input runtime is not running.")
        if not fixture_healthy:
            logger.error("Health Check Failed: Fixture runtime is not running.")
        if not output_healthy:
            logger.error("Health Check Failed: Output runtime is not running.")

        return broker_healthy and router_healthy and input_healthy and fixture_healthy and output_healthy

    def is_running(self) -> bool:
        return self._running

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        stop_event = stop_event or asyncio.Event()
        try:
            await self.start()
            # The 60Hz Engine (1 second / 60 frames = 0.0166 seconds per frame)
            target_interval = 1.0 / 60.0

            while not stop_event.is_set():
                loop_start = time.monotonic()

                # 1. Collect one frame of normalized input events.
                await self.input_manager.tick(dt=target_interval)

                # 2. Process one frame of the lighting universe.
                await self.router_manager.tick()

                # 3. Process one frame of the fixture layer.
                await self.fixture_manager.tick(dt=target_interval)

                # 4. Process one frame of the output layer.
                await self.output_manager.tick(dt=target_interval)

                # 5. Calculate how long the math took, and sleep for the exact remainder 
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
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    installed_signals = []

    # Request shutdown between frames instead of cancelling a NATS operation in
    # progress. This avoids leaving nats-py's internal flush state half-cancelled.
    for signum in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGHUP", None)):
        if signum is None:
            continue
        try:
            loop.add_signal_handler(signum, stop_event.set)
            installed_signals.append(signum)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        await orchestrator.run_forever(stop_event=stop_event)
    except asyncio.CancelledError:
        # SIGINT/SIGTERM/SIGHUP cancel the main task; run_forever's finally
        # block has already completed ordered shutdown.
        pass
    finally:
        for signum in installed_signals:
            loop.remove_signal_handler(signum)

if __name__ == "__main__":
    asyncio.run(main())
