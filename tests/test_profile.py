"""15 min data: parsing, storage with history backfill and the dashboard websocket command."""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.muj_cez import api, grid
from custom_components.muj_cez.const import DOMAIN
from custom_components.muj_cez.profile import ProfileStore

from .conftest import PASSWORD, USERNAME, load
from .test_grid import PV_UID
from .test_grid_ha import _entity, fake_fetch_all

TZ = ZoneInfo("Europe/Prague")


def quarters(start: date, end: date, value: float = 0.25) -> dict[datetime, float]:
    """15 min values for the local days start .. end-1."""
    t = grid.local_midnight(start).astimezone(UTC)
    stop = grid.local_midnight(end).astimezone(UTC)
    out = {}
    while t < stop:
        out[t] = value
        t += timedelta(minutes=15)
    return out


def test_parse_quarters_and_hours() -> None:
    q = grid.parse_quarters(load("pv_profile_export.json"))
    assert len(q) == 8
    first = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)  # 11:00 local
    assert q[first] == 0.01 and q[first + timedelta(minutes=45)] == 0.03
    assert grid.hourly_from_quarters(q) == grid.parse_profile(load("pv_profile_export.json"))
    assert grid.hourly_from_quarters(q)[first] == 0.04
    assert grid.parse_quarters(None) == {}


@pytest.mark.parametrize(
    ("day", "count"), [(date(2026, 11, 2), 96), (date(2026, 3, 29), 92), (date(2026, 10, 25), 100)]
)
def test_day_quarters_dst(day: date, count: int) -> None:
    values = grid.day_quarters(quarters(day, day + timedelta(days=1)), day)
    assert len(values) == count and set(values) == {250}
    assert grid.day_quarters({}, day) == [None] * count


def test_day_quarters_missing_values() -> None:
    day = date(2026, 11, 2)
    q = quarters(day, day + timedelta(days=1))
    del q[grid.local_midnight(day).astimezone(UTC) + timedelta(hours=1)]
    values = grid.day_quarters(q, day)
    assert values[4] is None and values[3] == 250 and values[5] == 250


def _month_later(day: date) -> date:
    """Same day of the next month (the last day of a shorter month)."""
    year, month = day.year + day.month // 12, day.month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


class FakeProfileClient:
    """get_profile_quarters with data from `first` (export twice the import), errors on demand.

    Like the portal, one request returns at most one calendar month from its start.
    """

    def __init__(self, first: date, fail_from: date | None = None) -> None:
        self.first = first
        self.fail_from = fail_from
        self.calls: list[tuple[str, date, date]] = []

    async def get_profile_quarters(
        self, sp: Any, role: str, start: date, end: date
    ) -> dict[datetime, float]:
        self.calls.append((role, start, end))
        if self.fail_from and end > self.fail_from:
            raise api.CezConnectionError("down")
        value = 0.25 if role == grid.PROFILE_IMPORT else 0.5
        end = min(end, _month_later(start))
        return quarters(max(start, self.first), end, value) if end > self.first else {}


SP = api.SupplyPoint(PV_UID, "859", "Domov", "", "", "", None, None, place_id="0004444444")
CACHE = {"uid": PV_UID, "import_from": "2026-08-20", "export_from": "2026-10-01"}


