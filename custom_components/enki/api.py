"""Enki API."""

from __future__ import annotations

import aiohttp
import asyncio
import logging
from dataclasses import dataclass
from typing import Any
import time

from .const import (
    LOGGER,
    ENKI_OIDC_URL,
    ENKI_URL,
    ENKI_HOME_API_KEY,
    ENKI_BFF_API_KEY,
    ENKI_NODE_API_KEY,
    ENKI_REFERENTIEL_API_KEY,
    ENKI_LIGHTS_API_KEY,
    ENKI_AIRFLOW_API_KEY,
    ENKI_POWER_API_KEY)

proxy = None

@dataclass
class Device:
    """API device."""
    home_id: str
    device_id: str #device_id represents the type of device used (Hw reference)
    node_id: str #node_id represents the physical device (toke,)
    device_name: str

class API:
    """Class for Enki API."""

    def __init__(self, user: str, pwd: str) -> None:
        """Initialise."""
        self.user = user
        self.pwd = pwd

    @property
    def controller_name(self) -> str:
        """Return the name of the controller."""
        return self.user

    async def check_connected(self) -> bool:
        """Tell if token is still valid"""
        if not hasattr(self, '_access_token') or time.time()>self._tokenExpiresTime:
             await self.connect()
        return True

    async def connect(self) -> bool:
        """Connect to the Enki API."""
        try:
            async with aiohttp.ClientSession() as session, session.request(
                method="POST",
                url=ENKI_OIDC_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type":"password",
                    "client_id": "enki-front",
                    "username": self.user,
                    "password": self.pwd},
                proxy=proxy,) as resp:

                    if resp.status == 200:
                        response = await resp.json()
                        LOGGER.debug("connect : " + str(response))
                        self._access_token = response["access_token"]
                        self._refresh_token = response["refresh_token"]
                        self._token_type = response["token_type"]
                        tokenExpiresTime = time.time() + response["expires_in"]
                        self._tokenExpiresTime = tokenExpiresTime
                        return True
                    else:
                        response = await resp.text()
                        LOGGER.error("Error connecting to api. status %s, response %s", resp.status, str(response))
                        raise APIAuthError("Error connecting to api. Invalid username or password.")
        except APIAuthError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise APIConnectionError("Error connecting to api : " + repr(err)) from err
        except Exception as err:
            raise APIConnectionError("Unexpected error connecting to api : " + repr(err)) from err

