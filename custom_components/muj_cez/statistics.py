"""Import smart meter data and spot prices as long-term statistics.

External statistics (selectable in the Energy dashboard):
- muj_cez:grid_import_<place>  hourly kWh imported from the grid (sum)
- muj_cez:grid_export_<place>  hourly kWh exported to the grid (sum)
- muj_cez:spot_price           hourly spot price in CZK/kWh (mean): OTE day-ahead
                               (ČNB rate), ČEZ portal as fallback

Data are available with a delay of about one day; only complete local days are
imported so a later run never leaves holes. Each run continues after the last
imported hour. The exported energy is valued at spot prices per month (portal prices,
gaps filled from an optional HA spot price sensor) for the payout comparison.
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
from . import ote
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


def expected_hours(day: date) -> int:
    start = gridlib.local_midnight(day)
    return round((gridlib.local_midnight(day + timedelta(days=1)) - start).total_seconds() / 3600)


async def async_import_spot_prices(
    hass: HomeAssistant, client: CezClient, first_day: date, today: date
) -> dict[datetime, float]:
    """Fill spot prices for every day from first_day up to yesterday that lacks hours.

    OTE (converted with ČNB rates) is the primary source; days OTE cannot provide are
    tried on the ČEZ portal. Existing complete days are not requested again.
    """
    if first_day >= today:
        return {}
    start = gridlib.local_midnight(first_day).astimezone(UTC)
    existing = await _spot_for(hass, start, gridlib.local_midnight(today).astimezone(UTC))
    counts: dict[date, int] = defaultdict(int)
    for hour in existing:
        counts[hour.astimezone(gridlib.TZ).date()] += 1
    missing = [
        first_day + timedelta(days=i)
        for i in range((today - first_day).days)
        if counts[first_day + timedelta(days=i)] < expected_hours(first_day + timedelta(days=i))
    ]
    if not missing:
        return {}
    prices: dict[datetime, float] = {}
    source = ote.OteSource(client.session)
    failed: list[date] = []
    for day in missing:
        try:
            day_prices = await source.day_prices(day)
        except ote.OteError as err:
            _LOGGER.debug("OTE prices for %s failed: %s", day, err)
            day_prices = {}
        if day_prices:
            prices.update(day_prices)
        else:
            failed.append(day)
        await asyncio.sleep(REQUEST_PAUSE)
    for day in failed:
        prices.update(await client.get_spot_prices(day, day + timedelta(days=1)))
    if prices:
        metadata = StatisticMetaData(
            source=DOMAIN,
            statistic_id=SPOT_STATISTIC_ID,
            name="Spotová cena elektřiny (OTE)",
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


async def _hourly(
    hass: HomeAssistant, stat_id: str, start: datetime, end: datetime | None, kind: str
) -> dict[datetime, float]:
    """Hourly statistic values ("mean" or "change") from the recorder for [start, end)."""
    from homeassistant.components.recorder.statistics import statistics_during_period

    rows = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, start, end, {stat_id}, "hour", None, {kind}
    )
    return {_start_of(r): r[kind] for r in rows.get(stat_id, []) if r.get(kind) is not None}


async def _spot_for(hass: HomeAssistant, start: datetime, end: datetime) -> dict[datetime, float]:
    """Portal spot prices already in the recorder for [start, end)."""
    return await _hourly(hass, SPOT_STATISTIC_ID, start, end, "mean")


async def sensor_spot_prices(
    hass: HomeAssistant, sensor: str | None, start: datetime, end: datetime | None
) -> dict[datetime, float]:
    """Hourly mean of a HA spot price sensor in CZK/kWh (CZK/MWh converted)."""
    if not sensor:
        return {}
    state = hass.states.get(sensor)
    unit = str((state.attributes.get("unit_of_measurement") if state else "") or "")
    divisor = 1000.0 if "mwh" in unit.lower() else 1.0
    prices = await _hourly(hass, sensor, start, end, "mean")
    return {h: v / divisor for h, v in prices.items()}


async def async_valuation(
    hass: HomeAssistant, place_id: str, export_from: str, spot_sensor: str | None
) -> dict[str, dict[str, float]]:
    """Exported kWh valued at hourly spot prices, per local month.

    Portal prices win; hours without them use the HA spot price sensor.
    """
    start = gridlib.local_midnight(date.fromisoformat(export_from)).astimezone(UTC)
    export = await _hourly(hass, statistic_id("export", place_id), start, None, "change")
    if not export:
        return {}
    first = min(export)
    prices = await sensor_spot_prices(hass, spot_sensor, first, None)
    prices.update(await _hourly(hass, SPOT_STATISTIC_ID, first, None, "mean"))
    months: dict[str, dict[str, float]] = {}
    for hour, kwh in export.items():
        price = prices.get(hour)
        if price is None or not kwh:
            continue
        m = months.setdefault(
            hour.astimezone(gridlib.TZ).strftime("%Y-%m"), {"value": 0.0, "kwh": 0.0}
        )
        m["value"] += kwh * price
        m["kwh"] += kwh
    return {
        k: {"value": round(v["value"], 4), "kwh": round(v["kwh"], 4)}
        for k, v in sorted(months.items())
    }


async def async_import_grid(
    hass: HomeAssistant,
    client: CezClient,
    sp: SupplyPoint,
    cache: dict[str, Any],
    today: date,
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
    return imported


def spot_overview(prices: dict[datetime, float], today: date) -> dict[str, Any]:
    """Spot price summaries for dashboards from hourly prices (CZK/kWh).

    months: average per local month; days: last 14 days (avg/min/max);
    profile: average price per local hour of day over the last 7 days (a naive
    estimate for days whose prices are not published yet).
    """
    by_month: dict[str, list[float]] = defaultdict(list)
    by_day: dict[date, list[float]] = defaultdict(list)
    by_hour: dict[int, list[float]] = defaultdict(list)
    week_ago = today - timedelta(days=7)
    for hour, price in prices.items():
        local = hour.astimezone(gridlib.TZ)
        by_month[local.strftime("%Y-%m")].append(price)
        if local.date() >= today - timedelta(days=14):
            by_day[local.date()].append(price)
        if local.date() >= week_ago:
            by_hour[local.hour].append(price)

    def stats(values: list[float]) -> dict[str, float]:
        return {
            "avg": round(sum(values) / len(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }

    return {
        "months": [{"month": m, **stats(v)} for m, v in sorted(by_month.items())],
        "days": [{"date": d.isoformat(), **stats(v)} for d, v in sorted(by_day.items())],
        "profile": [
            round(sum(by_hour[h]) / len(by_hour[h]), 4) if by_hour.get(h) else None
            for h in range(24)
        ],
    }


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
    spot_sensor: str | None = None,
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
        if firsts:
            changed = bool(await async_import_spot_prices(hass, client, min(firsts), today))
        for sp, cache in places:
            changed |= await async_import_grid(hass, client, sp, cache, today) > 0
    except CezError as err:
        _LOGGER.warning("Importing statistics failed: %s", err)
    # Let the recorder store the queued imports before reading them back.
    await get_instance(hass).async_block_till_done()
    yesterday = today - timedelta(days=1)
    day_start = gridlib.local_midnight(yesterday).astimezone(UTC)
    day_end = day_start + timedelta(days=1)
    prices = await sensor_spot_prices(hass, spot_sensor, day_start, day_end)
    prices.update(await _spot_for(hass, day_start, day_end))
    summary = spot_day_summary(prices, yesterday)
    history_start = gridlib.local_midnight(today - timedelta(days=800)).astimezone(UTC)
    history = await sensor_spot_prices(hass, spot_sensor, history_start, day_end)
    history.update(await _spot_for(hass, history_start, day_end))
    overview = spot_overview(history, today) if history else None
    for sp, cache in places:
        if summary and cache.get("spot_yesterday") != summary:
            cache["spot_yesterday"] = summary
            changed = True
        if overview and cache.get("spot_overview") != overview:
            cache["spot_overview"] = overview
            changed = True
        if cache.get("export_from"):
            valuation = await async_valuation(hass, sp.place_id, cache["export_from"], spot_sensor)
            if valuation != cache.get("valuation"):
                cache["valuation"] = valuation
                changed = True
    return changed
