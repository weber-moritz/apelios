"""In-memory broker runtime manager for local development and testing.

Provides a lightweight, zero-dependency broker implementation that doesn't
require any external server or subprocess.
"""

from .broker_interface import BrokerInterface


class MemoryRuntimeManager(BrokerInterface):
    """In-memory broker that requires no external dependencies.
    
    Useful for:
    - Local development without NATS server
    - Unit testing
    - CI/CD environments
    """
    
    def __init__(self, config=None):
        """Initialize memory broker runtime manager.
        
        Args:
            config: Optional configuration (ignored for memory broker)
        """
        self._running = False
    
    async def start_server(self) -> None:
        """Start the in-memory broker (no-op, always succeeds)."""
        self._running = True
    
    async def stop_server(self) -> None:
        """Stop the in-memory broker (no-op, always succeeds)."""
        self._running = False
    
    async def health_check(self, timeout: int = 5) -> bool:
        """Check if broker is healthy.
        
        Args:
            timeout: Timeout in seconds (ignored for memory broker)
            
        Returns:
            True: Always healthy for memory broker
        """
        return True
    
    def is_running(self) -> bool:
        """Check if broker is running.
        
        Returns:
            True: Always running for memory broker
        """
        return self._running
