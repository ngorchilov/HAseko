from __future__ import annotations
from datetime import timedelta

DOMAIN = "haseko"

CONF_API_KEY = "api_key"
CONF_SELECTED_SERIALS = "selected_serials"

DEFAULT_CLIENT_NAME = "HAseko"
DEFAULT_CLIENT_VERSION = "0.1"

UPDATE_INTERVAL = timedelta(seconds=60)

PLATFORMS = ["sensor", "binary_sensor"]
