"""
E2E seam integration: Mouse adapter → broker contract → middleware mapping.

Architectural intent
--------------------
The broker contract {"source": "device.axis", "value": float} is the ONLY
shared interface between the input layer and the middleware layer.  No module
imports another directly; they communicate exclusively via broker messages.

This file proves:
  1. A MouseAdapter tick produces bytes on the mock broker.
  2. Those bytes match the contract the MiddlewareInputSubscriber expects.
  3. The mapping profile resolves mouse.x → group1.pan and
     mouse.y → group1.tilt via the "relative" type.
  4. virtual_output_state reflects the correct value after process_frame().

A real NATS round-trip is already covered by
tests/test_integration_main_orchestrator.py.  This test is intentionally
faster and fully deterministic: the mock broker acts as the seam.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from apelios.input.input_publisher import InputPublisher
from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.middleware.middleware_core import MappingMiddleware
from apelios.middleware.middleware_input_subscriber import MiddlewareInputSubscriber
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mouse_mapping_profile() -> dict:
    """Minimal profile mirroring the mouse entries in mapping_default.json.

    Uses "relative" type because the mouse adapter sends per-frame evdev
    REL_X/REL_Y values — each value IS the delta for that frame, not a
    cumulative absolute position.  sensitivity=1.0 keeps the math 1-to-1.
    """
    return {
        "mouse.x": {"target": "group1.pan",  "type": "relative", "sensitivity": 1.0},
        "mouse.y": {"target": "group1.tilt", "type": "relative", "sensitivity": 1.0},
    }


@pytest.fixture
def shared_mock_broker() -> MagicMock:
    """Single mock broker shared by both layers — this is the seam."""
    mock = MagicMock()
    mock.connect    = AsyncMock()
    mock.publish    = AsyncMock()
    mock.subscribe  = AsyncMock()
    mock.disconnect = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wire_msg(raw_bytes: bytes) -> MagicMock:
    """Wrap raw bytes in a mock broker message (duck-types NATS Msg.data)."""
    msg = MagicMock()
    msg.data = raw_bytes
    return msg


def _make_raw_msg(source: str, value: float) -> MagicMock:
    """Build a mock broker message directly from a source key and value."""
    return _wire_msg(json.dumps({"source": source, "value": value}).encode("utf-8"))


# ---------------------------------------------------------------------------
# Test 1 — Full seam: real adapter tick → bytes → subscriber → mapping output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mouse_input_reaches_middleware_mapping(
    shared_mock_broker: MagicMock,
    mouse_mapping_profile: dict,
) -> None:
    """
    Full seam proof: a MouseAdapter tick produces broker bytes that the
    MiddlewareInputSubscriber parses, and process_frame() moves
    virtual_output_state for both group1.pan and group1.tilt.

    Journey
    -------
    MouseAdapter(fake_backend).tick()
      → InputPublisher.publish()
      → mock_broker.publish(bytes)          ← seam
      → MiddlewareInputSubscriber(bytes)
      → MappingMiddleware.handle_input()
      → process_frame()
      → virtual_output_state updated
    """
    mouse_module = pytest.importorskip("apelios.input.adapters.mouse_adapter")

    # Scriptable fake evdev backend — each call to poll() returns the next frame.
    class FakeMouseBackend:
        def __init__(self, frames: list[dict[str, float]]) -> None:
            self._frames = iter(frames)

        async def poll(self) -> dict[str, float]:
            try:
                return next(self._frames)
            except StopIteration:
                return {}

    # The real mouse adapter sends per-frame evdev REL_X/REL_Y values.
    # Each frame value IS the delta — not a cumulative position.
    # Frame 0: moved 0.1 right, 0.05 down.
    # Frame 1: moved 0.2 right, 0.10 down.
    fake_backend = FakeMouseBackend(frames=[{"x": 0.1, "y": 0.05}, {"x": 0.2, "y": 0.1}])
    adapter = mouse_module.MouseAdapter(device="mouse", backend=fake_backend)

    # --- Input side -------------------------------------------------------
    # Use start_registered_adapters(), NOT start(), to skip _bootstrap_adapters()
    # which would try to open a real evdev device.
    input_runtime = InputRuntimeManager(broker_client=shared_mock_broker)
    input_runtime.register_adapter(adapter)
    await input_runtime.start_registered_adapters()

    # --- Middleware side ---------------------------------------------------
    core = MappingMiddleware(profile=mouse_mapping_profile)
    middleware_runtime = MiddlewareRuntimeManager(
        middleware=core,
        broker_client=shared_mock_broker,
    )
    await middleware_runtime.start()

    # Steal the callback the middleware registered on the mock broker.
    # args[0] = subject string ("input.>"), args[1] = the subscriber callable.
    captured_callback = shared_mock_broker.subscribe.call_args.args[1]

    # --- Tick 1: first motion frame (x=0.1, y=0.05) -----------------------
    shared_mock_broker.publish.reset_mock()
    await input_runtime.tick(dt=0.016)

    # Assertion A: the input layer detected the event and published at least once.
    assert shared_mock_broker.publish.await_count >= 1, (
        "MouseAdapter should publish at least one message per tick"
    )

    # Route every published byte-payload across the seam to the middleware.
    for call in shared_mock_broker.publish.await_args_list:
        _subject, raw_bytes = call.args
        captured_callback(_wire_msg(raw_bytes))

    # "relative" applies value directly — output moves on the very first frame.
    await middleware_runtime.tick(dt=0.016)
    # 0.0 + 0.1 * 1.0 = 0.1
    assert core.virtual_output_state["group1.pan"]  == pytest.approx(0.1)
    # 0.0 + 0.05 * 1.0 = 0.05
    assert core.virtual_output_state["group1.tilt"] == pytest.approx(0.05)

    # --- Tick 2: second motion frame (x=0.2, y=0.1) -----------------------
    shared_mock_broker.publish.reset_mock()
    await input_runtime.tick(dt=0.016)

    for call in shared_mock_broker.publish.await_args_list:
        _subject, raw_bytes = call.args
        captured_callback(_wire_msg(raw_bytes))

    await middleware_runtime.tick(dt=0.016)

    # Assertion B: second frame accumulates on top of first.
    # 0.1 + 0.2 * 1.0 = 0.3
    assert core.virtual_output_state["group1.pan"]  == pytest.approx(0.3)
    # 0.05 + 0.1 * 1.0 = 0.15
    assert core.virtual_output_state["group1.tilt"] == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# Test 2 — Broker contract at the seam (narrow regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mouse_x_broker_payload_matches_middleware_contract(
    shared_mock_broker: MagicMock,
    mouse_mapping_profile: dict,
) -> None:
    """
    Contract guard: proves the exact bytes InputPublisher emits for mouse.x
    are parseable by MiddlewareInputSubscriber with source='mouse.x'.

    If the payload format ever drifts between the two layers, this test is
    the first to break.
    """
    mouse_module = pytest.importorskip("apelios.input.adapters.mouse_adapter")

    class SingleFrameBackend:
        async def poll(self) -> dict[str, float]:
            return {"x": 42.0}

    adapter = mouse_module.MouseAdapter(device="mouse", backend=SingleFrameBackend())
    publisher = InputPublisher(input_publish_prefix="input", broker_client=shared_mock_broker)
    await adapter.start(input_publisher=publisher)
    await adapter.tick(dt=0.016)

    assert shared_mock_broker.publish.await_count == 1
    _subject, raw_bytes = shared_mock_broker.publish.await_args.args

    # Prove the middleware subscriber can parse the raw bytes from the adapter.
    core = MappingMiddleware(profile=mouse_mapping_profile)
    subscriber = MiddlewareInputSubscriber(middleware=core)
    subscriber(_wire_msg(raw_bytes))

    assert "mouse.x" in core.current_raw_input
    assert core.current_raw_input["mouse.x"] == 42.0


# ---------------------------------------------------------------------------
# Test 3 — mouse.y → group1.tilt mapping path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mouse_y_maps_to_group1_tilt(
    shared_mock_broker: MagicMock,
    mouse_mapping_profile: dict,
) -> None:
    """Proves the mouse.y → group1.tilt entry in the mapping profile is active."""
    core = MappingMiddleware(profile=mouse_mapping_profile)
    subscriber = MiddlewareInputSubscriber(middleware=core)

    # "relative" applies value directly on the first frame — no priming step.
    # value=0.3, sensitivity=1.0  →  0.0 + 0.3 = 0.3
    subscriber(_make_raw_msg("mouse.y", 0.3))
    core.process_frame(dt=0.016)
    assert core.virtual_output_state["group1.tilt"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Test 4 — Proportional sub-clamping delta (the interesting physics case)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mouse_small_delta_maps_proportionally(
    shared_mock_broker: MagicMock,
    mouse_mapping_profile: dict,
) -> None:
    """
    Proves a delta small enough to avoid clamping moves the output state
    proportionally.  delta=0.1, sensitivity=1.0  →  output moves by 0.1.
    """
    core = MappingMiddleware(profile=mouse_mapping_profile)
    subscriber = MiddlewareInputSubscriber(middleware=core)

    # Frame 1: 0.0 + 0.1 * 1.0 = 0.1
    subscriber(_make_raw_msg("mouse.x", 0.1))
    core.process_frame(dt=0.016)
    assert core.virtual_output_state["group1.pan"] == pytest.approx(0.1)

    # Frame 2: same movement again — accumulates to 0.2
    subscriber(_make_raw_msg("mouse.x", 0.1))
    core.process_frame(dt=0.016)
    assert core.virtual_output_state["group1.pan"] == pytest.approx(0.2)
