"""Config flow for Integration 101 Template integration."""

from __future__ import annotations
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
)

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    from .api import API, APIAuthError, APIConnectionError

    api = API(data[CONF_USERNAME], data[CONF_PASSWORD])
    try:
        await api.connect()
    except APIAuthError as err:
        LOGGER.warning("Enki authentication failed for user %s: %s", data[CONF_USERNAME], err)
        raise InvalidAuth from err
    except APIConnectionError as err:
        LOGGER.warning("Enki connection failed for user %s: %s", data[CONF_USERNAME], err)
        raise CannotConnect from err
    return {"title": f"Enki - {data[CONF_USERNAME]}"}


class EnkiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Enki Integration."""

    VERSION = 1
    _input_data: dict[str, Any]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step."""
        # Called when you initiate adding an integration via the UI
        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            try:
                # Validate that the setup data is valid and if not handle errors.
                # The errors["base"] values match the values in your strings.json and translation files.
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                LOGGER.error("Enki config flow cannot connect for user %s", user_input.get(CONF_USERNAME))
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                LOGGER.error("Enki config flow invalid auth for user %s", user_input.get(CONF_USERNAME))
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                await self.async_set_unique_id(info.get("title"))
                self._abort_if_unique_id_configured()
                self._input_data = {**user_input, "_title": info["title"]}
                return await self.async_step_polling()

        # Show initial form.
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_polling(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the polling interval step."""
        if user_input is not None:
            title = self._input_data.pop("_title")
            return self.async_create_entry(
                title=title,
                data={**self._input_data, CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        return self.async_show_form(
            step_id="polling",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                        vol.Coerce(int), vol.Range(min=10, max=3600)
                    ),
                }
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Add reconfigure step to allow to reconfigure a config entry."""
        # This methid displays a reconfigure option in the integration and is
        # different to options.
        # It can be used to reconfigure any of the data submitted when first installed.
        # This is optional and can be removed if you do not want to allow reconfiguration.
        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                LOGGER.error("Enki reconfigure cannot connect for user %s", user_input.get(CONF_USERNAME))
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                LOGGER.error("Enki reconfigure invalid auth for user %s", user_input.get(CONF_USERNAME))
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    config_entry,
                    unique_id=config_entry.unique_id,
                    data={**config_entry.data, **user_input},
                    reason="reconfigure_successful",
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=config_entry.data[CONF_USERNAME]
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                }
            ),
            errors=errors,
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