# *******************************************************
    async def get_homes(self):
        """Get list of homes."""
        await self.check_connected()
        homes = []
        async with aiohttp.ClientSession() as session, session.request(
             method="GET",
             url=f"{ENKI_URL}/api-enki-home-prod/v1/homes",
             headers={"Authorization": f"{self._token_type} {self._access_token}",
                      "X-Gateway-APIKey": ENKI_HOME_API_KEY},
             proxy=proxy,) as resp:

                if resp.status == 200:
                    response = await resp.json()
                    LOGGER.debug("get_homes : " + str(response))
                    for home in response["items"]:
                        homes.append(home["id"])
                    return homes
                else:
                    response = await resp.text()
                    LOGGER.error("Error on get_homes. status %s, response %s", resp.status, str(response))
                    raise ValueError("bad credentials")

    def merge_properties(self, device: dict[str, Any], properties: dict[str, Any] | None) -> None:
        if not properties:
            return
        for prop in properties:
            if prop != "id":
                device[prop] = properties[prop]

    @staticmethod
    def _parse_bff_power(description: dict[str, Any] | None) -> float | None:
        """Parse power value from BFF description.value (e.g. '109 W' -> 109.0)."""
        if not description or not isinstance(description, dict):
            return None
        value_str = description.get("value")
        if not isinstance(value_str, str):
            return None
        try:
            return float(value_str.split()[0])
        except (ValueError, IndexError):
            return None

    async def get_items_in_section_for_home(self, home_id) -> list[dict[str, Any]]:
            """Get sections in home."""
            await self.check_connected()
            async with aiohttp.ClientSession() as session, session.request(
             method="GET",
             url=f"{ENKI_URL}/api-enki-mobile-bff-prod/v1/dashboard/homes/{home_id}?hasGroups=true",
             headers={"Authorization": f"{self._token_type} {self._access_token}",
                      "X-Gateway-APIKey": ENKI_BFF_API_KEY},
             proxy=proxy,) as resp:
                devices = []
                if resp.status == 200:
                    response = await resp.json()
                    LOGGER.debug("get_items_in_section_for_home : " + str(response))
                    for section in response["sections"]:
                        for item in section["items"]:
                            if 'deviceId' not in item["metadata"].keys():
                                continue
                            device = {
                                "homeId": home_id,
                                "deviceId": item["metadata"]["deviceId"],
                                "nodeId": item["metadata"]["nodeId"],
                                "deviceType": item["metadata"].get("deviceType"),
                                "mainChangeCapabilityId": item["metadata"].get("mainChangeCapabilityId"),
                                "mainCheckCapabilityId": item["metadata"].get("mainCheckCapabilityId"),
                                "mainChangeCapabilityEndpoints": [
                                    endpoint.get("id")
                                    for endpoint in (item["metadata"].get("mainChangeCapability") or {}).get("endpoints", [])
                                    if endpoint.get("id") is not None
                                ],
                                "deviceName": item["title"]["label"],
                                "state": item["state"],
                                "isEnabled": item["isEnabled"],
                                "powerProduction": self._parse_bff_power(item.get("description")),
                            }
                            devices.append(device)

                            node_info = await self.get_node(home_id, device.get("nodeId"))
                            self.merge_properties(device, node_info)

                            await self.refresh_device(device)

                            LOGGER.debug("device : " + repr(device))
                    return devices
                  
                else:
                    response = await resp.text()
                    LOGGER.error("Error on get_items_in_section_for_home. status %s, response %s", resp.status, str(response))
                    raise ValueError("bad credentials")

    async def refresh_device(self, device): 
        """Update device details"""
        device_info = await self.get_device(device.get("deviceId"))
        self.merge_properties(device, device_info)
        if not device.get("isEnabled"):
            return device

        capabilities = _capabilities_set(device)
        possible_values = _possible_values_dict(device)

        if _supports_light_state(capabilities, possible_values):
            await self._refresh_lights_device(device)

        if _supports_electrical_power(capabilities, possible_values):
            power_details = await self.get_electrical_power_details(device.get("homeId"), device.get("nodeId"))
            self.merge_properties(device, {
                "electricalPower": power_details.get("lastReportedValue"),
                "electricalEndpoints": power_details.get("endpoints", []),
            })

        if _supports_fan_speed(capabilities, possible_values):
            fan_speed = await self.get_fan_speed(device.get("homeId"), device.get("nodeId"))
            self.merge_properties(device, {"fanSpeed": fan_speed})

        if _supports_fan_rotation_direction(capabilities, possible_values):
            fan_rotation = await self.get_fan_rotation_direction(device.get("homeId"), device.get("nodeId"))
            self.merge_properties(device, {"fanRotationDirection": fan_rotation})

        if _supports_airflow_mode(capabilities, possible_values):
            airflow_mode = await self.get_airflow_mode(device.get("homeId"), device.get("nodeId"))
            self.merge_properties(device, {"airflowMode": airflow_mode})

        return device

    async def _refresh_lights_device(self, device: dict[str, Any]) -> None:
        """Refresh state for standard light devices."""
        light_details = await self.get_light_details(device.get("homeId"), device.get("nodeId"))
        self.merge_properties(device, light_details)

    async def get_node(self, home_id, node_id):
        """Get details on a node."""
        await self.check_connected()
        async with aiohttp.ClientSession() as session, session.request(
            method="GET",
            url=f"{ENKI_URL}/api-enki-node-agg-prod/v1/nodes/{node_id}",
            headers={"Authorization": f"{self._token_type} {self._access_token}",
                    "X-Gateway-APIKey": ENKI_NODE_API_KEY,
                    "homeId": f"{home_id}"},
            proxy=proxy,) as resp:

                if resp.status == 200:
                    response = await resp.json()
                    LOGGER.debug("get_node : " + str(response))
                    #print("\t\t" + response["icon"] + " " + response["factoryId"] + " " + response["modelNumber"])
                    return response

                else:
                    response = await resp.text()
                    if resp.status == 404:
                        LOGGER.warning("Node not found on get_node. status %s, response %s", resp.status, str(response))
                        return {}
                    LOGGER.error("Error on get_node. status %s, response %s", resp.status, str(response))
                    raise ValueError("bad credentials")

    async def get_device(self, id):
        """Get details on a device."""
        await self.check_connected()
        async with aiohttp.ClientSession() as session, session.request(
            method="GET",
            url=f"{ENKI_URL}/api-enki-referentiel-agg-prod/v1/devices/{id}",
            headers={"Authorization": f"{self._token_type} {self._access_token}",
                    "X-Gateway-APIKey": ENKI_REFERENTIEL_API_KEY},
            proxy=proxy,) as resp:

                if resp.status == 200:
                    response = await resp.json()
                    LOGGER.debug("get_device : " + str(response))
                    return response

                else:
                    response = await resp.text()
                    if resp.status == 404:
                        LOGGER.debug("Device not found on get_device. status %s, response %s", resp.status, str(response))
                        return {}
                    LOGGER.error("Error on get_device. status %s, response %s", resp.status, str(response))
                    raise ValueError("bad credentials")

    async def get_light_details(self,home_id, node_id):
         """Get light state"""
         await self.check_connected()
         async with aiohttp.ClientSession() as session, session.request(
             method="GET",
             url=f"{ENKI_URL}/api-enki-lighting-prod/v1/lighting/{node_id}/check-light-state",
             headers={"Authorization": f"{self._token_type} {self._access_token}",
                      "homeId": home_id,
                      "X-Gateway-APIKey": ENKI_LIGHTS_API_KEY},
             proxy=proxy,) as resp:

                if resp.status == 200:
                    response = await resp.json()
                    LOGGER.debug("get_light_details : " + str(response))
                    return response

                else:
                    response = await resp.text()
                    if resp.status == 404:
                        LOGGER.warning("Light details not found on get_light_details. status %s, response %s", resp.status, str(response))
                        return {}
                    LOGGER.error("Error on get_light_details. status %s, response %s", resp.status, str(response))
                    raise ValueError("bad credentials")

    async def change_light_state(self, home_id, node_id, changes: dict):
        await self.check_connected()
        
        data = (await self.get_light_details(home_id, node_id))["lastReportedValue"]
        data.update(changes)
        
        async with aiohttp.ClientSession() as session, session.request(
            method="POST",
            url=f"{ENKI_URL}/api-enki-lighting-prod/v1/lighting/{node_id}/change-light-state",
            headers={"Authorization": f"{self._token_type} {self._access_token}",
                    "homeId": home_id,
                    "X-Gateway-APIKey": ENKI_LIGHTS_API_KEY},
            proxy=proxy,
            json=data) as resp:

                if resp.status != 202:
                    response = await resp.text()
                    LOGGER.debug(resp.status)
                    LOGGER.error("Error on change_light_state. status %s, response %s", resp.status, str(response))
                    raise ValueError("bad credentials")

    async def _check_airflow_value(self, home_id, node_id, endpoint):
        """Read airflow value from one check endpoint."""
        await self.check_connected()
        async with aiohttp.ClientSession() as session, session.request(
            method="GET",
            url=f"{ENKI_URL}/api-enki-airflow-prod/v1/airflow/{node_id}/{endpoint}",
            headers={
                "Authorization": f"{self._token_type} {self._access_token}",
                "homeId": home_id,
                "X-Gateway-APIKey": ENKI_AIRFLOW_API_KEY,
            },
            proxy=proxy,
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                return response.get("lastReportedValue")

            response = await resp.text()
            if resp.status == 404:
                LOGGER.warning("Airflow endpoint not found on %s. status %s, response %s", endpoint, resp.status, str(response))
                return None
            LOGGER.error("Error on airflow check %s. status %s, response %s", endpoint, resp.status, str(response))
            raise ValueError("bad credentials")

    async def get_electrical_power_details(self, home_id, node_id):
        """Get electrical power state and endpoint states."""
        await self.check_connected()
        async with aiohttp.ClientSession() as session, session.request(
            method="GET",
            url=f"{ENKI_URL}/api-enki-power-prod/v1/power/{node_id}/check-electrical-power",
            headers={
                "Authorization": f"{self._token_type} {self._access_token}",
                "homeId": home_id,
                "X-Gateway-APIKey": ENKI_POWER_API_KEY,
            },
            proxy=proxy,
        ) as resp:
            if resp.status == 200:
                return await resp.json()

            response = await resp.text()
            if resp.status == 404:
                LOGGER.warning("Power endpoint not found. status %s, response %s", resp.status, str(response))
                return {}
            LOGGER.error("Error on power check. status %s, response %s", resp.status, str(response))
            raise ValueError("bad credentials")

    async def switch_electrical_power(self, home_id, node_id, value):
        """Switch electrical power globally."""
        await self.check_connected()
        payload = {"value": value}

        before_state = None
        if LOGGER.isEnabledFor(logging.DEBUG):
            try:
                before_state = await self.get_electrical_power_details(home_id, node_id)
            except Exception as err:
                before_state = {"error": repr(err)}

        LOGGER.info(
            "Calling switch-electrical-power for node %s (home %s) payload=%s",
            node_id,
            home_id,
            payload,
        )

        async with aiohttp.ClientSession() as session, session.request(
            method="POST",
            url=f"{ENKI_URL}/api-enki-power-prod/v1/power/{node_id}/switch-electrical-power",
            headers={
                "Authorization": f"{self._token_type} {self._access_token}",
                "homeId": home_id,
                "X-Gateway-APIKey": ENKI_POWER_API_KEY,
            },
            proxy=proxy,
            json=payload,
        ) as resp:
            if resp.status == 202:
                if LOGGER.isEnabledFor(logging.DEBUG):
                    try:
                        after_state = await self.get_electrical_power_details(home_id, node_id)
                    except Exception as err:
                        after_state = {"error": repr(err)}
                    LOGGER.debug(
                        "switch-electrical-power success node %s payload=%s before=%s after=%s",
                        node_id,
                        payload,
                        before_state,
                        after_state,
                    )
                return

            response = await resp.text()
            LOGGER.error("Error on power switch. status %s, response %s", resp.status, str(response))
            raise ValueError("bad credentials")

    async def _change_airflow_value(self, home_id, node_id, endpoint, value):
        """Write airflow value to one change endpoint."""
        await self.check_connected()
        async with aiohttp.ClientSession() as session, session.request(
            method="POST",
            url=f"{ENKI_URL}/api-enki-airflow-prod/v1/airflow/{node_id}/{endpoint}",
            headers={
                "Authorization": f"{self._token_type} {self._access_token}",
                "homeId": home_id,
                "X-Gateway-APIKey": ENKI_AIRFLOW_API_KEY,
            },
            proxy=proxy,
            json={"value": value},
        ) as resp:
            if resp.status == 202:
                return

            response = await resp.text()
            LOGGER.error("Error on airflow change %s. status %s, response %s", endpoint, resp.status, str(response))
            raise ValueError("bad credentials")

    async def get_fan_speed(self, home_id, node_id):
        """Get fan speed value."""
        return await self._check_airflow_value(home_id, node_id, "check-fan-speed")

    async def change_fan_speed(self, home_id, node_id, value):
        """Set fan speed value."""
        await self._change_airflow_value(home_id, node_id, "change-fan-speed", value)

    async def get_fan_rotation_direction(self, home_id, node_id):
        """Get fan rotation direction."""
        return await self._check_airflow_value(home_id, node_id, "check-fan-rotation-direction")

    async def change_fan_rotation_direction(self, home_id, node_id, value):
        """Set fan rotation direction."""
        await self._change_airflow_value(home_id, node_id, "change-fan-rotation-direction", value)

    async def get_airflow_mode(self, home_id, node_id):
        """Get airflow mode."""
        return await self._check_airflow_value(home_id, node_id, "check-airflow-mode")

    async def change_airflow_mode(self, home_id, node_id, value):
        """Set airflow mode."""
        await self._change_airflow_value(home_id, node_id, "change-airflow-mode", value)

# *******************************************************

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get devices on api."""
        homes = await self.get_homes()
        devices = []
        for home in homes:
            devices.extend(await self.get_items_in_section_for_home(home))

        return devices

class APIAuthError(Exception):
    """Exception class for auth error."""

class APIConnectionError(Exception):
    """Exception class for connection error."""


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


def _supports_light_state(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    """Tell whether light state check/change exists in metadata."""
    return (
        "change_light_state" in capabilities
        or "check_light_state" in capabilities
        or "change_light_state" in possible_values
        or "check_light_state" in possible_values
    )


def _supports_electrical_power(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    """Tell whether electrical power check/change exists in metadata."""
    return (
        "switch_electrical_power" in capabilities
        or "check_electrical_power" in capabilities
        or "switch_electrical_power" in possible_values
        or "check_electrical_power" in possible_values
    )


def _supports_fan_speed(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    """Tell whether fan speed control exists in metadata."""
    return (
        "change_fan_speed" in capabilities
        or "check_fan_speed" in capabilities
        or "change_fan_speed" in possible_values
        or "check_fan_speed" in possible_values
    )


def _supports_fan_rotation_direction(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    """Tell whether fan rotation direction exists in metadata."""
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
