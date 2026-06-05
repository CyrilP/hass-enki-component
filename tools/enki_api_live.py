"""Standalone live diagnostics for Enki API (no pytest required)."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from typing import Any


def _load_enki_api_class():
    """Load API class without importing Home Assistant integration package."""
    component_dir = Path(__file__).resolve().parents[1] / "custom_components" / "enki"
    package_name = "_enki_tools_runtime"

    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(component_dir)]
        sys.modules[package_name] = package

    const_module_name = f"{package_name}.const"
    if const_module_name not in sys.modules:
        const_spec = importlib.util.spec_from_file_location(
            const_module_name,
            component_dir / "const.py",
        )
        if const_spec is None or const_spec.loader is None:
            raise RuntimeError("Could not load const.py for live API script")
        const_module = importlib.util.module_from_spec(const_spec)
        sys.modules[const_module_name] = const_module
        const_spec.loader.exec_module(const_module)

    api_module_name = f"{package_name}.api"
    api_spec = importlib.util.spec_from_file_location(
        api_module_name,
        component_dir / "api.py",
    )
    if api_spec is None or api_spec.loader is None:
        raise RuntimeError("Could not load api.py for live API script")

    api_module = importlib.util.module_from_spec(api_spec)
    sys.modules[api_module_name] = api_module
    api_spec.loader.exec_module(api_module)

    return api_module.API


async def _run_live_api_check(user: str, password: str) -> None:
    api_cls = _load_enki_api_class()
    api = api_cls(user, password)

    connected = await api.connect()
    if connected is not True:
        raise RuntimeError("Enki API login did not return True")

    devices = await api.get_devices()
    if not isinstance(devices, list):
        raise RuntimeError("Enki API did not return a device list")

    print(f"\nDevices found: {len(devices)}")
    for index, device in enumerate(devices, start=1):
        name = device.get("deviceName") or "unknown-device"
        device_type = device.get("type") or "unknown-type"
        device_kind = device.get("deviceType") or "unknown-deviceType"
        node_id = device.get("nodeId") or "unknown-node"

        print(
            f"{index}. {name} | type={device_type} | deviceType={device_kind} | node={node_id}"
        )
        print("   raw-json:")
        print(json.dumps(device, indent=2, ensure_ascii=False, sort_keys=True))

        if device_kind == "ceiling_fans":
            home_id = device.get("homeId")
            await _print_ceiling_fan_endpoint_details(api, home_id, node_id, device.get("deviceId"))
        elif _is_normal_light_device(device):
            home_id = device.get("homeId")
            await _print_normal_light_details(api, home_id, node_id)
        elif _is_inverter_device(device):
            home_id = device.get("homeId")
            await _print_inverter_endpoint_details(api, home_id, node_id)


def _is_normal_light_device(device: dict[str, Any]) -> bool:
    """Detect non-ceiling-fan lights that should print check-light-state details."""
    if device.get("deviceType") == "ceiling_fans":
        return False

    if device.get("type") == "lights":
        return True

    capabilities = device.get("capabilities")
    return isinstance(capabilities, list) and (
        "check_light_state" in capabilities or "change_light_state" in capabilities
    )


def _is_inverter_device(device: dict[str, Any]) -> bool:
    """Detect inverter devices."""
    return device.get("type") == "inverters" or device.get("deviceType") == "inverters"


async def _print_inverter_endpoint_details(api: Any, home_id: str, node_id: str) -> None:
    """Print power production from BFF data for inverter devices."""
    print("\n   --- inverter production data (from BFF) ---")
    # Power is now extracted from the BFF dashboard description.value
    # It's already in the device dict from get_devices()
    print("   (power data is extracted from BFF dashboard, not a separate API)")


async def _print_normal_light_details(api: Any, home_id: str, node_id: str) -> None:
    """Print check-light-state for regular lights without endpoint semantics."""
    print("\n   --- check-light-state (normal light) ---")
    details = await api.get_light_details(home_id, node_id)
    if not details:
        print("   No light-state details returned")
        return

    print(json.dumps(details, indent=2, ensure_ascii=False, sort_keys=True))


async def _print_ceiling_fan_endpoint_details(api: Any, home_id: str, node_id: str, device_id: str) -> None:
    """Print all available endpoint info for a ceiling_fans device."""
    import aiohttp

    # Reuse the already-loaded const module to avoid homeassistant import
    const = sys.modules["_enki_tools_runtime.const"]
    enki_url = const.ENKI_URL
    enki_referentiel_api_key = const.ENKI_REFERENTIEL_API_KEY
    enki_bff_api_key = const.ENKI_BFF_API_KEY

    auth_headers = {
        "Authorization": f"{api._token_type} {api._access_token}",
    }

    async with aiohttp.ClientSession() as session:
        # 1. referentiel-agg: device model capabilities (no per-endpoint type labels)
        print("\n   --- referentiel-agg device (model capabilities) ---")
        async with session.get(
            f"{enki_url}/api-enki-referentiel-agg-prod/v1/devices/{device_id}",
            headers={**auth_headers, "X-Gateway-APIKey": enki_referentiel_api_key},
        ) as resp:
            if resp.status == 200:
                body = await resp.json()
                print(
                    f"   type={body.get('type')} "
                    f"| i18n={body.get('i18n')} "
                    f"| manufacturer={body.get('manufacturerId')}"
                )
                print(f"   protocols: {body.get('protocols')}")
                print(f"   capabilities: {body.get('capabilities')}")
                print(f"   possibleValues: {body.get('possibleValues')}")
            else:
                print(f"   HTTP {resp.status}: {await resp.text()}")

        # 2. BFF dashboard node: which endpoints are exposed via mainChangeCapability
        print("\n   --- BFF mainChangeCapability endpoints ---")
        async with session.get(
            f"{enki_url}/api-enki-mobile-bff-prod/v1/dashboard/homes/{home_id}?hasGroups=true",
            headers={**auth_headers, "X-Gateway-APIKey": enki_bff_api_key},
        ) as resp:
            if resp.status == 200:
                body = await resp.json()

                def find_node(data: Any, target: str) -> Any:
                    if isinstance(data, dict):
                        if data.get("nodeId") == target or data.get("id") == target:
                            return data
                        for value in data.values():
                            found = find_node(value, target)
                            if found:
                                return found
                    elif isinstance(data, list):
                        for item in data:
                            found = find_node(item, target)
                            if found:
                                return found
                    return None

                node = find_node(body, node_id)
                if node:
                    cap = node.get("mainChangeCapability") or {}
                    eps = cap.get("endpoints", [])
                    print(f"   mainChangeCapabilityId={node.get('mainChangeCapabilityId')}")
                    print(f"   endpoints exposed by BFF: {[ep['id'] for ep in eps]}")
                else:
                    print(f"   Node {node_id} not found in BFF dashboard")
            else:
                print(f"   HTTP {resp.status}: {await resp.text()}")


def _run_async(coro: Any) -> None:
    """Run async code with a Windows-compatible event loop policy."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
        # Let pending transport callbacks flush before closing the loop.
        loop.run_until_complete(asyncio.sleep(0))
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def main() -> int:
    """Entry point for standalone live diagnostics script."""
    parser = argparse.ArgumentParser(
        description="Run Enki live API diagnostics (equivalent to tests/test_api_live.py, without pytest)."
    )
    parser.add_argument("--user", default=os.getenv("ENKI_USER"), help="Enki username/email")
    parser.add_argument("--password", default=os.getenv("ENKI_PASSWORD"), help="Enki password")
    args = parser.parse_args()

    if not args.user or not args.password:
        print("Missing credentials. Set ENKI_USER and ENKI_PASSWORD or pass --user/--password.")
        return 2

    try:
        _run_async(_run_live_api_check(args.user, args.password))
    except Exception as exc:  # pragma: no cover - defensive path for runtime diagnostics script
        import traceback
        traceback.print_exc()
        print(f"Error running live diagnostics: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
