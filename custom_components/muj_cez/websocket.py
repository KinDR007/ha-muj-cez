"""Websocket commands for the dashboard."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

# The dashboard section identifies the place by a sensor of it.
PLACE_SENSOR_KEY = "grid_data_date"


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_profile)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/profile",
        vol.Required("entity_id"): str,
        vol.Optional("month"): vol.Match(r"^\d{4}-(0[1-9]|1[0-2])$"),
    }
)
@websocket_api.async_response
async def ws_profile(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """15 min import/export of the place of a smart meter sensor for one month."""
    entity = er.async_get(hass).async_get(msg["entity_id"])
    entry = (
        hass.config_entries.async_get_entry(entity.config_entry_id)
        if entity and entity.platform == DOMAIN and entity.config_entry_id
        else None
    )
    suffix = f"_{PLACE_SENSOR_KEY}"
    if (
        entity is None
        or entry is None
        or entry.state is not ConfigEntryState.LOADED
        or not entity.unique_id.endswith(suffix)
    ):
        connection.send_error(msg["id"], "not_found", "Unknown smart meter sensor")
        return
    coordinator = entry.runtime_data
    uid = entity.unique_id.removesuffix(suffix)
    spd = (coordinator.data.supply_points if coordinator.data else {}).get(uid)
    if spd is None:
        connection.send_error(msg["id"], "not_found", "Unknown supply point")
        return
    result = await coordinator.profiles.async_month(spd.supply_point.place_id, msg.get("month"))
    connection.send_result(msg["id"], result)
