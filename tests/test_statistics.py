"""Long-term statistics import (smart meter hourly data and spot prices)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.muj_cez import api, grid, ote, statistics

from .conftest import load
from .test_grid import FakeClient


def _profile(start: date, days: int, value: float, skip_last_hours: int = 0) -> list[dict]:
    """profile-data response with 15 min values for whole local days."""
    begin = grid.local_midnight(start).astimezone(UTC)
    end = grid.local_midnight(start + timedelta(days=days)).astimezone(UTC) - timedelta(
        hours=skip_last_hours
    )
    rows = []
    t = begin
    while t < end:
        rows.append({"profileReadingDatetimeFrom": t.isoformat(), "profileReadingValue": value})
        t += timedelta(minutes=15)
    return [{"data": rows}]


class FakeOte:
    """OTE stand-in: prices per day from `PRICES`, missing days raise OteError."""

    PRICES: dict[date, float] = {}
    calls: list[date] = []

    def __init__(self, session: object) -> None:
        pass

    async def day_prices(self, day: date) -> dict[datetime, float]:
        FakeOte.calls.append(day)
        price = FakeOte.PRICES.get(day)
        if price is None:
            raise ote.OteError("unpublished")
        start = grid.local_midnight(day).astimezone(UTC)
        hours = statistics.expected_hours(day)
        return {start + timedelta(hours=i): price for i in range(hours)}


@pytest.fixture(autouse=True)
def fake_ote(monkeypatch: pytest.MonkeyPatch) -> type[FakeOte]:
    FakeOte.PRICES = {}
    FakeOte.calls = []
    monkeypatch.setattr(statistics.ote, "OteSource", FakeOte)
    return FakeOte


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_db_url: str, enable_custom_integrations: None) -> None:
    """Recorder database must be prepared before hass is set up."""


def test_complete_days() -> None:
    hourly = grid.parse_profile(_profile(date(2026, 11, 10), 3, 0.25, skip_last_hours=2))
    kept = statistics.complete_days(hourly, date(2026, 11, 13))
    days = {h.astimezone(grid.TZ).date() for h in kept}
    # Last day misses two hours and is recent: left for the next run.
    assert days == {date(2026, 11, 10), date(2026, 11, 11)}
    # The same gap long ago is accepted (meter outage), the import never gets stuck.
    kept = statistics.complete_days(hourly, date(2026, 12, 31))
    assert len({h.astimezone(grid.TZ).date() for h in kept}) == 3
    # DST day has 25 hours.
    dst = grid.parse_profile(_profile(date(2026, 10, 25), 1, 0.25))
    assert len(dst) == 25
    assert len(statistics.complete_days(dst, date(2026, 10, 26))) == 25
    assert [
        statistics.expected_hours(date(2026, m, d)) for m, d in ((3, 29), (10, 25), (11, 2))
    ] == [
        23,
        25,
        24,
    ]
    # A spring day short of one hour is incomplete.
    spring = grid.parse_profile(_profile(date(2026, 3, 29), 1, 0.25, skip_last_hours=1))
    assert statistics.complete_days(spring, date(2026, 3, 30)) == {}


@pytest.fixture
def pv_sp() -> api.SupplyPoint:
    return api.parse_supply_points(load("pv_supply_points.json"))[0]


async def _stats(hass: HomeAssistant, stat_id: str, types: set[str]) -> list[dict[str, Any]]:
    from homeassistant.components.recorder import get_instance

    rows = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        datetime(2026, 1, 1, tzinfo=UTC),
        None,
        {stat_id},
        "hour",
        None,
        types,
    )
    return rows.get(stat_id, [])


async def test_import_grid_and_spot(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    pv_sp: api.SupplyPoint,
    freezer: FrozenDateTimeFactory,
) -> None:
    await hass.config.async_set_time_zone("Europe/Prague")
    today = date(2026, 11, 13)
    freezer.move_to(datetime(2026, 11, 13, 12, 0, tzinfo=grid.TZ))

    def handler(path: str, params: dict[str, str]) -> Any:
        if path.endswith("profile-data"):
            frm = datetime.fromisoformat(
                params["profileReadingDatetimeFrom"].replace("Z", "+00:00")
            )
            day = frm.astimezone(grid.TZ).date()
            if day >= today:
                return []
            value = 0.25 if params["profileReadingRoleId"] == grid.PROFILE_IMPORT else 0.5
            span = (min(today, day + timedelta(days=31)) - day).days
            return _profile(day, span, value)
        if path.endswith("spot-prices-simple"):
            frm = params["pricelistSpotConfigurationDatetimeFrom"]
            start = datetime.fromisoformat(frm.replace("Z", "+00:00"))
            return {
                "pricelistConfigurationUnit": {"entryId": "MWH"},
                "spotConfigurations": [
                    {
                        "pricelistSpotConfigurationDatetimeFrom": (start + timedelta(hours=i))
                        .isoformat()
                        .replace("+00:00", "Z"),
                        "pricelistSpotConfigurationPriceAverage": 2000.0,
                    }
                    for i in range(24 * 7)
                ],
            }
        raise api.CezConnectionError("HTTP 404")

    client = FakeClient(handler)
    cache = {
        "uid": pv_sp.uid,
        "import_from": "2026-11-10",
        "export_from": "2026-11-10",
        "import": {"2026-11-10": 24.0},
        "export": {"2026-11-10": 48.0},
    }
    statistics.REQUEST_PAUSE = 0
    changed = await statistics.async_update_statistics(
        hass, client, [pv_sp], {pv_sp.place_id: cache}
    )
    assert changed
    await async_wait_recording_done(hass)

    imp = await _stats(hass, statistics.statistic_id("import", pv_sp.place_id), {"sum"})
    exp = await _stats(hass, statistics.statistic_id("export", pv_sp.place_id), {"sum"})
    assert len(imp) == len(exp) == 72  # three complete local days
    assert imp[-1]["sum"] == pytest.approx(72.0)
    assert exp[-1]["sum"] == pytest.approx(144.0)
    spot = await _stats(hass, statistics.SPOT_STATISTIC_ID, {"mean"})
    assert spot and spot[0]["mean"] == pytest.approx(2.0)
    # Export valued at spot: 2 kWh/h * 2 CZK/kWh.
    assert cache["valuation"]["2026-11"]["kwh"] == pytest.approx(144.0)
    assert cache["valuation"]["2026-11"]["value"] == pytest.approx(288.0)
    assert cache["spot_yesterday"]["average"] == pytest.approx(2.0)
    assert cache["spot_overview"]["months"][-1]["avg"] == pytest.approx(2.0)

    # Second run: nothing new, nothing re-imported or double counted.
    client.calls.clear()
    changed = await statistics.async_update_statistics(
        hass, client, [pv_sp], {pv_sp.place_id: cache}
    )
    await async_wait_recording_done(hass)
    assert not changed
    assert not [c for c in client.calls if c[0].endswith("profile-data")]
    assert cache["valuation"]["2026-11"]["value"] == pytest.approx(288.0)
    exp = await _stats(hass, statistics.statistic_id("export", pv_sp.place_id), {"sum"})
    assert exp[-1]["sum"] == pytest.approx(144.0)


async def test_no_statistics_without_smart_meter(
    recorder_mock: Recorder, hass: HomeAssistant
) -> None:
    sp = api.parse_supply_points(load("supply_points.json"))[0]
    client = FakeClient(lambda p, q: (_ for _ in ()).throw(AssertionError("no request")))
    cache = {sp.place_id: {"uid": sp.uid, "import_from": None, "export_from": None}}
    assert not await statistics.async_update_statistics(hass, client, [sp], cache)


async def test_valuation_from_ha_spot_sensor(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    pv_sp: api.SupplyPoint,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Portal has no spot prices: the HA sensor (CZK/MWh) fills them."""
    from homeassistant.components.recorder.models import (
        StatisticData,
        StatisticMeanType,
        StatisticMetaData,
    )
    from homeassistant.components.recorder.statistics import async_import_statistics

    await hass.config.async_set_time_zone("Europe/Prague")
    today = date(2026, 11, 13)
    freezer.move_to(datetime(2026, 11, 13, 12, 0, tzinfo=grid.TZ))
    hass.states.async_set("sensor.spot", "3000", {"unit_of_measurement": "CZK/MWh"})
    start = grid.local_midnight(date(2026, 11, 10)).astimezone(UTC)
    async_import_statistics(
        hass,
        StatisticMetaData(
            source="recorder",
            statistic_id="sensor.spot",
            name="spot",
            unit_of_measurement="CZK/MWh",
            unit_class=None,
            has_sum=False,
            mean_type=StatisticMeanType.ARITHMETIC,
        ),
        [
            StatisticData(start=start + timedelta(hours=i), mean=3000.0, min=3000.0, max=3000.0)
            for i in range(72)
        ],
    )

    def handler(path: str, params: dict[str, str]) -> Any:
        if path.endswith("profile-data"):
            frm = datetime.fromisoformat(
                params["profileReadingDatetimeFrom"].replace("Z", "+00:00")
            )
            day = frm.astimezone(grid.TZ).date()
            if day >= today:
                return []
            return _profile(day, (today - day).days, 0.5)
        raise api.CezConnectionError("HTTP 404")

    statistics.REQUEST_PAUSE = 0
    cache = {"uid": pv_sp.uid, "export_from": "2026-11-10", "export": {"2026-11-10": 48.0}}
    await statistics.async_update_statistics(
        hass, FakeClient(handler), [pv_sp], {pv_sp.place_id: cache}, "sensor.spot"
    )
    assert cache["valuation"]["2026-11"]["kwh"] == pytest.approx(144.0)
    assert cache["valuation"]["2026-11"]["value"] == pytest.approx(432.0)
    assert cache["spot_yesterday"]["average"] == pytest.approx(3.0)
    # Without the sensor nothing can be valued.
    cache2 = {"uid": pv_sp.uid, "export_from": "2026-11-10"}
    await statistics.async_update_statistics(
        hass, FakeClient(handler), [pv_sp], {pv_sp.place_id: cache2}
    )
    assert cache2.get("valuation") in (None, {})


