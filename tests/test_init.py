"""Setup, sensors and scheduling tests."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.muj_cez.api import CezAuthError, CezConnectionError
from custom_components.muj_cez.const import (
    CONF_UPDATE_PERIOD,
    CONF_UPDATE_TIME,
    DOMAIN,
    RETRY_COUNT,
    RETRY_DELAY,
)

from .conftest import PASSWORD, UID, USERNAME

TZ = ZoneInfo("Europe/Prague")
# Monday
START = datetime(2026, 11, 16, 12, 0, tzinfo=TZ)


@pytest.fixture
async def entry(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(START)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _state(hass: HomeAssistant, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{UID}_{key}")
    assert entity_id, key
    return hass.states.get(entity_id).state


async def test_sensors(hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock) -> None:
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert _state(hass, "invoice_balance") == "-1947.99"
    assert _state(hass, "predicted_cost") == "14002.01"
    assert _state(hass, "recommended_advance") == "480.0"
    assert _state(hass, "current_advance") == "1450.0"
    assert _state(hass, "predicted_consumption") == "1821.99"
    assert _state(hass, "billing_period_end") == "2027-02-15"
    assert _state(hass, "next_advance_date") == "2026-11-16"
    assert _state(hass, "next_advance_amount") == "1450.0"
    assert _state(hass, "unpaid_advances") == "0.0"
    assert _state(hass, "last_period_consumption") == "1163.0"
    assert _state(hass, "last_period_cost") == "10764.77"
    assert _state(hass, "meter_reading") == "12882.0"
    assert _state(hass, "last_update") not in (STATE_UNKNOWN, None)
    assert _state(hass, "last_invoice") == "-4385.23"
    assert _state(hass, "last_payment") == "1450.0"
    assert _state(hass, "overdue_amount") == "0.0"
    assert _state(hass, "distribution_rate") == "D02d - Běžná domácnost bez topení a bojleru"
    assert _state(hass, "circuit_breaker") == "25.0"
    assert _state(hass, "contract_end") == "2027-07-16"
    assert _state(hass, "price_change_date") == "2027-07-17"
    assert _state(hass, "planned_outages") == "1"
    assert _state(hass, "ean") == "859100000000000001"
    assert _state(hass, "meter_number") == "1000000001"
    assert _state(hass, "contract_number") == "11111111"
    assert _state(hass, "customer_number") == "1"
    assert _state(hass, "product") == "E_ELE_REFIX_2"
    assert _state(hass, "billing_periods") == "4"
    periods = hass.states.get(
        er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{UID}_billing_periods")
    ).attributes["periods"]
    assert len(periods) == 5
    assert periods[-1]["predicted"] is True
    assert periods[-2]["settlement"] == -4385.23
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_unread_messages"
    )
    assert hass.states.get(entity_id).state == "2"
    attrs = hass.states.get(
        er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{UID}_next_advance_date")
    ).attributes
    assert attrs["variable_symbol"] == "1111111100"
    assert attrs["bank_account"] == "7770227/0100"

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_missing_parts_are_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    data = mock_client.fetch_all.return_value.supply_points
    data[UID].simulation = None
    data[UID].advance_plan = None
    data[UID].outages = None
    await _setup(hass, entry)
    assert _state(hass, "invoice_balance") == STATE_UNKNOWN
    assert _state(hass, "next_advance_date") == STATE_UNKNOWN
    assert _state(hass, "current_advance") == "1450.0"
    assert _state(hass, "customer_number") == STATE_UNKNOWN
    assert _state(hass, "planned_outages") == STATE_UNKNOWN


async def test_setup_not_ready(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    mock_client.fetch_all.side_effect = CezConnectionError("down")
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_auth_failed_starts_reauth(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    mock_client.fetch_all.side_effect = CezAuthError("bad")
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: datetime) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass, when)
    await hass.async_block_till_done()


async def test_daily_schedule(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock, freezer
) -> None:
    await _setup(hass, entry)
    assert mock_client.fetch_all.call_count == 1
    await _tick(hass, freezer, datetime(2026, 11, 16, 23, 59, 59, tzinfo=TZ))
    assert mock_client.fetch_all.call_count == 1
    await _tick(hass, freezer, datetime(2026, 11, 17, 0, 0, 0, tzinfo=TZ))
    assert mock_client.fetch_all.call_count == 2
    await _tick(hass, freezer, datetime(2026, 11, 18, 0, 0, 0, tzinfo=TZ))
    assert mock_client.fetch_all.call_count == 3


async def test_weekly_schedule_custom_time(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock, freezer
) -> None:
    hass.config_entries.async_update_entry(
        entry, options={CONF_UPDATE_PERIOD: "weekly", CONF_UPDATE_TIME: "03:15:00"}
    )
    await _setup(hass, entry)
    for day in range(17, 23):  # Tue..Sun
        await _tick(hass, freezer, datetime(2026, 11, day, 3, 15, tzinfo=TZ))
    assert mock_client.fetch_all.call_count == 1
    await _tick(hass, freezer, datetime(2026, 11, 23, 3, 15, tzinfo=TZ))  # Monday
    assert mock_client.fetch_all.call_count == 2


async def test_monthly_schedule(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock, freezer
) -> None:
    hass.config_entries.async_update_entry(entry, options={CONF_UPDATE_PERIOD: "monthly"})
    await _setup(hass, entry)
    await _tick(hass, freezer, datetime(2026, 11, 30, 0, 0, tzinfo=TZ))
    assert mock_client.fetch_all.call_count == 1
    await _tick(hass, freezer, datetime(2026, 12, 1, 0, 0, tzinfo=TZ))
    assert mock_client.fetch_all.call_count == 2


async def test_failed_update_keeps_values_and_retries(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock, freezer
) -> None:
    await _setup(hass, entry)
    good = mock_client.fetch_all.return_value
    mock_client.fetch_all.side_effect = CezConnectionError("down")

    now = datetime(2026, 11, 17, 0, 0, tzinfo=TZ)
    await _tick(hass, freezer, now)
    assert mock_client.fetch_all.call_count == 2
    assert _state(hass, "invoice_balance") == "-1947.99"

    for i in range(RETRY_COUNT):
        now += RETRY_DELAY
        await _tick(hass, freezer, now)
        assert mock_client.fetch_all.call_count == 3 + i
    # Gives up after RETRY_COUNT retries.
    now += RETRY_DELAY
    await _tick(hass, freezer, now)
    assert mock_client.fetch_all.call_count == 2 + RETRY_COUNT

    # Next scheduled run succeeds again.
    mock_client.fetch_all.side_effect = None
    mock_client.fetch_all.return_value = good
    await _tick(hass, freezer, datetime(2026, 11, 18, 0, 0, tzinfo=TZ))
    assert mock_client.fetch_all.call_count == 3 + RETRY_COUNT


async def test_retry_succeeds(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock, freezer
) -> None:
    await _setup(hass, entry)
    good = mock_client.fetch_all.return_value
    mock_client.fetch_all.side_effect = [CezConnectionError("down"), good]
    now = datetime(2026, 11, 17, 0, 0, tzinfo=TZ)
    await _tick(hass, freezer, now)
    await _tick(hass, freezer, now + RETRY_DELAY)
    assert mock_client.fetch_all.call_count == 3
    await _tick(hass, freezer, now + RETRY_DELAY * 2)
    assert mock_client.fetch_all.call_count == 3


async def test_unload_cancels_schedule(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock, freezer
) -> None:
    await _setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await _tick(hass, freezer, datetime(2026, 11, 17, 0, 0, tzinfo=TZ) + timedelta(seconds=0))
    assert mock_client.fetch_all.call_count == 1


async def test_comparison_with_reference_sensor(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    from datetime import date as _date

    from homeassistant.helpers import entity_registry as _er

    hass.config_entries.async_update_entry(
        entry, options={"reference_sensor": "sensor.grid_import"}
    )
    daily = {_date(2026, 2, 18) + timedelta(days=i): 4.0 for i in range(272)}
    with patch(
        "custom_components.muj_cez.coordinator.async_get_daily_energy",
        return_value=daily,
    ) as get_daily:
        await _setup(hass, entry)
    assert get_daily.call_args.args[1] == "sensor.grid_import"
    assert get_daily.call_args.args[2] == _date(2022, 2, 22)
    entity_id = _er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{UID}_consumption_comparison"
    )
    state = hass.states.get(entity_id)
    # 272 days (2026-02-18 .. 2026-11-16) * 4 kWh vs 1284 kWh measured by ČEZ
    assert float(state.state) == round((272 * 4 - 1284) / 1284 * 100, 1)
    assert state.attributes["reference_sensor"] == "sensor.grid_import"
    assert state.attributes["periods"][-1]["predicted"] is True


async def test_comparison_statistics_error(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    hass.config_entries.async_update_entry(
        entry, options={"reference_sensor": "sensor.grid_import"}
    )
    with patch(
        "custom_components.muj_cez.coordinator.async_get_daily_energy",
        side_effect=RuntimeError("recorder down"),
    ):
        await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert _state(hass, "consumption_comparison") == STATE_UNKNOWN


async def test_chart_unit_select(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    from homeassistant.helpers import entity_registry as _er

    await _setup(hass, entry)
    entity_id = _er.async_get(hass).async_get_entity_id(
        "select", DOMAIN, f"{entry.entry_id}_chart_unit"
    )
    assert hass.states.get(entity_id).state == "kwh"
    await hass.services.async_call(
        "select", "select_option", {"entity_id": entity_id, "option": "czk"}, blocking=True
    )
    assert hass.states.get(entity_id).state == "czk"


async def test_low_tariff_meter_reading(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """Dual tariff: NT register as its own sensor; single tariff points do not get it."""
    from .conftest import sample_data

    data = sample_data()
    reading = next(iter(data.supply_points.values())).meter_reading
    assert reading and reading.value_lt is None
    reading.value_lt = 13160.0
    mock_client.fetch_all.return_value = data
    await _setup(hass, entry)
    assert _state(hass, "meter_reading_low") == "13160.0"
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{UID}_meter_reading_low")
    assert hass.states.get(entity_id).attributes["reading_date"] == reading.reading_date


async def test_no_low_tariff_sensor_single_tariff(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    await _setup(hass, entry)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{UID}_meter_reading") is not None
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{UID}_meter_reading_low") is None
