"""Light setup for our Integration."""

from typing import Optional
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.components.light.const import DEFAULT_MIN_KELVIN, DEFAULT_MAX_KELVIN 
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EnkiConfigEntry
from .base import EnkiBaseEntity
from .coordinator import EnkiCoordinator
from .const import LOGGER

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnkiConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Binary Sensors."""
    coordinator: EnkiCoordinator = config_entry.runtime_data.coordinator

    lights = [
        entity
        for device in coordinator.data
        for entity in _build_light_entities(coordinator, device)
    ]
    async_add_entities(lights)

class EnkiLight(EnkiBaseEntity, LightEntity):
    """Implementation of an light depending on its capabilities."""
    _attr_supported_color_modes = set()
    _attr_color_mode = None
    _attr_min_color_temp_kelvin = None
    _attr_max_color_temp_kelvin = None
    BRIGHTNESS_SCALE = (1,255)

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: dict[str, Any],
        parameter: str,
        endpoint_id: int | None = None,
    ) -> None:
        """Initialise entity."""
        super().__init__(coordinator, device, parameter)
        self._device = device
        self._endpoint_id = endpoint_id
        self._color_temp_values = []
        self.parameter = parameter
        self._attr_supported_color_modes = set()  # instance-level to avoid class mutation
        self._attr_color_mode = None

        capabilities = _capabilities_set(device)
        if "possibleValues" in device and "change_brightness" in device["possibleValues"]:
            min_value = device["possibleValues"]["change_brightness"]["range"]["min"]
            max_value = device["possibleValues"]["change_brightness"]["range"]["max"]
            LOGGER.debug("brightness min : " + str(min_value))
            LOGGER.debug("brightness max : " + str(max_value))
            self.BRIGHTNESS_SCALE = (min_value, max_value)

        if "change_color_temperature" in capabilities:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.COLOR_TEMP
            if "possibleValues" in device and "change_color_temperature" in device["possibleValues"]:
                values = device["possibleValues"]["change_color_temperature"]["values"]
                min_value = int(values[0][1:-1])
                max_value = int(values[-1][1:-1])
                self._attr_min_color_temp_kelvin=min_value
                self._attr_max_color_temp_kelvin=max_value
                for val in values:
                    self._color_temp_values.append(int(val[1:-1]))
            else:
                self._attr_min_color_temp_kelvin=DEFAULT_MIN_KELVIN
                self._attr_max_color_temp_kelvin=DEFAULT_MAX_KELVIN

        if "change_brightness" in capabilities:
            if len(self._attr_supported_color_modes) == 0:
                self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            if self._attr_color_mode is None:
                self._attr_color_mode = ColorMode.BRIGHTNESS

        if "switch_electrical_power" in capabilities:
            if len(self._attr_supported_color_modes) == 0:
                self._attr_supported_color_modes.add(ColorMode.ONOFF)
                self._attr_color_mode = ColorMode.ONOFF

        if len(self._attr_supported_color_modes) > 1:
            self._attr_color_mode = ColorMode.UNKNOWN

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is on."""
        if self._endpoint_id is not None:
            endpoints = self.coordinator.get_device_parameter(self.node_id, "electricalEndpoints")
            if isinstance(endpoints, list):
                for ep in endpoints:
                    if not isinstance(ep, dict):
                        continue
                    if ep.get("id") == self._endpoint_id:
                        endpoint_lrv = ep.get("lastReportedValue")
                        if isinstance(endpoint_lrv, str):
                            return endpoint_lrv == "ON"
                        if isinstance(endpoint_lrv, dict):
                            power = endpoint_lrv.get("power")
                            return power == "ON" if power is not None else None

        # Fallback for devices without per-endpoint status shape.
        last_reported_values = self.coordinator.get_device_parameter(self.node_id, "lastReportedValue")
        if isinstance(last_reported_values, dict):
            power = last_reported_values.get("power")
            return power == "ON" if power is not None else None
        return None

    def closest_temp_value(self, target_value):
        return min(self._color_temp_values, key=lambda x: abs(x - target_value)) 

    def _light_endpoint_ids(self) -> list[int]:
        """Return endpoint ids used by light entities on this device."""
        return _main_change_capability_endpoint_ids(self._device)

    def _light_endpoints_have_mixed_power(self) -> bool:
        """Return True when at least one light endpoint is ON and another is OFF."""
        endpoint_ids = self._light_endpoint_ids()
        if len(endpoint_ids) <= 1:
            return False

        endpoints = self.coordinator.get_device_parameter(self.node_id, "electricalEndpoints")
        if not isinstance(endpoints, list):
            return False

        power_values: set[str] = set()
        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                continue
            endpoint_id = endpoint.get("id")
            if endpoint_id not in endpoint_ids:
                continue

            last_reported_value = endpoint.get("lastReportedValue")
            if isinstance(last_reported_value, str) and last_reported_value in {"ON", "OFF"}:
                power_values.add(last_reported_value)
            elif isinstance(last_reported_value, dict):
                power = last_reported_value.get("power")
                if power in {"ON", "OFF"}:
                    power_values.add(power)

            if len(power_values) > 1:
                return True

        return False

    def update_data_power_light_endpoints(self, power: str) -> None:
        """Apply optimistic power to known light endpoints in coordinator cache."""
        for endpoint_id in self._light_endpoint_ids():
            self.coordinator.update_endpoint_power(self.node_id, endpoint_id, power)

    async def _mixed_endpoint_workaround(self) -> None:
        """Send OFF first when needed to force a fresh ON transition for all lights."""
        if self._light_endpoints_have_mixed_power():
            await self.coordinator.api.change_light_state(
                self._device["homeId"],
                self._device["nodeId"],
                {"power": "OFF"},
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        # TODO: switch_electrical_power turns on ALL endpoints of the device (lights, fan, etc).
        # Until the API supports per-endpoint control without side-effects, use change_light_state
        # for all light entities regardless of whether they have an endpoint_id. This will turn on
        # all the lights but at least will not turn on the fan or other non-light endpoints.
        # Additional workaround: if the light endpoints are in mixed state (one ON, another OFF),
        # force an OFF->ON transition so turn_on is not ignored when global power is already ON.
        await self._mixed_endpoint_workaround()

        changes: dict[str, Any] = {"power": "ON"}
        if "brightness" in kwargs:
            ha_value = kwargs["brightness"]
            changes["brightness"] = round(ha_value / (255/self.BRIGHTNESS_SCALE[1]), 2)
            LOGGER.debug(f"setting brightness value to {ha_value} => {changes['brightness']}")

        if "color_temp_kelvin" in kwargs:
            ha_value = kwargs["color_temp_kelvin"]
            value = self.closest_temp_value(ha_value)
            LOGGER.debug("setting color temp to closest value : " + str(ha_value) + " => " + str(value))
            changes["colorTemperature"] = "T" + str(value) + "K"

        await self.coordinator.api.change_light_state(
            self._device["homeId"],
            self._device["nodeId"],
            changes,
        )

        self.update_data_power_light_endpoints("ON")
        self.coordinator.update_data(self.node_id, "lastReportedValue", "power", "ON")        
        if "brightness" in changes:
            self.coordinator.update_data(self.node_id, "lastReportedValue", "brightness", changes["brightness"])
        if "colorTemperature" in changes:
            self.coordinator.update_data(self.node_id, "lastReportedValue", "colorTemperature", changes["colorTemperature"])

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        # TODO: switch_electrical_power turns off ALL endpoints of the device (lights, fan, etc).
        # Until the API supports per-endpoint control without side-effects, use change_light_state
        # for all light entities regardless of whether they have an endpoint_id. This will turn off
        # all the lights but at least will not turn off the fan or other non-light endpoints.
        await self.coordinator.api.change_light_state(self._device["homeId"], self._device["nodeId"], {"power": "OFF"})

        self.update_data_power_light_endpoints("OFF")
        self.coordinator.update_data(self.node_id, "lastReportedValue", "power", "OFF")        

    @property
    def brightness(self) -> Optional[int]:
        """Return the current brightness."""
        last_reported_values = self.coordinator.get_device_parameter(self.node_id, "lastReportedValue")
        if "brightness" not in last_reported_values:
            return None
        return last_reported_values["brightness"]*(255/self.BRIGHTNESS_SCALE[1])
    
    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        last_reported_values = self.coordinator.get_device_parameter(self.node_id, "lastReportedValue")
        if "colorTemperature" not in last_reported_values:
            return None
        return int(last_reported_values["colorTemperature"][1:-1])


def _build_light_entities(coordinator: EnkiCoordinator, device: dict[str, Any]) -> list[LightEntity]:
    """Create light entities from power capability and BFF endpoint metadata."""
    if not _has_switch_electrical_power(device):

        return []

    endpoint_ids = _main_change_capability_endpoint_ids(device)
    if endpoint_ids:
        return [
            EnkiLight(coordinator, device, parameter=f"light_{chr(ord('a') + i)}", endpoint_id=endpoint_id)
            for i, endpoint_id in enumerate(endpoint_ids)
        ]

    return [EnkiLight(coordinator, device, parameter="light", endpoint_id=None)]


def _has_switch_electrical_power(device: dict[str, Any]) -> bool:
    """Check whether the device supports switch_electrical_power capability."""
    return "switch_electrical_power" in _capabilities_set(device)


def _main_change_capability_endpoint_ids(device: dict[str, Any]) -> list[int]:
    """Return BFF endpoints for mainChangeCapability=switch_electrical_power."""
    if device.get("mainChangeCapabilityId") != "switch_electrical_power":
        return []

    raw_endpoints = device.get("mainChangeCapabilityEndpoints")
    if not isinstance(raw_endpoints, list):
        return []

    endpoint_ids: set[int] = set()
    for endpoint in raw_endpoints:
        if isinstance(endpoint, int):
            endpoint_ids.add(endpoint)
            continue
        if isinstance(endpoint, dict):
            endpoint_id = endpoint.get("id")
            if isinstance(endpoint_id, int):
                endpoint_ids.add(endpoint_id)

    return sorted(endpoint_ids)


def _capabilities_set(device: dict[str, Any]) -> set[str]:
    """Return a safe capability set from device metadata."""
    capabilities = device.get("capabilities")
    if isinstance(capabilities, list):
        return {capability for capability in capabilities if isinstance(capability, str)}
    if isinstance(capabilities, dict):
        return set(capabilities.keys())
    return set()