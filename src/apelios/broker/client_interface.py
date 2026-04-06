from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

Callback = Callable[[Any], Awaitable[None] | None]


class BrokerClientInterface(ABC):
    """Abstract interface for broker client operations."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to broker."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker."""

    @abstractmethod
    async def publish(self, subject: str, message: bytes) -> None:
        """Publish message to subject."""

    @abstractmethod
    async def subscribe(self, subject: str, callback: Callback) -> None:
        """Subscribe to subject with callback."""