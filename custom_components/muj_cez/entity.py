"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN, MANUFACTURER, PORTAL_URL


def account_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Device representing the portal account (not a supply point)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Můj ČEZ",
        manufacturer=MANUFACTURER,
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=PORTAL_URL,
    )
