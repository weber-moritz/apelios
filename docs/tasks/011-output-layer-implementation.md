---
date: 2026-07-08
state: Draft # [Draft | In Progress | Done]
---

# Task 011: Output Layer Implementation

## 0. TDD Contract
- [ ] Tests written and committed before implementation begins
- [ ] All new tests fail initially (Red phase)
- [ ] Test files: `tests/output/`, `tests/output/adapters/`

## 1. Context & Scope

### Objective
Implement a new Output Layer that translates Fixture Layer DMX output to physical lighting protocols, completing the unidirectional data pipeline: **Hardware → Input → Router → Fixture → Output → Lights**.

### Background
The current architecture (ADR-002, ADR-005) defines a micro-kernel/hexagonal architecture with strict separation of concerns. The Fixture Layer publishes normalized DMX values to `output.<universe>.<address>` topics, but there is no dedicated layer to consume these messages and translate them to physical protocols like ArtNet, sACN, or DMX. The existing `artnet/controller.py` is a standalone implementation that doesn't integrate with the broker-based architecture.

This task implements the Output Layer following the **exact same micro-kernel pattern** as the Input, Router, and Fixture layers, ensuring architectural consistency and enabling protocol-agnostic output handling.

### Files in Scope

**New Module: `src/apelios/output/`**
- `output_runtime_manager.py` - Lifecycle management (start/stop/tick) only
- `output_core.py` - Data processing: DMX buffering, adapter management
- `output_input_subscriber.py` - Subscribes to `output.>` topics, forwards to core
- `base_output_adapter.py` - Interface contract for all protocol adapters
- `config/artnet_config.json` - ArtNet-specific configuration

**New Adapters Module: `src/apelios/output/adapters/`**
- `base_adapter.py` - Common adapter functionality
- `artnet_adapter.py` - ArtNet protocol implementation (PRIMARY TARGET)

**Integration:**
- `src/apelios/main_orchestrator.py` - Add Output Layer to startup/tick sequence

**New Tests: `tests/output/`**
- `test_output_runtime_manager.py`
- `test_output_core.py`
- `test_output_input_subscriber.py`
- `test_base_output_adapter.py`
- `tests/output/adapters/test_artnet_adapter.py`

### DO NOT TOUCH
- Existing Input Layer (`src/apelios/input/`)
- Existing Router Layer (`src/apelios/router/`)
- Existing Fixture Layer (`src/apelios/fixture/`)
- Existing Broker Layer (`src/apelios/broker/`)
- Existing Main Orchestrator (`src/apelios/main_orchestrator.py`) - only add, don't modify existing
- Existing ArtNet Controller (`src/apelios/artnet/controller.py`) - will be refactored separately

## 2. Strict Constraints

### Architectural Constraints (from ADR-002, ADR-004, ADR-005)
1. **Micro-Kernel Pattern**: Output Layer must follow the same runtime manager + core pattern as other layers
2. **Strict Separation of Concerns**: Runtime Manager handles lifecycle ONLY; Core handles data processing
3. **Broker-Based Communication**: All communication must use the injected `BrokerClient` from `src/apelios/broker/`
4. **No Direct Dependencies**: Output Layer must NOT import from other layers (Input, Router, Fixture)
5. **Stateless Design**: Output Core and adapters should be stateless where possible; only the DMX buffer maintains state between ticks
6. **Unidirectional Flow**: Output Layer consumes from `output.>` topics only; does not publish back

### Technical Constraints
1. **No Threading**: Must use `asyncio` only (per project stack in architecture.md)
2. **Type Safety**: Must use Python 3.12+ type hints strictly
3. **Sparse Buffering**: DMX buffer stores only channels that have been updated (sparse, not complete universes) to enable universe sharing with other devices
4. **Protocol Agnostic**: OutputCore must not know about specific protocols (ArtNet, sACN, etc.)

