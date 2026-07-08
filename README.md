# hass-enki-component

> **Development has moved.** Active maintenance continues at **[cyrilcolinet/enki-integration-hass](https://github.com/cyrilcolinet/enki-integration-hass)**.
>
> This repository is the original Enki integration for Home Assistant. If you still use it, switch to the canonical repo — same domain (`enki`), same folder (`custom_components/enki`). Update via HACS or copy files from a [release](https://github.com/cyrilcolinet/enki-integration-hass/releases), then restart Home Assistant. Do not uninstall the integration.
>
> Migration guide: [docs/MIGRATION.md](https://github.com/cyrilcolinet/enki-integration-hass/blob/main/docs/MIGRATION.md) (available after [PR #62](https://github.com/cyrilcolinet/enki-integration-hass/pull/62) is released).
>
> Discussion: [issue #78](https://github.com/CyrilP/hass-enki-component/issues/78)

---

## History

First Enki custom component for Home Assistant — started by [@CyrilP](https://github.com/CyrilP) for an Eglo V-link lamp, then extended by contributors (Radix fan, Envertech solar, Cadix fan, …).

**Originally tested devices:**
- Eglo V-link tunable white
- Inspire Radix ceiling fan with light
- Solar Panels by Envertech-Lexman
- Inspire Cadix ceiling fan with light

## Live API test

This repository includes a standalone live diagnostics script that can authenticate against Enki
and print available devices/actions from your account. This can help to develop and debug the
component against the real API.

Before running it locally, install runtime dependencies:

```bash
python -m pip install aiohttp
```

Run the script with credentials as parameters:

```bash
python tools/enki_api_live.py --user "your-email@example.com" --password "your-password"
```

You can also use environment variables:

```bash
export ENKI_USER="your-email@example.com"
export ENKI_PASSWORD="your-password"
python tools/enki_api_live.py
```

The maintained fork keeps an equivalent tool under `tools/enki_api_live.py`.
