# Enki API — REST Reference with JSON Schemas

> This API is not exhaustive. It includes the endpoints required to implement the Home Assistant integration features.

---

## Table of Contents

- [Common headers](#common-headers)
- [1. Authentication (Keycloak OIDC)](#1-authentication-keycloak-oidc)
  - [POST token — Login with username and password](#post-token--login-with-username-and-password)
  - [POST token — Refresh token](#post-token--refresh-token)
  - [POST token — OAuth2 code login](#post-token--oauth2-code-login)
  - [POST logout](#post-logout)
- [2. Home Management (Homes) — Queries](#2-home-management-homes--queries)
  - [GET homes — List user homes](#get-homes--list-user-homes)
  - [GET homes/{homeId} — Get a home](#get-homeshomeid--get-a-home)
  - [GET homes/oldest-home — Oldest home](#get-homesoldest-home--get-users-oldest-home)
- [3. Node / Device Management](#3-node--device-management)
  - [GET nodes — List home nodes](#get-nodes--list-home-nodes)
  - [GET nodes — List nodes by type](#get-nodes--list-nodes-by-type-variant)
  - [GET nodes/{nodeId} — Get a node](#get-nodesnodeid--get-a-node)
- [4. Lighting](#4-lighting)
  - [GET check-light-state](#get-lightingnodeidcheck-light-state--check-light-state)
  - [POST change-light-state](#post-lightingnodeidchange-light-state--change-light-state)
  - [GET check-dimming-mode](#get-lightingnodeidcheck-dimming-mode--check-dimming-mode)
  - [POST change-dimming-mode](#post-lightingnodeidchange-dimming-mode--change-dimming-mode)
  - [GET check-ballast-configuration](#get-lightingnodeidcheck-ballast-configuration--check-ballast-configuration)
  - [POST change-ballast-configuration](#post-lightingnodeidchange-ballast-configuration--change-ballast-configuration)
- [5. Fans / Airflow](#5-fans--airflow)
  - [GET check-fan-speed](#get-airflownodeidcheck-fan-speed--check-fan-speed)
  - [POST change-fan-speed](#post-airflownodeidchange-fan-speed--change-fan-speed)
  - [GET check-airflow-mode](#get-airflownodeidcheck-airflow-mode--check-airflow-mode)
  - [POST change-airflow-mode](#post-airflownodeidchange-airflow-mode--change-airflow-mode)
  - [GET check-fan-rotation-direction](#get-airflownodeidcheck-fan-rotation-direction--check-fan-rotation-direction)
  - [POST change-fan-rotation-direction](#post-airflownodeidchange-fan-rotation-direction--change-fan-rotation-direction)
- [6. Power Management / Power](#6-power-management--power)
  - [GET check-electrical-power](#get-powernodeidcheck-electrical-power--check-electrical-power)
  - [POST switch-electrical-power](#post-powernodeidswitch-electrical-power--switch-electrical-power)
  - [GET check-channel1-electrical-power](#get-powernodeidcheck-channel1-electrical-power--check-channel-1-power)
  - [POST switch-channel1-electrical-power](#post-powernodeidswitch-channel1-electrical-power--switch-channel-1-power)
  - [GET check-channel2-electrical-power](#get-powernodeidcheck-channel2-electrical-power--check-channel-2-power)
  - [POST switch-channel2-electrical-power](#post-powernodeidswitch-channel2-electrical-power--switch-channel-2-power)
  - [GET check-power-intensity](#get-powernodeidcheck-power-intensity--check-power-intensity)
  - [POST change-power-intensity](#post-powernodeidchange-power-intensity--change-power-intensity)
  - [GET check-dimmer-mode](#get-powernodeidcheck-dimmer-mode--check-power-dimmer-mode)
  - [POST switch-dimmer-mode](#post-powernodeidswitch-dimmer-mode--switch-power-dimmer-mode)
  - [GET check-electrical-power-restart-behaviour](#get-powernodeidcheck-electrical-power-restart-behaviour--check-restart-behavior)
  - [POST switch-electrical-power-restart-behaviour](#post-powernodeidswitch-electrical-power-restart-behaviour--change-restart-behavior)
  - [POST power-on-with-timer](#post-powernodeidpower-on-with-timer--power-on-with-timer)
- [General notes](#general-notes)

---

## Common headers

Unless otherwise stated, all main API endpoints require:

| Header | Description |
|--------|-------------|
| `Authorization` | `Bearer <access_token>` obtained from Keycloak |
| `X-Gateway-APIKey` | ADEO gateway API key |
| `homeId` | Active home ID (in header, not in path, except for specific cases) |

---

## 1. Authentication (Keycloak OIDC)

**Base URL:** `https://keycloak-prod.iot.leroymerlin.fr/realms/enki/protocol/openid-connect/`  
**Content-Type:** `application/x-www-form-urlencoded`

---

### POST `token` — Login with username and password

**Request (form fields):**
```
grant_type=password
username=<email>
password=<password>
client_id=<client_id>
```

**Response `200 OK`:**
```json
{
  "access_token": "eyJ...",
  "expires_in": 300,
  "refresh_token": "eyJ...",
  "refresh_expires_in": 1800
}
```

---

### POST `token` — Refresh token

**Request (form fields):**
```
grant_type=refresh_token
refresh_token=<refresh_token>
client_id=<client_id>
```

**Response `200 OK`:** same as login.

---

### POST `token` — OAuth2 code login

**Request (form fields):**
```
grant_type=authorization_code
code=<auth_code>
provider_type=<provider>
redirect_uri=<uri>
client_id=<client_id>
```

**Response `200 OK`:** same as login.

---

### POST `logout`

**Headers:** `Authorization: Bearer <access_token>`

**Request (form fields):**
```
client_id=<client_id>
refresh_token=<refresh_token>
```

**Response:** `204 No Content`

---

## 2. Home Management (Homes) — Queries

**Base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-home-prod/v1/`  
**Content-Type:** `application/json`

---

### GET `homes` — List user homes

**Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "abc123",
      "userId": "user-uuid",
      "creationDate": "2023-01-15T10:30:00Z",
      "updateDate": "2024-06-01T08:00:00Z",
      "countryId": "FR",
      "label": "My home",
      "timezone": "Europe/Paris",
      "address": {
        "staircaseAndFloorApartment": "3rd floor",
        "building": "Building A",
        "streetNumberAndStreet": "12 rue des Lilas",
        "locality": null,
        "zipCode": "75001",
        "city": "Paris",
        "inseeCode": "75056",
        "coordinates": { ... },
        "linky": null,
        "mdm": null,
        "linkyState": null
      }
    }
  ]
}
```

> `address` is optional (it can be `null`). Fields marked as optional by the API may return `null`.

---

### GET `homes/{homeId}` — Get a home

**Path params:** `homeId` — Home ID

**Response `200 OK`:**
```json
{
  "id": "abc123",
  "userId": "user-uuid",
  "creationDate": "2023-01-15T10:30:00Z",
  "updateDate": "2024-06-01T08:00:00Z",
  "countryId": "FR",
  "label": "My home",
  "timezone": "Europe/Paris",
  "address": { ... }
}
```

---

### GET `homes/oldest-home` — Get user's oldest home

**Response `200 OK`:** same schema as `GET homes/{homeId}`.

---

## 3. Node / Device Management

**Base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-node-agg-prod/v1/`  
**Content-Type:** `application/json`

---

### GET `nodes` — List home nodes

**Query params:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `homeId` | string | Home ID (required) |
| `nodeIds` | string[] | Node IDs to filter (optional) |
| `pairing_state` | string | Pairing state, e.g. `"PAIRED"` (optional) |

**Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "node-uuid",
      "type": "LIGHT",
      "pairingState": "PAIRED",
      "icon": "ceiling_light",
      "eui64": "0x00158D0001234567",
      "deviceId": "device-uuid",
      "homeId": "home-uuid",
      "parentId": "gateway-uuid",
      "creationDate": "2023-03-10T09:00:00Z",
      "updateDate": "2024-05-20T15:00:00Z",
      "label": "Living room light",
      "factoryId": "FACTORY_001",
      "modelNumber": "LX100",
      "externalId": null,
      "netatmoHomeId": null,
      "bridge": null,
      "nodeSecret": null,
      "p2pId": null,
      "p2pAuthKey": null,
      "p2pPassword": null,
      "macAddress": null
    }
  ]
}
```

> Optional fields may be `null`. `type` determines which additional services are available for the node.

---

### GET `nodes` — List nodes by type (variant)

**Query params:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `homeId` | string | Home ID |
| `parentId` | string | Parent node ID (gateway) |
| `types` | string[] | List of node types to filter (see valid values below) |
| `pairing_state` | string | Pairing state |

**Valid values for `types` (22 supported node types):**

| Type | Description |
|------|-------------|
| `LIGHTING` | Lighting lights/switches |
| `DIMMER` | Dimming controls |
| `FAN` | Fan controls |
| `ROLLER` | Motorized blinds/curtains |
| `THERMOSTAT` | Thermostats/HVAC |
| `CONTACT` | Contact/door sensors |
| `MOTION` | Motion sensors |
| `PRESENCE` | Presence detectors |
| `SMOKEALARM` | Smoke detectors |
| `WATER` | Water/leak detectors |
| `TEMPERATURE` | Temperature sensors |
| `HUMIDITY` | Humidity sensors |
| `ILLUMINANCE` | Illuminance/light sensors |
| `BRIGHTNESS` | Brightness sensors |
| `VIBRATION` | Vibration sensors |
| `BATTERYHEALTH` | Battery health monitors |
| `CONSUMPTION` | Energy consumption sensors |
| `PRODUCTION` | Energy production sensors (solar) |
| `ELECTRICALPOWER` | Electrical power sensors |
| `ELECTRICALINTENSITY` | Electrical current sensors |
| `NODE` | Generic nodes |
| `PAIRING` | Pairing nodes |

**Response `200 OK`:** same schema as the previous variant.

---

### GET `nodes/{nodeId}` — Get a node

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:** a `NodeDTO` object without the `items` wrapper:
```json
{
  "id": "node-uuid",
  "type": "LIGHT",
  "pairingState": "PAIRED",
  "icon": "ceiling_light",
  "eui64": "0x00158D0001234567",
  "deviceId": "device-uuid",
  "homeId": "home-uuid",
  "parentId": "gateway-uuid",
  "creationDate": "2023-03-10T09:00:00Z",
  "updateDate": "2024-05-20T15:00:00Z",
  "label": "Living room light",
  "factoryId": null,
  "modelNumber": "LX100",
  "externalId": null,
  "netatmoHomeId": null,
  "bridge": null,
  "nodeSecret": null,
  "p2pId": null,
  "p2pAuthKey": null,
  "p2pPassword": null,
  "macAddress": null
}
```

---

## 4. Lighting

**Base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-lighting-prod/v1/`  
**Content-Type:** `application/json`

---

### GET `lighting/{nodeId}/check-light-state` — Check light state

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T11:45:00Z",
  "lastReportedValue": {
    "colorMode": "COLOR_TEMPERATURE",
    "hue": 0.0,
    "saturation": 0.0,
    "brightness": 80.0,
    "colorTemperature": 4000.0,
    "power": "ON"
  }
}
```

> **`colorMode` values:** `COLOR_TEMPERATURE`, `HUE_SATURATION`, `WHITE`  
> **`power` values:** `ON`, `OFF`  
> `hue` and `saturation` are relevant only when `colorMode = HUE_SATURATION` (0–360 and 0–100 respectively).  
> `colorTemperature` is in Kelvin, relevant when `colorMode = COLOR_TEMPERATURE`.  
> `brightness` is a percentage (0–100).

---

### POST `lighting/{nodeId}/change-light-state` — Change light state

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "brightness": 75.0,
  "colorMode": "COLOR_TEMPERATURE",
  "hue": null,
  "saturation": null,
  "colorTemperature": 3500.0,
  "power": "ON"
}
```

> All fields are optional in the request; send only those you want to modify.  
> To turn off: `{"power": "OFF"}`.  
> To change brightness: `{"brightness": 50.0}`.

**Response:** `204 No Content`

---

### GET `lighting/{nodeId}/check-dimming-mode` — Check dimming mode

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T10:00:00Z",
  "lastReportedValue": "LEADING_EDGE"
}
```

> **`lastReportedValue` values:** `LEADING_EDGE`, `TRAILING_EDGE` (dimmer modes for dimmable bulbs).

---

### POST `lighting/{nodeId}/change-dimming-mode` — Change dimming mode

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "TRAILING_EDGE"
}
```

**Response:** `204 No Content`

---

### GET `lighting/{nodeId}/check-ballast-configuration` — Check ballast configuration

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "minLevel": 10,
  "maxLevel": 100
}
```

---

### POST `lighting/{nodeId}/change-ballast-configuration` — Change ballast configuration

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "minLevel": 10,
  "maxLevel": 100
}
```

**Response:** `204 No Content`

---

## 5. Fans / Airflow

**Base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-airflow-prod/v1/`  
**Content-Type:** `application/json`

---

### GET `airflow/{nodeId}/check-fan-speed` — Check fan speed

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T12:00:00Z",
  "lastReportedValue": 3
}
```

> `lastReportedValue`: integer representing speed (e.g. 1–5 depending on the device).

---

### POST `airflow/{nodeId}/change-fan-speed` — Change fan speed

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": 3
}
```

**Response:** `204 No Content`

---

### GET `airflow/{nodeId}/check-airflow-mode` — Check airflow mode

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T12:00:00Z",
  "lastReportedValue": "VENTILATION"
}
```

> **`lastReportedValue` values:** `VENTILATION`, `BOOST`, `AUTO`, `SLEEP`.

---

### POST `airflow/{nodeId}/change-airflow-mode` — Change airflow mode

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "VENTILATION"
}
```

**Response:** `204 No Content`

---

### GET `airflow/{nodeId}/check-fan-rotation-direction` — Check fan rotation direction

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T12:00:00Z",
  "lastReportedValue": "FORWARD"
}
```

> **`lastReportedValue` values:** `FORWARD`, `REVERSE`.

---

### POST `airflow/{nodeId}/change-fan-rotation-direction` — Change fan rotation direction

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "REVERSE"
}
```

**Response:** `204 No Content`

---

## 6. Power Management / Power

**Base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-power-prod/v1/`  
**Content-Type:** `application/json`

---

### GET `power/{nodeId}/check-electrical-power` — Check electrical power

**Path params:** `nodeId`  

**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T14:30:00Z",
  "lastReportedValue": "ON",
  "endpoints": [
    {
      "id": 1,
      "lastReportedValue": "ON",
      "lastReportedDate": "2024-06-03T14:30:00Z"
    }
  ]
}
```

> The `endpoints` field is optional. `lastReportedValue` can be `"ON"` or `"OFF"`.

---

### POST `power/{nodeId}/switch-electrical-power` — Switch electrical power

**Path params:** `nodeId`  

**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "ON"
}
```

> `value` can be `"ON"` or `"OFF"`.

**Response:** `204 No Content`

---

### GET `power/{nodeId}/check-channel1-electrical-power` — Check channel 1 power

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T14:30:00Z",
  "lastReportedValue": "ON"
}
```

---

### POST `power/{nodeId}/switch-channel1-electrical-power` — Switch channel 1 power

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "ON"
}
```

**Response:** `204 No Content`

---

### GET `power/{nodeId}/check-channel2-electrical-power` — Check channel 2 power

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T14:30:00Z",
  "lastReportedValue": "ON"
}
```

---

### POST `power/{nodeId}/switch-channel2-electrical-power` — Switch channel 2 power

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "ON"
}
```

**Response:** `204 No Content`

---

### GET `power/{nodeId}/check-power-intensity` — Check power intensity

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T14:30:00Z",
  "lastReportedValue": 2.5
}
```

> `lastReportedValue` is a floating-point number (current in amperes or another unit depending on the device).

---

### POST `power/{nodeId}/change-power-intensity` — Change power intensity

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": 2.5
}
```

**Response:** `204 No Content`

---

### GET `power/{nodeId}/check-dimmer-mode` — Check power dimmer mode

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T14:30:00Z",
  "lastReportedValue": "LEADING_EDGE"
}
```

> **`lastReportedValue` values:** `LEADING_EDGE`, `TRAILING_EDGE`.

---

### POST `power/{nodeId}/switch-dimmer-mode` — Switch power dimmer mode

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "TRAILING_EDGE"
}
```

**Response:** `204 No Content`

---

### GET `power/{nodeId}/check-electrical-power-restart-behaviour` — Check restart behavior

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Response `200 OK`:**
```json
{
  "nodeId": "node-uuid",
  "homeId": "home-uuid",
  "lastReportedDate": "2024-06-03T14:30:00Z",
  "lastReportedValue": "TURN_OFF"
}
```

> **`lastReportedValue` values:** `TURN_OFF`, `TURN_ON`, `RESTORE_PREVIOUS_STATE` (behavior after a power outage).

---

### POST `power/{nodeId}/switch-electrical-power-restart-behaviour` — Change restart behavior

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:**
```json
{
  "value": "RESTORE_PREVIOUS_STATE"
}
```

**Response:** `204 No Content`

---

### POST `power/{nodeId}/power-on-with-timer` — Power on with timer

**Path params:** `nodeId`  
**Additional headers:** `homeId`

**Request body:** (empty, no additional parameters)

**Response:** `204 No Content`

> Turns on the device with an automatic timer.

---

## General notes

- Dates follow ISO 8601 format: `"2024-06-03T12:00:00Z"`.
- Endpoints that return `204 No Content` do not include a response body.
- The `id` field in objects is a UUID string.
- Fields marked as optional by the API may appear as `null` in responses.
- State-read operations (`check-*`) return the last value reported by the device and the timestamp when it was reported; they do not necessarily represent real-time state.
