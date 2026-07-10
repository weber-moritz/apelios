---
date: 2026-07-10
state: In Progress # [Draft | In Progress | Done]
---

# Task 012: Output Layer Refactoring - Independent Adapter Loops

## Objective
**Architectural Refactoring:** Transition from orchestrator-coupled adapter sending to independent adapter loops with precise timing control. This fixes the rate limiting drift issue and enables multiple adapters at different rates.

### The Core Problem

The current design has a **fundamental timing flaw**: adapters are called at the orchestrator's tick rate (60Hz) but rate-limit themselves using relative time checks. With a 60Hz orchestrator and 40Hz adapter:

```
Orchestrator Tick:     0ms    16.67ms  33.33ms  50ms    66.67ms  83.33ms  100ms...
Adapter Check:        Send     Skip     Send    Skip    Send    Skip    Send...
Effective Rate:       0ms    (33.33)  (66.67) (100)  => ~30Hz (NOT 40Hz!)
```

**Why:** The relative time check `now - last_send >= interval` doesn't align with the orchestrator's tick timing, causing **timing drift** and **inconsistent effective rates**.

### Solution: Independent Adapter Loops

Each adapter manages its own sending loop at its configured rate:

```
Orchestrator (60Hz):     |-------|-------|-------|-------|
OutputCore:            Updates state on each tick

ArtNet Adapter (40Hz):   |------|------|------|------|
                         Send    Send    Send    Send   (exactly 25ms apart)

sACN Adapter (20Hz):     |---------|---------|---------|
                         Send         Send         Send   (exactly 50ms apart)
```

**Benefits:**
- ✅ Each adapter sends at **exactly** its configured rate
- ✅ No drift or alignment issues
- ✅ Multiple adapters at different rates work naturally
- ✅ Clean separation of concerns (core manages state, adapters manage timing)
- ✅ More extensible (add new adapters without affecting others)

---

## Architectural Design

### Current (Flawed) Architecture

```
┌─────────────────┐
│ Main Orchestrator │ (60Hz)
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ OutputRuntimeManager     │
│ - tick() at 60Hz         │
│ - calls core.process_frame()
└──────────────┬──────────┘
               │
               ▼
┌─────────────────────────┐
│ OutputCore               │
│ - process_frame():       │
│   - for each adapter:    │
│     - adapter.send_dmx() │ ◄── Called 60 times/sec
└──────────────┬──────────┘
               │
               ▼
┌─────────────────────────┐
│ ArtNetAdapter            │
│ - send_dmx():            │
│   - if _should_send():    │ ◄── Rate limiting with DRIFT
│     - actually send      │
└─────────────────────────┘
```

### New (Correct) Architecture

```
┌─────────────────┐
│ Main Orchestrator │ (60Hz)
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ OutputRuntimeManager     │
│ - tick() at 60Hz         │
│ - calls core.add_to_buffer()
│ - start() starts adapter loops
│ - stop() stops adapter loops
└──────────────┬──────────┘
               │
               ▼
┌─────────────────────────┐
│ OutputCore               │
│ - dmx_state: current DMX │ ◄── Always contains latest values
│ - add_to_buffer(): update │
│ - No longer sends to     │
│   adapters directly      │
└──────────────┬──────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌───────────────┐ ┌───────────────┐
│ ArtNetAdapter  │ │ sACN Adapter  │ (Independent loops)
│ (40Hz loop)    │ │ (20Hz loop)    │
│                │ │                │
│ while running: │ │ while running: │
│   read state   │ │   read state   │
│   send         │ │   send         │
│   sleep 25ms   │ │   sleep 50ms   │
└───────────────┘ └───────────────┘
```

---

## Why This Design?

### 1. Timing Precision (Primary Motivation)

**Problem:** Relative time checks (`now - last_send >= interval`) are sensitive to when the check happens.

**Example with 60Hz orchestrator, 40Hz adapter:**
```python
# Current (relative check) - DRIFT!
now = time.monotonic()
if now - self._last_send_time >= 0.025:  # 25ms
    self._last_send_time = now
    send()
```
- Tick at 0ms: Send (last_send=0ms)
- Tick at 16.67ms: 16.67ms < 25ms → Skip
- Tick at 33.33ms: 33.33ms >= 25ms → Send (last_send=33.33ms)
- Result: **33.33ms between sends = ~30Hz effective rate** ❌