### Output Contract (from this task design)
- **Subscribes to**: `output.<universe>.<address>` topics (wildcard: `output.>`)
- **Payload Format**: `{"universe": int, "address": int, "value": int}`
- **Data Redundancy**: Universe and address appear in both subject (for broker routing) and payload (for completeness)
- **Internal Buffer**: `dict[tuple[int, int], int]` mapping `(universe, address)` → `value` (sparse, only changed channels)

## 3. Architecture Design & Rationale

### Why This Architecture?

**Reference: ADR-002 (Architecture)** defines a micro-kernel architecture where each module has its own manager class that routes information inside the module and has start, stop, and tick functions called by the main orchestrator. This task follows that pattern exactly.

**Reference: ADR-004 (Stateless Input Adapters)** establishes the principle that edge modules should be stateless with data processing centralized. The Output Layer applies this inversely: the OutputCore is stateful (maintains DMX buffer), while protocol adapters are stateless (they just send).

**Reference: ADR-005 (Event Contract)** defines the payload format and topic structure. This task extends that contract to the output side with the new `output.<universe>.<address>` topic pattern.

**Reference: ADR-008 (State Management)** centralizes all stateful tracking in the Fixture Core. The Output Layer adds a new type of state: the DMX output buffer, which is intentionally separate from fixture state to maintain clean separation of concerns.

**Reference: architecture.md Section 4** defines the unidirectional data flow: Hardware → Input → Router → Fixture → Lights. This task inserts the Output Layer as the final translation step before Lights, making the complete flow: Hardware → Input → Router → Fixture → **Output** → Lights.

### Layer Structure

```
┌─────────────────────────────────────────────────────────────┐
│                      Output Layer                               │
├─────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────┐ │
│  │ OutputRuntime   │     │   OutputCore     │     │  Adapters│ │
│  │ Manager         │────▶│                 │────▶│          │ │
│  │                 │     │  - DMX buffer    │     │  - ArtNet│ │
│  │ - start/stop    │     │  - Adapter mgmt  │     │  - sACN  │ │
│  │ - tick          │     │  - send_to_all() │     │  - DMX   │ │
│  │ - bootstrap     │     │                 │     │  - OSC   │ │
│  └─────────────────┘     └─────────────────┘     └─────────┘ │
│           │                          │                       │      │
│           ▼                          ▼                       ▼      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Output Input Subscriber                     │ │
│  │  - Subscribes to: output.>                               │ │
│  │  - Forwards to: OutputCore.add_to_buffer()                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ output.<universe>.<address>
                              ▼
                    ┌──────────────────────┐
                    │    Fixture Layer       │
                    │  (publishes DMX values)│
                    └──────────────────────┘
```

### Why Sparse Buffering?

The DMX buffer maintains only channels that have been explicitly set by the Fixture Layer, not complete universes. This design decision enables **universe sharing** - multiple devices can send to the same ArtNet universe without overwriting each other's channels. 

Example: Apelios controls channels 10-20 in universe 1, while another device controls channels 50-100. With sparse buffering, Apelios sends only its channels, allowing the receiver to merge inputs from both sources. With complete universe buffering, Apelios would need to send all 512 channels (with 0 for uncontrolled ones), potentially overwriting the other device's data.

### Why Separate Runtime Manager and Core?

**Reference: Fixture Layer** separates FixtureRuntimeManager (lifecycle) from FixtureCore (state management). **Reference: Router Layer** separates RouterRuntimeManager (lifecycle) from MappingRouter (routing logic).

This separation ensures:
1. **Single Responsibility**: Runtime Manager handles ONLY lifecycle; Core handles ONLY data
2. **Testability**: Core can be tested without broker dependencies
3. **Consistency**: Matches existing layer patterns in the codebase
4. **Future Extensibility**: Core can be swapped without affecting lifecycle management

### Configuration Approach (MVP)

For the MVP, configuration is loaded **once at startup** (no hot-reloading). A separate `OutputConfig` class is intentionally omitted to maintain simplicity and follow the pattern of Router/Fixture layers, which use internal functions for config loading.

**Config files:**
- `artnet_config.json` - Contains source_ip, target_ip, universe, output_rate_hz

**Loading:** Handled by internal function in OutputRuntimeManager or OutputCore