async def test_spot_prices_from_ote_fill_missing_days(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    pv_sp: api.SupplyPoint,
    freezer: FrozenDateTimeFactory,
    fake_ote: type[FakeOte],
) -> None:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(datetime(2026, 11, 13, 12, 0, tzinfo=grid.TZ))
    fake_ote.PRICES = {date(2026, 11, d): float(d) for d in (10, 11, 12)}
    client = FakeClient(lambda p, q: (_ for _ in ()).throw(api.CezConnectionError("HTTP 404")))
    statistics.REQUEST_PAUSE = 0
    prices = await statistics.async_import_spot_prices(
        hass, client, date(2026, 11, 10), date(2026, 11, 13)
    )
    assert len(prices) == 72
    await async_wait_recording_done(hass)
    rows = await _stats(hass, statistics.SPOT_STATISTIC_ID, {"mean"})
    assert len(rows) == 72
    assert rows[-1]["mean"] == pytest.approx(12.0)
    # Complete days are not requested again; nothing is missing.
    fake_ote.calls.clear()
    assert (
        await statistics.async_import_spot_prices(
            hass, client, date(2026, 11, 10), date(2026, 11, 13)
        )
        == {}
    )
    assert fake_ote.calls == []
    # A day with missing hours is fetched again and completed.
    fake_ote.PRICES[date(2026, 11, 13)] = 13.0
    freezer.move_to(datetime(2026, 11, 14, 12, 0, tzinfo=grid.TZ))
    prices = await statistics.async_import_spot_prices(
        hass, client, date(2026, 11, 10), date(2026, 11, 14)
    )
    assert fake_ote.calls == [date(2026, 11, 13)]
    assert len(prices) == 24


