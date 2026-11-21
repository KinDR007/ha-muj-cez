"""Serve the integration's own Lovelace card and load it on every page.

The module is added with frontend.add_extra_js_url, so it works on any dashboard
(storage or YAML) without a Lovelace resource or HACS.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = f"/{DOMAIN}_frontend"
CARD_FILE = "muj-cez-reading-card.js"
CARD_PATH = Path(__file__).parent / CARD_FILE
CARD_URL = f"{URL_BASE}/{CARD_FILE}"


async def async_register_frontend(hass: HomeAssistant, version: str) -> None:
    if "frontend" not in hass.config.components or getattr(hass, "http", None) is None:
        return  # no UI (tests, headless setups)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")