**Future:** Hot-reloading can be added later without changing the core architecture (see 000-todo.md: "hot reload for all config files")

### Adapter Management

Following the Input Layer pattern (InputAdapterBootstrap), adapters are **hardcoded** for MVP:

```python
# In OutputRuntimeManager or OutputCore
OUTPUT_ADAPTERS = {
    "artnet": ArtNetAdapter,
    # Future: "sacn": SacnAdapter,
    # Future: "dmx": DmxAdapter,
}
```

This approach:
- Matches existing Input Layer bootstrap pattern
- Simplifies MVP implementation
- Can be extended to dynamic loading later (see 000-todo.md: "hot load for input and output adapters")

## 4. Test Specification

### Core Module Tests

**`tests/output/test_output_runtime_manager.py`**
- [ ] `test_runtime_manager_initializes_with_defaults` - Verify default broker client creation
- [ ] `test_runtime_manager_initializes_with_injected_dependencies` - DI injection works for broker and core
- [ ] `test_start_connects_to_broker_and_subscribes` - Broker connection and subscription established
- [ ] `test_start_is_idempotent` - Multiple starts don't cause issues
- [ ] `test_stop_disconnects_and_clears_state` - Clean shutdown
- [ ] `test_tick_calls_core_process_frame` - Tick delegates to core
- [ ] `test_bootstrap_registers_artnet_adapter` - Adapter loaded and registered

**`tests/output/test_output_core.py`**
- [ ] `test_core_initializes_with_empty_buffer` - Empty DMX buffer on creation
- [ ] `test_add_to_buffer_stores_value` - Single channel stored correctly
- [ ] `test_add_to_buffer_updates_existing_channel` - Overwrites previous value
- [ ] `test_add_to_buffer_handles_multiple_universes` - Stores across different universes
- [ ] `test_buffer_is_sparse` - Only stores channels that have been set
- [ ] `test_register_adapter_adds_to_list` - Adapter registration works
- [ ] `test_send_to_adapters_calls_all_adapters` - All registered adapters receive buffer
- [ ] `test_process_frame_clears_buffer` - Buffer cleared after processing
- [ ] `test_process_frame_with_no_buffer_is_noop` - No error when buffer is empty

**`tests/output/test_output_input_subscriber.py`**
- [ ] `test_subscriber_parses_topic_correctly` - `output.1.42` → universe=1, address=42
- [ ] `test_subscriber_parses_payload_correctly` - JSON parsing works
- [ ] `test_subscriber_calls_core_add_to_buffer` - Forwards to core with correct args
- [ ] `test_subscriber_handles_invalid_topic` - Graceful error handling
- [ ] `test_subscriber_handles_missing_fields` - Validates payload structure

**`tests/output/test_base_output_adapter.py`**
- [ ] `test_adapter_initializes_with_config` - Config stored correctly
- [ ] `test_adapter_start_sets_running_flag` - State tracking works
- [ ] `test_adapter_stop_clears_running_flag` - State tracking works
- [ ] `test_send_dmx_receives_buffer` - Buffer parameter accepted
- [ ] `test_is_running_returns_correct_state` - State query works

**`tests/output/adapters/test_artnet_adapter.py`**
- [ ] `test_artnet_adapter_initializes_with_config` - Config validation
- [ ] `test_artnet_adapter_start_connects_via_aioartnet` - Library integration
- [ ] `test_artnet_adapter_stop_disconnects_cleanly` - Clean shutdown
- [ ] `test_artnet_adapter_send_dmx_filters_by_universe` - Only sends configured universe
- [ ] `test_artnet_adapter_send_dmx_handles_sparse_buffer` - Partial universe support
- [ ] `test_artnet_adapter_send_dmx_formats_correctly` - Protocol formatting
- [ ] `test_artnet_adapter_handles_16bit_values` - 16-bit DMX support

## 5. Implementation Steps

