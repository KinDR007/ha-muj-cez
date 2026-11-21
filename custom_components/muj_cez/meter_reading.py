"""Meter reading form backend (card muj-cez-reading-card, action submit_meter_reading).

The form lists the electricity consumption points of the loaded accounts (each account
is a config entry with its own client). The previous readings come fresh from the
portal when the form is opened (cached briefly), so a reading entered on the web a
minute ago is taken into account.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import reading
from .api import CezError, SupplyPoint
from .const import DOMAIN, docs_url

_LOGGER = logging.getLogger(__name__)

CACHE_SECONDS = 300


class ReadingError(Exception):
    """Unknown point, invalid input or a portal error; `code` for the frontend."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class PointState:
    entry_id: str
    sp: SupplyPoint
    device: str | None
    registers: dict[str, list[tuple[date, float]]]
    fetched: float
    # From /meter-reading-consumption-vals and /self-meter-reading (optional).
    portal_usage: dict[str, float] = field(default_factory=dict)
    remaining: dict[str, int] = field(default_factory=dict)
    taken: set[date] = field(default_factory=set)
    types: list[str] | None = None  # offered reading types, None = unknown (all)
    date_ranges: dict[str, tuple[date, date] | None] = field(default_factory=dict)

    @property
    def dual_tariff(self) -> bool:
        return "nt" in self.registers

    @property
    def register_names(self) -> list[str]:
        return ["vt", "nt"] if self.dual_tariff else ["vt"]

    def previous(self) -> dict[str, reading.Previous]:
        return {
            reg: reading.Previous(points[-1][0], points[-1][1])
            for reg, points in self.registers.items()
            if points
        }

    def usage(self, today: date) -> dict[str, float | None]:
        """kWh per day: last billing period as the portal uses it, else from the readings."""
        return {
            reg: self.portal_usage.get(reg) or reading.daily_usage(points, today)
            for reg, points in self.registers.items()
        }


def _cache(hass: HomeAssistant) -> dict[str, PointState]:
    return hass.data.setdefault(DOMAIN, {}).setdefault("readings", {})


def _entries(hass: HomeAssistant, entry_id: str | None) -> list[Any]:
    entries = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.state is ConfigEntryState.LOADED and (entry_id is None or e.entry_id == entry_id)
    ]
    if entry_id is not None and not entries:
        raise ReadingError("not_found", "Unknown or not loaded account")
    return entries


def _points(entry: Any) -> list[SupplyPoint]:
    data = entry.runtime_data.data
    return [
        spd.supply_point
        for spd in (data.supply_points.values() if data else [])
        if not spd.supply_point.production and spd.supply_point.commodity.startswith("E")
    ]


async def _state(hass: HomeAssistant, entry: Any, sp: SupplyPoint, fresh: bool) -> PointState:
    key = f"{entry.entry_id}:{sp.uid}"
    cached = _cache(hass).get(key)
    if cached and not fresh and time.monotonic() - cached.fetched < CACHE_SECONDS:
        return cached
    today = dt_util.now().date()
    client = entry.runtime_data.client
    try:
        registers, device = await client.get_register_readings(sp, today)
    except CezError as err:
        raise ReadingError("portal", str(err)) from err
    state = PointState(entry.entry_id, sp, device, registers, time.monotonic())
    # Optional extras: the form works without them.
    try:
        state.portal_usage, state.remaining = reading.parse_consumption_vals(
            await client.get_reading_consumption(sp)
        )
    except CezError as err:
        _LOGGER.debug("Reading consumption %s: %s", sp.ean, err)
    try:
        state.taken = reading.taken_days(await client.get_self_readings(sp))
    except CezError as err:
        _LOGGER.debug("Self readings %s: %s", sp.ean, err)
    try:
        state.types = reading.parse_types(await client.get_reading_types(sp))
    except CezError as err:
        _LOGGER.debug("Reading types %s: %s", sp.ean, err)
    _cache(hass)[key] = state
    return state


def _find(hass: HomeAssistant, entry_id: str, ean: str) -> tuple[Any, SupplyPoint]:
    entry = _entries(hass, entry_id)[0]
    sp = next((p for p in _points(entry) if p.ean == ean), None)
    if sp is None:
        raise ReadingError("not_found", "Unknown supply point")
    return entry, sp


