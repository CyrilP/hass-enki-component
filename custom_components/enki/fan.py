"""Fan setup for Enki integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EnkiConfigEntry
from .base import EnkiBaseEntity
from .coordinator import EnkiCoordinator




async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnkiConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up fan entities."""
    coordinator: EnkiCoordinator = config_entry.runtime_data.coordinator

    fans = [
        EnkiFan(coordinator, device, "state")
        for device in coordinator.data
        if _is_fan_device(device)
    ]

    async_add_entities(fans)


class EnkiFan(EnkiBaseEntity, FanEntity):
    """Representation of an Enki fan."""

    _attr_supported_features = FanEntityFeature(0)
    _attr_preset_modes: list[str] = []

    def __init__(self, coordinator: EnkiCoordinator, device: dict[str, Any], parameter: str) -> None:
        super().__init__(coordinator, device, parameter)
        self.parameter = "fan"

        self._capabilities = _capabilities_set(device)
        self._possible_values = _possible_values_dict(device)
        self._max_fan_speed = _fan_max_speed(device)
        self._supports_speed = _supports_fan_speed(self._capabilities, self._possible_values) and self._max_fan_speed is not None
        self._supports_direction = _supports_fan_direction(self._capabilities, self._possible_values)
        self._attr_preset_modes = _airflow_modes(self._possible_values)
        self._supports_preset_mode = _supports_airflow_mode(self._capabilities, self._possible_values) and bool(self._attr_preset_modes)
        self._supports_power = "switch_electrical_power" in self._capabilities

        self._attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self._supports_speed:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED
        if self._supports_direction:
            self._attr_supported_features |= FanEntityFeature.DIRECTION
        if self._supports_preset_mode:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

    @property
    def percentage(self) -> int | None:
        """Return fan speed percentage."""
        if not self._supports_speed:
            return None

        speed = self.coordinator.get_device_parameter(self.node_id, "fanSpeed")
        if speed is None:
            return None
        speed_value = max(0, min(self._max_fan_speed, int(speed)))
        return round((speed_value / self._max_fan_speed) * 100)

    @property
    def is_on(self) -> bool | None:
        """Return if fan is on."""
        if not self._supports_speed:
            last_reported = self.coordinator.get_device_parameter(self.node_id, "lastReportedValue")
            if isinstance(last_reported, dict):
                power = last_reported.get("power")
                if isinstance(power, str):
                    return power == "ON"
            return None

        speed = self.coordinator.get_device_parameter(self.node_id, "fanSpeed")
        return speed is not None and int(speed) > 0

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        """Turn fan on."""
        if preset_mode is not None and self._supports_preset_mode:
            await self.async_set_preset_mode(preset_mode)

        if not self._supports_speed:
            if self._supports_power:
                await self.coordinator.api.switch_electrical_power(self.device["homeId"], self.node_id, "ON")
            return

        target_percentage = percentage if percentage is not None else 15
        await self.async_set_percentage(target_percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn fan off by setting speed to 0."""
        if not self._supports_speed:
            if self._supports_power:
                await self.coordinator.api.switch_electrical_power(self.device["homeId"], self.node_id, "OFF")
            return

        await self.coordinator.api.change_fan_speed(self.device["homeId"], self.node_id, 0)
        self.coordinator.update_data(self.node_id, None, "fanSpeed", 0)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set speed percentage."""
        if not self._supports_speed:
            return

        bounded = max(0, min(100, percentage))
        speed = round((bounded / 100) * self._max_fan_speed)
        await self.coordinator.api.change_fan_speed(self.device["homeId"], self.node_id, speed)
        self.coordinator.update_data(self.node_id, None, "fanSpeed", speed)

    @property
    def current_direction(self) -> str | None:
        """Return current fan direction."""
        if not self._supports_direction:
            return None

        value = self.coordinator.get_device_parameter(self.node_id, "fanRotationDirection")
        if value == "COUNTERCLOCKWISE":
            return DIRECTION_REVERSE
        if value == "CLOCKWISE":
            return DIRECTION_FORWARD
        return None

    async def async_set_direction(self, direction: str) -> None:
        """Set fan direction."""
        if not self._supports_direction:
            return

        value = "CLOCKWISE" if direction == DIRECTION_FORWARD else "COUNTERCLOCKWISE"
        await self.coordinator.api.change_fan_rotation_direction(
            self.device["homeId"], self.node_id, value
        )
        self.coordinator.update_data(self.node_id, None, "fanRotationDirection", value)

    @property
    def preset_mode(self) -> str | None:
        """Return airflow mode as preset mode."""
        if not self._supports_preset_mode:
            return None

        value = self.coordinator.get_device_parameter(self.node_id, "airflowMode")
        if value in self._attr_preset_modes:
            return value
        return None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set airflow mode."""
        if not self._supports_preset_mode:
            return

        if preset_mode not in self._attr_preset_modes:
            raise ValueError(f"Unsupported preset mode: {preset_mode}")

        await self.coordinator.api.change_airflow_mode(
            self.device["homeId"], self.node_id, preset_mode
        )
        self.coordinator.update_data(self.node_id, None, "airflowMode", preset_mode)


def _capabilities_set(device: dict[str, Any]) -> set[str]:
    """Return capabilities as a normalized string set."""
    capabilities = device.get("capabilities")
    if isinstance(capabilities, list):
        return {capability for capability in capabilities if isinstance(capability, str)}
    if isinstance(capabilities, dict):
        return set(capabilities.keys())
    return set()


def _possible_values_dict(device: dict[str, Any]) -> dict[str, Any]:
    """Return possibleValues metadata as a dict if available."""
    possible_values = device.get("possibleValues")
    if isinstance(possible_values, dict):
        return possible_values
    return {}


def _supports_fan_speed(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    """Tell whether fan speed control exists in metadata."""
    return (
        "change_fan_speed" in capabilities
        or "check_fan_speed" in capabilities
        or "change_fan_speed" in possible_values
        or "check_fan_speed" in possible_values
    )


def _supports_fan_direction(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    """Tell whether fan direction control exists in metadata."""
    return (
        "change_fan_rotation_direction" in capabilities
        or "check_fan_rotation_direction" in capabilities
        or "change_fan_rotation_direction" in possible_values
        or "check_fan_rotation_direction" in possible_values
    )


def _supports_airflow_mode(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    """Tell whether airflow mode exists in metadata."""
    return (
        "change_airflow_mode" in capabilities
        or "check_airflow_mode" in capabilities
        or "change_airflow_mode" in possible_values
        or "check_airflow_mode" in possible_values
    )


def _fan_max_speed(device: dict[str, Any]) -> int | None:
    """Read max fan speed from possibleValues. Returns None if not available."""
    possible_values = _possible_values_dict(device)
    speed_meta = possible_values.get("change_fan_speed") or possible_values.get("check_fan_speed")
    if isinstance(speed_meta, dict):
        speed_range = speed_meta.get("range")
        if isinstance(speed_range, dict):
            raw_max = speed_range.get("max")
            if isinstance(raw_max, (int, float)) and raw_max > 0:
                return max(1, int(round(raw_max)))
    return None


def _airflow_modes(possible_values: dict[str, Any]) -> list[str]:
    """Read airflow mode options from possibleValues metadata. Returns [] if not available."""
    airflow_meta = possible_values.get("change_airflow_mode") or possible_values.get("check_airflow_mode")
    if isinstance(airflow_meta, dict):
        values = airflow_meta.get("values")
        if isinstance(values, list):
            return [value for value in values if isinstance(value, str)]
    return []


def _is_fan_device(device: dict[str, Any]) -> bool:
    """Detect fan devices from capabilities/possibleValues metadata."""
    capabilities = _capabilities_set(device)
    possible_values = _possible_values_dict(device)

    return (
        _supports_fan_speed(capabilities, possible_values)
        or _supports_fan_direction(capabilities, possible_values)
        or _supports_airflow_mode(capabilities, possible_values)
    )