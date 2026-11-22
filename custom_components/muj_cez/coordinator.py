"""Data update coordinator with time-of-day scheduling."""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from collections.abc import Callable
from datetime import date, datetime
from functools import partial
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import grid as gridlib
from .api import CezAuthError, CezClient, CezData, CezError
from .cache import DataCache, last_scheduled_run
from .compare import DailyEnergy, build_comparison
from .const import (
    CONF_HDO,
    CONF_INVOICE_PERIODS,
    CONF_PARTNER,
    CONF_REFERENCE_EXPORT_SENSOR,
    CONF_REFERENCE_SENSOR,
    CONF_SPOT_PRICE_SENSOR,
    CONF_UPDATE_PERIOD,
    CONF_UPDATE_TIME,
    DEFAULT_UPDATE_PERIOD,
    DEFAULT_UPDATE_TIME,
    DOMAIN,
    HDO_MAX_AGE,
    HDO_REFRESH_TIME,
    HDO_TIMEOUT,
    PERIOD_MONTHLY,
    PERIOD_WEEKLY,
    RETRY_COUNT,
    RETRY_DELAY,
    STORAGE_VERSION,
    price_breakdown_enabled,
)
from .distribuce import DipClient, DipError, merge, parse_signals, prune
from .pricing import InvoiceStore
from .profile import ProfileStore
from .statistics import async_update_statistics, statistic_id

_LOGGER = logging.getLogger(__name__)