async def test_backfill_then_recent_days(hass: HomeAssistant) -> None:
    store = ProfileStore(hass, "entry1")
    client = FakeProfileClient(date(2026, 8, 20))
    assert await store.async_update(client, SP, CACHE, date(2026, 11, 16))
    imports = [c for c in client.calls if c[0] == grid.PROFILE_IMPORT]
    assert imports[0][1] == date(2026, 8, 20) and imports[-1][2] == date(2026, 11, 16)
    assert all((b - a).days <= grid.PROFILE_WINDOW_DAYS for _, a, b in client.calls)

    for m, count in (("2026-09", 30), ("2026-10", 31)):  # no day lost at the request edges
        days = (await store.async_month(SP.place_id, m))["days"]
        assert len([d for d in days if d["import"]]) == count
    month = await store.async_month(SP.place_id, None)
    assert month["month"] == "2026-11"
    assert month["months"] == ["2026-08", "2026-09", "2026-10", "2026-11"]
    assert [d["date"] for d in month["days"]][-1] == "2026-11-15"
    assert month["days"][0]["import"] == [250] * 96 and month["days"][0]["export"] == [500] * 96
    assert month["import_done"] == "2026-11-15"
    october = await store.async_month(SP.place_id, "2026-10")
    dst = next(d for d in october["days"] if d["date"] == "2026-10-25")
    assert len(dst["import"]) == 100
    august = await store.async_month(SP.place_id, "2026-08")
    assert august["days"][0]["date"] == "2026-08-20" and august["days"][0]["export"] is None
    assert (await store.async_month(SP.place_id, "2025-01"))["days"] == []

    # Next day: only the recent days are fetched again, data survive a reload.
    client.calls.clear()
    reloaded = ProfileStore(hass, "entry1")
    await reloaded.async_update(client, SP, CACHE, date(2026, 11, 17))
    assert client.calls == [
        (grid.PROFILE_IMPORT, date(2026, 11, 14), date(2026, 11, 17)),
        (grid.PROFILE_EXPORT, date(2026, 11, 14), date(2026, 11, 17)),
    ]
    assert (await reloaded.async_month(SP.place_id, None))["days"][-1]["date"] == "2026-11-16"


async def test_backfill_resumes_after_error(hass: HomeAssistant) -> None:
    store = ProfileStore(hass, "entry1")
    failing = FakeProfileClient(date(2026, 8, 20), fail_from=date(2026, 10, 1))
    await store.async_update(failing, SP, {**CACHE, "export_from": None}, date(2026, 11, 16))
    done = (await store.async_month(SP.place_id, None))["import_done"]
    assert done == "2026-09-16"
    client = FakeProfileClient(date(2026, 8, 20))
    await store.async_update(client, SP, {**CACHE, "export_from": None}, date(2026, 11, 16))
    assert client.calls[0][1] == date(2026, 9, 17)
    assert (await store.async_month(SP.place_id, None))["import_done"] == "2026-11-15"


async def test_remove(hass: HomeAssistant, hass_storage: dict[str, Any]) -> None:
    store = ProfileStore(hass, "entry1")
    await store.async_update(FakeProfileClient(date(2026, 11, 1)), SP, CACHE, date(2026, 11, 16))
    keys = [k for k in hass_storage if k.startswith(f"{DOMAIN}.entry1.profile")]
    assert f"{DOMAIN}.entry1.profile_0004444444_2026" in keys
    await store.async_remove()
    assert not [k for k in hass_storage if k.startswith(f"{DOMAIN}.entry1.profile")]


@pytest.mark.freeze_time("2026-11-16T11:00:00+00:00")
async def test_websocket_profile(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, mock_client: AsyncMock
) -> None:
    await hass.config.async_set_time_zone("Europe/Prague")
    mock_client.fetch_all.side_effect = fake_fetch_all
    fake = FakeProfileClient(date(2026, 11, 1))
    mock_client.get_profile_quarters.side_effect = fake.get_profile_quarters
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    sensor = _entity(hass, PV_UID, "grid_data_date")
    assert sensor
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/profile", "entity_id": sensor})
    result = (await ws.receive_json())["result"]
    assert result["month"] == "2026-11" and result["months"] == ["2026-11"]
    assert len(result["days"]) == 15 and result["days"][0]["import"][0] == 250

    await ws.send_json(
        {"id": 2, "type": f"{DOMAIN}/profile", "entity_id": sensor, "month": "2026-10"}
    )
    assert (await ws.receive_json())["result"]["days"] == []

    other = _entity(hass, PV_UID, "grid_import_month")
    for i, (eid, month) in enumerate(
        [(other, None), ("sensor.nope", None), (sensor, "2026-13")], start=3
    ):
        await ws.send_json(
            {
                "id": i,
                "type": f"{DOMAIN}/profile",
                "entity_id": eid,
                **({"month": month} if month else {}),
            }
        )
        reply = await ws.receive_json()
        assert not reply["success"], eid
