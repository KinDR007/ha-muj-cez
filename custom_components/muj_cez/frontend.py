"""Serve the integration's own Lovelace cards and load them on every page.

The module is added with frontend.add_extra_js_url, so it works on any dashboard
(storage or YAML) without a Lovelace resource or HACS.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = f"/{DOMAIN}_frontend"
# Meter reading card, tabs of a supply point view.
CARD_FILES = ("muj-cez-reading-card.js", "muj-cez-tabs.js")


def _fingerprints(here: Path) -> dict[str, str]:
    """Short content hash per card: a changed card gets a new URL even within one
    integration version (dev builds), so browsers do not keep the old one."""
    return {name: hashlib.sha1((here / name).read_bytes()).hexdigest()[:8] for name in CARD_FILES}


async def async_register_frontend(hass: HomeAssistant, version: str) -> None:
    if "frontend" not in hass.config.components or getattr(hass, "http", None) is None:
        return  # no UI (tests, headless setups)
    here = Path(__file__).parent
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(f"{URL_BASE}/{name}", str(here / name), cache_headers=False)
            for name in CARD_FILES
        ]
    )
    hashes = await hass.async_add_executor_job(_fingerprints, here)
    for name in CARD_FILES:
        add_extra_js_url(hass, f"{URL_BASE}/{name}?v={version}-{hashes[name]}")
