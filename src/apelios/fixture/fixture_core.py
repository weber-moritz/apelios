"""Fixture state engine."""

from __future__ import annotations

from typing import Any


class FixtureCore:
    """Resolve fixture types into normalized state and DMX output."""

    def __init__(self, patch: dict[str, Any] | None = None) -> None:
        self.patch = patch or {}
        self.inbox: dict[str, dict[str, Any]] = {}
        self.internal_state: dict[str, float] = {}
        self.dmx_output: dict[tuple[int, int], int] = {}

    def process_frame(self, dt: float) -> None:
        """Process all pending payloads for one frame."""
        self.dmx_output = {}

        fixtures = self.patch.get("fixtures", {})
        if not isinstance(fixtures, dict):
            return

        for target, payload in list(self.inbox.items()):
            fixture_name, parameter_name = self._split_target(target)
            if fixture_name is None or parameter_name is None:
                continue

            fixture_patch = fixtures.get(fixture_name)
            if not isinstance(fixture_patch, dict):
                continue

            parameters = fixture_patch.get("parameters", {})
            if not isinstance(parameters, dict):
                continue

            parameter_patch = parameters.get(parameter_name)
            if not isinstance(parameter_patch, dict):
                continue

            current_state = self.internal_state.get(target, 0.0)
            type_ = str(payload.get("type", parameter_patch.get("type", "absolute_uni")))
            input_value = float(payload.get("value", 0.0))
            next_state = self._apply_type(current_state, input_value, type_, dt)

            limits = parameter_patch.get("limits", [0.0, 1.0])
            minimum, maximum = self._extract_limits(limits)
            next_state = max(minimum, min(maximum, next_state))

            self.internal_state[target] = next_state

            universe = int(fixture_patch.get("universe", 0))
            fixture_base_address = int(fixture_patch.get("address", 0))
            parameter_offset = self._get_parameter_offset(fixtures, fixture_name, parameter_name, parameters, parameter_patch)
            address = fixture_base_address + parameter_offset
            width = int(parameter_patch.get("width", 8))
            self._write_dmx(universe, address, width, next_state)

        self.inbox.clear

    def _apply_type(self, current_state: float, input_value: float, type_: str, dt: float) -> float:
        if type_ == "delta":
            return current_state + input_value
        if type_ == "rate":
            return current_state + (input_value * dt)
        return input_value

    def _write_dmx(self, universe: int, address: int, width: int, normalized_value: float) -> None:
        if width == 16:
            value_16 = int(round(max(0.0, min(1.0, normalized_value)) * 65535))
            coarse = (value_16 >> 8) & 0xFF
            fine = value_16 & 0xFF
            self.dmx_output[(universe, address)] = coarse
            self.dmx_output[(universe, address + 1)] = fine
            return

        value_8 = int(round(max(0.0, min(1.0, normalized_value)) * 255))
        self.dmx_output[(universe, address)] = value_8

    def _extract_limits(self, limits: Any) -> tuple[float, float]:
        if isinstance(limits, (list, tuple)) and len(limits) == 2:
            try:
                return float(limits[0]), float(limits[1])
            except (TypeError, ValueError):
                pass
        return 0.0, 1.0

    def _get_parameter_offset(
        self,
        fixtures: dict[str, Any],
        fixture_name: str,
        parameter_name: str,
        parameters: dict[str, Any],
        parameter_patch: dict[str, Any],
    ) -> int:
        """Get parameter offset, either explicit or sequential.
        
        If parameter has explicit 'address' field, use it.
        Otherwise, calculate sequential offset based on previous parameters' (offset + width).
        """
        # If parameter has explicit address, use it
        if "address" in parameter_patch:
            return int(parameter_patch["address"])
        
        # Otherwise, calculate sequential offset
        offset = 0
        for param_name, param_patch in parameters.items():
            if param_name == parameter_name:
                return offset
            # Add this parameter's width to the offset
            param_width = int(param_patch.get("width", 8))
            offset += param_width
        
        return offset

    def _split_target(self, target: str) -> tuple[str | None, str | None]:
        parts = target.split(".")
        if len(parts) < 2:
            return None, None
        return parts[0], parts[-1]