### Phase 1: Core Infrastructure
- [ ] Create `src/apelios/output/__init__.py` with exports
- [ ] Create `src/apelios/output/output_runtime_manager.py` - Lifecycle only
- [ ] Create `src/apelios/output/output_core.py` - Data processing
- [ ] Create `src/apelios/output/output_input_subscriber.py` - Message consumption
- [ ] Create `src/apelios/output/base_output_adapter.py` - Adapter interface
- [ ] Create `src/apelios/output/config/artnet_config.json` - Default config
- [ ] Create corresponding test files
- [ ] Verify all tests fail initially (Red phase)

### Phase 2: ArtNet Adapter Implementation
- [ ] Create `src/apelios/output/adapters/__init__.py`
- [ ] Create `src/apelios/output/adapters/base_adapter.py`
- [ ] Create `src/apelios/output/adapters/artnet_adapter.py`
- [ ] Create test files for ArtNet adapter
- [ ] Verify all tests pass (Green phase)

### Phase 3: Integration
- [ ] Update `src/apelios/main_orchestrator.py` to include Output Layer
- [ ] Add Output Runtime Manager to startup/shutdown sequence
- [ ] Add Output Layer to tick loop (after Fixture Layer)
- [ ] Verify end-to-end integration

### Phase 4: Refactoring (Optional)
- [ ] Review code for consistency with other layers
- [ ] Add type hints and docstrings
- [ ] Optimize if needed

## 6. Acceptance Criteria

### Build
- **All pytest are green** - All tests pass without failures
- **All features as required above are met** - Complete implementation of specified functionality
- **Matches the ADRs and architecture guidelines** - Full compliance with ADR-002, ADR-004, ADR-005, ADR-008, and architecture.md
- **Logic is logical** - Design decisions are sound and consistent

### Test
- **All new tests pass**: `pytest tests/output/ -v` succeeds
- **No regressions**: `pytest tests/ -v` passes all existing tests
- **Code coverage**: New code has test coverage >= existing project average

### Behavior
- **Fixture → Output Flow**: Fixture Layer output correctly flows to Output Layer
- **DMX Buffering**: Only changed channels are buffered (sparse buffer)
- **ArtNet Output**: ArtNet adapter successfully sends DMX data to configured target
- **Universe Sharing**: Multiple devices can send to the same universe without overwriting each other's channels (sparse buffer enables this)
- **Configuration**: ArtNet adapter uses settings from config file

### Architecture Compliance
- **Micro-Kernel**: Follows same pattern as Input, Router, Fixture layers
- **Separation of Concerns**: Runtime Manager handles lifecycle; Core handles data; Adapters handle protocols
- **Decoupled**: No direct dependencies between layers
- **Broker-Based**: All communication via BrokerClient (from `src/apelios/broker/`)
- **Async**: Uses asyncio exclusively (no threading)
- **Stateless Adapters**: Protocol adapters are stateless; state lives in OutputCore

## 7. Contracts and Interfaces

### Topic Contract

| Aspect | Specification |
|--------|---------------|
| **Subscribed Topics** | `output.>` (wildcard subscription) |
| **Topic Pattern** | `output.<universe>.<address>` |
| **Example** | `output.1.42` |

### Payload Contract

**Published by:** Fixture Layer (FixtureOutputPublisher)  
**Consumed by:** Output Layer (OutputInputSubscriber)

```json
{
  "universe": 1,
  "address": 42,
  "value": 135
}
```

**Field Types:**
- `universe`: int (1-65535, typically 1-16 for most setups)
- `address`: int (1-512, DMX channel address)
- `value`: int (0-255 for 8-bit, or 0-65535 for 16-bit)

**Rationale:** Data redundancy (universe/address in both subject and payload) ensures message integrity even if broker topic parsing fails. This follows the same principle as the Input Layer's source field (ADR-005).

### Internal DMX Buffer Format

```python
dmx_buffer: dict[tuple[int, int], int] = {
    (1, 10): 135,    # universe 1, address 10 = 135
    (1, 42): 200,    # universe 1, address 42 = 200
    (2, 5): 0,       # universe 2, address 5 = 0
}
```

**Sparse Buffer**: Only contains channels that have been explicitly set. Unset channels are not present in the dict, enabling universe sharing with other devices.

