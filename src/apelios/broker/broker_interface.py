from abc import ABC, abstractmethod


class BrokerInterface(ABC):
    """Abstract interface for broker runtime management."""

    @abstractmethod
    async def start_server(self) -> None:
        """Start the broker server."""
        pass

    @abstractmethod
    async def stop_server(self) -> None:
        """Stop the broker server."""
        pass

    @abstractmethod
    async def health_check(self, timeout: int = 5) -> bool:
        """Check if broker is healthy."""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if broker process is running."""
        pass