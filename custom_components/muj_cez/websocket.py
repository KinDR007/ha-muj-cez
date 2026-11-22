"""Websocket commands for the dashboard."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from . import invoice, invoice_gas, meter_reading, pricelist, pricelist_gas
from .const import DOMAIN, price_breakdown_enabled

# The dashboard section identifies the place by a sensor of it.
PLACE_SENSOR_KEY = "grid_data_date"


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_profile)
    websocket_api.async_register_command(hass, ws_prices)
    websocket_api.async_register_command(hass, ws_reading_form)
    websocket_api.async_register_command(hass, ws_reading_check)
    websocket_api.async_register_command(hass, ws_reading_submit)


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


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/prices", vol.Required("entity_id"): str}
)
@websocket_api.async_response
async def ws_prices(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Price breakdown per month of the supply point of a sensor (with its production point)."""
    entity = er.async_get(hass).async_get(msg["entity_id"])
    entry = (
        hass.config_entries.async_get_entry(entity.config_entry_id)
        if entity and entity.platform == DOMAIN and entity.config_entry_id
        else None
    )
    if entity is None or entry is None or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "Unknown sensor")
        return
    if not price_breakdown_enabled(entry.options):
        connection.send_error(msg["id"], "disabled", "Price breakdown is turned off")
        return
    coordinator = entry.runtime_data
    points = coordinator.data.supply_points if coordinator.data else {}
    spd = next((s for uid, s in points.items() if entity.unique_id.startswith(f"{uid}_")), None)
    if spd is None or spd.supply_point.production:
        connection.send_error(msg["id"], "not_found", "Unknown consumption supply point")
        return
    sp = spd.supply_point
    agreements = {sp.agreement_id} | {
        s.supply_point.agreement_id
        for s in points.values()
        if s.supply_point.production and s.supply_point.place_id == sp.place_id
    }
    invoices = await coordinator.invoices.async_invoices(agreements)
    contract = spd.contract
    # Gas: own price lists (band by the yearly consumption) and simulation components.
    yearly = spd.last_period.consumption_kwh if spd.last_period else None
    sources = (
        pricelist_gas.price_sources(
            await coordinator.invoices.async_gas_pricelists(sp.ean),
            yearly / 1000 if yearly else None,
        )
        if sp.gas
        else pricelist.price_sources(
            await coordinator.invoices.async_pricelists(sp.ean),
            contract.tariff_code if contract else None,
            contract.circuit_breaker if contract else None,
            contract.phase if contract else None,
        )
    )
    report = invoice.build_report(
        invoices,
        spd.sim_items,
        spd.simulation.measured_until if spd.simulation else None,
        invoice.weights_from_readings(spd.readings or []),
        sources,
        invoice_gas.SIM_PARTS if sp.gas else None,
        invoice_gas.SIM_NAMES if sp.gas else None,
    )
    connection.send_result(msg["id"], {"supply_point": sp.name, "ean": sp.ean, **report})


READING_FIELDS = {
    vol.Required("entry_id"): str,
    vol.Required("ean"): str,
    vol.Optional("reading_type"): vol.Any(str, None),
    vol.Optional("date"): vol.Any(str, None),
    vol.Optional("vt"): vol.Any(str, int, float, None),
    vol.Optional("nt"): vol.Any(str, int, float, None),
    vol.Optional("note"): vol.Any(str, None),
}


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/reading_form", vol.Optional("entry_id"): str}
)
@websocket_api.async_response
async def ws_reading_form(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Supply points with their previous readings for the meter reading card."""
    try:
        result = await meter_reading.async_form(hass, msg.get("entry_id"))
    except meter_reading.ReadingError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/reading_check", **READING_FIELDS}
)
@websocket_api.async_response
async def ws_reading_check(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Validate the entered reading (errors block sending, warnings do not)."""
    try:
        result, _state = await meter_reading.async_check(hass, msg)
    except meter_reading.ReadingError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"], result.as_dict())


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/reading_submit", **READING_FIELDS}
)
@websocket_api.async_response
async def ws_reading_submit(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send the reading to the portal."""
    try:
        result = await meter_reading.async_submit(hass, msg)
    except meter_reading.ReadingError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"], result)