### Protocol Adapter Interface

```python
class BaseOutputAdapter:
    """Interface for all output protocol adapters."""
    
    def __init__(self, config: dict) -> None:
        """Initialize with protocol-specific configuration."""
        pass
    
    async def start(self) -> None:
        """Start the protocol output stream."""
        pass
    
    async def stop(self) -> None:
        """Stop the protocol output stream."""
        pass
    
    async def send_dmx(self, dmx_buffer: dict[tuple[int, int], int]) -> None:
        """Send DMX data. Called on each tick.
        
        Args:
            dmx_buffer: Sparse dict of (universe, address) -> value
        """
        pass
    
    def is_running(self) -> bool:
        """Return whether adapter is currently running."""
        pass
```

### OutputCore Interface

```python
class OutputCore:
    """Core data processing for Output Layer."""
    
    def __init__(self) -> None:
        """Initialize with empty DMX buffer."""
        pass
    
    def add_to_buffer(self, universe: int, address: int, value: int) -> None:
        """Add or update a DMX channel in the buffer."""
        pass
    
    def register_adapter(self, adapter: BaseOutputAdapter) -> None:
        """Register a protocol adapter."""
        pass
    
    def process_frame(self) -> None:
        """Process one frame: send buffer to all adapters, then clear."""
        pass
```

## 8. Configuration File Format

### ArtNet Config (`src/apelios/output/config/artnet_config.json`)

```json
{
  "source_ip": "192.168.8.1",
  "target_ip": "192.168.8.255",
  "universe": 10,
  "output_rate_hz": 40
}
```

**Fields:**
- `source_ip`: String - IP address of this machine (for ArtNet unicast)
- `target_ip`: String - Target IP or broadcast address
- `universe`: Integer - ArtNet universe to output to
- `output_rate_hz`: Float - Output refresh rate in Hz

## 9. Dependencies

### New Dependencies
- `aioartnet` - For ArtNet protocol support (already exists in project)

### Existing Dependencies Used
- `BrokerClient` from `src/apelios/broker/` - Injected broker client for all NATS communication
- `asyncio` - Core async framework
- `json` - Config file parsing
- `pathlib` - Config file path handling

## 10. References

### ADR References
- **ADR-002: Architecture** - Overall micro-kernel architecture pattern, module separation
- **ADR-004: Stateless Input Adapters** - Stateless principle, edge vs. core separation
- **ADR-005: Event Contract** - Payload formats, topic structure, source field concept
- **ADR-008: State Management** - Centralized state principles (applied to DMX buffer)

### Architecture References
- **architecture.md Section 2** - Project stack (Python 3.12+, asyncio, NATS)
- **architecture.md Section 3** - Architectural principles (Separation of Concerns, Decoupled Communication, Stateless Edge)
- **architecture.md Section 4.2** - Topic Flow diagram and data direction
- **architecture.md Section 6.E** - Fixture Layer definition (Output Layer is the next logical step)
- **architecture.md Section 6.F** - Output Layer placeholder (this task implements it)

### Related Task Documents
- **000-todo.md** - Future enhancements: hot-reload, hot-load adapters, disconnect-proof adapters, GUI

## 11. Future Enhancements (Out of Scope)

The following are tracked in 000-todo.md and will be implemented in future tasks:
- Hot-reloading of config files
- Dynamic loading/unloading of output adapters
- Disconnect and reconnect proof adapters
- GUI integration for output configuration
- Additional protocol adapters: sACN, DMX, OSC, NATS Out
- Complete universe buffering option (for receivers that don't support sparse merging)
- Output priority merging (LTP/HTP modes)
- Multiple universes per protocol adapter
- Protocol adapter failover/fallback mechanisms

---

**Task Created**: 2026-07-08  
**Architectural Design**: Based on ADR-002, ADR-004, ADR-005, ADR-008, and architecture.md  
**Priority**: High (Enables actual lighting control)  
**Estimated Complexity**: Medium (Follows established patterns)  
**Primary Target**: ArtNet protocol implementation  
**Author**: Mistral Vibe (for motzel)
