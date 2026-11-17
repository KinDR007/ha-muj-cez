"""Data update coordinator with time-of-day scheduling."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import grid as gridlib
from .api import CezAuthError, CezClient, CezData, CezError
from .compare import DailyEnergy, build_comparison
from .const import (
    CONF_REFERENCE_EXPORT_SENSOR,
    CONF_REFERENCE_SENSOR,
    CONF_SPOT_PRICE_SENSOR,
    CONF_UPDATE_PERIOD,
    CONF_UPDATE_TIME,
    DEFAULT_UPDATE_PERIOD,
    DEFAULT_UPDATE_TIME,
    DOMAIN,
    PERIOD_MONTHLY,
    PERIOD_WEEKLY,
    RETRY_COUNT,
    RETRY_DELAY,
    STORAGE_VERSION,
)
from .statistics import async_update_statistics, statistic_id

_LOGGER = logging.getLogger(__name__)

type MujCezConfigEntry = ConfigEntry[MujCezCoordinator]


def is_update_day(period: str, now: datetime) -> bool:
    """Weekly runs on Mondays, monthly on the 1st."""
    if period == PERIOD_WEEKLY:
        return now.weekday() == 0
    if period == PERIOD_MONTHLY:
        return now.day == 1
    return True


async def async_get_daily_energy(
    hass: HomeAssistant, statistic_id: str, start: date
) -> DailyEnergy:
    """Daily energy (kWh, local days) from recorder long-term statistics."""
    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.statistics import statistics_during_period

    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.start_of_local_day(start),
        None,
        {statistic_id},
        "day",
        None,
        {"change"},
    )
    daily: DailyEnergy = {}
    for row in stats.get(statistic_id, []):
        change = row.get("change")
        start_ts = row.get("start")
        if change is None or start_ts is None:
            continue
        started = (
            dt_util.utc_from_timestamp(start_ts) if isinstance(start_ts, int | float) else start_ts
        )
        daily[dt_util.as_local(started).date()] = change
    return daily


def parse_time(value: str) -> tuple[int, int, int]:
    parts = [int(p) for p in value.split(":")] + [0, 0]
    return parts[0], parts[1], parts[2]


class MujCezCoordinator(DataUpdateCoordinator[CezData]):
    """Fetches data on a fixed schedule instead of a polling interval."""

    config_entry: MujCezConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MujCezConfigEntry, client: CezClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=None)
        self.client = client
        self.last_success_time: datetime | None = None
        self._retry_unsub: CALLBACK_TYPE | None = None
        self._retries = 0
        self._grid_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.grid"
        )
        self._grid_cache: dict[str, dict[str, Any]] | None = None
        self._statistics_task: asyncio.Task[None] | None = None

    async def _async_update_data(self) -> CezData:
        if self._grid_cache is None:
            self._grid_cache = await self._grid_store.async_load() or {}
        try:
            data = await self.client.fetch_all(dt_util.now().date(), self._grid_cache)
        except CezAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CezError as err:
            raise UpdateFailed(str(err)) from err
        await self._grid_store.async_save(self._grid_cache)
        await self._async_add_comparison(data)
        await self._async_add_grid(data)
        self.last_success_time = dt_util.utcnow()
        if data.grid:
            self._schedule_statistics(data)
        return data

    def _schedule_statistics(self, data: CezData) -> None:
        """Import long-term statistics in the background (backfill may take minutes)."""
        if "recorder" not in self.hass.config.components:
            return
        if self._statistics_task and not self._statistics_task.done():
            return
        self._statistics_task = self.config_entry.async_create_background_task(
            self.hass, self._async_run_statistics(data), f"{DOMAIN}_statistics"
        )

    async def _async_run_statistics(self, data: CezData) -> None:
        try:
            changed = await async_update_statistics(
                self.hass,
                self.client,
                [spd.supply_point for spd in data.supply_points.values()],
                self._grid_cache or {},
                self.config_entry.options.get(CONF_SPOT_PRICE_SENSOR),
            )
        except Exception:  # never break the integration because of statistics
            _LOGGER.exception("Importing statistics failed")
            return
        if not changed:
            return
        await self._grid_store.async_save(self._grid_cache or {})
        if self.data is not None:
            await self._async_add_grid(self.data)
            self.async_update_listeners()

    async def _async_add_grid(self, data: CezData) -> None:
        """Smart meter summaries per consumption place (only places with data)."""
        today = dt_util.now().date()
        options = self.config_entry.options
        for place_id, cache in (self._grid_cache or {}).items():
            imp = gridlib.from_cache(cache.get("import"))
            exp = gridlib.from_cache(cache.get("export"))
            if not imp and not exp:
                continue
            info: dict[str, Any] = {
                "uid": cache.get("uid"),
                "import_from": cache.get("import_from"),
                "export_from": cache.get("export_from"),
                "summary": gridlib.summary(imp, exp, today),
                "months": [m.as_dict() for m in gridlib.monthly(imp, exp)],
                "spot_yesterday": cache.get("spot_yesterday"),
                "spot_overview": cache.get("spot_overview"),
                "statistics": {
                    key: statistic_id(key, place_id)
                    for key in ("import", "export")
                    if cache.get(f"{key}_from")
                },
            }
            for key, daily, option in (
                ("import", imp, CONF_REFERENCE_SENSOR),
                ("export", exp, CONF_REFERENCE_EXPORT_SENSOR),
            ):
                sensor = options.get(option)
                if not sensor or not daily:
                    continue
                try:
                    ha = await async_get_daily_energy(self.hass, sensor, min(daily))
                except Exception:  # recorder unavailable or statistics error
                    _LOGGER.exception("Reading statistics of %s failed", sensor)
                    continue
                info[f"{key}_comparison"] = gridlib.compare_monthly(daily, ha)
                info[f"{key}_reference_sensor"] = sensor
            for spd in data.supply_points.values():
                sp = spd.supply_point
                if sp.production and sp.place_id == place_id and spd.payouts:
                    info["payouts"] = gridlib.payout_months(
                        spd.payouts, exp, cache.get("valuation")
                    )
            data.grid[place_id] = info

    async def _async_add_comparison(self, data: CezData) -> None:
        """Compare portal values with the configured HA energy sensor (optional)."""
        sensor = self.config_entry.options.get(CONF_REFERENCE_SENSOR)
        today = dt_util.now().date()
        daily: DailyEnergy | None = None
        if sensor:
            starts = [
                p.date_from
                for spd in data.supply_points.values()
                for p in spd.periods or []
                if p.date_from
            ]
            try:
                daily = await async_get_daily_energy(self.hass, sensor, min(starts, default=today))
            except Exception:  # recorder unavailable or statistics error
                _LOGGER.exception("Reading statistics of %s failed", sensor)
        for uid, spd in data.supply_points.items():
            comparison: dict[str, Any] = build_comparison(spd, daily, today)
            comparison["reference_sensor"] = sensor
            data.comparison[uid] = comparison

    async def async_scheduled_refresh(self) -> None:
        """Refresh and schedule a retry on failure."""
        self._cancel_retry()
        await self.async_refresh()
        if self.last_update_success:
            self._retries = 0
            return
        if self._retries >= RETRY_COUNT:
            _LOGGER.warning("Update failed, giving up until next scheduled run")
            self._retries = 0
            return
        self._retries += 1
        _LOGGER.debug("Update failed, retry %s/%s in %s", self._retries, RETRY_COUNT, RETRY_DELAY)

        @callback
        def _retry(_now: datetime) -> None:
            self._retry_unsub = None
            self.config_entry.async_create_background_task(
                self.hass, self.async_scheduled_refresh(), f"{DOMAIN}_retry"
            )

        self._retry_unsub = async_call_later(self.hass, RETRY_DELAY, _retry)

    def _cancel_retry(self) -> None:
        if self._retry_unsub:
            self._retry_unsub()
            self._retry_unsub = None

    @callback
    def async_setup_schedule(self) -> Callable[[], None]:
        options = self.config_entry.options
        period = options.get(CONF_UPDATE_PERIOD, DEFAULT_UPDATE_PERIOD)
        hour, minute, second = parse_time(options.get(CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME))

        @callback
        def _on_time(now: datetime) -> None:
            if not is_update_day(period, now):
                return
            self._retries = 0
            self.config_entry.async_create_background_task(
                self.hass, self.async_scheduled_refresh(), f"{DOMAIN}_scheduled"
            )

        unsub_time = async_track_time_change(
            self.hass, _on_time, hour=hour, minute=minute, second=second
        )

        @callback
        def _unsub() -> None:
            unsub_time()
            self._cancel_retry()

        return _unsub
