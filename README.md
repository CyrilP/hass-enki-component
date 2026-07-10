# hass-enki-component

This repository is now archived.

I started this project just to manage my eglo lamp, I don't have anything more from the enki ecosystem and it's not easy to maintain because of my limited device range and lack of time.

I agreed with [@cyrilcolinet](https://github.com/cyrilcolinet) to move the now "official" integration to his repository https://github.com/cyrilcolinet/enki-integration-hass

So Long, and Thanks for All the Fish

---

Enki custom component for Home Assistant

Tested devices:
- Eglo V-link tunable white
- Inspire Radix ceiling fan with light
- NEW! Solar Panels by Envertech-Lexman
- Inspire Cadix ceiling fan with light

Howto :

- install HACS
- add this repo
- add Enki integration

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
