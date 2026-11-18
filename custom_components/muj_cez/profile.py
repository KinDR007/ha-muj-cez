"""15 min import/export of smart meter places, kept for the dashboard.

Long-term statistics of Home Assistant are hourly, so the 15 min values of the portal
are stored by the integration: one store per place and year
(`muj_cez.<entry>.profile_<place>_<year>`), Wh per 15 min of each local day:

  {"import": {"2026-11-01": [12, 8, ...96 values], ...}, "export": {...}}

A day has 96 values (92 / 100 on the days the clock changes), None where the portal
has no value. Kept are the current month and the HISTORY_MONTHS months before it (the
whole current year included); older days are deleted. The first run fills this history
(about 15 requests per direction), later runs fetch the last days again (the portal
publishes and corrects them with a delay of about a day).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import grid as gridlib
from .api import CezClient, CezError, SupplyPoint
from .const import DOMAIN, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

KINDS = (("import", gridlib.PROFILE_IMPORT), ("export", gridlib.PROFILE_EXPORT))
# Days fetched again on every run.
RECENT_DAYS = 3
HISTORY_MONTHS = 12
REQUEST_PAUSE = 0.5

type YearData = dict[str, dict[str, list[int | None]]]


def history_start(today: date) -> date:
    """First day of the month HISTORY_MONTHS months before the current one."""
    months = today.year * 12 + today.month - 1 - HISTORY_MONTHS
    return date(months // 12, months % 12 + 1, 1)


class ProfileStore:
    """Stored 15 min values of the places of one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._meta_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.profile"
        )
        self._meta: dict[str, Any] | None = None
        self._years: dict[tuple[str, int], YearData] = {}
        self._lock = asyncio.Lock()

    def _store(self, place_id: str, year: int) -> Store[YearData]:
        return Store(
            self.hass, STORAGE_VERSION, f"{DOMAIN}.{self.entry_id}.profile_{place_id}_{year}"
        )

    async def _load_meta(self) -> dict[str, Any]:
        if self._meta is None:
            self._meta = await self._meta_store.async_load() or {}
        return self._meta

    async def _year(self, place_id: str, year: int) -> YearData:
        key = (place_id, year)
        if key not in self._years:
            data = await self._store(place_id, year).async_load() or {}
            self._years[key] = {kind: dict(data.get(kind) or {}) for kind, _ in KINDS}
        return self._years[key]

    async def async_update(
        self, client: CezClient, sp: SupplyPoint, cache: dict[str, Any], today: date
    ) -> bool:
        """Fetch missing and recent days of a place; True when something was stored."""
        async with self._lock:
            meta = await self._load_meta()
            place = meta.setdefault(sp.place_id, {"years": []})
            changed = False
            for kind, role in KINDS:
                first = cache.get(f"{kind}_from")
                if not first:
                    continue
                done = place.get(f"{kind}_done")
                start = max(date.fromisoformat(first), history_start(today))
                if done:
                    start = max(
                        start,
                        min(
                            date.fromisoformat(done) + timedelta(days=1),
                            today - timedelta(days=RECENT_DAYS),
                        ),
                    )
                for a, b in gridlib.windows(start, today, gridlib.PROFILE_WINDOW_DAYS):
                    try:
                        quarters = await client.get_profile_quarters(sp, role, a, b)
                    except CezError as err:
                        _LOGGER.warning("15 min %s data of %s failed: %s", kind, sp.ean, err)
                        break
                    changed |= await self._put(sp.place_id, kind, quarters, a, b)
                    place[f"{kind}_done"] = (b - timedelta(days=1)).isoformat()
                    await self._meta_store.async_save(meta)
                    await asyncio.sleep(REQUEST_PAUSE)
            await self._prune(sp.place_id, history_start(today))
            return changed

    async def _prune(self, place_id: str, keep_from: date) -> None:
        """Delete the days before keep_from (whole years by their store)."""
        assert self._meta is not None
        place = self._meta[place_id]
        keep = keep_from.isoformat()
        for y in list(place["years"]):
            if y < keep_from.year:
                await self._store(place_id, y).async_remove()
                self._years.pop((place_id, y), None)
                place["years"].remove(y)
            elif y == keep_from.year:
                data = await self._year(place_id, y)
                old = [(k, d) for k, _ in KINDS for d in data[k] if d < keep]
                for k, d in old:
                    del data[k][d]
                if old:
                    await self._store(place_id, y).async_save(data)
        await self._meta_store.async_save(self._meta)

    async def _put(
        self, place_id: str, kind: str, quarters: dict[Any, float], start: date, end: date
    ) -> bool:
        """Store the days start .. end-1 that have values; True on change."""
        assert self._meta is not None
        place = self._meta[place_id]
        dirty: set[int] = set()
        seen: set[int] = set()
        day = start
        while day < end:
            values = gridlib.day_quarters(quarters, day)
            if any(v is not None for v in values):
                seen.add(day.year)
                year = await self._year(place_id, day.year)
                if year[kind].get(day.isoformat()) != values:
                    year[kind][day.isoformat()] = values
                    dirty.add(day.year)
            day += timedelta(days=1)
        for y in dirty:
            data = self._years[(place_id, y)]
            data[kind] = dict(sorted(data[kind].items()))
            await self._store(place_id, y).async_save(data)
        # Every year with data is listed, also when its store already had the same days.
        place["years"] = sorted(set(place["years"]) | seen)
        return bool(dirty)

    async def async_month(self, place_id: str, month: str | None) -> dict[str, Any]:
        """Days of one month (default: the last month with data) and all months with data."""
        meta = await self._load_meta()
        place = meta.get(place_id) or {}
        months: set[str] = set()
        for y in place.get("years") or []:
            year = await self._year(place_id, y)
            for kind, _ in KINDS:
                months.update(d[:7] for d in year[kind])
        ordered = sorted(months)
        if month is None and ordered:
            month = ordered[-1]
        days: list[dict[str, Any]] = []
        if month and int(month[:4]) in (place.get("years") or []):
            year = await self._year(place_id, int(month[:4]))
            dates = sorted({d for kind, _ in KINDS for d in year[kind] if d.startswith(month)})
            days = [{"date": d, **{kind: year[kind].get(d) for kind, _ in KINDS}} for d in dates]
        return {
            "month": month,
            "months": ordered,
            "days": days,
            "import_done": place.get("import_done"),
            "export_done": place.get("export_done"),
        }

    async def async_remove(self) -> None:
        """Delete all stores of the entry."""
        meta = await self._load_meta()
        for place_id, place in meta.items():
            for y in place.get("years") or []:
                await self._store(place_id, y).async_remove()
        await self._meta_store.async_remove()
        self._meta, self._years = {}, {}