**New (absolute scheduling) - PRECISE!**
```python
# New (absolute scheduling) - EXACT!
next_send = 0  # Start immediately
while running:
    now = time.monotonic()
    if now >= next_send:
        send()
        next_send = now + 0.025  # Schedule next exactly 25ms from now
    await asyncio.sleep(0.001)  # Small sleep to yield
```
- Send at 0ms, next_send = 25ms
- Send at 25ms, next_send = 50ms
- Send at 50ms, next_send = 75ms
- Result: **Exactly 40Hz** ✅

### 2. Multiple Rates Support

**Current:** All adapters are called at 60Hz, each rate-limits independently.
- Works but with drift
- Hard to reason about
- Testing complex

**New:** Each adapter has its own loop at its own rate.
- 40Hz adapter: sends every 25ms
- 20Hz adapter: sends every 50ms
- 100Hz adapter: sends every 10ms
- **All work simultaneously without interference** ✅

### 3. Separation of Concerns

**Current:** OutputCore does too much:
- Maintains DMX buffer
- Manages adapters
- Calls adapter.send_dmx()
- Clears buffer after sending

**New:** Clear division:
- **OutputCore:** Maintains current DMX state (single responsibility)
- **Adapters:** Send DMX at their rate (single responsibility)
- **RuntimeManager:** Manages lifecycle (single responsibility)

### 4. Alignment with ADRs

**ADR-002 (Micro-kernel):** "Each module has its own manager class that routes information inside the module and has start, stop, and tick functions."
- ✅ Adapters now have their own lifecycle (start/stop) and "tick" (run_loop)

