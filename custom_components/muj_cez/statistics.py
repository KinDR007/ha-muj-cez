"""Import smart meter data and spot prices as long-term statistics.

External statistics (selectable in the Energy dashboard):
- muj_cez:grid_import_<place>  hourly kWh imported from the grid (sum)
- muj_cez:grid_export_<place>  hourly kWh exported to the grid (sum)
- muj_cez:spot_price           hourly spot price in CZK/kWh (mean), portal history

Data are available with a delay of about one day; only complete local days are
imported so a later run never leaves holes. Each run continues after the last
imported hour. While exporting hours are imported, their value at the spot price is
accumulated per month in the grid cache (used for payout comparison).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import grid as gridlib
from .api import CezClient, CezError, SupplyPoint
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SPOT_STATISTIC_ID = f"{DOMAIN}:spot_price"
SPOT_UNIT = "CZK/kWh"
# Pause between portal requests during a backfill.
REQUEST_PAUSE = 0.5
# Incomplete days younger than this are retried on the next run.
RECENT_DAYS = 3


def statistic_id(kind: str, place_id: str) -> str:
    return f"{DOMAIN}:grid_{kind}_{place_id}".lower()


def complete_days(hourly: dict[datetime, float], before: date) -> dict[datetime, float]:
    """Hours of local days before `before`, stopping at a recent incomplete day.

    A day of the last RECENT_DAYS days with missing hours is probably not processed
    by the portal yet: it and later days are left for the next run. Older incomplete
    days (meter outage) are imported as they are so the import never gets stuck.
    """
    by_day: dict[date, dict[datetime, float]] = defaultdict(dict)
    for hour, value in hourly.items():
        day = hour.astimezone(gridlib.TZ).date()
        if day < before:
            by_day[day][hour] = value
    result: dict[datetime, float] = {}
    for day in sorted(by_day):
        start = gridlib.local_midnight(day)
        end = gridlib.local_midnight(day + timedelta(days=1))
        expected = round((end - start).total_seconds() / 3600)
        if len(by_day[day]) < expected and day >= before - timedelta(days=RECENT_DAYS):
            break
        result.update(by_day[day])
    return result


async def _last(hass: HomeAssistant, stat_id: str, types: set[str]) -> dict[str, Any] | None:
    rows = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, stat_id, True, types
    )
    found = rows.get(stat_id)
    return found[0] if found else None


def _start_of(row: dict[str, Any]) -> datetime:
    start = row["start"]
    return dt_util.utc_from_timestamp(start) if isinstance(start, int | float) else start


async def async_import_spot_prices(
    hass: HomeAssistant, client: CezClient, first_day: date, today: date
) -> dict[datetime, float]:
    """Import spot prices from the last imported hour (or first_day) up to yesterday."""
    last = await _last(hass, SPOT_STATISTIC_ID, {"mean"})
    start_day = first_day
    if last:
        start_day = max(
            first_day, _start_of(last).astimezone(gridlib.TZ).date() + timedelta(days=1)
        )
    if start_day >= today:
        return {}
    prices: dict[datetime, float] = {}
    for a, b in gridlib.windows(start_day, today, gridlib.SPOT_WINDOW_DAYS):
        prices.update(await client.get_spot_prices(a, b))
        await asyncio.sleep(REQUEST_PAUSE)
    if prices:
        metadata = StatisticMetaData(
            source=DOMAIN,
            statistic_id=SPOT_STATISTIC_ID,
            name="ČEZ spotová cena",
            unit_of_measurement=SPOT_UNIT,
            unit_class=None,
            has_sum=False,
            mean_type=StatisticMeanType.ARITHMETIC,
        )
        async_add_external_statistics(
            hass,
            metadata,
            [StatisticData(start=h, mean=p, min=p, max=p) for h, p in sorted(prices.items())],
        )
    return prices


async def _spot_for(hass: HomeAssistant, start: datetime, end: datetime) -> dict[datetime, float]:
    """Spot prices already in the recorder for [start, end)."""
    from homeassistant.components.recorder.statistics import statistics_during_period

    rows = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, start, end, {SPOT_STATISTIC_ID}, "hour", None, {"mean"}
    )
    return {
        _start_of(r): r["mean"]
        for r in rows.get(SPOT_STATISTIC_ID, [])
        if r.get("mean") is not None
    }


async def async_import_grid(
    hass: HomeAssistant,
    client: CezClient,
    sp: SupplyPoint,
    cache: dict[str, Any],
    today: date,
    spot: dict[datetime, float],
) -> int:
    """Import hourly import/export of one consumption place; returns imported hours."""
    imported = 0
    for kind, role in (("import", gridlib.PROFILE_IMPORT), ("export", gridlib.PROFILE_EXPORT)):
        first = cache.get(f"{kind}_from")
        if not first:
            continue
        stat_id = statistic_id(kind, sp.place_id)
        last = await _last(hass, stat_id, {"sum"})
        base = 0.0
        after: datetime | None = None
        start_day = date.fromisoformat(first)
        if last:
            after = _start_of(last)
            base = last.get("sum") or 0.0
            start_day = (after + timedelta(hours=1)).astimezone(gridlib.TZ).date()
        elif kind == "export":
            cache["valuation"] = {}
        if start_day >= today:
            continue
        hourly: dict[datetime, float] = {}
        for a, b in gridlib.windows(start_day, today, gridlib.PROFILE_WINDOW_DAYS):
            hourly.update(await client.get_profile(sp, role, a, b))
            await asyncio.sleep(REQUEST_PAUSE)
        hours = complete_days(hourly, today)
        if after is not None:
            hours = {h: v for h, v in hours.items() if h > after}
        if not hours:
            continue
        total = base
        rows = []
        for hour, value in sorted(hours.items()):
            total += value
            rows.append(StatisticData(start=hour, state=value, sum=round(total, 4)))
        label = "odběr ze sítě" if kind == "import" else "přetoky do sítě"
        async_add_external_statistics(
            hass,
            StatisticMetaData(
                source=DOMAIN,
                statistic_id=stat_id,
                name=f"ČEZ {label} ({sp.address or sp.ean})",
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                unit_class="energy",
                has_sum=True,
                mean_type=StatisticMeanType.NONE,
            ),
            rows,
        )
        imported += len(rows)
        if kind == "export":
            prices = dict(spot)
            missing = [h for h in hours if h not in prices]
            if missing:
                prices.update(
                    await _spot_for(hass, min(missing), max(missing) + timedelta(hours=1))
                )
            valuation = cache.setdefault("valuation", {})
            for hour, kwh in hours.items():
                price = prices.get(hour)
                if price is None or not kwh:
                    continue
                month = valuation.setdefault(
                    hour.astimezone(gridlib.TZ).strftime("%Y-%m"), {"value": 0.0, "kwh": 0.0}
                )
                month["value"] = round(month["value"] + kwh * price, 4)
                month["kwh"] = round(month["kwh"] + kwh, 4)
    return imported


def spot_day_summary(prices: dict[datetime, float], day: date) -> dict[str, Any] | None:
    values = [p for h, p in prices.items() if h.astimezone(gridlib.TZ).date() == day]
    if not values:
        return None
    return {
        "date": day.isoformat(),
        "average": round(sum(values) / len(values), 4),
        "min": min(values),
        "max": max(values),
        "hours": len(values),
    }


async def async_update_statistics(
    hass: HomeAssistant,
    client: CezClient,
    supply_points: list[SupplyPoint],
    grid_cache: dict[str, dict[str, Any]],
) -> bool:
    """Import statistics for all places with smart meter data. Returns True on change."""
    today = dt_util.now().date()
    places = [
        (sp, grid_cache[sp.place_id])
        for sp in supply_points
        if sp.place_id in grid_cache
        and grid_cache[sp.place_id].get("uid") == sp.uid
        and (
            grid_cache[sp.place_id].get("import_from") or grid_cache[sp.place_id].get("export_from")
        )
    ]
    if not places:
        return False
    changed = False
    try:
        firsts = [
            date.fromisoformat(min(cache[k]))
            for _sp, cache in places
            for k in ("import", "export")
            if cache.get(k)
        ]
        spot: dict[datetime, float] = {}
        if firsts:
            spot = await async_import_spot_prices(hass, client, min(firsts), today)
            summary = spot_day_summary(spot, today - timedelta(days=1))
            if summary is None and not spot:
                yesterday = today - timedelta(days=1)
                start = gridlib.local_midnight(yesterday).astimezone(UTC)
                existing = await _spot_for(hass, start, start + timedelta(days=1))
                summary = spot_day_summary(existing, yesterday)
            for _sp, cache in places:
                if summary:
                    cache["spot_yesterday"] = summary
            changed = bool(spot)
        for sp, cache in places:
            changed |= await async_import_grid(hass, client, sp, cache, today, spot) > 0
    except CezError as err:
        _LOGGER.warning("Importing statistics failed: %s", err)
    return changed