async def async_form(hass: HomeAssistant, entry_id: str | None = None) -> dict[str, Any]:
    """Data for the card: points with the previous readings, types, limits, mode."""
    points = []
    for entry in _entries(hass, entry_id):
        for sp in _points(entry):
            state = await _state(hass, entry, sp, fresh=True)
            prev = state.previous()
            last = max((p.day for p in prev.values()), default=None)
            points.append(
                {
                    "key": f"{entry.entry_id}:{sp.uid}",
                    "entry_id": entry.entry_id,
                    "ean": sp.ean,
                    "label": f"{sp.name} · {sp.ean[-7:]}" if sp.name else sp.ean,
                    "device": state.device,
                    "dual_tariff": state.dual_tariff,
                    "remaining_control": state.remaining.get(reading.REASONS["control"]),
                    "types": state.types or list(reading.TYPES),
                    "previous": {
                        "date": last.isoformat() if last else None,
                        **{reg: p.value for reg, p in prev.items()},
                    },
                }
            )
    return {
        "today": dt_util.now().date().isoformat(),
        "points": points,
        "types": list(reading.TYPES),
        "distributor_types": list(reading.DISTRIBUTOR_TYPES),
        "note_max": reading.NOTE_MAX,
        "docs_url": docs_url("odecet"),
    }


def _parse_day(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


async def _date_range(
    entry: Any, state: PointState, reading_type: str | None
) -> tuple[date, date] | None:
    """Allowed dates of the reading type, fetched once per type (cached with the state)."""
    reason = reading.REASONS.get(reading_type or "diary")
    if reason is None:
        return None
    if reason not in state.date_ranges:
        try:
            data = await entry.runtime_data.client.get_reading_form_config(state.sp, reason)
        except CezError as err:
            _LOGGER.debug("Reading form config %s: %s", state.sp.ean, err)
            data = None
        state.date_ranges[reason] = reading.parse_date_range(data)
    return state.date_ranges[reason]


async def async_check(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[reading.Check, PointState]:
    entry, sp = _find(hass, data["entry_id"], data["ean"])
    state = await _state(hass, entry, sp, fresh=False)
    today = dt_util.now().date()
    reading_type = data.get("reading_type")
    result = reading.check(
        {"vt": data.get("vt"), "nt": data.get("nt")},
        state.register_names,
        state.previous(),
        state.usage(today),
        _parse_day(data.get("date")),
        today,
        data.get("note") or "",
        reading_type,
        state.taken,
        state.remaining,
        await _date_range(entry, state, reading_type),
    )
    if state.types is not None and (reading_type or "diary") not in state.types:
        result.errors.append(reading.Issue("type_unavailable", "type"))
    return result, state


async def async_submit(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate again and send the reading to the portal."""
    entry, sp = _find(hass, data["entry_id"], data["ean"])
    await _state(hass, entry, sp, fresh=True)  # previous readings as of now
    result, state = await async_check(hass, data)
    if not result.ok:
        raise ReadingError("invalid", ", ".join(f"{i.field}: {i.code}" for i in result.errors))
    request = reading.build_request(
        sp.ean,
        state.device,
        data.get("reading_type") or "diary",
        _parse_day(data.get("date")) or dt_util.now().date(),
        reading.parse_value(data.get("vt")) or 0,
        reading.parse_value(data.get("nt")) if state.dual_tariff else None,
        data.get("note") or "",
    )
    _LOGGER.info("Sending meter reading of %s: %s", sp.ean, request)
    try:
        response = await entry.runtime_data.client.submit_meter_reading(request)
    except CezError as err:
        _LOGGER.error("Meter reading of %s rejected: %s", sp.ean, err)
        raise ReadingError("portal", str(err)) from err
    _LOGGER.info("Meter reading of %s sent, portal response: %s", sp.ean, response)
    _cache(hass).pop(f"{entry.entry_id}:{sp.uid}", None)
    response = response if isinstance(response, dict) else {}
    return {
        "sent": True,
        "request": request,
        "activity_id": response.get("activityId"),
        # Portal: values look unusual (e.g. meter replaced) / distributor rejected them,
        # resubmit with photos of the display (on the portal).
        "implausible": bool(response.get("meterReadingImplausible")),
        "attachment_needed": bool(response.get("isAttachmentNeeded")),
        "response": response,
    }
