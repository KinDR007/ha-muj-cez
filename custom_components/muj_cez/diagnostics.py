"""Diagnostics for the Muj CEZ integration.

Besides the redacted parsed data, `portal` holds pseudonymized raw responses of the
portal for every customer account of the login (anonymize.py): account list, supply
points per account and the latest real meter readings of the entry's supply points.
They show the structure of accounts this integration was not developed with (issue
reports) without personal data.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .anonymize import Anonymizer
from .api import SIMULATED_READING_TYPE, CezError, _val
from .const import CONF_PARTNER
from .coordinator import MujCezConfigEntry

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PARTNER,
    "title",
    "unique_id",
    "uid",
    "code",
    "place_id",
    "ean",
    "name",
    "address",
    "device",
    "agreement_id",
    "contract_name",
    "customer_number",
    "variable_symbol",
    "bank_account",
    "number",
}
READINGS = 40


async def _portal(entry: MujCezConfigEntry) -> dict[str, Any]:
    client = entry.runtime_data.client
    anon = Anonymizer()
    out: dict[str, Any] = {}

    async def raw(c: Any, path: str) -> Any:
        try:
            return anon(await c.get_raw(path))
        except CezError as err:
            return {"error": anon(str(err))}

    token = await raw(client, "/user/token-data")
    out["token_data"] = token
    try:
        partners, default = await client.get_accounts()
    except CezError:
        partners, default = [], None
    out["selected_account"] = anon(client.partner, "partner") if client.partner else None
    out["accounts"] = []
    for partner in partners:
        other = client.with_partner(partner)
        out["accounts"].append(
            {
                "partner": anon(partner, "partner"),
                "default": partner == default,
                "supply_points": await raw(other, "/supply-points/RetrieveSupplyPoints"),
            }
        )
    readings = {}
    data = entry.runtime_data.data
    for spd in data.supply_points.values() if data else []:
        sp = spd.supply_point
        try:
            rows = await client.get_raw(f"/supply-points/{sp.uid}/ReadMeterReading")
        except CezError as err:
            readings[anon(sp.uid, "uid")] = {"error": anon(str(err))}
            continue
        real = [
            r
            for r in rows or []
            if isinstance(r, dict) and _val(r.get("meterReadingType")) != SIMULATED_READING_TYPE
        ]
        real.sort(key=lambda r: str(r.get("meterReadingRegisterDate")))
        readings[anon(sp.uid, "uid")] = anon(real[-READINGS:])
    out["meter_readings"] = readings
    return out


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
        "portal": await _portal(entry),
    }
