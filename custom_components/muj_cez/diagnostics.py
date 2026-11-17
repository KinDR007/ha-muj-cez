"""Diagnostics for the Muj CEZ integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import MujCezConfigEntry

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    "uid",
    "ean",
    "name",
    "address",
    "device",
    "agreement_id",
    "customer_number",
    "variable_symbol",
    "bank_account",
    "number",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MujCezConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "last_success_time": coordinator.last_success_time,
        "unread_messages": data.unread_messages if data else None,
        "supply_points": [
            async_redact_data(asdict(spd), TO_REDACT)
            for spd in (data.supply_points.values() if data else [])
        ],
    }
