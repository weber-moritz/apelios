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
        """Process all pending payloads for one frame.
        
        For Phase 6: Multiple inputs can map to the same target.
        - Group inbox entries by target
        - For each target, sum contributions from all sources
        - Track per-target state for absolute value initialization
        """
        self.dmx_output = {}

        fixtures = self.patch.get("fixtures", {})
        if not isinstance(fixtures, dict):
            return

        # Group inbox entries by target
        # inbox is now keyed by source: {source: {source, target, type, value}}
        targets: dict[str, list[dict[str, Any]]] = {}
        for source, payload in list(self.inbox.items()):
            target = payload.get("target")
            if not isinstance(target, str):
                continue
            if target not in targets:
                targets[target] = []
            targets[target].append(payload)

        # Process each target
        for target, payloads in targets.items():
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

            # Get per-target state
            target_state = self.internal_state.get(target, {"value": 0.0, "has_first_abs": False, "first_abs_value": 0.0})
            
            # Calculate total contribution for this frame
            total_delta = 0.0
            
            for payload in payloads:
                type_ = str(payload.get("type") or "absolute_uni")
                input_value = float(payload.get("value", 0.0))
                
                if type_ == "absolute_uni":
                    # First absolute sets the base value
                    if not target_state["has_first_abs"]:
                        target_state["has_first_abs"] = True
                        target_state["first_abs_value"] = input_value
                        target_state["value"] = input_value
                    else:
                        # Subsequent absolutes contribute delta
                        delta = input_value - target_state["value"]
                        total_delta += delta
                        target_state["value"] = input_value
                elif type_ == "absolute_bi":
                    # Treat absolute_bi as absolute for now
                    if not target_state["has_first_abs"]:
                        target_state["has_first_abs"] = True
                        target_state["first_abs_value"] = input_value
                        target_state["value"] = input_value
                    else:
                        delta = input_value - target_state["value"]
                        total_delta += delta
                        target_state["value"] = input_value
                elif type_ == "delta":
                    total_delta += input_value
                elif type_ == "rate":
                    total_delta += input_value * dt
            
            # Apply total delta to current value
            new_value = target_state["value"] + total_delta
            
            # Apply limits
            limits = parameter_patch.get("limits", [0.0, 1.0])
            minimum, maximum = self._extract_limits(limits)
            new_value = max(minimum, min(maximum, new_value))
            target_state["value"] = new_value
            self.internal_state[target] = target_state

            # Write DMX output
            universe = int(fixture_patch.get("universe", 0))
            fixture_base_address = int(fixture_patch.get("address", 0))
            parameter_offset = self._get_parameter_offset(fixtures, fixture_name, parameter_name, parameters, parameter_patch)
            address = fixture_base_address + parameter_offset
            width = int(parameter_patch.get("width", 8))
            self._write_dmx(universe, address, width, new_value)

        self.inbox.clear()

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
        Otherwise, calculate sequential offset based on previous parameters' channel counts.
        The 'width' field indicates bit depth (8 or 16), which translates to channel count.
        """
        # If parameter has explicit address, use it
        if "address" in parameter_patch:
            return int(parameter_patch["address"])
        
        # Otherwise, calculate sequential offset
        offset = 0
        for param_name, param_patch in parameters.items():
            if param_name == parameter_name:
                return offset
            # Add this parameter's DMX channel count to the offset
            # width=8 means 8-bit = 1 channel, width=16 means 16-bit = 2 channels
            param_width = int(param_patch.get("width", 8))
            channel_count = 2 if param_width == 16 else 1
            offset += channel_count
        
        return offset

    def _split_target(self, target: str) -> tuple[str | None, str | None]:
        parts = target.split(".")
        if len(parts) < 2:
            return None, None
        return parts[0], parts[-1]