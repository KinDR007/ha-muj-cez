"""Portal data kept between Home Assistant restarts.

A restart reuses the data of the last successful download when no scheduled update
time has passed since then, so the portal is not asked for the same data again and the
entities are there at once. Stale data are shown until the refresh in the background
replaces them. The cache is dropped when the integration version or the account changes.
"""

from __future__ import annotations

import dataclasses
import hashlib
import types
import typing
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import CezData
from .const import DOMAIN, STORAGE_VERSION

_DATE = "__date__"
_DATETIME = "__datetime__"


def encode(value: Any) -> Any:
    """Dataclasses and dates to JSON values (dates tagged, also inside plain dicts)."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, datetime):
        return {_DATETIME: value.isoformat()}
    if isinstance(value, date):
        return {_DATE: value.isoformat()}
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [encode(v) for v in value]
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        if _DATE in value and len(value) == 1:
            return date.fromisoformat(value[_DATE])
        if _DATETIME in value and len(value) == 1:
            return datetime.fromisoformat(value[_DATETIME])
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def decode(tp: Any, value: Any) -> Any:
    """JSON values back to the annotated type (dataclasses, lists, dicts of them)."""
    if value is None:
        return None
    origin = typing.get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        return decode(args[0], value) if len(args) == 1 else _plain(value)
    if origin is list:
        (arg,) = typing.get_args(tp)
        return [decode(arg, v) for v in value]
    if origin is dict:
        _key, arg = typing.get_args(tp)
        return {k: decode(arg, v) for k, v in value.items()}
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        hints = typing.get_type_hints(tp)
        return tp(
            **{
                f.name: decode(hints[f.name], value[f.name])
                for f in dataclasses.fields(tp)
                if f.name in value
            }
        )
    return _plain(value)


def schema(tp: Any = CezData) -> str:
    """Short hash of the data structure (field names of the nested dataclasses): data
    cached by a build with other fields are not used."""
    seen: list[str] = []

    def walk(t: Any) -> None:
        for arg in typing.get_args(t):
            walk(arg)
        if isinstance(t, type) and dataclasses.is_dataclass(t) and t.__name__ not in seen:
            seen.append(t.__name__)
            hints = typing.get_type_hints(t)
            seen.extend(f.name for f in dataclasses.fields(t))
            for f in dataclasses.fields(t):
                walk(hints[f.name])

    walk(tp)
    return hashlib.sha1(",".join(seen).encode()).hexdigest()[:12]


def last_scheduled_run(
    now: datetime, time: tuple[int, int, int], is_day: typing.Callable[[datetime], bool]
) -> datetime | None:
    """Latest scheduled update time not after `now` (within the last 31 days)."""
    hour, minute, second = time
    for days in range(32):
        when = (now - timedelta(days=days)).replace(
            hour=hour, minute=minute, second=second, microsecond=0
        )
        if when <= now and is_day(when):
            return when
    return None


class DataCache:
    """Last downloaded portal data and the time of the last HDO download."""

    def __init__(self, hass: HomeAssistant, entry_id: str, identity: dict[str, Any]) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.cache"
        )
        # Integration version and account: a cache of another one is not used.
        self._identity = identity
        self._content: dict[str, Any] | None = None

    async def _load(self) -> dict[str, Any]:
        if self._content is None:
            stored = await self._store.async_load() or {}
            self._content = stored if stored.get("identity") == self._identity else {}
        return self._content

    async def async_get_data(self) -> tuple[CezData, datetime] | None:
        """Cached data with the time they were downloaded, None if unusable."""
        content = await self._load()
        try:
            data = decode(CezData, content["data"])
            fetched = dt_util.parse_datetime(content["fetched"])
        except (KeyError, TypeError, ValueError):
            return None
        if fetched is None or not data.supply_points:
            return None
        return data, fetched

    async def async_save_data(self, data: CezData, fetched: datetime) -> None:
        content = await self._load()
        # Derived values (comparison, smart meter summary, HDO) are computed again.
        stored = dataclasses.replace(data, comparison={}, grid={}, hdo={})
        content.update(identity=self._identity, fetched=fetched.isoformat(), data=encode(stored))
        await self._store.async_save(content)

    async def async_get_hdo_fetched(self) -> datetime | None:
        value = (await self._load()).get("hdo_fetched")
        return dt_util.parse_datetime(value) if value else None

    async def async_save_hdo_fetched(self, when: datetime) -> None:
        content = await self._load()
        content.update(identity=self._identity, hdo_fetched=when.isoformat())
        await self._store.async_save(content)

    async def async_remove(self) -> None:
        await self._store.async_remove()