**ADR-004 (Stateless Adapters):** "Edge modules should be stateless with data processing centralized."
- ✅ Adapters are stateless (they read from core, don't maintain DMX state)
- ✅ Core maintains the state

**ADR-008 (State Management):** "Centralized state in Fixture Core."
- ✅ OutputCore centralizes DMX state (analogous to FixtureCore)

---

## Detailed Implementation Plan

### Phase 1: Prepare OutputCore for Shared Access

**Goal:** OutputCore maintains current DMX state that adapters can read.

**Changes to `src/apelios/output/output_core.py`:**

```python
"""Output core - maintains current DMX state for Output Layer.

This is the stateful component that holds the current DMX values.
Adapters read from this state and send at their own rates.
"""

class OutputCore:
    """Maintains current DMX state for all universes.
    
    This class is the single source of truth for what DMX values
    should be output. It receives updates from OutputInputSubscriber
    and provides read access to adapters.
    
    Attributes:
        dmx_state: Current DMX state as sparse dict of (universe, address) -> value.
        adapters: List of registered adapters (for tracking/debugging only).
    """
    
    def __init__(self) -> None:
        """Initialize with empty DMX state."""
        # Current state - always contains latest values for all channels
        self.dmx_state: dict[tuple[int, int], int] = {}
        # Adapters registered (for debugging/tracking, not for sending)
        self.adapters: list[BaseOutputAdapter] = []

    def add_to_buffer(self, universe: int, address: int, value: int) -> None:
        """Update current DMX state with latest value.
        
        Args:
            universe: DMX universe (1-65535).
            address: DMX address (1-512).
            value: DMX value (0-255 for 8-bit, 0-65535 for 16-bit).
        """
        self.dmx_state[(universe, address)] = value

    def register_adapter(self, adapter: BaseOutputAdapter) -> None:
        """Register adapter for tracking/debugging (optional).
        
        Note: Adapters read from dmx_state directly. This method is
        for tracking purposes only.
        
        Args:
            adapter: Adapter instance to register.
        """
        self.adapters.append(adapter)

    # process_frame() can be removed or kept as no-op for backward compat
    async def process_frame(self, dt: float | None = None) -> None:
        """Process one frame (no-op in new architecture).
        
        This method is kept for backward compatibility but no longer
        sends to adapters. Adapters now have their own loops.
        
        Args:
            dt: Delta time (unused).
        """
        # No longer sends to adapters - they have their own loops
        pass
```

**Rationale:**
- `dmx_state` (not `dmx_buffer`) better describes its purpose: current state
- No clearing - state persists between ticks
- Adapters read directly from `dmx_state`
- `process_frame()` kept for compatibility but is now a no-op

---

### Phase 2: Update BaseOutputAdapter Interface

**Goal:** Adapters manage their own lifecycle and timing.

**Changes to `src/apelios/output/base_output_adapter.py`:**

```python
"""Base output adapter interface.

All output protocol adapters inherit from this class and implement
the abstract methods. Adapters are stateless and manage their own
sending loops at their configured rates.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .output_core import OutputCore


class BaseOutputAdapter(ABC):
    """Interface for all output protocol adapters.
    
    Adapters are stateless (per ADR-004) and manage their own sending
    loops. Each adapter reads DMX state from the OutputCore and sends
    at its configured rate.
    
    Attributes:
        config: Protocol-specific configuration.
        _running: Lifecycle flag.
        _task: asyncio task for the adapter's loop.
        core: Reference to OutputCore for reading DMX state.
    """
    
    def __init__(self, config: dict | None = None, core: OutputCore | None = None) -> None:
        """Initialize with configuration and core reference.
        
        Args:
            config: Protocol-specific configuration dict.
            core: OutputCore instance for reading DMX state.
        """
        self.config = config or {}
        self.core = core
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the adapter's independent sending loop.
        
        Creates and tracks an asyncio task that runs the adapter's
        loop at its configured rate.
        """
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the adapter's loop and clean up.
        
        Cancels the adapter's asyncio task and waits for it to finish.
        """
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # Task was cancelled, which is expected
                pass
            self._task = None

    def is_running(self) -> bool:
        """Check if adapter is currently running.
        
        Returns:
            True if the adapter's loop is active, False otherwise.
        """
        return self._running

    @abstractmethod
    async def _run_loop(self) -> None:
        """Main adapter loop - runs at the adapter's configured rate.
        
        Subclasses implement this to:
        1. Read current DMX state from self.core.dmx_state
        2. Send it via the protocol
        3. Sleep until next send time
        
        This loop runs independently of the orchestrator's tick.
        """
        pass
```

**Rationale:**
- `core` reference passed in constructor
- `_run_loop()` is the new abstract method (replaces `send_dmx()` as the main entry point)
- Task management in start/stop
- `is_running()` for lifecycle checks

---

### Phase 3: Update ArtNetAdapter for Independent Loop

**Goal:** ArtNetAdapter implements its own precise timing loop.

**Changes to `src/apelios/output/adapters/artnet_adapter.py`:**

```python
"""ArtNet output adapter.

Provides ArtNet protocol support with independent timing loop.
The adapter reads current DMX state from OutputCore and sends at
exactly the configured rate (typically 40Hz).
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from aioartnet import ArtNetClient

from ..base_output_adapter import BaseOutputAdapter

if TYPE_CHECKING:
    from aioartnet import ArtNetUniverse
    from ..output_core import OutputCore


class ArtNetAdapter(BaseOutputAdapter):
    """ArtNet protocol adapter for DMX output.
    
    Implements independent sending loop at configured rate. Reads
    current DMX state from OutputCore, filters to configured universe,
    and sends via ArtNet protocol.
    
    Attributes:
        universe: ArtNet universe to output to.
        source_ip: Source IP for ArtNet packets.
        target_ip: Target IP/broadcast address.
        output_rate_hz: Sending rate in Hz.
        client: aioartnet client instance.
        universe_obj: aioartnet universe object.
        dmx_data: 512-channel buffer for ArtNet.
        core: Reference to OutputCore.
    """
    
    def __init__(self, config: dict | None = None, core: OutputCore | None = None) -> None:
        """Initialize with ArtNet configuration and core reference.
        
        Args:
            config: Configuration with source_ip, target_ip, universe, output_rate_hz.
            core: OutputCore instance for reading DMX state.
        """
        super().__init__(config, core)
        self.universe = config.get("universe", 0) if config else 0
        self.source_ip = config.get("source_ip", "127.0.0.1") if config else "127.0.0.1"
        self.target_ip = config.get("target_ip", "127.0.0.1") if config else "127.0.0.1"
        self.output_rate_hz = config.get("output_rate_hz", 40) if config else 40
        
        self.client: ArtNetClient | None = None
        self.universe_obj: ArtNetUniverse | None = None
        self.dmx_data: bytearray = bytearray(512)

    async def start(self) -> None:
        """Start ArtNet connection and the independent sending loop."""
        if self._running:
            return
        
        # Initialize network connection
        try:
            self.client = ArtNetClient()
            self.client.unicast_ip = self.source_ip
            self.client.broadcast_ip = self.target_ip
            await self.client.connect()
            self.universe_obj = self.client.set_port_config(
                universe=self.universe,
                is_input=True
            )
        except Exception:
            # Allow tests to run without real network
            self.client = None
            self.universe_obj = None
        
        # Start the independent loop
        await super().start()

    async def stop(self) -> None:
        """Stop ArtNet connection and the sending loop."""
        if not self._running:
            return
        
        # Stop the loop first (calls parent stop)
        await super().stop()
        
        # Then clean up network
        if self.universe_obj:
            try:
                self.universe_obj.set_dmx(bytes(bytearray(512)))
            except Exception:
                pass
        
        if self.client and self.client.protocol and self.client.protocol.transport:
            try:
                self.client.protocol.transport.close()
            except Exception:
                pass
        
        self.client = None
        self.universe_obj = None

    async def _run_loop(self) -> None:
        """Run the ArtNet sending loop at configured rate.
        
        Reads current DMX state from core, filters to configured universe,
        formats for ArtNet, and sends. Uses absolute time scheduling for
        precise rate control.
        """
        if self.client is None or self.universe_obj is None:
            # Can't send without connection - sleep and retry
            while self._running:
                await asyncio.sleep(0.1)
                if self.client and self.universe_obj:
                    break
            if not self._running:
                return
        
        interval = 1.0 / self.output_rate_hz if self.output_rate_hz > 0 else 0.016
        next_send_time = time.monotonic()  # Send immediately first time
        
        while self._running:
            now = time.monotonic()
            
            # Check if it's time to send
            if now >= next_send_time:
                # Read current state from core
                if self.core:
                    await self._send_dmx(self.core.dmx_state)
                
                # Schedule next send exactly interval seconds from now
                next_send_time = now + interval
            
            # Sleep a small amount to yield control
            # This prevents busy-waiting while maintaining precision
            sleep_time = next_send_time - time.monotonic()
            if sleep_time > 0:
                await asyncio.sleep(min(sleep_time, 0.001))
            else:
                await asyncio.sleep(0)  # Yield control

    async def _send_dmx(self, dmx_state: dict[tuple[int, int], int]) -> None:
        """Send DMX data via ArtNet (internal method).
        
        Args:
            dmx_state: Current DMX state from OutputCore.
        """
        if self.client is None or self.universe_obj is None:
            return
        
        # Reset buffer to all zeros
        self.dmx_data = bytearray(512)
        
        # Apply only channels for our configured universe
        for (universe, address), value in dmx_state.items():
            if universe != self.universe:
                continue
            
            # Clamp address to valid range (1-512)
            if 1 <= address <= 512:
                # Handle 16-bit values by splitting into MSB/LSB
                if value > 255:
                    msb = (value >> 8) & 0xFF
                    lsb = value & 0xFF
                    self.dmx_data[address - 1] = msb
                    if address < 512:
                        self.dmx_data[address] = lsb
                else:
                    self.dmx_data[address - 1] = value
        
        # Send the DMX data
        self.universe_obj.set_dmx(bytes(self.dmx_data))
```

**Key Changes:**
- `_run_loop()`: New main loop method with precise timing
- `_send_dmx()`: Renamed from `send_dmx()` (now internal)
- `core` reference: Passed in constructor for reading state
- Absolute time scheduling: `next_send_time = now + interval`
- Small sleeps: Yield control without busy-waiting

---

### Phase 4: Update OutputAdapterBootstrap

**Goal:** Pass core reference to adapters, start their loops.

**Changes to `src/apelios/output/output_adapter_bootstrap.py`:**

```python
"""Bootstrap module for the output layer.

Creates and starts protocol adapters with their independent loops.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .output_core import OutputCore
    from .output_runtime_manager import OutputRuntimeManager


class OutputAdapterBootstrap:
    """Bootstrap adapter creation and lifecycle for the output layer.
    
    Creates adapter instances, passes them the OutputCore reference,
    and starts their independent sending loops.
    
    Attributes:
        adapter_list: List of adapter names to create.
        core: OutputCore reference to pass to adapters.
        _adapters: List of created adapter instances.
    """
    
    def __init__(self, adapter_list: list[str] | None = None, core: OutputCore | None = None) -> None:
        """Initialize bootstrap with optional adapter list and core.
        
        Args:
            adapter_list: List of adapter names to create (default: ["artnet"]).
            core: OutputCore instance to pass to adapters.
        """
        self.adapter_list = adapter_list or ["artnet"]
        self.core = core
        self._adapters: list[BaseOutputAdapter] = []

    def _load_artnet_config(self) -> dict[str, int | str | float]:
        """Load ArtNet configuration from JSON file.
        
        Returns:
            Configuration dictionary with source_ip, target_ip, universe, output_rate_hz.
        """
        config_path = Path(__file__).parent / "config" / "artnet_config.json"
        
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            return config
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "source_ip": "127.0.0.1",
                "target_ip": "127.0.0.1",
                "universe": 0,
                "output_rate_hz": 40
            }

    async def bootstrap(self, runtime_manager: OutputRuntimeManager) -> None:
        """Create, configure, and start adapters with independent loops.
        
        Args:
            runtime_manager: OutputRuntimeManager (core reference taken from here).
        """
        # Use core from runtime_manager if not provided in constructor
        core = self.core or runtime_manager.core
        
        adapters_by_name = {
            "artnet": lambda: self._create_artnet_adapter(core),
        }

        for adapter_name in self.adapter_list:
            creator = adapters_by_name.get(adapter_name)
            if not creator:
                continue

            try:
                adapter = await creator()
                self._adapters.append(adapter)
                # Register with core for tracking (optional)
                if core:
                    core.register_adapter(adapter)
                # Adapter starts its own loop when start() is called
                # The loop is started by OutputRuntimeManager
            except Exception:
                pass

    async def _create_artnet_adapter(self, core: OutputCore) -> ArtNetAdapter:
        """Create and return configured ArtNet adapter.
        
        Args:
            core: OutputCore instance to pass to adapter.
            
        Returns:
            Configured ArtNetAdapter instance.
        """
        from .adapters.artnet_adapter import ArtNetAdapter
        
        config = self._load_artnet_config()
        return ArtNetAdapter(config=config, core=core)

    async def stop_adapters(self) -> None:
        """Stop all started adapters."""
        for adapter in self._adapters:
            await adapter.stop()
        self._adapters = []
```

**Key Changes:**
- Takes `core` in constructor
- Passes `core` to adapters during creation
- `bootstrap()` creates adapters but doesn't start them (runtime manager does that)
- Added `stop_adapters()` for cleanup

---

### Phase 5: Update OutputRuntimeManager

**Goal:** Manage adapter lifecycle (start/stop adapter loops).

**Changes to `src/apelios/output/output_runtime_manager.py`:**

```python
"""Output runtime manager.

Owns output-layer lifecycle and broker connectivity.
Manages the OutputCore and starts/stops adapter loops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

fromapelios.broker.broker_client import BrokerClient

if TYPE_CHECKING:
    from .output_core import OutputCore
    from .output_input_subscriber import OutputInputSubscriber
    from .output_adapter_bootstrap import OutputAdapterBootstrap


class OutputRuntimeManager:
    """Own the output layer lifecycle.
    
    Handles start/stop/tick lifecycle. Data processing is delegated
    to OutputCore. Adapters have independent sending loops that are
    started/stopped with this manager.
    
    Attributes:
        broker_client: BrokerClient for NATS communication.
        core: OutputCore for DMX state management.
        input_subscriber: Subscriber for broker messages.
        _running: Lifecycle flag.
        _bootstrap: Adapter bootstrap instance.
    """
    
    def __init__(
        self,
        broker_client: BrokerClient | None = None,
        core: OutputCore | None = None,
    ) -> None:
        """Initialize with optional broker client and core.
        
        Args:
            broker_client: Injected BrokerClient for NATS communication.
            core: Injected OutputCore for DMX state management.
        """
        self.broker_client = broker_client or BrokerClient()
        self.core = core or self._create_core()
        self.input_subscriber = self._create_input_subscriber()
        self._running = False
        self._bootstrap: OutputAdapterBootstrap | None = None

    def _create_core(self) -> OutputCore:
        """Create default OutputCore instance.
        
        Returns:
            New OutputCore for DMX state management.
        """
        from .output_core import OutputCore
        return OutputCore()

    def _create_input_subscriber(self) -> OutputInputSubscriber:
        """Create default OutputInputSubscriber instance.
        
        Returns:
            New OutputInputSubscriber for broker messages.
        """
        from .output_input_subscriber import OutputInputSubscriber
        return OutputInputSubscriber(self.core)

    async def _bootstrap_adapters(self) -> None:
        """Create and start adapter loops via bootstrap."""
        from .output_adapter_bootstrap import OutputAdapterBootstrap
        
        self._bootstrap = OutputAdapterBootstrap(core=self.core)
        await self._bootstrap.bootstrap(self)
        
        # Start all adapter loops
        # Note: Bootstrap creates adapters but doesn't start them.
        # We need to start them here. But how do we access them?
        # Option 1: Bootstrap returns list of adapters
        # Option 2: Bootstrap starts them internally
        # For now, let's have bootstrap handle starting

    async def start(self) -> None:
        """Start output runtime.
        
        Connects to broker, subscribes to output topics, and starts adapter loops.
        """
        if self._running:
            return

        await self.broker_client.connect()
        await self.broker_client.subscribe("output.>", self.input_subscriber)
        await self._bootstrap_adapters()
        
        # If bootstrap didn't start adapters, start them now
        # This depends on how we implement bootstrap
        
        self._running = True

    async def stop(self) -> None:
        """Stop output runtime.
        
        Stops all adapter loops, disconnects from broker.
        """
        if not self._running:
            return

        # Stop all adapters first
        if self._bootstrap:
            await self._bootstrap.stop_adapters()
        
        await self.broker_client.disconnect()
        self._running = False

    def is_running(self) -> bool:
        """Check if runtime is currently running.
        
        Returns:
            True if started and not stopped, False otherwise.
        """
        return self._running

    async def tick(self, dt: float = 0.016) -> None:
        """Process one output frame.
        
        Delegates to core for state updates. Adapters have their own
        loops and read from core directly, so no sending happens here.
        
        Args:
            dt: Delta time in seconds (default 1/60 = 0.016).
        """
        # Core is updated by OutputInputSubscriber on broker messages
        # Adapters read from core.dmx_state in their own loops
        # So tick() just needs to exist for the orchestrator to call it
        await self.core.process_frame(dt=dt)
```

**Note:** There's a question about how adapters get started. Two options:
- **Option A:** Bootstrap creates AND starts adapters
- **Option B:** Bootstrap creates, RuntimeManager starts

I think **Option A** is cleaner: bootstrap handles the full adapter lifecycle.

But actually, looking at the InputLayer pattern, the InputRuntimeManager has:
- `register_adapter()` - registers
- `start_adapter()` - starts
- `start_registered_adapters()` - starts all

So for consistency, we should follow that pattern.

Let me revise the OutputRuntimeManager:

```python
async def _bootstrap_adapters(self) -> None:
    """Create adapters via bootstrap."""
    from .output_adapter_bootstrap import OutputAdapterBootstrap
    
    bootstrap = OutputAdapterBootstrap(core=self.core)
    await bootstrap.bootstrap(self)
    # Adapters are created and registered with core
    # But NOT started yet - runtime manager starts them

async def start(self) -> None:
    if self._running:
        return

    await self.broker_client.connect()
    await self.broker_client.subscribe("output.>", self.input_subscriber)
    await self._bootstrap_adapters()
    
    # Start all adapter loops
    await self._start_adapters()
    
    self._running = True

async def _start_adapters(self) -> None:
    """Start all registered adapters' loops."""
    # Adapters are registered with core by bootstrap
    # We need to access them to start their loops
    # Option: core.adapters contains the list
    for adapter in self.core.adapters:
        await adapter.start()

async def stop(self) -> None:
    if not self._running:
        return

    # Stop all adapters first
    for adapter in self.core.adapters:
        await adapter.stop()
    
    await self.broker_client.disconnect()
    self._running = False
```

But wait, this has a problem: `self.core.adapters` is populated by `register_adapter()`, which is called by bootstrap. But the bootstrap we have doesn't call `register_adapter()` yet.

Let me think about this more carefully.

Currently, in our modified bootstrap, we have:
```python
adapter = await creator()
self._adapters.append(adapter)
# Register with core for tracking (optional)
if core:
    core.register_adapter(adapter)
```

So adapters ARE registered with core. So `self.core.adapters` will have the list.

But there's another issue: who calls `adapter.start()`?

In the InputLayer, InputRuntimeManager has:
```python
async def start(self):
    await self.broker_client.connect()
    await self._bootstrap_adapters()
    self._running = True

async def _bootstrap_adapters(self):
    bootstrap = InputAdapterBootstrap()
    await bootstrap.bootstrap(self)
    # Adapters are registered but NOT started

async def start_registered_adapters(self):
    for adapter in self.registered_adapters:
        await self.start_adapter(adapter)

async def start_adapter(self, adapter):
    await adapter.start(input_publisher=self.input_publisher)
    self._running_adapters.append(adapter)
```

So InputLayer separates:
1. Bootstrap: creates and registers adapters
2. start_registered_adapters(): starts them

For consistency, we should do the same for OutputLayer.

But actually, for OutputLayer, the adapters don't need the runtime manager to start them - they can start themselves when their `start()` is called. The only thing is that the runtime manager needs to call `adapter.start()`.

So the simplest approach:
1. Bootstrap creates adapters and registers them with core
2. RuntimeManager.start() calls adapter.start() for all adapters in core.adapters
3. RuntimeManager.stop() calls adapter.stop() for all adapters

This is clean and consistent.

But wait - there's still an issue. Currently, bootstrap creates adapters but doesn't start them. And the runtime manager doesn't have a way to access the adapters.

The simplest fix: have bootstrap store the adapters in the runtime manager, OR have the runtime manager access them via core.adapters.

Since core already has `self.adapters` list, and bootstrap calls `core.register_adapter()`, we can use `self.core.adapters`.

So the final OutputRuntimeManager:

```python
async def start(self) -> None:
    if self._running:
        return

    await self.broker_client.connect()
    await self.broker_client.subscribe("output.>", self.input_subscriber)
    await self._bootstrap_adapters()
    
    # Start all adapter loops
    for adapter in self.core.adapters:
        await adapter.start()
    
    self._running = True

async def stop(self) -> None:
    if not self._running:
        return

    # Stop all adapters first
    for adapter in self.core.adapters:
        await adapter.stop()
    
    await self.broker_client.disconnect()
    self._running = False

async def _bootstrap_adapters(self) -> None:
    """Create adapters via bootstrap."""
    from .output_adapter_bootstrap import OutputAdapterBootstrap
    
    bootstrap = OutputAdapterBootstrap(core=self.core)
    await bootstrap.bootstrap(self)
    # Adapters are now created, registered with core, and ready to start
```

And the bootstrap:
```python
async def bootstrap(self, runtime_manager: OutputRuntimeManager) -> None:
    core = self.core or runtime_manager.core
    adapters_by_name = {"artnet": lambda: self._create_artnet_adapter(core)}
    
    for adapter_name in self.adapter_list:
        creator = adapters_by_name.get(adapter_name)
        if not creator:
            continue
        try:
            adapter = await creator()
            self._adapters.append(adapter)
            if core:
                core.register_adapter(adapter)
            # Don't start here - runtime manager will start all at once
        except Exception:
            pass
```

This is clean and consistent with the InputLayer pattern.

---

Now, let me think about the test impact. The current tests expect:
- `adapter.send_dmx()` to be called
- But with the new architecture, `send_dmx()` doesn't exist (it's `_send_dmx()`)
- And adapters have their own loops