def test_spot_overview() -> None:
    today = date(2026, 11, 17)
    prices = {}
    for d in range(20):
        day = today - timedelta(days=20 - d)
        start = grid.local_midnight(day).astimezone(UTC)
        for h in range(statistics.expected_hours(day)):
            prices[start + timedelta(hours=h)] = float(h) + (0.5 if d % 2 else 0.0)
    ov = statistics.spot_overview(prices, today)
    assert [m["month"] for m in ov["months"]] == ["2026-10", "2026-11"]
    assert len(ov["days"]) == 14
    assert ov["days"][-1]["date"] == "2026-11-16"
    assert ov["days"][-1]["min"] == pytest.approx(0.5)
    assert len(ov["profile"]) == 24
    # Hour 5 over the last 7 days: 5 or 5.5 alternating.
    assert 5.0 <= ov["profile"][5] <= 5.5
    assert statistics.spot_overview({}, today)["profile"] == [None] * 24


async def test_missing_hours_imported_again(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    pv_sp: api.SupplyPoint,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Statistics of older versions with a lost day are filled once, later sums corrected."""
    await hass.config.async_set_time_zone("Europe/Prague")
    today = date(2026, 11, 13)
    freezer.move_to(datetime(2026, 11, 13, 12, 0, tzinfo=grid.TZ))
    stat_id = statistics.statistic_id("import", pv_sp.place_id)
    meta = statistics.StatisticMetaData(
        source=statistics.DOMAIN,
        statistic_id=stat_id,
        name="import",
        unit_of_measurement="kWh",
        unit_class="energy",
        has_sum=True,
        mean_type=statistics.StatisticMeanType.NONE,
    )
    hours = sorted(grid.parse_profile(_profile(date(2026, 11, 9), 4, 0.25)))
    lost = {h for h in hours if h.astimezone(grid.TZ).date() == date(2026, 11, 10)}
    rows, total = [], 0.0
    for h in hours:
        if h not in lost:
            total += 1.0
            rows.append(statistics.StatisticData(start=h, state=1.0, sum=total))
    statistics.async_add_external_statistics(hass, meta, rows)
    await async_wait_recording_done(hass)

    def handler(path: str, params: dict[str, str]) -> Any:
        if path.endswith("profile-data") and params["profileReadingRoleId"] == grid.PROFILE_IMPORT:
            frm = datetime.fromisoformat(
                params["profileReadingDatetimeFrom"].replace("Z", "+00:00")
            )
            day = frm.astimezone(grid.TZ).date()
            return _profile(day, (today - day).days, 0.25) if day < today else []
        raise api.CezConnectionError("HTTP 404")

    client = FakeClient(handler)
    cache = {"uid": pv_sp.uid, "import_from": "2026-11-09", "import": {"2026-11-09": 24.0}}
    statistics.REQUEST_PAUSE = 0
    assert await statistics.async_update_statistics(hass, client, [pv_sp], {pv_sp.place_id: cache})
    await async_wait_recording_done(hass)
    stats = await _stats(hass, stat_id, {"sum"})
    assert len(stats) == 96 and stats[-1]["sum"] == pytest.approx(96.0)
    assert cache["import_gaps_checked"] == statistics.GAPS_CHECK_VERSION

    # Checked once: no history requests on the next run.
    client.calls.clear()
    await statistics.async_update_statistics(hass, client, [pv_sp], {pv_sp.place_id: cache})
    assert not [c for c in client.calls if c[0].endswith("profile-data")]
