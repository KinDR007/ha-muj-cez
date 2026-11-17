"""HDO from the ČEZ Distribuce portal: schedule parsing, tariff state and sensors."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.muj_cez import api, distribuce
from custom_components.muj_cez.const import CONF_HDO, DOMAIN
from custom_components.muj_cez.distribuce import HIGH, LOW, TZ, hdo_state, parse_signals

from .conftest import PASSWORD, USERNAME, FakeDip, load, sample_data


def at(day: int, hour: int, minute: int = 0, month: int = 11) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=TZ)


@pytest.fixture
def schedule() -> dict:
    parsed = parse_signals(load("dip_signals.json"))
    assert parsed
    return parsed


def test_parse_signals(schedule: dict) -> None:
    assert schedule["signal"] == "EVV3"
    assert schedule["signals"] == ["EVV3", "EVV8"]  # the second signal is not the tariff
    assert len(schedule["days"]) == 7
    assert schedule["days"]["2026-11-17"][0] == ["00:00", "10:00"]
    assert schedule["days"]["2026-11-18"] == [["22:00", "24:00"]]
    assert parse_signals(None) is None
    assert parse_signals({"signals": []}) is None
    assert parse_signals({"signals": [{"signal": "A", "datum": "bad", "casy": "1-2"}]}) is None


@pytest.mark.parametrize(
    ("now", "tariff", "switch"),
    [
        (at(17, 9), LOW, at(17, 10)),
        (at(17, 10, 30), HIGH, at(17, 11)),
        (at(17, 17, 59), HIGH, at(17, 18)),
        # 17th ends low at 24:00, the 18th starts high
        (at(17, 23), LOW, at(18, 0)),
        (at(18, 12), HIGH, at(18, 22)),
        # 18th 22:00-24:00 joins 19th 00:00-06:00 across midnight
        (at(18, 23), LOW, at(19, 6)),
        (at(19, 0, 30), LOW, at(19, 6)),
        # last day: the window runs to the end of the schedule, next switch unknown
        (at(23, 23), LOW, None),
    ],
)
def test_hdo_state(schedule: dict, now: datetime, tariff: str, switch: datetime | None) -> None:
    state = hdo_state(schedule, now)
    assert state is not None
    assert state["tariff"] == tariff
    assert state["next_switch"] == switch


def test_hdo_state_attributes_and_bounds(schedule: dict) -> None:
    state = hdo_state(schedule, at(17, 9))
    assert state
    assert state["low_hours_today"] == 20
    assert state["today"][0] == "00:00-10:00"
    assert state["tomorrow"] == ["22:00-24:00"]
    assert state["schedule_until"] == "2026-11-23"
    assert hdo_state(schedule, at(16, 23)) is None  # before the schedule
    assert hdo_state(schedule, at(24, 0)) is None  # after it
    assert hdo_state(None, at(17, 9)) is None


def test_dst_day_has_25_hours() -> None:
    sched = {"signal": "A", "days": {"2026-10-25": [["00:00", "24:00"]]}}
    state = hdo_state(sched, datetime(2026, 10, 25, 12, tzinfo=TZ))
    assert state and state["low_hours_today"] == 25
    assert state["next_switch"] is None


def test_prune_and_merge(schedule: dict) -> None:
    pruned = distribuce.prune(schedule, date(2026, 11, 20))
    assert min(pruned["days"]) == "2026-11-19"
    new = {"signal": "EVV3", "signals": ["EVV3"], "days": {"2026-11-24": [["00:00", "08:00"]]}}
    merged = distribuce.merge(pruned, new)
    assert list(merged["days"])[-1] == "2026-11-24" and "2026-11-19" in merged["days"]
    assert merged["signals"] == ["EVV3"]


def test_choose_environment() -> None:
    data = {
        "environments": [
            {"environmentId": "P", "partners": [{"partnerId": "2"}]},
            {
                "environmentId": "D",
                "selectedPartnerId": "4",
                "partners": [{"partnerId": "3"}, {"partnerId": "4"}],
            },
        ]
    }
    assert distribuce.choose_environment(data) == ("D", "4")
    with pytest.raises(distribuce.DipError):
        distribuce.choose_environment({"environments": []})


def test_execution_token() -> None:
    html = '<input type="hidden" name="execution" value="e1s1-abc"/>'
    match = distribuce._EXECUTION.search(html)
    assert match and (match.group(1) or match.group(2)) == "e1s1-abc"


def test_unit_prices_latest_item() -> None:
    def item(kind: str, mwh: float, amount: float, end: str) -> dict:
        return {
            "invoiceItemType": f"Zúčtování spotřeby {kind}",
            "invoiceItemConsumption": mwh,
            "invoiceItemAmountWithTax": amount,
            "invoiceItemPeriodTo": end,
        }

    items = [
        item("VT", 0.1, 500.0, "2026-06-30"),
        item("VT", 0.1, 420.0, "2026-10-31"),  # price change: the latest wins
        item("NT", 0.0, 0.0, "2026-11-30"),  # no consumption, ignored
        item("NT", 0.2, 680.0, "2026-10-31"),
        {"invoiceItemType": "Zúčtování stálého platu EE", "invoiceItemAmountWithTax": 300.0},
    ]
    assert api.parse_unit_prices(items) == {"VT": 4.2, "NT": 3.4}
    assert api.parse_simulation(load("simulation.json")).unit_prices == {"VT": 5.733}


# ---------------------------------------------------------------------------
# Home Assistant
# ---------------------------------------------------------------------------


async def _setup(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, options: dict | None = None
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(at(17, 9, 30))
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options=options or {},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _entity(hass: HomeAssistant, key: str) -> str | None:
    uid = next(iter(sample_data().supply_points))
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{uid}_{key}")


async def test_hdo_sensors_switch_without_refresh(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    fake_dip: type[FakeDip],
    freezer: FrozenDateTimeFactory,
) -> None:
    data = sample_data()
    next(iter(data.supply_points.values())).simulation.unit_prices = {"VT": 4.24, "NT": 3.43}
    mock_client.fetch_all.return_value = data
    fake_dip.signals_data = {"*": load("dip_signals.json")}
    await _setup(hass, freezer)

    tariff, switch, price = (
        _entity(hass, k) for k in ("hdo_tariff", "hdo_next_switch", "current_price")
    )
    assert tariff and switch and price
    assert hass.states.get(tariff).state == LOW
    assert hass.states.get(tariff).attributes["signal"] == "EVV3"
    assert hass.states.get(price).state == "3.43"
    assert dt_util.parse_datetime(hass.states.get(switch).state) == at(17, 10)

    # Crossing the switch updates the state without a coordinator refresh.
    calls = mock_client.fetch_all.await_count
    freezer.move_to(at(17, 10, 0) + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert mock_client.fetch_all.await_count == calls
    assert hass.states.get(tariff).state == HIGH
    assert hass.states.get(price).state == "4.24"
    assert dt_util.parse_datetime(hass.states.get(switch).state) == at(17, 11)


async def test_hdo_survives_portal_failure(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    fake_dip: type[FakeDip],
    freezer: FrozenDateTimeFactory,
) -> None:
    fake_dip.signals_data = {"*": load("dip_signals.json")}
    entry = await _setup(hass, freezer)
    assert _entity(hass, "hdo_tariff")
    # The stored schedule is used when the portal fails on the next run.
    fake_dip.error = distribuce.DipError("down")
    coordinator = entry.runtime_data
    await coordinator.async_update_hdo(coordinator.data, force=True)
    assert coordinator.data.hdo and fake_dip.calls == 2


async def test_no_hdo_entities_without_schedule(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    fake_dip: type[FakeDip],
    freezer: FrozenDateTimeFactory,
) -> None:
    fake_dip.error = distribuce.DipAuthError("rejected")
    await _setup(hass, freezer)
    assert _entity(hass, "hdo_tariff") is None
    # Single tariff price is known from the simulation even without HDO.
    price = _entity(hass, "current_price")
    assert price and hass.states.get(price).state == "5.733"


async def test_hdo_disabled(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    fake_dip: type[FakeDip],
    freezer: FrozenDateTimeFactory,
) -> None:
    fake_dip.signals_data = {"*": load("dip_signals.json")}
    await _setup(hass, freezer, {CONF_HDO: False})
    assert fake_dip.calls == 0
    assert _entity(hass, "hdo_tariff") is None