So we need to update the tests. But the user said "we can rewrite the test in a refactoring".

For TDD, we should:
1. First, understand what the tests are testing
2. Update the implementation
3. Update the tests to match the new behavior

But actually, for a refactoring, the tests should still pass if we do it right. The external behavior should be the same: adapters should still send DMX data at their configured rates.

The issue is that the tests mock `adapter.send_dmx()` and verify it's called. With the new architecture, `send_dmx()` is called from the adapter's own loop, not from the core.

So we have two options:
1. Update tests to work with the new architecture
2. Keep `send_dmx()` as a public method for backward compatibility, and have `_run_loop()` call it

Option 2 is better for minimal test changes:

```python
# In ArtNetAdapter:
async def send_dmx(self, dmx_state: dict[tuple[int, int], int]) -> None:
    """Send DMX data via ArtNet.
    
    This is the public method for sending DMX. Called either from
    the adapter's own loop or from external code (for testing).
    
    Args:
        dmx_state: Current DMX state to send.
    """
    await self._send_dmx(dmx_state)

async def _run_loop(self) -> None:
    # ...
    if self.core:
        await self.send_dmx(self.core.dmx_state)  # Call public method
    # ...
```

This way, tests that mock `send_dmx()` will still work, because the adapter's loop calls `send_dmx()`.

