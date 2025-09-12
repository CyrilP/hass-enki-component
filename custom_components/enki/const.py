"""Constants for Enki integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# This is the internal name of the integration, it should also match the directory
# name for the integration.
DOMAIN = "enki"
NAME = "Enki"

DEFAULT_SCAN_INTERVAL = 5

ENKI_OIDC_URL = "https://keycloak-prod.iot.leroymerlin.fr/realms/enki/protocol/openid-connect/token"
ENKI_URL = "https://enki.api.devportal.adeo.cloud"
ENKI_HOME_API_KEY = "FULsxyI3x1f7MtLVOsP6V1DeAPmBQJCB"
ENKI_BFF_API_KEY = "Bco7qBHRHOQiSVcEHdgS0rijpebMBwkB"
ENKI_NODE_API_KEY = "UBb0Kv6xXpG6bOvD8VZ9A63uxqQ4G1A3"
ENKI_REFERENTIEL_API_KEY = "3uk9rlaIUgBsz1tEPV7GQMhhGfRwPFJY"
ENKI_USER_API_KEY = "Px5B6M16shAhnSU7uSMTE3x3AgWmky4R"
