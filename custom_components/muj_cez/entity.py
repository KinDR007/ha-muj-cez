"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .api import SupplyPoint
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


def supply_point_device_info(sp: SupplyPoint) -> DeviceInfo:
    """Device of a supply point (its sensors, button)."""
    return DeviceInfo(
        identifiers={(DOMAIN, sp.uid)},
        name=f"ČEZ {sp.name}",
        manufacturer=MANUFACTURER,
        model=sp.product or None,
        serial_number=sp.ean,
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=PORTAL_URL,
    )