Actually, wait. The tests mock the adapter instance and its `send_dmx` method. Let me check:

From test_output_runtime_manager.py:
```python
async def test_bootstrap_registers_artnet_adapter(self, mock_broker_client, mock_output_core):
    manager = OutputRuntimeManager(
        broker_client=mock_broker_client,
        core=mock_output_core
    )
    
    await manager.start()
    
    # Check that adapters were registered with the core
    mock_output_core.register_adapter.assert_called()
```

This test doesn't mock `send_dmx()`. It just checks that `register_adapter` is called.

From test_artnet_adapter.py, there are tests like:
```python
async def test_artnet_adapter_send_dmx_filters_by_universe(self, mock_client_class):
    # ...
    await adapter.start()
    dmx_buffer = {(1, 10): 135, (1, 20): 255, (2, 5): 100, (3, 15): 50}
    await adapter.send_dmx(dmx_buffer)
    # ... verify
```

This test calls `adapter.send_dmx()` directly. With our new architecture, this should still work because we're keeping `send_dmx()` as a public method.

But there's a problem: with the new architecture, `send_dmx()` is called from the adapter's loop, not from the core. So tests that expect `send_dmx()` to be called during `process_frame()` will fail.

Let me check if any tests do that:

From test_output_core.py:
```python
async def test_send_to_adapters_calls_all_adapters(self, mock_adapter1, mock_adapter2):
    """process_frame should call send_dmx on all adapters."""
    core = OutputCore()
    core.register_adapter(mock_adapter1)
    core.register_adapter(mock_adapter2)
    
    await core.process_frame()
    
    mock_adapter1.send_dmx.assert_awaited_once()
    mock_adapter2.send_dmx.assert_awaited_once()
```