# Fields refreshed after a meter reading; an optional request that fails keeps the
# previous value instead of emptying the sensors.
READING_FIELDS = (
    "simulation",
    "months",
    "sim_items",
    "advance_plan",
    "last_period",
    "meter_reading",
    "readings",
    "advance_settings",
)

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

    def __init__(
        self,
        hass: HomeAssistant,
        entry: MujCezConfigEntry,
        client: CezClient,
        version: str = "",
    ) -> None:
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
        self._hdo_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.hdo"
        )
        self._hdo: dict[str, dict[str, Any]] | None = None
        self._hdo_fetched: datetime | None = None
        self._hdo_warned = False
        self.dip_client = DipClient
        self.profiles = ProfileStore(hass, entry.entry_id)
        self._profile_task: asyncio.Task[None] | None = None
        self.invoices = InvoiceStore(hass, entry.entry_id)
        self._invoice_task: asyncio.Task[None] | None = None
        # Reload of a running HA (or a new entry): check invoices of all points now.
        self._force_invoices = hass.is_running
        # Per consumption point uid: when its invoices were last checked (price card).
        self.invoices_updated: dict[str, str] = {}
        identity = {
            "version": version,
            "username": entry.data[CONF_USERNAME],
            "partner": entry.data.get(CONF_PARTNER),
        }
        self.cache = DataCache(hass, entry.entry_id, identity)
        # HA start uses the cached data (see cache.py); a reload of the entry downloads.
        self._use_cache = not hass.is_running
        # Cached data older than the last scheduled update: refresh after the setup.
        self.refresh_after_start = False

    def _fresh(self, fetched: datetime) -> bool:
        """No scheduled update time has passed since the data were downloaded."""
        options = self.config_entry.options
        period = options.get(CONF_UPDATE_PERIOD, DEFAULT_UPDATE_PERIOD)
        time = parse_time(options.get(CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME))
        last = last_scheduled_run(dt_util.now(), time, partial(is_update_day, period))
        return last is None or fetched >= last

    async def _async_update_data(self) -> CezData:
        if self._grid_cache is None:
            self._grid_cache = await self._grid_store.async_load() or {}
        cached = None
        if self._use_cache:  # first refresh after the HA start only
            self._use_cache = False
            cached = await self.cache.async_get_data()
        data: CezData | None = None
        downloaded = False
        if cached and self._fresh(cached[1]):
            data, fetched = cached
            _LOGGER.debug("Using data downloaded at %s", fetched)
        elif cached:
            # Show the stored values now, download in the background after the setup.
            data, fetched = cached
            self.refresh_after_start = True
        else:
            data = await self._async_fetch()
            fetched = dt_util.utcnow()
            downloaded = True
        await self._async_add_comparison(data)
        await self._async_add_grid(data)
        await self.async_update_hdo(data)
        self.last_success_time = fetched
        if data.grid:
            self._schedule_statistics(data)
            if downloaded:  # the recent 15 min days are fetched again with new data only
                self._schedule_profiles(data)
        if price_breakdown_enabled(self.config_entry.options):
            self._schedule_invoices(data)
        return data

    async def _async_fetch(self) -> CezData:
        try:
            data = await self.client.fetch_all(dt_util.now().date(), self._grid_cache)
        except CezAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CezError as err:
            raise UpdateFailed(str(err)) from err
        await self._grid_store.async_save(self._grid_cache)
        await self.cache.async_save_data(data, dt_util.utcnow())
        return data

    def _schedule_invoices(self, data: CezData) -> None:
        """Download new settlements for the price breakdown in the background."""
        if self._invoice_task and not self._invoice_task.done():
            return
        self._invoice_task = self.config_entry.async_create_background_task(
            self.hass, self._async_run_invoices(data), f"{DOMAIN}_invoices"
        )

    async def _async_run_invoices(self, data: CezData, only: str | None = None) -> None:
        today = dt_util.now().date()
        try:
            force = self._force_invoices and only is None
            self._force_invoices = False
            checked: list[str] = []
            added = 0
            for uid in list(data.supply_points) if force else [only]:
                added += await self.invoices.async_update(
                    self.client,
                    data,
                    today,
                    self.config_entry.options.get(CONF_INVOICE_PERIODS),
                    uid,
                )
                checked += self.invoices.checked_now
            if added:
                _LOGGER.debug("Stored %s new invoices", added)
        except Exception:  # never break the integration because of the dashboard data
            _LOGGER.exception("Storing invoices failed")
            return
        if checked:
            now = dt_util.utcnow().isoformat()
            self.invoices_updated.update(dict.fromkeys(checked, now))
            self.async_update_listeners()

    async def async_refresh_invoices(self, uid: str) -> None:
        """Manual refresh (button): download new invoices of one point now."""
        if self.data is None or not price_breakdown_enabled(self.config_entry.options):
            return
        if self._invoice_task and not self._invoice_task.done():
            await self._invoice_task
        self._invoice_task = self.config_entry.async_create_background_task(
            self.hass, self._async_run_invoices(self.data, uid), f"{DOMAIN}_invoices"
        )
        await self._invoice_task

    def _schedule_profiles(self, data: CezData) -> None:
        """Store 15 min values in the background (the first run fills the history)."""
        if self._profile_task and not self._profile_task.done():
            return
        self._profile_task = self.config_entry.async_create_background_task(
            self.hass, self._async_run_profiles(data), f"{DOMAIN}_profiles"
        )

    async def _async_run_profiles(self, data: CezData) -> None:
        today = dt_util.now().date()
        for spd in data.supply_points.values():
            sp = spd.supply_point
            cache = (self._grid_cache or {}).get(sp.place_id)
            if sp.production or not cache or cache.get("uid") != sp.uid:
                continue
            try:
                await self.profiles.async_update(self.client, sp, cache, today)
            except Exception:  # never break the integration because of the dashboard data
                _LOGGER.exception("Storing 15 min data failed")

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

    async def async_update_hdo(self, data: CezData, force: bool = False) -> None:
        """HDO schedules of the consumption points from the ČEZ Distribuce portal.

        Optional: any failure keeps the stored schedule (it covers about a week).
        """
        if not self.config_entry.options.get(CONF_HDO, True):
            data.hdo = {}
            return
        if self._hdo is None:
            self._hdo = await self._hdo_store.async_load() or {}
            self._hdo_fetched = await self.cache.async_get_hdo_fetched()
        eans = [
            spd.supply_point.ean
            for spd in data.supply_points.values()
            if not spd.supply_point.production and not spd.supply_point.gas and spd.supply_point.ean
        ]
        stale = self._hdo_fetched is None or dt_util.utcnow() - self._hdo_fetched > HDO_MAX_AGE
        if eans and (force or stale):
            await self._async_fetch_hdo(eans)
        today = dt_util.now().date()
        self._hdo = {ean: prune(s, today) for ean, s in self._hdo.items() if ean in eans}
        await self._hdo_store.async_save(self._hdo)
        data.hdo = dict(self._hdo)

    async def _async_fetch_hdo(self, eans: list[str]) -> None:
        assert self._hdo is not None
        entry = self.config_entry
        factory = partial(async_create_clientsession, self.hass, auto_cleanup=False)
        try:
            async with (
                asyncio.timeout(HDO_TIMEOUT),
                self.dip_client(
                    entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], factory, detach=True
                ) as dip,
            ):
                for ean in eans:
                    try:
                        schedule = parse_signals(await dip.signals(ean))
                    except DipError as err:
                        _LOGGER.debug("HDO of %s failed: %s", ean, err)
                        continue
                    if schedule:
                        self._hdo[ean] = merge(self._hdo.get(ean), schedule)
                    else:  # no HDO on this supply point (single tariff, smart meter)
                        self._hdo.pop(ean, None)
        except (DipError, TimeoutError) as err:
            log = _LOGGER.debug if self._hdo_warned else _LOGGER.warning
            log("ČEZ Distribuce portal (HDO) unavailable: %s", err)
            self._hdo_warned = True
            return
        self._hdo_fetched = dt_util.utcnow()
        self._hdo_warned = False
        await self.cache.async_save_hdo_fetched(self._hdo_fetched)

    async def _async_refresh_hdo(self) -> None:
        if self.data is None:
            return
        await self.async_update_hdo(self.data, force=True)
        self.async_update_listeners()

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
            # The reference sensor measures electricity: gas points get portal values only.
            gas = spd.supply_point.gas
            comparison: dict[str, Any] = build_comparison(spd, None if gas else daily, today)
            comparison["reference_sensor"] = None if gas else sensor
            data.comparison[uid] = comparison

    async def async_refresh_point(self, uid: str) -> None:
        """After a meter reading: fetch only what the reading changes for one point
        (readings, billing simulation, advances, billing periods) and update sensors."""
        data = self.data
        spd = data.supply_points.get(uid) if data else None
        if data is None or spd is None or spd.supply_point.production:
            return
        fresh = dataclasses.replace(spd)
        try:
            await self.client.fetch_readings_and_billing(
                fresh, data.documents, dt_util.now().date()
            )
        except CezError as err:
            _LOGGER.warning("Refresh of %s after the reading failed: %s", spd.supply_point.ean, err)
            return
        for name in READING_FIELDS:
            if getattr(fresh, name) is None:
                setattr(fresh, name, getattr(spd, name))
        if fresh.last_period is spd.last_period:
            fresh.periods = spd.periods  # history request failed, keep the periods
        # The full refresh may have replaced the data meanwhile.
        current = self.data
        if current is None or uid not in current.supply_points:
            return
        updated = dataclasses.replace(
            current,
            supply_points={**current.supply_points, uid: fresh},
            comparison=dict(current.comparison),
        )
        await self._async_add_comparison(updated)
        self.async_set_updated_data(updated)
        await self.cache.async_save_data(updated, self.last_success_time or dt_util.utcnow())

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
        def _on_hdo_time(_now: datetime) -> None:
            self.config_entry.async_create_background_task(
                self.hass, self._async_refresh_hdo(), f"{DOMAIN}_hdo"
            )

        unsub_hdo = async_track_time_change(
            self.hass, _on_hdo_time, hour=HDO_REFRESH_TIME[0], minute=HDO_REFRESH_TIME[1], second=0
        )

        @callback
        def _unsub() -> None:
            unsub_time()
            unsub_hdo()
            self._cancel_retry()

        return _unsub
