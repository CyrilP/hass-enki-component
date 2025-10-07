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
    # This gets the data update coordinator from the config entry runtime data as specified in your __init__.py
    coordinator: EnkiCoordinator = config_entry.runtime_data.coordinator

    # ----------------------------------------------------------------------------
    # Here we are going to add some lights entities for the lights in our mock data.
    # We have an on/off light and a dimmable light in our mock data, so add each
    # specific class based on the light type.
    # ----------------------------------------------------------------------------
    lights = []

    lights.extend(
        [
            EnkiLight(coordinator, device, "state")
            for device in coordinator.data
            if device.get("type") == "lights"
        ]
    )

    # Create the lights.
    async_add_entities(lights)

class EnkiLight(EnkiBaseEntity, LightEntity):
    """Implementation of an light depending on its capabilities."""
    _attr_supported_color_modes = set()
    _attr_color_mode = None
    _attr_min_color_temp_kelvin = None
    _attr_max_color_temp_kelvin = None
    BRIGHTNESS_SCALE = (1,255)

    def __init__(
        self, coordinator: EnkiCoordinator, device: dict[str, Any], parameter: str
    ) -> None:
        """Initialise entity."""
        super().__init__(coordinator, device, parameter)
        self._device = device
        if "possibleValues" in device and "change_brightness" in device["possibleValues"]:
            min = device["possibleValues"]["change_brightness"]["range"]["min"]
            max = device["possibleValues"]["change_brightness"]["range"]["max"]
            LOGGER.debug("brightness min : " + str(min))
            LOGGER.debug("brightness max : " + str(max))
            self.BRIGHTNESS_SCALE = (min, max)

        if "change_color_temperature" in device["capabilities"]:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.COLOR_TEMP
            if "possibleValues" in device and "change_color_temperature" in device["possibleValues"]:
                values = device["possibleValues"]["change_color_temperature"]["values"]
                min = int(values[0][1:-1])
                max = int(values[-1][1:-1])
                self._attr_min_color_temp_kelvin=min
                self._attr_max_color_temp_kelvin=max
                self._color_temp_values = []
                for val in values:
                    self._color_temp_values.append(int(val[1:-1]))
            else:
                self._attr_min_color_temp_kelvin=DEFAULT_MIN_KELVIN
                self._attr_max_color_temp_kelvin=DEFAULT_MAX_KELVIN

        if "change_brightness" in device["capabilities"]:
            if len(self._attr_supported_color_modes) == 0:
                self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            if self._attr_color_mode is None:
                self._attr_color_mode = ColorMode.BRIGHTNESS

        if "switch_electrical_power" in  device["capabilities"]:
            if len(self._attr_supported_color_modes) == 0:
                self._attr_supported_color_modes.add(ColorMode.ONOFF)
                self._attr_color_mode = ColorMode.ONOFF

        if len(self._attr_supported_color_modes) > 1:
            self._attr_color_mode = ColorMode.UNKNOWN

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is on."""
        # This needs to enumerate to true or false
        last_reported_values = self.coordinator.get_device_parameter(self.node_id, "lastReportedValue")
        return (
            last_reported_values["power"] == "ON"
        )

    def closest_temp_value(self, target_value):
        return min(self._color_temp_values, key=lambda x: abs(x - target_value)) 

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if "brightness" in kwargs:
            ha_value = kwargs["brightness"]
            value = round(ha_value / (255/self.BRIGHTNESS_SCALE[1]), 2)
            LOGGER.debug(f"setting brightness value to {ha_value} => {value}")
            await self.coordinator.api.change_light_state(self._device["homeId"], self._device["nodeId"], "brightness", value)
            self.coordinator.update_data(self.node_id, "lastReportedValue", "brightness", value)
        elif "color_temp_kelvin" in kwargs:
            ha_value = kwargs["color_temp_kelvin"]
            value = self.closest_temp_value(ha_value)
            LOGGER.debug("setting color temp to closest value : " + str(ha_value) + " => " + str(value))
            await self.coordinator.api.change_light_state(self._device["homeId"], self._device["nodeId"], "colorTemperature", "T" + str(value) + "K")
            self.coordinator.update_data(self.node_id, "lastReportedValue", "colorTemperature", "T" + str(value) + "K")
        else:
            await self.coordinator.api.change_light_state(self._device["homeId"], self._device["nodeId"], "power", "ON")
            self.coordinator.update_data(self.node_id, "lastReportedValue", "power", "ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.coordinator.api.change_light_state(self._device["homeId"], self._device["nodeId"], "power", "OFF")
        self.coordinator.update_data(self.node_id, "lastReportedValue", "power", "OFF")

    @property
    def brightness(self) -> Optional[int]:
        """Return the current brightness."""
        last_reported_values = self.coordinator.get_device_parameter(self.node_id, "lastReportedValue")
        return last_reported_values["brightness"]*(255/self.BRIGHTNESS_SCALE[1])
    
    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        last_reported_values = self.coordinator.get_device_parameter(self.node_id, "lastReportedValue")
        return int(last_reported_values["colorTemperature"][1:-1])