**This test WILL FAIL** with our new architecture, because `process_frame()` no longer calls `send_dmx()`.

So we need to update this test. The new behavior is:
- `process_frame()` does nothing (or just updates internal state)
- Adapters call `send_dmx()` from their own loops

So the test should verify:
1. Adapters are started when runtime manager starts
2. Adapters have their own loops
3. Adapters call `send_dmx()` at their configured rate

This is a **breaking change** in the architecture. The tests need to be updated.

But the user said "we can rewrite the test in a refactoring". So that's fine.

---

## 🎯 **Final Implementation Plan Summary**

### Files to Modify:
1. `src/apelios/output/output_core.py` - Maintain state, remove clearing
2. `src/apelios/output/base_output_adapter.py` - Add loop management
3. `src/apelios/output/adapters/artnet_adapter.py` - Implement independent loop
4. `src/apelios/output/output_adapter_bootstrap.py` - Pass core to adapters
5. `src/apelios/output/output_runtime_manager.py` - Start/stop adapter loops

### Tests to Update:
- `tests/output/test_output_core.py` - Update process_frame tests
- `tests/output/test_artnet_adapter.py` - Tests already call send_dmx() directly, should work
- `tests/output/test_output_runtime_manager.py` - May need updates for adapter lifecycle

### TDD Approach:
1. **First, update the implementation** (we've designed it above)
2. **Then, run tests** and see which ones fail
3. **Update tests** to match new behavior
4. **Verify all tests pass**

---

## ✅ **Why This is the Right Approach**

### 1. Follows ADR Principles
- **ADR-002 (Micro-kernel):** Each adapter is now a self-contained module with its own lifecycle
- **ADR-004 (Stateless):** Adapters remain stateless (read from core, don't store DMX state)
- **ADR-008 (State Management):** State centralized in OutputCore

### 2. Solves the Timing Problem
- Absolute scheduling ensures exact rates
- No drift or alignment issues
- Multiple rates work naturally

### 3. Better Separation of Concerns
- **OutputCore:** Maintains DMX state (single responsibility)
- **Adapters:** Send DMX at their rate (single responsibility)
- **RuntimeManager:** Manages lifecycle (single responsibility)

### 4. More Extensible
- Easy to add new adapters with different rates
- Adapters don't depend on orchestrator tick rate
- Cleaner architecture for future enhancements

### 5. Follows TDD
- Tests define the behavior
- Implementation matches the tests (after updating them)
- Refactoring maintains test coverage

---

## 📋 **Execution Steps**

### Step 1: Update OutputCore
- Rename dmx_buffer to dmx_state
- Remove clearing from process_frame()
- Keep register_adapter() for tracking

### Step 2: Update BaseOutputAdapter
- Add core reference
- Add task management
- Add abstract _run_loop()
- Keep send_dmx() as public method for tests

### Step 3: Update ArtNetAdapter
- Implement _run_loop() with precise timing
- Rename send_dmx logic to _send_dmx()
- Keep send_dmx() as wrapper for backward compatibility

### Step 4: Update OutputAdapterBootstrap
- Pass core to adapters
- Register adapters with core

### Step 5: Update OutputRuntimeManager
- Start/stop adapter loops
- Keep tick() as no-op or for future use

### Step 6: Run Tests
- Identify failing tests
- Update them to match new architecture

### Step 7: Verify
- All 58 output tests pass
- All 218 total tests pass
- No regressions

---

**Ready to implement?** This plan addresses your rate limiting concern with a clean, architectural solution that follows all ADRs and TDD principles.

The key insight: **adapters control their own timing loops**, independent of the orchestrator's tick rate. This ensures precise rates and enables multiple adapters at different speeds.

Would you like me to proceed with the implementation?
