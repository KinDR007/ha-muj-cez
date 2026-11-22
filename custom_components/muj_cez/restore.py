"""Contract details from the recorder history of the integration's own sensors.

Used when the portal does not answer the contract request (product calculator HTTP 500)
and no earlier download is at hand (e.g. the outage started before the data were kept
between refreshes): the last valid states of the contract sensors give the same values.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .api import ContractInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

HISTORY_DAYS = 30
CONTRACT_SENSORS = (
    "distribution_rate",
    "circuit_breaker",
    "contract_end",
    "price_change_date",
    "product",
)
_INVALID = (None, "", "unknown", "unavailable")


def _last_valid(states: list[State]) -> State | None:
    return next((s for s in reversed(states) if s.state not in _INVALID), None)


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def contract_from_states(states: dict[str, State | None]) -> ContractInfo | None:
    """ContractInfo from the last valid state per contract sensor key."""
    rate, breaker = states.get("distribution_rate"), states.get("circuit_breaker")
    end, change, product = (
        states.get("contract_end"),
        states.get("price_change_date"),
        states.get("product"),
    )
    if not any((rate, breaker, end, change, product)):
        return None
    attrs = dict(rate.attributes) if rate else {}
    tariff = attrs.get("tariff_code")
    phase = breaker.attributes.get("phase") if breaker else None
    # The sensor shows the rate name, or the tariff code when the name is not known.
    name = rate.state if rate and rate.state != tariff else None
    return ContractInfo(
        tariff_code=tariff,
        circuit_breaker=_float(breaker.state) if breaker else None,
        phase=int(phase) if isinstance(phase, int | float) else None,
        product=product.state if product else None,
        contract_end=_day(end.state) if end else None,
        price_change_date=_day(change.state) if change else None,
        double_tariff=attrs.get("double_tariff"),
        distribution_rate=name,
        recommended_distribution_rate=attrs.get("recommended"),
    )


async def async_contract_from_history(hass: HomeAssistant, uid: str) -> ContractInfo | None:
    """Last valid contract details of a supply point recorded by its sensors."""
    if "recorder" not in hass.config.components:
        return None
    from homeassistant.components.recorder import get_instance, history

    registry = er.async_get(hass)
    ids = {
        key: entity_id
        for key in CONTRACT_SENSORS
        if (entity_id := registry.async_get_entity_id("sensor", DOMAIN, f"{uid}_{key}"))
    }
    if not ids:
        return None
    start = dt_util.utcnow() - timedelta(days=HISTORY_DAYS)

    def query() -> dict[str, list[State]]:
        return history.get_significant_states(
            hass,
            start,
            None,
            list(ids.values()),
            significant_changes_only=False,
        )

    try:
        found = await get_instance(hass).async_add_executor_job(query)
    except Exception:  # recorder unavailable: the sensors stay unknown
        _LOGGER.exception("Reading the contract history of %s failed", uid)
        return None
    return contract_from_states(
        {key: _last_valid(list(found.get(entity_id, []))) for key, entity_id in ids.items()}
    )
